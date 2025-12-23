"""
Authentication module for Beyond The Club.

Provides JWT-based authentication independent of Firebase.
Supports multiple auth types: password, phone-only (voice), SMS OTP (future).
"""

from .jwt_handler import JWTHandler, TokenPayload
from .password import PasswordHandler
from .users import UserStore, User

__all__ = [
    "JWTHandler",
    "TokenPayload",
    "PasswordHandler",
    "UserStore",
    "User",
]
