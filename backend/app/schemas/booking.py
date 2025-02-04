from pydantic import BaseModel
from datetime import datetime

class BookingIn(BaseModel):
    technician_name: str
    service: str
    booking_datetime: datetime

class BookingOut(BaseModel):
    id: int
    technician_name: str
    service: str
    booking_datetime: datetime

    class Config:
        from_attributes = True 