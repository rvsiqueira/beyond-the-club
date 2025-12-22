"""Main bot orchestrator."""

import time
import logging
import json
from pathlib import Path
from typing import Optional
from datetime import datetime

from .config import Config, load_config
from .firebase_auth import FirebaseAuth, FirebaseTokens
from .sms_auth import SMSAuth
from .beyond_api import BeyondAPI
from .session_monitor import SessionMonitor

logger = logging.getLogger(__name__)

TOKEN_CACHE_FILE = Path.home() / ".beyondtheclub_tokens.json"


class BeyondBot:
    """Main bot that orchestrates authentication and session monitoring."""

    def __init__(self, config: Optional[Config] = None):
        self.config = config or load_config()
        self.firebase_auth = FirebaseAuth(self.config.firebase, on_tokens_updated=self._save_tokens)
        self.sms_auth = SMSAuth(self.firebase_auth, self.config.api_base_url)
        self.api: Optional[BeyondAPI] = None
        self.monitor: Optional[SessionMonitor] = None
        self._running = False

    def _save_tokens(self, tokens: FirebaseTokens):
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

    def _load_tokens(self) -> Optional[FirebaseTokens]:
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

            logger.info("Cached tokens expired, will need re-authentication")
            return tokens  # Return anyway, we can try to refresh

        except Exception as e:
            logger.warning(f"Could not load cached tokens: {e}")
            return None

    def authenticate_admin(self) -> FirebaseTokens:
        """Authenticate with admin credentials to get initial token."""
        if not self.config.auth.admin_email or not self.config.auth.admin_password:
            raise ValueError("Admin email and password must be configured")

        logger.info("Authenticating with admin credentials...")
        tokens = self.firebase_auth.verify_password(
            self.config.auth.admin_email,
            self.config.auth.admin_password
        )
        return tokens

    def authenticate_user_sms(self, sms_code: Optional[str] = None) -> FirebaseTokens:
        """
        Authenticate user via SMS.

        If sms_code is not provided, sends SMS and prompts for code.
        """
        # First, get admin token
        admin_tokens = self.authenticate_admin()

        phone = self.config.auth.phone_number
        if not phone:
            raise ValueError("Phone number must be configured")

        if sms_code is None:
            # Send SMS
            logger.info(f"Sending SMS code to {phone}...")
            self.sms_auth.send_sms_code(phone, admin_tokens.id_token)

            # Prompt for code
            sms_code = input("Enter the SMS code you received: ").strip()

        # Complete authentication
        logger.info("Verifying SMS code...")
        user_tokens = self.sms_auth.complete_auth_flow(
            phone, sms_code, admin_tokens.id_token
        )

        self._save_tokens(user_tokens)
        return user_tokens

    def initialize(self, sms_code: Optional[str] = None, use_cached: bool = True) -> bool:
        """
        Initialize the bot with authentication.

        Args:
            sms_code: SMS verification code (if not provided, will prompt)
            use_cached: Try to use cached tokens first

        Returns:
            True if initialization successful
        """
        try:
            # Try cached tokens first
            if use_cached:
                cached = self._load_tokens()
                if cached:
                    self.firebase_auth._tokens = cached
                    try:
                        # Verify token is still valid
                        token = self.firebase_auth.get_valid_token()
                        logger.info("Using cached authentication")
                    except Exception:
                        logger.info("Cached tokens invalid, re-authenticating...")
                        cached = None

                if cached:
                    self._setup_api_and_monitor()
                    return True

            # Full SMS authentication
            self.authenticate_user_sms(sms_code)
            self._setup_api_and_monitor()
            return True

        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            raise

    def _setup_api_and_monitor(self):
        """Set up the API client and session monitor."""
        self.api = BeyondAPI(
            self.config.api_base_url,
            self.firebase_auth.get_valid_token
        )
        self.monitor = SessionMonitor(self.api, self.config.session)
        logger.info("Bot initialized successfully")

    def run_once(self) -> int:
        """
        Run a single check for available sessions.

        Returns:
            Number of sessions booked
        """
        if not self.monitor:
            raise RuntimeError("Bot not initialized. Call initialize() first.")

        available = self.monitor.run_check(auto_book=self.config.bot.auto_book)
        return len([s for s in available if s.id in self.monitor.get_booked_sessions()])

    def run(self):
        """Run the bot continuously with configured interval."""
        if not self.monitor:
            raise RuntimeError("Bot not initialized. Call initialize() first.")

        self._running = True
        interval = self.config.bot.check_interval_seconds

        logger.info(f"Starting bot with {interval}s check interval")
        logger.info(f"Monitoring levels: {self.config.session.levels}")
        logger.info(f"Monitoring wave sides: {self.config.session.wave_sides}")
        logger.info(f"Target hours: {self.config.session.target_hours or 'Any'}")
        logger.info(f"Target dates: {self.config.session.target_dates or 'Any'}")
        logger.info(f"Auto-book: {self.config.bot.auto_book}")

        try:
            while self._running:
                try:
                    booked = self.run_once()
                    if booked > 0:
                        logger.info(f"Booked {booked} session(s) this check")

                except Exception as e:
                    logger.error(f"Error during check: {e}")

                logger.info(f"Next check in {interval} seconds...")
                time.sleep(interval)

        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
        finally:
            self._running = False

    def stop(self):
        """Stop the running bot."""
        self._running = False

    def close(self):
        """Clean up resources."""
        if self.api:
            self.api.close()
        self.firebase_auth.close()
        self.sms_auth.close()
