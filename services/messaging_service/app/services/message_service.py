"""Message service business logic."""
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
from datetime import datetime
from typing import List, Optional

from ..models import Conversation, Message
from ..schemas import MessageCreateSchema, ConversationSchema, MessageSchema

class MessageService:
    """Service for message operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def get_user_conversations(self, user_id: int) -> List[ConversationSchema]:
        """Get all conversations for a user."""
        conversations = self.db.query(Conversation).filter(
            or_(
                Conversation.participant_one_id == user_id,
                Conversation.participant_two_id == user_id
            )
        ).order_by(desc(Conversation.last_message_at)).all()
        
        return [ConversationSchema.from_orm(c) for c in conversations]
    
    async def get_conversation_messages(
        self,
        conversation_id: int,
        limit: int = 50,
        offset: int = 0
    ) -> List[MessageSchema]:
        """Get messages for a conversation."""
        messages = self.db.query(Message).filter(
            Message.conversation_id == conversation_id
        ).order_by(desc(Message.created_at)).limit(limit).offset(offset).all()
        
        return [MessageSchema.from_orm(m) for m in reversed(messages)]
    
    async def create_message(self, message_data: MessageCreateSchema) -> MessageSchema:
        """Create a new message."""
        message = Message(
            conversation_id=message_data.conversation_id,
            sender_id=message_data.sender_id,
            recipient_id=message_data.recipient_id,
            content=message_data.content,
            message_type=message_data.message_type,
            file_url=message_data.file_url,
            file_name=message_data.file_name,
            is_read=False
        )
        
        self.db.add(message)
        
        # Update conversation last_message_at
        conversation = self.db.query(Conversation).filter(
            Conversation.id == message_data.conversation_id
        ).first()
        if conversation:
            conversation.last_message_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(message)
        
        return MessageSchema.from_orm(message)
    
    async def mark_message_read(self, message_id: int) -> None:
        """Mark a message as read."""
        message = self.db.query(Message).filter(Message.id == message_id).first()
        if message:
            message.is_read = True
            message.read_at = datetime.utcnow()
            self.db.commit()
    
    async def get_or_create_conversation(
        self,
        user_one_id: int,
        user_two_id: int
    ) -> ConversationSchema:
        """Get or create a conversation between two users."""
        # Ensure consistent ordering
        p1, p2 = min(user_one_id, user_two_id), max(user_one_id, user_two_id)
        
        conversation = self.db.query(Conversation).filter(
            and_(
                Conversation.participant_one_id == p1,
                Conversation.participant_two_id == p2
            )
        ).first()
        
        if not conversation:
            conversation = Conversation(
                participant_one_id=p1,
                participant_two_id=p2
            )
            self.db.add(conversation)
            self.db.commit()
            self.db.refresh(conversation)
        
        return ConversationSchema.from_orm(conversation)
