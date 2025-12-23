"""
JWT token handler.

Generates and validates JWT tokens for our own authentication system.
Independent of Firebase - used for web, voice agent, and API auth.
"""

import os
import time
import logging
from typing import Optional, Literal
from dataclasses import dataclass, asdict

from jose import jwt, JWTError

logger = logging.getLogger(__name__)

# Token configuration
DEFAULT_SECRET_KEY = "beyond-the-club-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_SECONDS = 3600  # 1 hour
REFRESH_TOKEN_EXPIRE_SECONDS = 86400 * 7  # 7 days

AuthType = Literal["password", "phone_only", "sms_otp"]


@dataclass
class TokenPayload:
    """JWT token payload."""
    user_id: str
    phone: str
    auth_type: AuthType
    exp: int  # Expiration timestamp
    iat: int  # Issued at timestamp
    token_type: str = "access"  # "access" or "refresh"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "TokenPayload":
        return cls(**data)


class JWTHandler:
    """
    Handles JWT token generation and validation.

    Supports:
    - Access tokens (short-lived, for API calls)
    - Refresh tokens (long-lived, for getting new access tokens)
    - Multiple auth types (password, phone_only, sms_otp)
    """

    def __init__(self, secret_key: Optional[str] = None):
        """
        Initialize JWT handler.

        Args:
            secret_key: Secret key for signing tokens.
                       Falls back to JWT_SECRET_KEY env var or default.
        """
        self.secret_key = (
            secret_key
            or os.getenv("JWT_SECRET_KEY")
            or DEFAULT_SECRET_KEY
        )

        if self.secret_key == DEFAULT_SECRET_KEY:
            logger.warning(
                "Using default JWT secret key. "
                "Set JWT_SECRET_KEY environment variable in production!"
            )

    def create_access_token(
        self,
        user_id: str,
        phone: str,
        auth_type: AuthType,
        expires_in: Optional[int] = None
    ) -> str:
        """
        Create an access token.

        Args:
            user_id: Unique user identifier
            phone: User's phone number
            auth_type: How the user authenticated
            expires_in: Custom expiration in seconds (default: 1 hour)

        Returns:
            Encoded JWT token string
        """
        now = int(time.time())
        exp = now + (expires_in or ACCESS_TOKEN_EXPIRE_SECONDS)

        payload = TokenPayload(
            user_id=user_id,
            phone=phone,
            auth_type=auth_type,
            exp=exp,
            iat=now,
            token_type="access"
        )

        token = jwt.encode(payload.to_dict(), self.secret_key, algorithm=ALGORITHM)
        logger.debug(f"Created access token for user {user_id}, expires in {exp - now}s")
        return token

    def create_refresh_token(
        self,
        user_id: str,
        phone: str,
        auth_type: AuthType,
        expires_in: Optional[int] = None
    ) -> str:
        """
        Create a refresh token.

        Args:
            user_id: Unique user identifier
            phone: User's phone number
            auth_type: How the user authenticated
            expires_in: Custom expiration in seconds (default: 7 days)

        Returns:
            Encoded JWT refresh token string
        """
        now = int(time.time())
        exp = now + (expires_in or REFRESH_TOKEN_EXPIRE_SECONDS)

        payload = TokenPayload(
            user_id=user_id,
            phone=phone,
            auth_type=auth_type,
            exp=exp,
            iat=now,
            token_type="refresh"
        )

        token = jwt.encode(payload.to_dict(), self.secret_key, algorithm=ALGORITHM)
        logger.debug(f"Created refresh token for user {user_id}, expires in {exp - now}s")
        return token

    def create_token_pair(
        self,
        user_id: str,
        phone: str,
        auth_type: AuthType
    ) -> tuple[str, str]:
        """
        Create both access and refresh tokens.

        Args:
            user_id: Unique user identifier
            phone: User's phone number
            auth_type: How the user authenticated

        Returns:
            Tuple of (access_token, refresh_token)
        """
        access = self.create_access_token(user_id, phone, auth_type)
        refresh = self.create_refresh_token(user_id, phone, auth_type)
        return access, refresh

    def verify_token(self, token: str) -> Optional[TokenPayload]:
        """
        Verify and decode a token.

        Args:
            token: JWT token string

        Returns:
            TokenPayload if valid, None if invalid or expired
        """
        try:
            data = jwt.decode(token, self.secret_key, algorithms=[ALGORITHM])
            payload = TokenPayload.from_dict(data)

            # Check expiration
            if payload.exp < int(time.time()):
                logger.debug("Token expired")
                return None

            return payload

        except JWTError as e:
            logger.debug(f"Token verification failed: {e}")
            return None

    def refresh_access_token(self, refresh_token: str) -> Optional[str]:
        """
        Create a new access token from a valid refresh token.

        Args:
            refresh_token: Valid refresh token

        Returns:
            New access token if refresh token is valid, None otherwise
        """
        payload = self.verify_token(refresh_token)

        if payload is None:
            return None

        if payload.token_type != "refresh":
            logger.warning("Attempted to refresh with non-refresh token")
            return None

        return self.create_access_token(
            user_id=payload.user_id,
            phone=payload.phone,
            auth_type=payload.auth_type
        )

    def get_token_expiry(self, token: str) -> Optional[int]:
        """
        Get the expiration timestamp of a token.

        Args:
            token: JWT token string

        Returns:
            Expiration timestamp or None if invalid
        """
        payload = self.verify_token(token)
        return payload.exp if payload else None

    def is_token_expired(self, token: str) -> bool:
        """
        Check if a token is expired.

        Args:
            token: JWT token string

        Returns:
            True if expired or invalid, False if still valid
        """
        return self.verify_token(token) is None
