from fastapi import APIRouter, Depends, Query
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Booking, Slot
from app.schemas import ResetRequest, SlotWithAvailability
from app.security import require_api_key

router = APIRouter()


@router.post("/reset", dependencies=[Depends(require_api_key)])
def reset_slots(
    payload: ResetRequest,
    db: Session = Depends(get_db),
):
    db.execute(delete(Booking))
    db.execute(delete(Slot))

    for slot_data in payload.slots:
        db.add(
            Slot(
                id=slot_data.id,
                provider=slot_data.provider,
                start=slot_data.start,
                end=slot_data.end,
            )
        )

    db.commit()
    return {"message": "Done"}


@router.get(
    "/slots",
    response_model=dict[str, list[SlotWithAvailability]],
    dependencies=[Depends(require_api_key)],
)
def list_slots(
    provider: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    query = db.query(Slot)
    if provider is not None:
        query = query.filter(Slot.provider == provider)
    slots = query.order_by(Slot.start.asc()).all()

    confirmed_slot_ids = {
        slot_id
        for (slot_id,) in db.query(Booking.slot_id)
        .filter(Booking.status == "confirmed")
        .all()
    }

    return {
        "slots": [
            {
                "id": slot.id,
                "provider": slot.provider,
                "start": slot.start,
                "end": slot.end,
                "available": slot.id not in confirmed_slot_ids,
            }
            for slot in slots
        ]
    }
