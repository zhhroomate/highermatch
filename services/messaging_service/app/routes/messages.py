"""Message routes."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List

from ..schemas import MessageSchema, MessageCreateSchema, ConversationSchema
from ..services.message_service import MessageService

router = APIRouter(prefix="/api/messages", tags=["messages"])

def get_db():
    """Get database session."""
    # 这里应该连接到实际的数据库
    pass

@router.get("/conversations", response_model=List[ConversationSchema])
async def get_conversations(user_id: int, db: Session = Depends(get_db)):
    """Get all conversations for a user."""
    service = MessageService(db)
    return await service.get_user_conversations(user_id)

@router.get("/conversations/{conversation_id}/messages", response_model=List[MessageSchema])
async def get_conversation_messages(
    conversation_id: int,
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """Get messages for a conversation."""
    service = MessageService(db)
    return await service.get_conversation_messages(conversation_id, limit, offset)

@router.post("/send", response_model=MessageSchema)
async def send_message(message: MessageCreateSchema, db: Session = Depends(get_db)):
    """Send a message."""
    service = MessageService(db)
    return await service.create_message(message)

@router.put("/{message_id}/read")
async def mark_message_read(message_id: int, db: Session = Depends(get_db)):
    """Mark a message as read."""
    service = MessageService(db)
    await service.mark_message_read(message_id)
    return {"success": True}

@router.post("/conversations/get-or-create")
async def get_or_create_conversation(
    user_one_id: int,
    user_two_id: int,
    db: Session = Depends(get_db)
):
    """Get or create a conversation between two users."""
    service = MessageService(db)
    return await service.get_or_create_conversation(user_one_id, user_two_id)
