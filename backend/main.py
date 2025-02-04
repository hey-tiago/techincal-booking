import re
from datetime import datetime, timedelta, time
import asyncio
import sys

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from tortoise import fields, models, Tortoise
from tortoise.contrib.fastapi import register_tortoise
from contextlib import asynccontextmanager

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# -------------------------------
# Security Imports and Setup
# -------------------------------
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import jwt
from jwt import PyJWTError
from passlib.context import CryptContext

SECRET_KEY = "your-secret-key"  # Replace with a secure secret key!
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
         status_code=401,
         detail="Could not validate credentials",
         headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except PyJWTError:
        raise credentials_exception
    user = await User.filter(username=username).first()
    if user is None:
        raise credentials_exception
    return user

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
            # These seed bookings are created without a user.
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
            "models": ["main"],
            "default_connection": "default",
            "routers": [],
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
# Models and Schemas
# -------------------------------

# User model
class User(models.Model):
    id = fields.IntField(pk=True)
    username = fields.CharField(max_length=50, unique=True)
    hashed_password = fields.CharField(max_length=128)
    bookings: fields.ReverseRelation["Booking"]

    def __str__(self):
        return self.username

# Booking model now linked to a User
class Booking(models.Model):
    id = fields.IntField(pk=True)
    technician_name = fields.CharField(max_length=100)
    service = fields.CharField(max_length=100)
    booking_datetime = fields.DatetimeField()
    user = fields.ForeignKeyField("models.User", related_name="bookings", null=True)

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

