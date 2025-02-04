import logging
from datetime import datetime, time, timedelta
from enum import Enum
from typing import Optional, Dict, Any, List, Union
from dataclasses import dataclass, field
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse
from app.models.booking import Booking
import json
from pydantic_graph import BaseNode, End, Graph, GraphRunContext

# ---------------------------------------------------------------------------
# Logging Configuration
# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Add a console handler if not already present
if not logger.handlers:
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s - %(filename)s - %(lineno)d')
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

# ---------------------------------------------------------------------------
# Pydantic Models and Enums
# ---------------------------------------------------------------------------

# For routing decisions.
class RoutingTarget(str, Enum):
    BOOKING = "booking"
    GENERAL = "general"
    CLARIFICATION = "clarification"

class RoutingDecision(BaseModel):
    target: RoutingTarget
    clarifying_question: Optional[str] = None
    confidence: float = Field(ge=0, le=1, description="Confidence in the routing decision")
    missing_info: Optional[List[str]] = Field(default=None, description="List of missing information needed")

# For booking actions.
class ActionType(str, Enum):
    NEW_BOOKING = "new_booking"
    CANCEL_BOOKING = "cancel_booking"
    GET_BOOKING_ID = "get_booking_id"
    EDIT_BOOKING = "edit_booking"

class BookingAction(BaseModel):
    action_type: Optional[ActionType] = None
    booking_id: Optional[int] = None
    service: Optional[str] = None
    booking_datetime: Optional[datetime] = None
    technician_name: Optional[str] = None

@dataclass
class BookingDependencies:
    current_datetime: datetime
    business_hours_start: time = time(9, 0)  # 9 AM
    business_hours_end: time = time(17, 0)   # 5 PM

class ChatResponse(BaseModel):
    message_type: str
    text: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    conversation_history: Optional[List[Dict[str, Any]]] = None

    def model_dump(self, **kwargs) -> dict:
        """Custom serialization using Pydantic V2's model_dump"""
        return {
            "message_type": self.message_type,
            "text": self.text,
            "details": self.details,
            "conversation_history": self.conversation_history
        }

    def dict(self, **kwargs) -> dict:
        """Backwards compatibility for Pydantic v1"""
        return self.model_dump(**kwargs)

# ---------------------------------------------------------------------------
# Agent Definitions
# ---------------------------------------------------------------------------

# Update the router agent to be more specific about its decisions
class RouterDecision(BaseModel):
    """Router's decision about how to handle the user's request"""
    target: RoutingTarget
    confidence: float = Field(ge=0, le=1, description="Confidence in the routing decision")
    missing_info: Optional[List[str]] = Field(default=None, description="List of missing information needed")
    clarifying_question: Optional[str] = None

# Router agent with improved prompt and type safety
router_agent = Agent(
    'openai:gpt-4o',
    result_type=RoutingDecision,
    system_prompt="""
    You are an intelligent conversation router for a technical services booking system.
    Your job is to analyze the user's request and determine the appropriate handling path.
    
    When users ask about:
    - Business hours, services, policies -> route to "general"
    - Making/changing/canceling bookings -> route to "booking"
    - Unclear requests -> route to "clarification"
    
    NEVER echo back the user's message.
    ALWAYS analyze the intent and route appropriately.
    
    Return a RoutingDecision with:
    - target: booking, general, or clarification
    - confidence (0-1)
    - missing_info if required
    - clarifying_question if needed
    """
)

# Update BookingActionResult to include validation results
class BookingActionResult(BaseModel):
    action: BookingAction
    success: bool
    message: str
    validation_errors: Optional[List[str]] = None

