from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.models.user import User
from app.core.security import get_current_user
from app.services.chat import process_message

router = APIRouter()

class ChatMessage(BaseModel):
    message: str

@router.post("")
async def chat_endpoint(chat_message: ChatMessage, current_user: User = Depends(get_current_user)):
    response = await process_message(chat_message.message, current_user)
    return {"response": response} 