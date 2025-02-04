import re
from datetime import datetime, timedelta, time
import asyncio
import sys

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from tortoise import fields, models, Tortoise
from tortoise.contrib.fastapi import register_tortoise
from contextlib import asynccontextmanager

# Load environment variables from .env file
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# -------------------------------
# Database Initialization and Seeding
# -------------------------------
async def init_db():
    """
    Seed the database with initial booking data if none exist.
    """
    # Wait until Tortoise ORM is ready.
    if not await Booking.all().exists():
        try:
            dt1 = datetime.strptime("15/10/2022 10:00AM", "%d/%m/%Y %I:%M%p")
            dt2 = datetime.strptime("16/10/2022 6:00PM", "%d/%m/%Y %I:%M%p")
            dt3 = datetime.strptime("18/10/2022 11:00AM", "%d/%m/%Y %I:%M%p")
            await Booking.create(
                technician_name="Nicolas Woollett", service="Plumber", booking_datetime=dt1
            )
            await Booking.create(
                technician_name="Franky Flay", service="Electrician", booking_datetime=dt2
            )
            await Booking.create(
                technician_name="Griselda Dickson", service="Welder", booking_datetime=dt3
            )
            print("Database seeded with initial booking data.")
        except Exception as e:
            print(f"Error seeding database: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

app = FastAPI(title="Technician Booking System", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------
# Tortoise config
# -------------------------------
config = {
    "connections": {"default": "sqlite://bookings.db"},
    "apps": {
        "models": {
            "models": ["main"],  # Adjust this if your models are in another module
            "default_connection": "default",
            "routers": [],  # Explicitly provide an empty list
        }
    },
}

register_tortoise(
    app,
    config=config,
    generate_schemas=True,
    add_exception_handlers=True,
)

# -------------------------------
# Tortoise ORM Model and Schemas
# -------------------------------
class Booking(models.Model):
    id = fields.IntField(pk=True)
    technician_name = fields.CharField(max_length=100)
    service = fields.CharField(max_length=100)
    booking_datetime = fields.DatetimeField()

    def __str__(self):
        return (
            f"Booking(id={self.id}, technician={self.technician_name}, "
            f"service={self.service}, datetime={self.booking_datetime})"
        )

    class Meta:
        table = "booking"

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

# -------------------------------
# API Endpoints for Bookings
# -------------------------------
@app.get("/bookings", response_model=list[BookingOut])
async def list_bookings():
    """List all bookings."""
    return await Booking.all()

@app.get("/bookings/{booking_id}", response_model=BookingOut)
async def get_booking(booking_id: int):
    """Retrieve a booking by its ID."""
    booking = await Booking.filter(id=booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    return booking

@app.delete("/bookings/{booking_id}")
async def delete_booking(booking_id: int):
    """Delete a booking by its ID."""
    booking = await Booking.filter(id=booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    await booking.delete()
    return {"detail": f"Booking ID {booking_id} cancelled"}

@app.post("/bookings", response_model=BookingOut)
async def schedule_booking(booking_in: BookingIn):
    """
    Schedule a new booking.
    Checks that the same technician is not already booked at the same time.
    (A booking is assumed to last one hour.)
    """
    conflict = await Booking.filter(
        technician_name=booking_in.technician_name,
        booking_datetime=booking_in.booking_datetime,
    ).exists()
    if conflict:
        raise HTTPException(
            status_code=400,
            detail=f"Technician {booking_in.technician_name} is already booked at "
                   f"{booking_in.booking_datetime.strftime('%d/%m/%Y %I:%M%p')}",
        )
    booking = await Booking.create(
        technician_name=booking_in.technician_name,
        service=booking_in.service,
        booking_datetime=booking_in.booking_datetime,
    )
    return booking

# -------------------------------
# Natural Language "Chat" Endpoint
# -------------------------------
class ChatMessage(BaseModel):
    message: str

@app.post("/chat")
async def chat_endpoint(chat_message: ChatMessage):
    """
    Process a natural language message and perform the appropriate booking action.
    """
    response = await process_message(chat_message.message)
    return {"response": response}

from pydantic_ai import Agent
from datetime import datetime, timedelta, time
from enum import Enum

class ActionType(str, Enum):
    NEW_BOOKING = "new_booking"
    CANCEL_BOOKING = "cancel_booking"
    GET_BOOKING_ID = "get_booking_id"

from typing import Optional


class BookingAction(BaseModel):
    action_type: ActionType
    booking_id: Optional[int] = None
    service: Optional[str] = None
    booking_datetime: Optional[datetime] = None
    technician_name: Optional[str] = None

from dataclasses import dataclass
@dataclass
class BookingDependencies:
    current_datetime: datetime
    business_hours_start: time = time(9, 0)  # 9 AM
    business_hours_end: time = time(17, 0)   # 5 PM

chat_agent = Agent(
    'openai:gpt-4o',
    result_type=BookingAction,
    deps_type=BookingDependencies,
     system_prompt="""
    You are a booking assistant for a technical services company.
    
    Business Rules:
    - Working hours are between 9:00 AM and 5:00 PM
    - Bookings cannot be made in the past
    - Each booking takes 1 hour
    - You MUST use the current_datetime from the dependencies to validate dates
    - All dates MUST be after the current_datetime provided
    
    When processing booking requests:
    1. First check the current_datetime from dependencies
    2. All bookings must be after this current_datetime
    3. Validate the requested time is during working hours (9 AM - 5 PM)
    4. If date is not specified:
       - If the requested time is available today after current_datetime, use today
       - If not available today or time has passed, use next available day
    5. If only time is specified:
       - If it's before the time today and within working hours, use today
       - If the time has passed today, use tomorrow
    
    IMPORTANT: Always validate against current_datetime from dependencies, not any hardcoded date.
    
    For new bookings (action_type: new_booking):
    - Extract the service type (plumber, electrician, etc.)
    - Extract and validate the booking time and date against current_datetime
    - Extract the technician name if provided
    - Return null for booking_datetime if the requested time is invalid or in the past
    
    For cancellations (action_type: cancel_booking):
    - Extract the booking ID number
    
    For booking ID queries (action_type: get_booking_id):
    - Simply set the action type
    """
)

async def process_message(message: str) -> str:
    """
    Process natural language instructions using PydanticAI.
    """
    try:
        
        current_datetime = datetime.now()
        deps = BookingDependencies(current_datetime)
        message_with_time = f"Current date and time is: {current_datetime.strftime('%Y-%m-%d %H:%M:%S')}. User request: {message}"


        result = await chat_agent.run(message_with_time, deps=deps)
        action = result.data

        if action.action_type == ActionType.CANCEL_BOOKING:
            if action.booking_id is None:
                return "No booking ID provided in cancellation command."
            booking = await Booking.filter(id=action.booking_id).first()
            if booking:
                await booking.delete()
                return f"Booking ID {action.booking_id} cancelled"
            else:
                return f"Booking ID {action.booking_id} not found"

        elif action.action_type == ActionType.GET_BOOKING_ID:
            booking = await Booking.all().order_by("-id").first()
            if booking:
                return f"Your booking ID is {booking.id}"
            else:
                return "No bookings found."

        elif action.action_type == ActionType.NEW_BOOKING:
            if not action.service or not action.booking_datetime:
                return "Could not determine service type or time for booking."
                        # Validate booking is not in the past
            if action.booking_datetime < current_datetime:
                return f"Sorry, bookings cannot be made in the past. Current time is {current_datetime.strftime('%d/%m/%Y %I:%M%p')}."

            # Calculate the end time (1 hour after start)
            booking_end = action.booking_datetime + timedelta(hours=1)
            
            # Check for any overlapping bookings
            conflict = await Booking.filter(
                technician_name=action.service,
                booking_datetime__gte=action.booking_datetime - timedelta(hours=1),
                booking_datetime__lt=booking_end
            ).exists()
            
            if conflict:
                return (f"Time slot {action.booking_datetime.strftime('%d/%m/%Y %I:%M%p')} "
                        f"is not available for {action.service}. Each booking requires a 1-hour window.")

            booking = await Booking.create(
                technician_name=action.service,
                service=action.service,
                booking_datetime=action.booking_datetime,
            )
            return (f"Booking confirmed for {booking.booking_datetime.strftime('%d/%m/%Y %I:%M%p')} "
                    f"with booking ID {booking.id}")

    except Exception as e:
        return f"Sorry, I couldn't process that request: {str(e)}"

# -------------------------------
# Console Application Interface
# -------------------------------
async def run_console_async():
    # Initialize Tortoise ORM with the same config used in the FastAPI app
    await Tortoise.init(
        db_url="sqlite://bookings.db",
        modules={"models": ["__main__"]}
    )
    await Tortoise.generate_schemas()
    
    # Initialize the database with seed data if needed
    await init_db()
    
    print("Technician Booking Console. Type your message or 'quit' to exit:")
    while True:
        user_input = input("> ")
        if user_input.lower() == "quit":
            break
        response = await process_message(user_input)
        print(response)
    
    # Properly close connections when done
    await Tortoise.close_connections()

def run_console():
    asyncio.run(run_console_async())

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "console":
        run_console()
    else:
        import uvicorn
        uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)