# Update booking_agent with stricter time validation
booking_agent = Agent(
    'openai:gpt-4o',
    result_type=BookingActionResult,
    deps_type=BookingDependencies,
    system_prompt="""
    You are a booking processor for a technical services company.
    Extract booking details from the conversation and validate business rules.
    
    CRITICAL TIME HANDLING RULES:
    1. When a user mentions ONLY a date (e.g., "tomorrow", "next Monday") WITHOUT a specific time:
       - Set action_type to "new_booking"
       - Set service to the requested service
       - Set booking_datetime to None
       - Set success to False
       - Include a message asking for the specific time
       - NEVER assume a default time
    2. Time MUST be explicitly stated (e.g., "at 2 PM", "at 14:00")
    3. NEVER create a booking without an explicit time
    
    Business Rules:
    - Business hours: 9 AM to 5 PM only
    - Minimum 1 hour advance notice
    - Each service takes 1 hour
    - Available services: gardening, cleaning, maintenance
    
    Example responses:
    1. For "book gardening tomorrow":
      {
        "action": {
          "action_type": "new_booking",
          "service": "gardening",
          "booking_datetime": null
        },
        "success": false,
        "message": "What time would you like to book gardening for tomorrow? Our business hours are 9 AM to 5 PM."
      }
    
    2. For "book gardening tomorrow at 2pm":
      {
        "action": {
          "action_type": "new_booking",
          "service": "gardening",
          "booking_datetime": "2024-02-05 14:00:00"
        },
        "success": true,
        "message": "Checking availability for gardening tomorrow at 2 PM"
      }
    """
)

# First, create a result type for general info responses
class GeneralInfoResponse(BaseModel):
    """Response format for general inquiries"""
    response: str
    additional_details: Optional[Dict[str, Any]] = None

# Update general info agent with result type and clearer prompt
general_info_agent = Agent(
    'openai:gpt-4o',
    result_type=GeneralInfoResponse,
    system_prompt="""
    You are a helpful booking assistant for a technical services company.
    
    IMPORTANT BUSINESS INFORMATION:
    - Business hours: 9 AM to 5 PM
    - Available services: gardening, cleaning, maintenance
    - Each service takes 1 hour
    - Bookings require minimum 1 hour advance notice
    
    Your job is to:
    1. Provide clear, accurate information about our services and policies
    2. Use the conversation history and context for relevant responses
    3. Return responses in a structured format
    
    ALWAYS return a GeneralInfoResponse with:
    - response: Clear, user-friendly message
    - additional_details: Any relevant extra information (optional)
    
    Example response for "What are your working hours?":
    {
        "response": "Our business hours are from 9:00 AM to 5:00 PM. During these hours, we offer gardening, cleaning, and maintenance services.",
        "additional_details": {
            "business_hours": "9 AM - 5 PM",
            "services": ["gardening", "cleaning", "maintenance"]
        }
    }
    """
)

# Clarification agent: Asks follow-up questions when the intent is ambiguous.
clarification_agent = Agent(
    'openai:gpt-4o',
    system_prompt="""
    You are a helpful booking assistant that gathers missing information for service bookings.
    
    When responding to incomplete booking requests:
    1. Acknowledge the current booking information provided
    2. Ask for specific missing details
    3. Provide relevant information to help the user decide (e.g., available time slots, service options)
    
    Business hours are 9 AM to 5 PM.
    Services must be booked at least 1 hour in advance.
    Each service takes 1 hour.
    
    Example response for "I want gardening tomorrow":
    "I see you'd like to book gardening services for tomorrow. What time would you prefer? 
    Our available time slots for tomorrow are: 9 AM, 10 AM, 11 AM, 2 PM, and 3 PM."
    
    Always maintain a friendly and helpful tone.
    """
)

# ---------------------------------------------------------------------------
# Helper Functions for Booking Actions
# ---------------------------------------------------------------------------

