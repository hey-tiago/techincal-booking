from datetime import datetime, time, timedelta
from enum import Enum
from typing import Optional, Dict, Any
from dataclasses import dataclass
from pydantic import BaseModel
from pydantic_ai import Agent
from app.models.booking import Booking

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
    message_type: str
    text: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

chat_agent = Agent(
    'openai:gpt-4o',
    result_type=BookingAction,
    deps_type=BookingDependencies,
    system_prompt="""
    You are a booking action processor for a technical services company.
    Your ONLY job is to identify and extract booking-related actions when they EXACTLY match the specified patterns.
    If a request doesn't exactly match these patterns, return None for all fields.

    Action Types and Required Parameters:
    1. NEW_BOOKING (action_type: new_booking)
         Required: service AND booking_datetime
         Pattern: Must include both a specific service and a specific time
         Examples: 
         - "I want to book a maintenance for tomorrow at 2pm"
         - "Schedule repair service for next Monday at 10am"
    
    2. CANCEL_BOOKING (action_type: cancel_booking)
         Required: booking_id
         Pattern: Must explicitly mention canceling with a numeric ID
         Examples:
         - "cancel booking 123"
         - "cancel 123"
    
    3. EDIT_BOOKING (action_type: edit_booking)
         Required: booking_id AND booking_datetime
         Pattern: Must include both a booking ID and a new time
         Examples:
         - "change booking 123 to tomorrow at 3pm"
         - "reschedule booking 123 to next Monday"
    
    4. GET_BOOKING_ID (action_type: get_booking_id)
         Required: booking_id
         Pattern: Must explicitly request info about a numeric booking ID
         Examples:
         - "get booking id 123"
         - "show booking 123"
         - "what are the details for booking 123"

    If the input doesn't EXACTLY match these patterns or is missing required parameters,
    DO NOT assign an action_type. Return None for all fields instead.
    """
)

general_info_agent = Agent(
    'openai:gpt-4o',
    system_prompt="""
    You are a helpful booking assistant for a technical services company.
    You help users understand their bookings and company policies.
    
    Use the provided information to answer questions about:
    - Business hours (from dependencies)
    - User's existing bookings
    - General booking policies
    - Available services
    - Scheduling guidelines
    
    Always reference the current_datetime and business_hours from dependencies when discussing availability.
    When discussing bookings, use the provided booking information from the context.
    
    Be concise but informative in your responses.
    """
)

async def process_message(message: str, current_user) -> ChatResponse:
    try:
        print(f"Processing message: {message}")
        current_datetime = datetime.now()
        
        # Fetch user's bookings
        user_bookings = await Booking.filter(user_id=current_user.id).all()
        bookings_info = [
            {
                "id": b.id,
                "service": b.service,
                "technician": b.technician_name,
                "datetime": b.booking_datetime.strftime('%Y-%m-%d %I:%M%p')
            }
            for b in user_bookings
        ]
        
        deps = BookingDependencies(current_datetime)
        message_with_context = f"""Current date and time is: {current_datetime.strftime('%Y-%m-%d %H:%M:%S')}
User's bookings: {bookings_info}
User request: {message}"""

        try:
            result = await chat_agent.run(message_with_context, deps=deps)
            action = result.data
            print(f"Action: {action}")

            if action and action.action_type:
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

        except Exception as validation_error:
            print(f"Validation error or no action matched, falling back to general info: {validation_error}")
            # Fall back to general info agent for non-action queries
            general_response = await general_info_agent.run(
                message_with_context,
                deps=deps
            )
            return ChatResponse(message_type="markdown", text=str(general_response.data))

    except Exception as e:
        return ChatResponse(message_type="error", text=f"Sorry, I couldn't process that request: {str(e)}") 