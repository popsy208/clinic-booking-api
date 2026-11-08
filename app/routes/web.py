from fastapi import APIRouter, Depends, Header
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import NewBooking
from app.routes.slots import list_slots
from app.routes.bookings import create_booking

router = APIRouter()


@router.get("/web/slots")
def web_list_slots(db: Session = Depends(get_db)):
    return list_slots(provider=None, db=db)


@router.post("/web/bookings", status_code=201)
def web_create_booking(
    payload: NewBooking,
    db: Session = Depends(get_db),
    idempotency_key: str | None = Header(
        default=None,
        alias="Idempotency-Key",
    ),
):
    result = create_booking(
        payload=payload,
        db=db,
        idempotency_key=idempotency_key,
    )

    if isinstance(result, JSONResponse):
        return result

    return JSONResponse(status_code=201, content=result)