async def handle_cancel_booking(action: BookingAction, current_user) -> ChatResponse:
    if action.booking_id is None:
        return ChatResponse(message_type="text", text="No booking ID provided in cancellation command.")
    booking = await Booking.filter(id=action.booking_id, user_id=current_user.id).first()
    if booking:
        await booking.delete()
        logger.info(f"Cancelled booking {action.booking_id} for user {current_user.id}")
        return ChatResponse(message_type="text", text=f"Booking ID {action.booking_id} cancelled.")
    else:
        return ChatResponse(message_type="text", text=f"Booking ID {action.booking_id} not found for the current user.")

async def handle_get_booking(action: BookingAction, current_user) -> ChatResponse:
    if action.booking_id is None:
        return ChatResponse(message_type="text", text="No booking ID provided for retrieving details.")
    booking = await Booking.filter(id=action.booking_id, user_id=current_user.id).first()
    if booking:
        details = {
            "id": booking.id,
            "service": booking.service,
            "technician": booking.technician_name,
            "datetime": booking.booking_datetime.strftime('%Y-%m-%d %I:%M %p')
        }
        return ChatResponse(message_type="booking_details", details=details)
    return ChatResponse(message_type="text", text="No booking found with that ID.")

async def handle_new_booking(
    action: BookingAction,
    current_user,
    current_datetime: datetime,
    deps: BookingDependencies
) -> ChatResponse:
    logger.info(f"[handle_new_booking] Validating booking request: {action.model_dump(exclude_none=True)}")
    
    # First check for existing bookings for this user on the same day
    if action.booking_datetime:
        start_of_day = action.booking_datetime.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)
        
        existing_bookings = await Booking.filter(
            user_id=current_user.id,
            service=action.service,
            booking_datetime__gte=start_of_day,
            booking_datetime__lt=end_of_day
        ).all()
        
        if existing_bookings:
            logger.warning(f"[handle_new_booking] User already has booking(s) for {action.service} on this day")
            existing_times = [b.booking_datetime.strftime('%I:%M %p') for b in existing_bookings]
            return ChatResponse(
                message_type="error",
                text=f"You already have {action.service} booking(s) for this day at: {', '.join(existing_times)}. "
                     f"Would you like to book for a different day or cancel an existing booking?"
            )

    if not action.service:
        logger.warning("[handle_new_booking] Missing service")
        return ChatResponse(
            message_type="error",
            text="Please specify which service you'd like to book (gardening, cleaning, or maintenance)."
        )

    if not action.booking_datetime:
        logger.info("[handle_new_booking] No booking time specified")
        return ChatResponse(
            message_type="clarification",
            text=f"What time would you like to book the {action.service} service? "
                 f"Please specify a time between {deps.business_hours_start.strftime('%I:%M %p')} "
                 f"and {deps.business_hours_end.strftime('%I:%M %p')}."
        )

    # Validate booking time is in the future
    if action.booking_datetime < current_datetime:
        logger.warning(f"[handle_new_booking] Attempted booking in the past: {action.booking_datetime}")
        return ChatResponse(
            message_type="error",
            text=f"Bookings cannot be made in the past. Current time is {current_datetime.strftime('%I:%M %p')}."
        )

    # Validate business hours
    booking_time = action.booking_datetime.time()
    if not (deps.business_hours_start <= booking_time <= deps.business_hours_end):
        logger.warning(f"[handle_new_booking] Attempted booking outside business hours: {booking_time}")
        return ChatResponse(
            message_type="error",
            text=f"Sorry, we can only accept bookings between "
                 f"{deps.business_hours_start.strftime('%I:%M %p')} and {deps.business_hours_end.strftime('%I:%M %p')}. "
                 f"Please choose a different time."
        )

    # Rest of the validation logic...
    resolved_technician = action.technician_name if action.technician_name else action.service
    conflict = await Booking.filter(
        technician_name=resolved_technician,
        booking_datetime__gte=action.booking_datetime - timedelta(hours=1),
        booking_datetime__lt=action.booking_datetime + timedelta(hours=1)
    ).exists()
    if conflict:
        return ChatResponse(
            message_type="text",
            text=f"Time slot {action.booking_datetime.strftime('%d/%m/%Y %I:%M %p')} is not available for {resolved_technician}."
        )
    booking = await Booking.create(
        technician_name=resolved_technician,
        service=action.service,
        booking_datetime=action.booking_datetime,
        user=current_user
    )
    details = {
        "id": booking.id,
        "service": booking.service,
        "technician": booking.technician_name,
        "datetime": booking.booking_datetime.strftime('%Y-%m-%d %I:%M %p')
    }
    logger.info(f"Created new booking {booking.id} for user {current_user.id}")
    return ChatResponse(message_type="booking_details", text="Booking confirmed:", details=details)

