import hashlib
import json
import math
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy import func, or_
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    Booking,
    BookingAttempt,
    BookingRateLimitLock,
    IdempotencyRecord,
    Slot,
)
from app.schemas import BookingResponse, NewBooking
from app.security import require_api_key

router = APIRouter()


def enforce_booking_rate_limit(db: Session, email: str):
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(seconds=60)
    dialect = db.bind.dialect.name
    try:
        if dialect == "sqlite":
            statement = sqlite_insert(BookingRateLimitLock).values(
                email=email
            ).on_conflict_do_nothing(index_elements=["email"])
        elif dialect == "postgresql":
            statement = pg_insert(BookingRateLimitLock).values(
                email=email
            ).on_conflict_do_nothing(index_elements=["email"])
        else:
            raise RuntimeError(
                "Unsupported database for booking rate limiting."
            )
        db.execute(statement)
        db.query(BookingRateLimitLock).filter(
            BookingRateLimitLock.email == email
        ).with_for_update().first()
        attempts = (
            db.query(BookingAttempt)
            .filter(
                BookingAttempt.email == email,
                BookingAttempt.attempted_at >= window_start,
            )
            .order_by(BookingAttempt.attempted_at.asc())
            .all()
        )
        db.add(BookingAttempt(email=email, attempted_at=now))
        db.commit()
        if len(attempts) >= 5:
            oldest_attempt = attempts[0].attempted_at
            if oldest_attempt.tzinfo is None:
                oldest_attempt = oldest_attempt.replace(tzinfo=timezone.utc)
            retry_after = max(
                1,
                math.ceil(
                    60 - (now - oldest_attempt).total_seconds()
                ),
            )
            raise HTTPException(
                status_code=429,
                detail="Too many booking attempts. Please try again later.",
                headers={"Retry-After": str(retry_after)},
            )
    except HTTPException:
        raise
    except Exception:
        db.rollback()
        raise


@router.post(
    "/bookings",
    response_model=BookingResponse,
    status_code=201,
    dependencies=[Depends(require_api_key)],
)
def create_booking(
    payload: NewBooking,
    db: Session = Depends(get_db),
    idempotency_key: str | None = Header(
        default=None,
        alias="Idempotency-Key",
    ),
):
    name = payload.name.strip()
    email = str(payload.email).strip().lower()
    slot_id = payload.slot_id.strip()
    enforce_booking_rate_limit(db, email)
    if not slot_id or not name or not email:
        raise HTTPException(
            status_code=400,
            detail="Slot ID, name and email are required.",
        )

    request_body = payload.model_dump(mode="json")
    request_hash = hashlib.sha256(
        json.dumps(
            request_body,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()

    if idempotency_key is not None:
        existing_record = (
            db.query(IdempotencyRecord)
            .filter(IdempotencyRecord.key == idempotency_key)
            .first()
        )
        if existing_record is not None:
            if existing_record.request_hash != request_hash:
                raise HTTPException(
                    status_code=422,
                    detail="Idempotency key was used with a different request.",
                )
            return JSONResponse(
                content=existing_record.response_body,
                status_code=existing_record.status_code,
            )

    slot = db.query(Slot).filter(Slot.id == slot_id).first()
    if slot is None:
        raise HTTPException(
            status_code=404,
            detail="Appointment slot not found.",
        )

    slot_start = slot.start
    if slot_start.tzinfo is None:
        slot_start = slot_start.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    if slot_start <= now:
        raise HTTPException(
            status_code=400,
            detail="This appointment has already started.",
        )

    booking = Booking(
        id=str(uuid4()),
        slot_id=slot.id,
        name=name,
        email=email,
        status="confirmed",
        created_at=now,
    )
    db.add(booking)
    try:
        db.flush()
        response_body = BookingResponse.model_validate(booking).model_dump(
            mode="json"
        )
        if idempotency_key is not None:
            db.add(
                IdempotencyRecord(
                    key=idempotency_key,
                    request_hash=request_hash,
                    response_body=response_body,
                    status_code=201,
                )
            )
        db.commit()
    except IntegrityError:
        db.rollback()
        if idempotency_key is not None:
            existing_record = (
                db.query(IdempotencyRecord)
                .filter(IdempotencyRecord.key == idempotency_key)
                .first()
            )
            if existing_record is not None:
                if existing_record.request_hash != request_hash:
                    raise HTTPException(
                        status_code=422,
                        detail="Idempotency key was used with a different request.",
                    )
                return JSONResponse(
                    content=existing_record.response_body,
                    status_code=existing_record.status_code,
                )
        existing_booking = (
            db.query(Booking)
            .filter(
                Booking.slot_id == slot.id,
                Booking.status == "confirmed",
            )
            .first()
        )
        if existing_booking is not None:
            raise HTTPException(
                status_code=409,
                detail="This appointment slot is already booked.",
            )
        raise

    return response_body


@router.get(
    "/bookings/{booking_id}",
    response_model=BookingResponse,
    dependencies=[Depends(require_api_key)],
)
def get_booking(
    booking_id: str,
    db: Session = Depends(get_db),
):
    booking = (
        db.query(Booking)
        .filter(Booking.id == booking_id)
        .first()
    )
    if booking is None:
        raise HTTPException(
            status_code=404,
            detail="Booking not found.",
        )
    return booking


@router.get(
    "/bookings",
    dependencies=[Depends(require_api_key)],
)
def list_bookings(
    email: str = Query(...),
    limit: int = Query(default=10, ge=1, le=50),
    cursor: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    # Search using a case-insensitive email match.
    clean_email = email.strip().lower()

    if not clean_email:
        raise HTTPException(
            status_code=400,
            detail="Email is required.",
        )

    query = db.query(Booking).filter(
        func.lower(Booking.email) == clean_email
    )

    # If a cursor is supplied, find the previous page's last booking.
    if cursor is not None:
        last_booking = (
            db.query(Booking)
            .filter(
                Booking.id == cursor,
                func.lower(Booking.email) == clean_email,
            )
            .first()
        )

        if last_booking is None:
            raise HTTPException(
                status_code=400,
                detail="Invalid cursor.",
            )

        query = query.filter(
            or_(
                Booking.created_at > last_booking.created_at,
                (
                    (Booking.created_at == last_booking.created_at)
                    & (Booking.id > last_booking.id)
                ),
            )
        )

    # Retrieve one extra record to determine whether another page exists.
    bookings = (
        query.order_by(
            Booking.created_at.asc(),
            Booking.id.asc(),
        )
        .limit(limit + 1)
        .all()
    )

    has_more = len(bookings) > limit
    bookings = bookings[:limit]
    next_cursor = (
        bookings[-1].id
        if has_more and bookings
        else None
    )

    return {
        "bookings": bookings,
        "next_cursor": next_cursor,
    }


@router.delete(
    "/bookings/{booking_id}",
    response_model=BookingResponse,
    dependencies=[Depends(require_api_key)],
)
def cancel_booking(
    booking_id: str,
    db: Session = Depends(get_db),
):
    booking = (
        db.query(Booking)
        .filter(Booking.id == booking_id)
        .first()
    )
    if booking is None:
        raise HTTPException(
            status_code=404,
            detail="Booking not found.",
        )
    if booking.status == "cancelled":
        raise HTTPException(
            status_code=409,
            detail="This booking has already been cancelled.",
        )
    booking.status = "cancelled"
    db.commit()
    db.refresh(booking)
    return booking
