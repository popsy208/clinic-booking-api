from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Slot(Base):
    __tablename__ = "slots"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    provider: Mapped[str] = mapped_column(String, nullable=False)
    start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class Booking(Base):
    __tablename__ = "bookings"
    __table_args__ = (
        Index(
            "uq_bookings_confirmed_slot",
            "slot_id",
            unique=True,
            sqlite_where=text("status = 'confirmed'"),
            postgresql_where=text("status = 'confirmed'"),
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    slot_id: Mapped[str] = mapped_column(
        String, ForeignKey("slots.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(
        String, nullable=False, default="confirmed"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


class IdempotencyRecord(Base):
    __tablename__ = "idempotency_records"

    key: Mapped[str] = mapped_column(
        String(255),
        primary_key=True,
    )
    request_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    response_body: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
    )
    status_code: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )


class BookingAttempt(Base):
    __tablename__ = "booking_attempts"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    attempted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_booking_attempts_email_time", "email", "attempted_at"),
    )


class BookingRateLimitLock(Base):
    __tablename__ = "booking_rate_limit_locks"

    email: Mapped[str] = mapped_column(String(320), primary_key=True)