async def handle_edit_booking(
    action: BookingAction,
    current_user,
    current_datetime: datetime,
    deps: BookingDependencies
) -> ChatResponse:
    if action.booking_id is None or action.booking_datetime is None:
        return ChatResponse(message_type="text", text="Missing booking ID or new datetime for editing.")
    booking = await Booking.filter(id=action.booking_id, user_id=current_user.id).first()
    if not booking:
        return ChatResponse(message_type="text", text=f"No booking found with ID {action.booking_id} for the current user.")
    if action.booking_datetime < current_datetime:
        return ChatResponse(message_type="text", text="Cannot set booking to a past time.")
    booking_time = action.booking_datetime.time()
    if not (deps.business_hours_start <= booking_time <= deps.business_hours_end):
        return ChatResponse(
            message_type="text",
            text=f"New booking time {action.booking_datetime.strftime('%I:%M %p')} is outside business hours "
                 f"({deps.business_hours_start.strftime('%I:%M %p')} - {deps.business_hours_end.strftime('%I:%M %p')})."
        )
    conflict = await Booking.filter(
        technician_name=booking.technician_name,
        booking_datetime__gte=action.booking_datetime - timedelta(hours=1),
        booking_datetime__lt=action.booking_datetime + timedelta(hours=1)
    ).exclude(id=booking.id).exists()
    if conflict:
        return ChatResponse(
            message_type="text",
            text=f"Time slot {action.booking_datetime.strftime('%d/%m/%Y %I:%M %p')} is not available for {booking.technician_name}."
        )
    booking.booking_datetime = action.booking_datetime
    await booking.save()
    details = {
        "id": booking.id,
        "service": booking.service,
        "technician": booking.technician_name,
        "datetime": booking.booking_datetime.strftime('%Y-%m-%d %I:%M %p')
    }
    logger.info(f"Updated booking {booking.id} for user {current_user.id} to new datetime {action.booking_datetime}")
    return ChatResponse(
        message_type="booking_details",
        text=f"Booking {booking.id} updated to {booking.booking_datetime.strftime('%d/%m/%Y %I:%M %p')}",
        details=details
    )

# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

