from pydantic_settings import BaseSettings
from datetime import time

class Settings(BaseSettings):
    SECRET_KEY: str = "your-secret-key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    DATABASE_URL: str = "sqlite://bookings.db"
    BUSINESS_HOURS_START: time = time(9, 0)  # 9 AM
    BUSINESS_HOURS_END: time = time(17, 0)   # 5 PM

    class Config:
        env_file = ".env"

settings = Settings() 