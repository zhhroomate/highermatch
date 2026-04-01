"""Messaging service schemas."""
from .conversation import ConversationSchema, ConversationCreateSchema
from .message import MessageSchema, MessageCreateSchema

__all__ = [
    "ConversationSchema",
    "ConversationCreateSchema",
    "MessageSchema",
    "MessageCreateSchema",
]
