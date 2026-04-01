"""Conversation model."""
from datetime import datetime
from sqlalchemy import Column, Integer, DateTime, String
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Conversation(Base):
    """Conversation model for private messaging."""
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    participant_one_id = Column(Integer, nullable=False, index=True)
    participant_two_id = Column(Integer, nullable=False, index=True)
    last_message_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    class Config:
        from_attributes = True
