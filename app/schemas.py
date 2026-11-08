from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class SlotInput(BaseModel):
    id: str
    provider: str
    start: datetime
    end: datetime


class ResetRequest(BaseModel):
    slots: list[SlotInput]


class SlotResponse(BaseModel):
    id: str
    provider: str
    start: datetime
    end: datetime


class SlotWithAvailability(SlotResponse):
    available: bool


class NewBooking(BaseModel):
    slot_id: str
    name: str
    email: EmailStr


class BookingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    slot_id: str
    name: str
    email: str
    status: str
    created_at: datetime