# Update handle_booking_action to actually create the booking
async def handle_booking_action(
    action: BookingAction,
    current_user,
    deps: BookingDependencies
) -> ChatResponse:
    logger.info(f"[handle_booking_action] Processing action: {action.model_dump(exclude_none=True)}")
    
    if action.action_type == ActionType.NEW_BOOKING:
        # Check for missing time
        if not action.booking_datetime:
            logger.info("[handle_booking_action] No explicit time provided")
            return ChatResponse(
                message_type="clarification",
                text=f"Please specify what time you'd like to book the {action.service} service. "
                     f"Our business hours are {deps.business_hours_start.strftime('%I:%M %p')} to "
                     f"{deps.business_hours_end.strftime('%I:%M %p')}."
            )

        # Check for existing bookings before proceeding
        start_of_day = action.booking_datetime.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)
        
        existing_booking = await Booking.filter(
            user_id=current_user.id,
            service=action.service,
            booking_datetime__gte=start_of_day,
            booking_datetime__lt=end_of_day
        ).first()
        
        if existing_booking:
            logger.warning(f"[handle_booking_action] Duplicate booking attempt detected")
            return ChatResponse(
                message_type="error",
                text=f"You already have a {action.service} booking on this day at "
                     f"{existing_booking.booking_datetime.strftime('%I:%M %p')}. "
                     f"Would you like to book for a different day or cancel the existing booking?"
            )

    if action.action_type == ActionType.NEW_BOOKING:
        if not all([action.service, action.booking_datetime]):
            return ChatResponse(
                message_type="error",
                text="Missing required booking information (service or time)."
            )
        try:
            # Check for booking conflicts
            existing_booking = await Booking.filter(
                booking_datetime=action.booking_datetime,
                service=action.service,
                user=current_user
            ).first()
            
            if existing_booking:
                return ChatResponse(
                    message_type="error", 
                    text=f"There is already a {action.service} booking at {action.booking_datetime.strftime('%I:%M %p')}. Please select a different time."
                )
            # Create the actual booking in your database
            booking = await Booking.create(
                user=current_user,
                service=action.service,
                booking_datetime=action.booking_datetime,
                technician_name=action.technician_name or action.service
            )
            return ChatResponse(
                message_type="booking_confirmed",
                text=f"Booking confirmed for {action.service} at {action.booking_datetime.strftime('%I:%M %p on %B %d, %Y')}.",
                details={
                    "booking_id": booking.id,
                    "service": booking.service,
                    "datetime": booking.booking_datetime.strftime('%Y-%m-%d %I:%M %p'),
                    "technician": booking.technician_name
                }
            )
        except Exception as e:
            logger.error(f"Booking creation failed: {e}")
            return ChatResponse(
                message_type="error",
                text="Sorry, there was an error creating your booking. Please try again."
            )
    elif action.action_type == ActionType.CANCEL_BOOKING:
        if action.booking_id is None:
            return ChatResponse(message_type="text", text="No booking ID provided in cancellation command.")
        booking = await Booking.filter(id=action.booking_id, user_id=current_user.id).first()
        if booking:
            await booking.delete()
            logger.info(f"Cancelled booking {action.booking_id} for user {current_user.id}")
            return ChatResponse(message_type="text", text=f"Booking ID {action.booking_id} cancelled.")
        return ChatResponse(message_type="text", text=f"No booking found with ID {action.booking_id}.")
    elif action.action_type == ActionType.GET_BOOKING_ID:
        if action.booking_id is None:
            return ChatResponse(message_type="text", text="No booking ID provided for retrieving details.")
        booking = await Booking.filter(id=action.booking_id, user_id=current_user.id).first()
        if booking:
            details = {
                "id": booking.id,
                "service": booking.service,
                "technician": booking.technician_name,
                "datetime": booking.booking_datetime.strftime('%Y-%m-%d %I:%M %p')
            }
            return ChatResponse(message_type="booking_details", details=details)
        return ChatResponse(message_type="text", text=f"Retrieving details for booking ID {action.booking_id}.")
    elif action.action_type == ActionType.EDIT_BOOKING:
        if action.booking_id is None:
            return ChatResponse(message_type="text", text="No booking ID provided for editing.")
        booking = await Booking.filter(id=action.booking_id, user_id=current_user.id).first()
        if not booking:
            return ChatResponse(message_type="text", text=f"No booking found with ID {action.booking_id}.")
        booking.service = action.service
        booking.technician_name = action.technician_name
        return ChatResponse(message_type="booking_details", text=f"Booking {action.booking_id} updated.")
    else:
        return ChatResponse(message_type="text", text="Unrecognized booking action.")

async def create_booking_context(current_user, current_datetime: datetime) -> str:
    # Here you would query your database for the user's bookings and available slots.
    user_bookings = [b.model_dump() for b in await Booking.filter(user_id=current_user.id).all()]
    all_bookings = [b.model_dump() for b in await Booking.filter(
        booking_datetime__gte=current_datetime,
        booking_datetime__lt=current_datetime + timedelta(days=7)
    ).all()]
    
    return (
        f"Current datetime: {current_datetime.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"User's existing bookings: {user_bookings}\n"
        f"All booked slots next 7 days: {all_bookings}"
    )

