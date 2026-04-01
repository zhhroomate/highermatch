"""Conversation schemas."""
from datetime import datetime
from pydantic import BaseModel

class ConversationCreateSchema(BaseModel):
    """Schema for creating a conversation."""
    participant_one_id: int
    participant_two_id: int

class ConversationSchema(BaseModel):
    """Schema for conversation response."""
    id: int
    participant_one_id: int
    participant_two_id: int
    last_message_at: datetime
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
