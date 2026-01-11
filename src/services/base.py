"""
Base service classes and shared context.

The ServiceContext holds all shared state and dependencies that services need.
This allows the CLI (main.py) and future API/MCP to share the same logic.
"""

import logging
from typing import Optional, Callable
from dataclasses import dataclass, field

from ..config import Config, load_config, SportConfig
from ..firebase_auth import FirebaseAuth, FirebaseTokens
from ..sms_auth import SMSAuth
from ..beyond_api import BeyondAPI
from .sms_service import SMSService

logger = logging.getLogger(__name__)


@dataclass
class ServiceContext:
    """
    Shared context for all services.

    This replaces the monolithic BeyondBot state with a clean dependency container.
    All services receive this context and use it to access shared resources.
    """
    config: Config
    firebase_auth: FirebaseAuth
    sms_auth: SMSAuth
    api: Optional[BeyondAPI] = None
    current_sport: str = "surf"
    _sms: Optional[SMSService] = field(default=None, repr=False)

    # Callbacks
    on_tokens_updated: Optional[Callable[[FirebaseTokens], None]] = None

    @property
    def sms(self) -> SMSService:
        """Lazy-loaded SMS service."""
        if self._sms is None:
            self._sms = SMSService()
        return self._sms

    def __post_init__(self):
        """Initialize Firebase auth with token callback if provided."""
        if self.on_tokens_updated:
            self.firebase_auth._on_tokens_updated = self.on_tokens_updated

    @classmethod
    def create(
        cls,
        config: Optional[Config] = None,
        on_tokens_updated: Optional[Callable[[FirebaseTokens], None]] = None
    ) -> "ServiceContext":
        """
        Factory method to create a ServiceContext with all dependencies.

        Args:
            config: Optional config (loads from env if not provided)
            on_tokens_updated: Optional callback when tokens are refreshed

        Returns:
            Configured ServiceContext
        """
        cfg = config or load_config()
        firebase_auth = FirebaseAuth(cfg.firebase, on_tokens_updated=on_tokens_updated)
        sms_auth = SMSAuth(firebase_auth, cfg.api_base_url)

        return cls(
            config=cfg,
            firebase_auth=firebase_auth,
            sms_auth=sms_auth,
            on_tokens_updated=on_tokens_updated
        )

    def set_sport(self, sport: str):
        """Set the current sport context."""
        available = self.config.get_available_sports()
        if sport not in available:
            raise ValueError(f"Sport '{sport}' not available. Available: {available}")
        self.current_sport = sport
        logger.info(f"Sport context set to: {sport}")

    def get_sport_config(self) -> SportConfig:
        """Get the SportConfig for the current sport."""
        return self.config.get_sport_config(self.current_sport)

    def setup_api(self):
        """Initialize the API client (requires authentication)."""
        if not self.firebase_auth._tokens:
            raise RuntimeError("Not authenticated. Call authenticate first.")

        self.api = BeyondAPI(
            self.config.api_base_url,
            self.firebase_auth.get_valid_token
        )
        logger.info(f"API initialized for sport: {self.current_sport}")

    def is_initialized(self) -> bool:
        """Check if the context is fully initialized (authenticated + API ready)."""
        return self.api is not None

    def close(self):
        """Clean up resources."""
        if self.api:
            self.api.close()
        self.firebase_auth.close()
        self.sms_auth.close()


class BaseService:
    """
    Base class for all services.

    Each service receives the shared context and provides focused functionality.
    """

    def __init__(self, context: ServiceContext):
        self.context = context

    @property
    def config(self) -> Config:
        return self.context.config

    @property
    def api(self) -> BeyondAPI:
        if not self.context.api:
            raise RuntimeError("API not initialized. Call context.setup_api() first.")
        return self.context.api

    @property
    def current_sport(self) -> str:
        return self.context.current_sport

    @property
    def sport_config(self) -> SportConfig:
        return self.context.get_sport_config()

    def require_initialized(self):
        """Raise error if context is not fully initialized."""
        if not self.context.is_initialized():
            raise RuntimeError("Service not initialized. Call initialize() first.")
