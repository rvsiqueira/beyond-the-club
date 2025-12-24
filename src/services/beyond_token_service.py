"""
Beyond Token Service.

Manages Firebase/Beyond tokens per user phone number.
Each web user has their own Beyond API token stored and linked to their phone.
"""

import json
import time
import logging
from pathlib import Path
from typing import Optional, Dict
from dataclasses import dataclass, asdict

from .base import BaseService, ServiceContext
from ..firebase_auth import FirebaseTokens

logger = logging.getLogger(__name__)

BEYOND_TOKENS_FILE = Path(__file__).parent.parent.parent / "data" / ".beyondtheclub_user_tokens.json"


@dataclass
class UserBeyondToken:
    """Beyond API tokens for a specific user."""
    phone: str
    id_token: str
    refresh_token: str
    expires_at: float
    updated_at: float


class BeyondTokenService(BaseService):
    """
    Service for managing Beyond API tokens per user.

    Each user (identified by phone) has their own Beyond tokens stored separately.
    """

    def __init__(self, context: ServiceContext):
        super().__init__(context)
        self._tokens_cache: Dict[str, UserBeyondToken] = {}
        self._load_tokens()

    def _ensure_data_dir(self):
        """Ensure the data directory exists."""
        BEYOND_TOKENS_FILE.parent.mkdir(parents=True, exist_ok=True)

    def _load_tokens(self):
        """Load all user tokens from file."""
        try:
            if BEYOND_TOKENS_FILE.exists():
                data = json.loads(BEYOND_TOKENS_FILE.read_text())
                for phone, token_data in data.items():
                    self._tokens_cache[phone] = UserBeyondToken(**token_data)
                logger.info(f"Loaded Beyond tokens for {len(self._tokens_cache)} users")
        except Exception as e:
            logger.warning(f"Could not load Beyond tokens: {e}")
            self._tokens_cache = {}

    def _save_tokens(self):
        """Save all user tokens to file."""
        try:
            self._ensure_data_dir()
            data = {phone: asdict(token) for phone, token in self._tokens_cache.items()}
            BEYOND_TOKENS_FILE.write_text(json.dumps(data, indent=2))
            logger.debug("Beyond tokens saved")
        except Exception as e:
            logger.warning(f"Could not save Beyond tokens: {e}")

    def get_token(self, phone: str) -> Optional[UserBeyondToken]:
        """Get Beyond token for a user."""
        return self._tokens_cache.get(phone)

    def has_valid_token(self, phone: str) -> bool:
        """Check if user has a valid (non-expired) Beyond token."""
        token = self.get_token(phone)
        if not token:
            return False
        # Check if token is expired (with 60s buffer)
        return token.expires_at > time.time() + 60

    def save_token(self, phone: str, firebase_tokens: FirebaseTokens):
        """Save Beyond token for a user."""
        self._tokens_cache[phone] = UserBeyondToken(
            phone=phone,
            id_token=firebase_tokens.id_token,
            refresh_token=firebase_tokens.refresh_token,
            expires_at=firebase_tokens.expires_at,
            updated_at=time.time()
        )
        self._save_tokens()
        logger.info(f"Saved Beyond token for user {phone}")

    def delete_token(self, phone: str):
        """Delete Beyond token for a user."""
        if phone in self._tokens_cache:
            del self._tokens_cache[phone]
            self._save_tokens()
            logger.info(f"Deleted Beyond token for user {phone}")

    def request_sms(self, phone: str) -> str:
        """
        Request SMS code for Beyond authentication.

        Returns session_info for tracking the request.
        """
        # Get admin token first
        admin_tokens = self.context.firebase_auth.verify_password(
            self.config.auth.admin_email,
            self.config.auth.admin_password
        )

        logger.info(f"Requesting Beyond SMS for {phone}...")
        self.context.sms_auth.send_sms_code(phone, admin_tokens.id_token)

        # Return a session identifier (we use phone as session for simplicity)
        return f"sms_session_{phone}_{int(time.time())}"

    def verify_sms(self, beyond_phone: str, code: str, session_info: str, store_for_phone: Optional[str] = None) -> FirebaseTokens:
        """
        Verify SMS code and get Beyond tokens.

        Args:
            beyond_phone: Phone number used for Beyond verification (received SMS)
            code: SMS code received
            session_info: Session info from request_sms
            store_for_phone: Phone to store tokens for (web user phone). If None, uses beyond_phone.

        Returns:
            Firebase tokens for the user
        """
        # Get admin token
        admin_tokens = self.context.firebase_auth.verify_password(
            self.config.auth.admin_email,
            self.config.auth.admin_password
        )

        logger.info(f"Verifying Beyond SMS code for {beyond_phone}...")
        user_tokens = self.context.sms_auth.complete_auth_flow(
            beyond_phone, code, admin_tokens.id_token
        )

        # Save tokens linked to web user phone (or beyond_phone if not specified)
        storage_phone = store_for_phone or beyond_phone
        self.save_token(storage_phone, user_tokens)

        return user_tokens

    def get_valid_id_token(self, phone: str) -> Optional[str]:
        """
        Get a valid ID token for the user, refreshing if needed.

        Returns None if no token or refresh fails.
        """
        token = self.get_token(phone)
        if not token:
            return None

        # Check if we need to refresh
        if token.expires_at <= time.time() + 60:
            try:
                refreshed = self._refresh_token(phone, token)
                if refreshed:
                    return refreshed.id_token
                return None
            except Exception as e:
                logger.warning(f"Failed to refresh token for {phone}: {e}")
                return None

        return token.id_token

    def _refresh_token(self, phone: str, token: UserBeyondToken) -> Optional[UserBeyondToken]:
        """Refresh an expired token."""
        try:
            # Set the token in firebase auth temporarily
            self.context.firebase_auth._tokens = FirebaseTokens(
                id_token=token.id_token,
                refresh_token=token.refresh_token,
                expires_at=token.expires_at
            )

            # Refresh
            new_tokens = self.context.firebase_auth.refresh_token()

            # Save the new tokens
            self.save_token(phone, new_tokens)

            return self.get_token(phone)

        except Exception as e:
            logger.error(f"Token refresh failed for {phone}: {e}")
            # Delete invalid token
            self.delete_token(phone)
            return None