# User schemas
class UserCreate(BaseModel):
    username: str
    password: str

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
async def delete_booking(booking_id: int, current_user: User = Depends(get_current_user)):
    """Delete a booking by its ID (only if it belongs to the current user)."""
    booking = await Booking.filter(id=booking_id, user_id=current_user.id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found for the current user")
    await booking.delete()
    return {"detail": f"Booking ID {booking_id} cancelled"}

@app.post("/bookings", response_model=BookingOut)
async def schedule_booking(booking_in: BookingIn, current_user: User = Depends(get_current_user)):
    """
    Schedule a new booking for the authenticated user.
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
        user=current_user,
    )
    return booking

@app.get("/my-bookings", response_model=list[BookingOut])
async def my_bookings(current_user: User = Depends(get_current_user)):
    """List bookings for the current authenticated user."""
    return await Booking.filter(user_id=current_user.id)

# -------------------------------
# Authentication Endpoints
# -------------------------------
@app.post("/signup")
async def signup(user: UserCreate):
    existing = await User.filter(username=user.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already registered")
    hashed_password = get_password_hash(user.password)
    await User.create(username=user.username, hashed_password=hashed_password)
    return {"msg": "User created successfully"}

@app.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await User.filter(username=form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user.username}, expires_delta=access_token_expires)
    return {"access_token": access_token, "token_type": "bearer"}

# -------------------------------
# Chat / Natural Language Endpoint
# -------------------------------
# Additional action type for editing bookings
from enum import Enum
from typing import Optional, Dict, Any
from dataclasses import dataclass

class ActionType(str, Enum):
    NEW_BOOKING = "new_booking"
    CANCEL_BOOKING = "cancel_booking"
    GET_BOOKING_ID = "get_booking_id"
    EDIT_BOOKING = "edit_booking"

class BookingAction(BaseModel):
    action_type: ActionType
    booking_id: Optional[int] = None
    service: Optional[str] = None
    booking_datetime: Optional[datetime] = None
    technician_name: Optional[str] = None

@dataclass
class BookingDependencies:
    current_datetime: datetime
    business_hours_start: time = time(9, 0)  # 9 AM
    business_hours_end: time = time(17, 0)   # 5 PM

class BookingDetails(BaseModel):
    id: int
    service: str
    technician_name: str
    booking_datetime: datetime

    def format_datetime(self) -> str:
        return self.booking_datetime.strftime('%Y-%m-%d %I:%M%p')

class ChatResponse(BaseModel):
    message_type: str  # 'text', 'booking_details', 'error'
    text: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

from pydantic_ai import Agent

chat_agent = Agent(
    'openai:gpt-4o',
    result_type=BookingAction,
    deps_type=BookingDependencies,
    system_prompt="""
    You are a booking assistant for a technical services company.

    Business Rules:
    - Working hours are between 9:00 AM and 5:00 PM.
    - Bookings cannot be made in the past.
    - Each booking takes 1 hour.
    - All dates must be after the provided current_datetime.
    - When processing booking requests, use current_datetime from dependencies.
    - For new bookings (action_type: new_booking):
         - Extract the service type and validate the requested time.
         - Use the provided technician name if available.
    - For cancellations (action_type: cancel_booking):
         - Extract the booking ID.
    - For editing bookings (action_type: edit_booking):
         - Extract the booking ID and the new booking datetime.
    - For booking ID queries (action_type: get_booking_id):
         - Simply set the action type.
    """
)

async def process_message(message: str, current_user) -> ChatResponse:
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
                return ChatResponse(message_type="text", text="No booking ID provided in cancellation command.")
            booking = await Booking.filter(id=action.booking_id, user_id=current_user.id).first()
            if booking:
                await booking.delete()
                return ChatResponse(message_type="text", text=f"Booking ID {action.booking_id} cancelled")
            else:
                return ChatResponse(message_type="text", text=f"Booking ID {action.booking_id} not found for the current user")

        elif action.action_type == ActionType.GET_BOOKING_ID:
            booking = await Booking.filter(id=action.booking_id, user_id=current_user.id).first()
            if booking:
                return ChatResponse(
                    message_type="booking_details",
                    details={
                        "id": booking.id,
                        "service": booking.service,
                        "technician": booking.technician_name,
                        "datetime": booking.booking_datetime.strftime('%Y-%m-%d %I:%M%p')
                    }
                )
            return ChatResponse(message_type="text", text="No booking found with that ID.")

        elif action.action_type == ActionType.NEW_BOOKING:
            if not action.service or not action.booking_datetime:
                return ChatResponse(message_type="text", text="Could not determine service type or time for booking.")
            if action.booking_datetime < current_datetime:
                return ChatResponse(message_type="text", text=f"Bookings cannot be made in the past. Current time is {current_datetime.strftime('%d/%m/%Y %I:%M%p')}.")
            # Check for overlapping bookings
            conflict = await Booking.filter(
                technician_name=action.service,
                booking_datetime__gte=action.booking_datetime - timedelta(hours=1),
                booking_datetime__lt=action.booking_datetime + timedelta(hours=1)
            ).exists()
            if conflict:
                return ChatResponse(
                    message_type="text",
                    text=f"Time slot {action.booking_datetime.strftime('%d/%m/%Y %I:%M%p')} is not available for {action.service}."
                )
            booking = await Booking.create(
                technician_name=action.technician_name or action.service,
                service=action.service,
                booking_datetime=action.booking_datetime,
                user=current_user
            )
            return ChatResponse(
                message_type="booking_details",
                text="Booking confirmed:",
                details={
                    "id": booking.id,
                    "service": booking.service,
                    "technician": booking.technician_name,
                    "datetime": booking.booking_datetime.strftime('%Y-%m-%d %I:%M%p')
                }
            )

        elif action.action_type == ActionType.EDIT_BOOKING:
            if action.booking_id is None or action.booking_datetime is None:
                return ChatResponse(message_type="text", text="Missing booking ID or new datetime for editing.")
            booking = await Booking.filter(id=action.booking_id, user_id=current_user.id).first()
            if not booking:
                return ChatResponse(message_type="text", text=f"No booking found with ID {action.booking_id} for the current user.")
            if action.booking_datetime < current_datetime:
                return ChatResponse(message_type="text", text="Cannot set booking to a past time.")
            booking.booking_datetime = action.booking_datetime
            await booking.save()
            return ChatResponse(
                message_type="booking_details",
                text=f"Booking {booking.id} updated to {booking.booking_datetime.strftime('%d/%m/%Y %I:%M%p')}",
                details={
                    "id": booking.id,
                    "service": booking.service,
                    "technician": booking.technician_name,
                    "datetime": booking.booking_datetime.strftime('%Y-%m-%d %I:%M%p')
                }
            )

        else:
            return ChatResponse(message_type="text", text="Command not recognized.")
    except Exception as e:
        return ChatResponse(message_type="error", text=f"Sorry, I couldn't process that request: {str(e)}")

class ChatMessage(BaseModel):
    message: str

@app.post("/chat")
async def chat_endpoint(chat_message: ChatMessage, current_user: User = Depends(get_current_user)):
    response = await process_message(chat_message.message, current_user)
    return {"response": response}

# -------------------------------
# Console Application Interface (Optional)
# -------------------------------
async def run_console_async():
    await Tortoise.init(db_url="sqlite://bookings.db", modules={"models": ["__main__"]})
    await Tortoise.generate_schemas()
    await init_db()
    
    print("Technician Booking Console. Type your message or 'quit' to exit:")
    while True:
        user_input = input("> ")
        if user_input.lower() == "quit":
            break
        # For console testing, you might use a dummy current_user.
        dummy_user = await User.filter(username="dummy").first()
        if not dummy_user:
            dummy_user = await User.create(username="dummy", hashed_password=get_password_hash("dummy"))
        response = await process_message(user_input, dummy_user)
        print(response)
    
    await Tortoise.close_connections()

def run_console():
    asyncio.run(run_console_async())

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "console":
        run_console()
    else:
        import uvicorn
        uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)