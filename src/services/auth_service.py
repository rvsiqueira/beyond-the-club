"""
Authentication service.

Handles Firebase authentication and token management.
"""

import json
import time
import logging
from pathlib import Path
from typing import Optional

from .base import BaseService, ServiceContext
from ..firebase_auth import FirebaseTokens

logger = logging.getLogger(__name__)

TOKEN_CACHE_FILE = Path(__file__).parent.parent.parent / ".beyondtheclub_tokens.json"


class AuthService(BaseService):
    """
    Service for authentication.

    Responsibilities:
    - Authenticate via Firebase (admin + SMS)
    - Token caching and refresh
    - Initialize API after authentication
    """

    def __init__(self, context: ServiceContext):
        super().__init__(context)

    def save_tokens(self, tokens: FirebaseTokens):
        """Save tokens to cache file."""
        try:
            data = {
                "id_token": tokens.id_token,
                "refresh_token": tokens.refresh_token,
                "expires_at": tokens.expires_at
            }
            TOKEN_CACHE_FILE.write_text(json.dumps(data))
            logger.debug("Tokens saved to cache")
        except Exception as e:
            logger.warning(f"Could not save tokens: {e}")

    def load_tokens(self) -> Optional[FirebaseTokens]:
        """Load tokens from cache file."""
        try:
            if not TOKEN_CACHE_FILE.exists():
                return None

            data = json.loads(TOKEN_CACHE_FILE.read_text())
            tokens = FirebaseTokens(
                id_token=data["id_token"],
                refresh_token=data["refresh_token"],
                expires_at=data["expires_at"]
            )

            # Check if tokens are still valid (or can be refreshed)
            if tokens.expires_at > time.time():
                logger.info("Loaded valid tokens from cache")
                return tokens

            logger.info("Cached tokens expired, will try to refresh")
            return tokens  # Return anyway, we can try to refresh

        except Exception as e:
            logger.warning(f"Could not load cached tokens: {e}")
            return None

    def authenticate_admin(self) -> FirebaseTokens:
        """Authenticate with admin credentials to get initial token."""
        if not self.config.auth.admin_email or not self.config.auth.admin_password:
            raise ValueError("Admin email and password must be configured")

        logger.info("Authenticating with admin credentials...")
        tokens = self.context.firebase_auth.verify_password(
            self.config.auth.admin_email,
            self.config.auth.admin_password
        )
        return tokens

    def send_sms_code(self, phone: Optional[str] = None) -> bool:
        """
        Send SMS verification code.

        Args:
            phone: Phone number (uses config if not provided)

        Returns:
            True if SMS sent successfully
        """
        phone = phone or self.config.auth.phone_number
        if not phone:
            raise ValueError("Phone number must be configured")

        # First get admin token
        admin_tokens = self.authenticate_admin()

        logger.info(f"Sending SMS code to {phone}...")
        self.context.sms_auth.send_sms_code(phone, admin_tokens.id_token)
        return True

    def verify_sms_code(self, sms_code: str, phone: Optional[str] = None) -> FirebaseTokens:
        """
        Verify SMS code and complete authentication.

        Args:
            sms_code: The SMS code received
            phone: Phone number (uses config if not provided)

        Returns:
            User tokens
        """
        phone = phone or self.config.auth.phone_number
        if not phone:
            raise ValueError("Phone number must be configured")

        # Get admin token first
        admin_tokens = self.authenticate_admin()

        logger.info("Verifying SMS code...")
        user_tokens = self.context.sms_auth.complete_auth_flow(
            phone, sms_code, admin_tokens.id_token
        )

        self.save_tokens(user_tokens)
        return user_tokens

    def authenticate_user_sms(self, sms_code: Optional[str] = None) -> FirebaseTokens:
        """
        Full SMS authentication flow.

        If sms_code is not provided, sends SMS and prompts for code.
        """
        phone = self.config.auth.phone_number
        if not phone:
            raise ValueError("Phone number must be configured")

        if sms_code is None:
            # Send SMS and prompt
            self.send_sms_code(phone)
            sms_code = input("Enter the SMS code you received: ").strip()

        return self.verify_sms_code(sms_code, phone)

    def initialize(self, sms_code: Optional[str] = None, use_cached: bool = True) -> bool:
        """
        Initialize authentication and setup API.

        Args:
            sms_code: SMS verification code (if not provided, will prompt)
            use_cached: Try to use cached tokens first

        Returns:
            True if initialization successful
        """
        try:
            # Try cached tokens first
            if use_cached:
                cached = self.load_tokens()
                if cached:
                    self.context.firebase_auth._tokens = cached
                    try:
                        # Verify token is still valid
                        self.context.firebase_auth.get_valid_token()
                        logger.info("Using cached authentication")
                        self.context.setup_api()
                        return True
                    except Exception:
                        logger.info("Cached tokens invalid, re-authenticating...")

            # Full SMS authentication
            tokens = self.authenticate_user_sms(sms_code)
            self.context.firebase_auth._tokens = tokens
            self.context.setup_api()
            return True

        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            raise

    def initialize_with_tokens(self, tokens: FirebaseTokens) -> bool:
        """
        Initialize API with pre-obtained tokens.

        This is used by the web API when user has already authenticated via SMS modal.
        Does NOT send SMS - just sets up the API with provided tokens.

        Args:
            tokens: Firebase tokens obtained via SMS verification

        Returns:
            True if initialization successful
        """
        try:
            self.context.firebase_auth._tokens = tokens
            self.context.firebase_auth.get_valid_token()  # Validate/refresh if needed
            self.context.setup_api()
            logger.info("Initialized API with provided tokens")
            return True
        except Exception as e:
            logger.error(f"Token initialization failed: {e}")
            raise

    def try_initialize_cached_only(self) -> bool:
        """
        Try to initialize using only cached tokens.

        Does NOT send SMS if no valid cached token exists.
        Returns False if no valid token available (caller should handle this).

        Returns:
            True if initialized successfully, False if no valid cached token
        """
        try:
            cached = self.load_tokens()
            if cached:
                self.context.firebase_auth._tokens = cached
                try:
                    self.context.firebase_auth.get_valid_token()
                    self.context.setup_api()
                    logger.info("Initialized with cached tokens (no SMS)")
                    return True
                except Exception:
                    logger.info("Cached tokens invalid, SMS required")
                    return False
            else:
                logger.info("No cached tokens, SMS required")
                return False
        except Exception as e:
            logger.warning(f"Cache-only initialization failed: {e}")
            return False

    def is_authenticated(self) -> bool:
        """Check if currently authenticated."""
        return self.context.firebase_auth._tokens is not None

    def get_current_token(self) -> Optional[str]:
        """Get the current ID token (refreshing if needed)."""
        try:
            return self.context.firebase_auth.get_valid_token()
        except Exception:
            return None
