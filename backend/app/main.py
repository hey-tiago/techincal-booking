from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from tortoise.contrib.fastapi import register_tortoise
from contextlib import asynccontextmanager
from datetime import datetime

from app.core.config import settings
from app.api.endpoints import auth, bookings, chat
from app.models.booking import Booking

# Database initialization
async def init_db():
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

app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Tortoise ORM configuration
TORTOISE_ORM = {
    "connections": {"default": settings.DATABASE_URL},
    "apps": {
        "models": {
            "models": ["app.models.booking", "app.models.user"],
            "default_connection": "default",
        },
    },
}

register_tortoise(
    app,
    config=TORTOISE_ORM,
    generate_schemas=True,
    add_exception_handlers=True,
)

# Include routers
app.include_router(auth.router, tags=["auth"])
app.include_router(bookings.router, prefix="/bookings", tags=["bookings"])
app.include_router(chat.router, prefix="/chat", tags=["chat"])

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "console":
        from app.console import run_console
        run_console()
    else:
        import uvicorn
        uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)