def extract_message_content(msg: ModelMessage) -> str:
    """
    Helper to extract a string of content from a ModelMessage.
    Assumes that the first part contains the main content.
    """
    if msg.parts and hasattr(msg.parts[0], "content"):
        return msg.parts[0].content
    return str(msg)

def safe_message_to_dict(msg: Any) -> Dict[str, Any]:
    """
    Safely convert a message to a dictionary.
    If the message has a .dict() method, use it. Otherwise, return a dictionary with its string representation.
    """
    if hasattr(msg, "dict"):
        try:
            return msg.dict()
        except Exception as e:
            logger.debug(f"Error converting msg with dict(): {e}")
    return {"content": str(msg)}

async def handle_general_inquiry(user_message: str, context_message: str, message_history: List[ModelMessage]) -> ChatResponse:
    """
    A helper method to process general inquiries by invoking the general_info_agent.
    """
    logger.info("[handle_general_inquiry] Calling general_info_agent")
    general_result = await general_info_agent.run(context_message, message_history=message_history)
    response_text = str(general_result.data)
    updated_history = general_result.all_messages()
    return ChatResponse(
        message_type="markdown",
        text=response_text,
        conversation_history=[safe_message_to_dict(msg) for msg in updated_history]
    )

# ---------------------------------------------------------------------------
# Graph & State Definitions for Conversation Flow
# ---------------------------------------------------------------------------

@dataclass
class ChatState:
    conversation_history: List[ModelMessage] = field(default_factory=list)
    user: Any = None  # current user

# Each node in the graph will return a ChatResponse (or End[ChatResponse]) when complete.
# The graph nodes update the shared state so that conversation history is preserved automatically.

@dataclass
class RouterNode(BaseNode[ChatState]):
    user_message: str

    async def run(self, ctx: GraphRunContext[ChatState]) -> Union[
        End[ChatResponse], "ClarificationNode", "BookingNode", "GeneralInquiryNode"
    ]:
        logger.info("================== RouterNode START ==================")
        logger.info(f"RouterNode received message: {self.user_message}")
        
        current_datetime = datetime.now()
        context = await create_booking_context(ctx.state.user, current_datetime)
        logger.debug(f"Created context: {context}")
        
        if ctx.state.conversation_history:
            logger.debug(f"Conversation history length: {len(ctx.state.conversation_history)}")
            conversation_text = "\n".join(
                extract_message_content(msg) for msg in ctx.state.conversation_history
            )
            context_message = f"{conversation_text}\nUser: {self.user_message}"
        else:
            logger.debug("No conversation history")
            context_message = f"{context}\nUser: {self.user_message}"

        logger.info("Calling router_agent")
        routing_result = await router_agent.run(context_message, message_history=ctx.state.conversation_history)
        routing_decision = routing_result.data
        logger.info(f"Router decision: {routing_decision}")

        ctx.state.conversation_history = routing_result.all_messages()

        next_node = None
        if routing_decision.target == RoutingTarget.GENERAL:
            logger.info("Routing to GeneralInquiryNode")
            next_node = GeneralInquiryNode(
                context_message=context_message,
                user_message=self.user_message
            )
        elif routing_decision.target == RoutingTarget.BOOKING:
            logger.info("Routing to BookingNode")
            next_node = BookingNode(
                context_message=context_message,
                user_message=self.user_message
            )
        elif routing_decision.target == RoutingTarget.CLARIFICATION:
            logger.info("Routing to ClarificationNode")
            next_node = ClarificationNode(
                routing_decision=routing_decision,
                context_message=context_message
            )
        else:
            logger.error(f"Unknown routing target: {routing_decision.target}")
            next_node = End(ChatResponse(
                message_type="error",
                text="I'm sorry, I couldn't process your request properly."
            ))

        logger.info(f"RouterNode returning next node: {type(next_node).__name__}")
        logger.info("================== RouterNode END ==================")
        return next_node

