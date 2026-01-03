"""
MCP Authentication module.

Provides API Key validation and Session Token management for Voice Agents.

Authentication Flow:
1. Voice Agent calls POST /auth/session with X-API-Key header and caller_id
2. MCP validates API Key (app authentication)
3. MCP verifies caller_id exists in user base
4. MCP checks if caller_id has valid Beyond token
5. MCP generates session_token for this transaction
6. Voice Agent uses session_token for SSE connection and all operations
"""

import os
import time
import secrets
import logging
from typing import Optional
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class Session:
    """Represents an authenticated MCP session."""
    token: str
    caller_id: str
    created_at: float
    expires_at: float
    has_beyond_token: bool = False
    user_name: Optional[str] = None
    member_ids: list = field(default_factory=list)


class SessionManager:
    """
    Manages MCP sessions for Voice Agent authentication.

    Sessions are stored in memory and expire after a configurable time.
    """

    def __init__(self):
        self._sessions: dict[str, Session] = {}
        self._api_key: Optional[str] = None
        self._session_expiry: int = 600  # 10 minutes default
        self._load_config()

    def _load_config(self):
        """Load configuration from environment."""
        self._api_key = os.getenv("MCP_API_KEY")
        self._session_expiry = int(os.getenv("MCP_SESSION_EXPIRY_SECONDS", "600"))

        if not self._api_key:
            logger.warning(
                "MCP_API_KEY not set! MCP endpoints will be unprotected. "
                "Set MCP_API_KEY in .env for production."
            )

    def validate_api_key(self, api_key: Optional[str]) -> bool:
        """
        Validate the API key from Voice Agent.

        Args:
            api_key: The API key to validate

        Returns:
            True if valid, False otherwise
        """
        # If no API key configured, allow all (development mode)
        if not self._api_key:
            logger.warning("No MCP_API_KEY configured - allowing request (dev mode)")
            return True

        if not api_key:
            return False

        # Constant-time comparison to prevent timing attacks
        return secrets.compare_digest(api_key, self._api_key)

    def create_session(
        self,
        caller_id: str,
        has_beyond_token: bool = False,
        user_name: Optional[str] = None,
        member_ids: Optional[list] = None
    ) -> Session:
        """
        Create a new session for a caller.

        Args:
            caller_id: Phone number of the caller
            has_beyond_token: Whether caller has valid Beyond API token
            user_name: Name of the user (if known)
            member_ids: List of member IDs linked to this caller

        Returns:
            New Session object
        """
        # Clean up expired sessions first
        self._cleanup_expired()

        # Generate secure session token
        token = f"sess_{secrets.token_urlsafe(32)}"

        now = time.time()
        session = Session(
            token=token,
            caller_id=caller_id,
            created_at=now,
            expires_at=now + self._session_expiry,
            has_beyond_token=has_beyond_token,
            user_name=user_name,
            member_ids=member_ids or []
        )

        self._sessions[token] = session
        logger.info(f"Created session for {caller_id}, expires in {self._session_expiry}s")

        return session

    def get_session(self, token: str) -> Optional[Session]:
        """
        Get a session by token.

        Args:
            token: Session token

        Returns:
            Session if valid and not expired, None otherwise
        """
        session = self._sessions.get(token)

        if not session:
            return None

        # Check if expired
        if time.time() > session.expires_at:
            del self._sessions[token]
            logger.info(f"Session expired for {session.caller_id}")
            return None

        return session

    def invalidate_session(self, token: str) -> bool:
        """
        Invalidate/delete a session.

        Args:
            token: Session token to invalidate

        Returns:
            True if session was found and deleted
        """
        if token in self._sessions:
            session = self._sessions[token]
            del self._sessions[token]
            logger.info(f"Session invalidated for {session.caller_id}")
            return True
        return False

    def _cleanup_expired(self):
        """Remove all expired sessions."""
        now = time.time()
        expired = [
            token for token, session in self._sessions.items()
            if now > session.expires_at
        ]
        for token in expired:
            del self._sessions[token]

        if expired:
            logger.info(f"Cleaned up {len(expired)} expired sessions")

    def get_active_sessions_count(self) -> int:
        """Get count of active (non-expired) sessions."""
        self._cleanup_expired()
        return len(self._sessions)


# Global session manager instance
_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """Get or create the global session manager."""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager


async def authenticate_request(
    api_key: Optional[str],
    caller_id: str
) -> tuple[bool, str, Optional[Session]]:
    """
    Authenticate a session request from Voice Agent.

    Args:
        api_key: API key from X-API-Key header
        caller_id: Phone number of the caller

    Returns:
        Tuple of (success, message, session)
    """
    from .context import get_services

    manager = get_session_manager()

    # 1. Validate API Key
    if not manager.validate_api_key(api_key):
        return False, "Invalid API key", None

    # 2. Normalize phone number
    caller_id = caller_id.strip()
    if not caller_id.startswith("+"):
        caller_id = f"+{caller_id}"

    # 3. Check if caller exists in user base
    services = get_services()

    # Try to find user by phone
    from src.auth.users import get_user_by_phone
    user = get_user_by_phone(caller_id)

    user_name = None
    member_ids = []

    if user:
        user_name = user.get("name")
        member_ids = user.get("member_ids", [])

    # 4. Check if caller has valid Beyond token
    has_beyond_token = services.beyond_tokens.has_valid_token(caller_id)

    # 5. Create session
    session = manager.create_session(
        caller_id=caller_id,
        has_beyond_token=has_beyond_token,
        user_name=user_name,
        member_ids=member_ids
    )

    return True, "Session created", session


def validate_session_token(token: str) -> Optional[Session]:
    """
    Validate a session token from Authorization header.

    Args:
        token: Bearer token from Authorization header

    Returns:
        Session if valid, None otherwise
    """
    manager = get_session_manager()
    return manager.get_session(token)
