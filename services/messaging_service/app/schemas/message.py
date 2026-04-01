"""Message schemas."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel

class MessageCreateSchema(BaseModel):
    """Schema for creating a message."""
    conversation_id: int
    sender_id: int
    recipient_id: int
    content: str
    message_type: str = "text"
    file_url: Optional[str] = None
    file_name: Optional[str] = None

class MessageSchema(BaseModel):
    """Schema for message response."""
    id: int
    conversation_id: int
    sender_id: int
    recipient_id: int
    content: str
    message_type: str
    file_url: Optional[str]
    file_name: Optional[str]
    is_read: bool
    read_at: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True