@dataclass
class ClarificationNode(BaseNode[ChatState]):
    routing_decision: RoutingDecision
    context_message: str

    async def run(self, ctx: GraphRunContext[ChatState]) -> End[ChatResponse]:
        logger.info("[ClarificationNode] Calling clarification_agent")
        clar_result = await clarification_agent.run(self.context_message, message_history=ctx.state.conversation_history)
        response_text = str(clar_result.data)
        updated_history = clar_result.all_messages()
        ctx.state.conversation_history = updated_history
        return End(ChatResponse(
            message_type="clarification",
            text=response_text,
            conversation_history=[safe_message_to_dict(msg) for msg in updated_history]
        ))

@dataclass
class BookingNode(BaseNode[ChatState]):
    context_message: str
    user_message: str

    async def run(self, ctx: GraphRunContext[ChatState]) -> End[ChatResponse]:
        logger.info(f"[BookingNode] Processing booking request: {self.user_message}")
        booking_result = await booking_agent.run(self.context_message, message_history=ctx.state.conversation_history)
        booking_action = booking_result.data.action
        
        logger.info(f"[BookingNode] Booking agent result: {booking_result.data.model_dump(exclude_none=True)}")
        
        if not booking_result.data.success:
            logger.info(f"[BookingNode] Booking validation failed: {booking_result.data.message}")
            return End(ChatResponse(
                message_type="clarification",
                text=booking_result.data.message
            ))

        updated_history = booking_result.all_messages()
        ctx.state.conversation_history = updated_history
        if booking_action.action_type:
            deps = BookingDependencies(current_datetime=datetime.now())
            response = await handle_booking_action(booking_action, ctx.state.user, deps)
            response.conversation_history = [safe_message_to_dict(msg) for msg in updated_history]
            return End(response)
        else:
            # Fallback to general inquiry if no booking action was found.
            gen_response = await handle_general_inquiry(self.user_message, self.context_message, updated_history)
            return End(gen_response)

@dataclass
class GeneralInquiryNode(BaseNode[ChatState]):
    context_message: str
    user_message: str

    async def run(self, ctx: GraphRunContext[ChatState]) -> End[ChatResponse]:
        logger.info("================== GeneralInquiryNode START ==================")
        logger.info(f"GeneralInquiryNode processing message: {self.user_message}")
        
        general_result = await general_info_agent.run(
            self.context_message,
            message_history=ctx.state.conversation_history
        )
        
        # Extract the structured response
        info_response = general_result.data
        logger.info(f"Generated response: {info_response}")
        
        updated_history = general_result.all_messages()
        ctx.state.conversation_history = updated_history
        
        response = End(ChatResponse(
            message_type="text",
            text=info_response.response,
            details=info_response.additional_details,
            conversation_history=[safe_message_to_dict(msg) for msg in updated_history]
        ))
        
        logger.info("================== GeneralInquiryNode END ==================")
        return response

# Make sure the graph is properly initialized with all nodes
chat_graph = Graph(nodes=(RouterNode, ClarificationNode, BookingNode, GeneralInquiryNode))

async def process_message_graph(message: str, current_user) -> ChatResponse:
    """
    Process an incoming message using the chat graph.
    """
    logger.info("================== process_message_graph START ==================")
    logger.info(f"Processing message: {message}")
    
    state = ChatState(user=current_user)
    
    logger.info("Starting graph execution")
    result, history = await chat_graph.run(
        RouterNode(user_message=message), 
        state=state
    )
    
    logger.info(f"Graph execution completed. History types: {[type(h).__name__ for h in history]}")
    logger.info(f"Result type: {type(result).__name__}")
    logger.info("================== process_message_graph END ==================")
    
    return result
