import asyncio
import sys
from tortoise import Tortoise
from .core.security import get_password_hash
from .models.user import User
from .services.chat import process_message

async def run_console_async():
    await Tortoise.init(
        db_url="sqlite://bookings.db", 
        modules={"models": ["app.models.booking", "app.models.user"]}
    )
    await Tortoise.generate_schemas()
    
    print("Technician Booking Console. Type your message or 'quit' to exit:")
    while True:
        user_input = input("> ")
        if user_input.lower() == "quit":
            break
        dummy_user = await User.filter(username="dummy").first()
        if not dummy_user:
            dummy_user = await User.create(
                username="dummy", 
                hashed_password=get_password_hash("dummy")
            )
        response = await process_message(user_input, dummy_user)
        print(response)
    
    await Tortoise.close_connections()

def run_console():
    asyncio.run(run_console_async()) 