"""Routers module initialization"""

from app.routers.auth import router, get_current_user_id, get_current_user

__all__ = [
    "router",
    "get_current_user_id",
    "get_current_user",
]
