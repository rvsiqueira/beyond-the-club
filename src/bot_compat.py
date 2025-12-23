"""
Compatibility layer for BeyondBot.

This module provides a BeyondBot-compatible interface that uses the new
services layer internally. This allows the CLI (main.py) to continue working
unchanged while we migrate to the services architecture.

Usage:
    # In main.py, just change the import:
    # from src.bot import BeyondBot
    from src.bot_compat import BeyondBot

The interface is 100% compatible with the original BeyondBot.
"""

import logging
from typing import Optional, List, Dict, Any, Callable
from pathlib import Path

from .config import Config, load_config, SportConfig
from .firebase_auth import FirebaseAuth, FirebaseTokens
from .sms_auth import SMSAuth
from .services import (
    ServiceContext,
    AuthService,
    MemberService,
    AvailabilityService,
    BookingService,
    MonitorService,
    Member,
    MemberPreferences,
    SessionPreference,
    AvailableSlot,
)

logger = logging.getLogger(__name__)


class BeyondBot:
    """
    Compatibility wrapper that provides the original BeyondBot interface
    using the new services layer internally.

    This is a drop-in replacement for the original BeyondBot class.
    """

    def __init__(self, config: Optional[Config] = None):
        self.config = config or load_config()

        # Create context with token saving callback
        self._context = ServiceContext.create(
            config=self.config,
            on_tokens_updated=self._save_tokens
        )

        # Create services
        self._auth_service = AuthService(self._context)
        self._member_service = MemberService(self._context)
        self._availability_service = AvailabilityService(
            self._context, self._member_service
        )
        self._booking_service = BookingService(
            self._context, self._member_service, self._availability_service
        )
        self._monitor_service = MonitorService(
            self._context,
            self._member_service,
            self._availability_service,
            self._booking_service
        )

        # State for compatibility
        self._running = False
        self._selected_members: List[int] = []

    # === Property accessors for compatibility ===

    @property
    def firebase_auth(self) -> FirebaseAuth:
        return self._context.firebase_auth

    @property
    def sms_auth(self) -> SMSAuth:
        return self._context.sms_auth

    @property
    def api(self):
        return self._context.api

    @property
    def _current_sport(self) -> str:
        return self._context.current_sport

    @_current_sport.setter
    def _current_sport(self, value: str):
        self._context.current_sport = value

    # === Sport Configuration ===

    def set_sport(self, sport: str):
        """Set the current sport context."""
        self._context.set_sport(sport)

    def get_sport_config(self) -> SportConfig:
        """Get the SportConfig for the current sport."""
        return self._context.get_sport_config()

    # === Token Management (delegated to AuthService) ===

    def _save_tokens(self, tokens: FirebaseTokens):
        """Save tokens to cache file."""
        self._auth_service.save_tokens(tokens)

    def _load_tokens(self) -> Optional[FirebaseTokens]:
        """Load tokens from cache file."""
        return self._auth_service.load_tokens()

    # === Member Management (delegated to MemberService) ===

    def refresh_members(self) -> List[Member]:
        """Fetch members from API and update cache."""
        return self._member_service.refresh_members()

    def get_members(self, force_refresh: bool = False) -> List[Member]:
        """Get members list (from cache or API)."""
        return self._member_service.get_members(force_refresh)

    def get_member_by_id(self, member_id: int) -> Optional[Member]:
        """Get a specific member by ID."""
        return self._member_service.get_member_by_id(member_id)

    def get_member_by_name(self, name: str) -> Optional[Member]:
        """Get a specific member by name (case insensitive)."""
        return self._member_service.get_member_by_name(name)

    def get_member_preferences(
        self, member_id: int, sport: Optional[str] = None
    ) -> Optional[MemberPreferences]:
        """Get preferences for a specific member and sport."""
        return self._member_service.get_member_preferences(member_id, sport)

    def set_member_preferences(
        self, member_id: int, preferences: MemberPreferences, sport: Optional[str] = None
    ):
        """Set preferences for a specific member and sport."""
        self._member_service.set_member_preferences(member_id, preferences, sport)

    def clear_member_preferences(self, member_id: int, sport: Optional[str] = None):
        """Clear preferences for a specific member and sport."""
        self._member_service.clear_member_preferences(member_id, sport)

    def has_member_preferences(self, member_id: int, sport: Optional[str] = None) -> bool:
        """Check if a member has preferences configured for a sport."""
        return self._member_service.has_member_preferences(member_id, sport)

    def get_member_sports_with_preferences(self, member_id: int) -> List[str]:
        """Get list of sports for which a member has preferences."""
        return self._member_service.get_member_sports_with_preferences(member_id)

    def get_members_without_booking(self) -> List[Member]:
        """Get members that don't have an active booking."""
        return self._member_service.get_members_without_booking()

    # === Authentication (delegated to AuthService) ===

    def authenticate_admin(self) -> FirebaseTokens:
        """Authenticate with admin credentials to get initial token."""
        return self._auth_service.authenticate_admin()

    def authenticate_user_sms(self, sms_code: Optional[str] = None) -> FirebaseTokens:
        """Authenticate user via SMS."""
        return self._auth_service.authenticate_user_sms(sms_code)

    def initialize(self, sms_code: Optional[str] = None, use_cached: bool = True) -> bool:
        """Initialize the bot with authentication."""
        return self._auth_service.initialize(sms_code, use_cached)

    def _setup_api_and_monitor(self):
        """Set up the API client (compatibility method)."""
        self._context.setup_api()

    # === Availability (delegated to AvailabilityService) ===

    def _load_availability_cache(self) -> Dict[str, Any]:
        """Load availability cache from file."""
        return self._availability_service._load_cache()

    def _save_availability_cache(self, cache: Dict[str, Any]):
        """Save availability cache to file."""
        self._availability_service._save_cache(cache)

    def is_availability_cache_valid(self) -> bool:
        """Check if availability cache is valid."""
        return self._availability_service.is_cache_valid()

    def get_availability_cache(self) -> Dict[str, Any]:
        """Get the availability cache."""
        return self._availability_service.get_cache()

    def scan_availability(self) -> List[AvailableSlot]:
        """Scan all level/wave_side combinations and return available slots."""
        return self._availability_service.scan_availability()

    def get_slots_from_cache(self) -> List[AvailableSlot]:
        """Get available slots from cache."""
        return self._availability_service.get_slots_from_cache()

    def _find_slot_for_combo(
        self,
        level: str,
        wave_side: str,
        member_id: int,
        target_dates: Optional[List[str]] = None,
        target_hours: Optional[List[str]] = None
    ) -> Optional[AvailableSlot]:
        """Fast search for available slot for a specific level/wave_side combo."""
        return self._availability_service.find_slot_for_combo(
            level, wave_side, member_id, target_dates, target_hours
        )

    # === Booking (delegated to BookingService) ===

    def create_booking_for_slot(
        self,
        slot: AvailableSlot,
        member_id: int
    ) -> dict:
        """Create a booking for a specific slot and member."""
        return self._booking_service.create_booking(slot, member_id)

    def swap_booking(
        self,
        voucher_code: str,
        new_member_id: int,
        slot: AvailableSlot
    ) -> dict:
        """Swap a booking from one member to another atomically."""
        return self._booking_service.swap_booking(voucher_code, new_member_id, slot)

    def find_matching_slot_for_member(
        self,
        member_id: int,
        target_dates: Optional[List[str]] = None,
        refresh_availability: bool = True
    ) -> Optional[AvailableSlot]:
        """Find the first available slot matching member's preferences."""
        return self._booking_service.find_matching_slot(
            member_id, target_dates, refresh_availability
        )

    # === Monitor (delegated to MonitorService) ===

    def run_auto_monitor(
        self,
        member_ids: List[int],
        target_dates: Optional[List[str]] = None,
        duration_minutes: int = 120,
        check_interval_seconds: int = 30,
        on_status_update: Optional[Callable[[str, str], None]] = None
    ) -> Dict[int, dict]:
        """Run automatic monitoring and booking for selected members."""
        return self._monitor_service.run_auto_monitor(
            member_ids=member_ids,
            target_dates=target_dates,
            duration_minutes=duration_minutes,
            check_interval_seconds=check_interval_seconds,
            on_status_update=on_status_update
        )

    # === Legacy run methods (for continuous monitoring) ===

    def run_once(self) -> int:
        """Run a single check for available sessions."""
        if not self._selected_members:
            logger.warning("No members selected for monitoring")
            return 0

        results = self._monitor_service.run_single_check(
            member_ids=self._selected_members,
            auto_book=self.config.bot.auto_book
        )

        return len([r for r in results.values() if r.get("success")])

    def run(self):
        """Run the bot continuously with configured interval."""
        import time

        self._running = True
        interval = self.config.bot.check_interval_seconds
        sport_config = self.get_sport_config()

        logger.info(f"Starting bot with {interval}s check interval for {sport_config.name}")

        if self._selected_members:
            member_names = []
            for member_id in self._selected_members:
                member = self.get_member_by_id(member_id)
                if member:
                    prefs = self.get_member_preferences(member_id, self._current_sport)
                    if prefs:
                        sessions_strs = []
                        for s in prefs.sessions:
                            attrs = "/".join(s.attributes.values())
                            sessions_strs.append(attrs)
                        member_names.append(f"{member.social_name} ({', '.join(sessions_strs)})")
                    else:
                        member_names.append(member.social_name)
            logger.info(f"Monitoring members: {', '.join(member_names)}")

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
        self._monitor_service.stop()

    def close(self):
        """Clean up resources."""
        self._context.close()


# Re-export data classes for compatibility
__all__ = [
    "BeyondBot",
    "Member",
    "MemberPreferences",
    "SessionPreference",
    "AvailableSlot",
]
