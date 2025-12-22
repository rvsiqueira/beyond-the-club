"""Main bot orchestrator."""

import time
import logging
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
from dataclasses import dataclass, asdict, field

from .config import Config, load_config, SportConfig
from .firebase_auth import FirebaseAuth, FirebaseTokens
from .sms_auth import SMSAuth
from .beyond_api import BeyondAPI
from .session_monitor import SessionMonitor

logger = logging.getLogger(__name__)

TOKEN_CACHE_FILE = Path(__file__).parent.parent / ".beyondtheclub_tokens.json"
MEMBERS_CACHE_FILE = Path(__file__).parent.parent / ".beyondtheclub_members.json"


@dataclass
class SessionPreference:
    """A session preference with dynamic attributes per sport."""
    attributes: Dict[str, str] = field(default_factory=dict)

    # Convenience properties for surf (backwards compatibility)
    @property
    def level(self) -> str:
        return self.attributes.get("level", "")

    @property
    def wave_side(self) -> str:
        return self.attributes.get("wave_side", "")

    # Convenience property for tennis
    @property
    def court(self) -> str:
        return self.attributes.get("court", "")

    @classmethod
    def from_surf(cls, level: str, wave_side: str) -> "SessionPreference":
        """Create a surf session preference."""
        return cls(attributes={"level": level, "wave_side": wave_side})

    @classmethod
    def from_tennis(cls, court: str) -> "SessionPreference":
        """Create a tennis session preference."""
        return cls(attributes={"court": court})


@dataclass
class MemberPreferences:
    """Preferences for a member for a specific sport."""
    sessions: List[SessionPreference]
    target_hours: List[str]
    target_dates: List[str]


@dataclass
class Member:
    """A member from the title."""
    member_id: int
    name: str
    social_name: str
    is_titular: bool
    usage: int
    limit: int


class BeyondBot:
    """Main bot that orchestrates authentication and session monitoring."""

    def __init__(self, config: Optional[Config] = None):
        self.config = config or load_config()
        self.firebase_auth = FirebaseAuth(self.config.firebase, on_tokens_updated=self._save_tokens)
        self.sms_auth = SMSAuth(self.firebase_auth, self.config.api_base_url)
        self.api: Optional[BeyondAPI] = None
        self.monitor: Optional[SessionMonitor] = None
        self._running = False
        self._members_cache: Dict[str, Any] = {}
        self._selected_members: List[int] = []
        self._current_sport: str = "surf"  # Default sport

    def set_sport(self, sport: str):
        """Set the current sport context."""
        available = self.config.get_available_sports()
        if sport not in available:
            raise ValueError(f"Sport '{sport}' not available. Available: {available}")
        self._current_sport = sport
        logger.info(f"Sport context set to: {sport}")

    def get_sport_config(self) -> SportConfig:
        """Get the SportConfig for the current sport."""
        return self.config.get_sport_config(self._current_sport)

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

    # --- Members Cache Methods ---

    def _load_members_cache(self) -> Dict[str, Any]:
        """Load members cache from file."""
        try:
            if not MEMBERS_CACHE_FILE.exists():
                return {"members": [], "preferences": {}, "last_updated": None}

            data = json.loads(MEMBERS_CACHE_FILE.read_text())
            self._members_cache = data
            return data
        except Exception as e:
            logger.warning(f"Could not load members cache: {e}")
            return {"members": [], "preferences": {}, "last_updated": None}

    def _save_members_cache(self):
        """Save members cache to file."""
        try:
            self._members_cache["last_updated"] = datetime.now().isoformat()
            MEMBERS_CACHE_FILE.write_text(json.dumps(self._members_cache, indent=2))
            logger.debug("Members cache saved")
        except Exception as e:
            logger.warning(f"Could not save members cache: {e}")

    def _migrate_preferences_if_needed(self):
        """Migrate old flat preferences to per-sport format."""
        if not self._members_cache.get("preferences"):
            return

        migrated = False
        for member_id, prefs in self._members_cache["preferences"].items():
            # Check if already in new format (has sport keys)
            if isinstance(prefs, dict) and "sessions" in prefs:
                # Old format: {sessions: [...], target_hours: [...], target_dates: [...]}
                # Migrate to: {surf: {sessions: [...], ...}}
                self._members_cache["preferences"][member_id] = {
                    "surf": prefs
                }
                migrated = True
                logger.info(f"Migrated preferences for member {member_id} to multi-sport format")

        if migrated:
            self._save_members_cache()

    def refresh_members(self) -> List[Member]:
        """Fetch members from API and update cache."""
        if not self.api:
            raise RuntimeError("Bot not initialized. Call initialize() first.")

        response = self.api.get_schedule_status(self._current_sport)
        members_data = response.get("value", [])

        members = []
        for item in members_data:
            member_info = item.get("member", {})
            member = Member(
                member_id=member_info.get("memberId"),
                name=member_info.get("name", ""),
                social_name=member_info.get("socialName", ""),
                is_titular=member_info.get("isTitular", False),
                usage=item.get("usage", 0),
                limit=item.get("limit", 0)
            )
            members.append(member)

        # Update cache with new members list
        self._members_cache["members"] = [asdict(m) for m in members]
        self._save_members_cache()

        logger.info(f"Refreshed {len(members)} members from API")
        return members

    def get_members(self, force_refresh: bool = False) -> List[Member]:
        """Get members list (from cache or API)."""
        if not self._members_cache:
            self._load_members_cache()
            self._migrate_preferences_if_needed()

        if force_refresh or not self._members_cache.get("members"):
            return self.refresh_members()

        # Return cached members
        members = []
        for m in self._members_cache.get("members", []):
            members.append(Member(
                member_id=m["member_id"],
                name=m["name"],
                social_name=m["social_name"],
                is_titular=m["is_titular"],
                usage=m["usage"],
                limit=m["limit"]
            ))
        return members

    def get_member_by_id(self, member_id: int) -> Optional[Member]:
        """Get a specific member by ID."""
        members = self.get_members()
        for m in members:
            if m.member_id == member_id:
                return m
        return None

    def get_member_by_name(self, name: str) -> Optional[Member]:
        """Get a specific member by name (case insensitive)."""
        members = self.get_members()
        name_lower = name.lower()
        for m in members:
            if m.social_name.lower() == name_lower or m.name.lower() == name_lower:
                return m
        return None

    def get_member_preferences(self, member_id: int, sport: Optional[str] = None) -> Optional[MemberPreferences]:
        """Get preferences for a specific member and sport."""
        if not self._members_cache:
            self._load_members_cache()
            self._migrate_preferences_if_needed()

        sport = sport or self._current_sport
        member_prefs = self._members_cache.get("preferences", {}).get(str(member_id))

        if not member_prefs:
            return None

        # Handle both old format (direct) and new format (per-sport)
        if "sessions" in member_prefs:
            # Old format - assume it's for surf
            if sport != "surf":
                return None
            prefs_data = member_prefs
        else:
            # New format - get sport-specific prefs
            prefs_data = member_prefs.get(sport)

        if not prefs_data:
            return None

        sessions = []
        for s in prefs_data.get("sessions", []):
            # Handle both old format (level, wave_side) and new format (attributes)
            if "attributes" in s:
                sessions.append(SessionPreference(attributes=s["attributes"]))
            elif "level" in s and "wave_side" in s:
                # Old surf format
                sessions.append(SessionPreference.from_surf(s["level"], s["wave_side"]))
            elif "court" in s:
                # Tennis format
                sessions.append(SessionPreference.from_tennis(s["court"]))

        return MemberPreferences(
            sessions=sessions,
            target_hours=prefs_data.get("target_hours", []),
            target_dates=prefs_data.get("target_dates", [])
        )

    def set_member_preferences(self, member_id: int, preferences: MemberPreferences, sport: Optional[str] = None):
        """Set preferences for a specific member and sport."""
        if not self._members_cache:
            self._load_members_cache()
            self._migrate_preferences_if_needed()

        sport = sport or self._current_sport

        if "preferences" not in self._members_cache:
            self._members_cache["preferences"] = {}

        member_id_str = str(member_id)
        if member_id_str not in self._members_cache["preferences"]:
            self._members_cache["preferences"][member_id_str] = {}

        # Ensure it's in new format
        if "sessions" in self._members_cache["preferences"][member_id_str]:
            # Migrate old format
            old_prefs = self._members_cache["preferences"][member_id_str]
            self._members_cache["preferences"][member_id_str] = {"surf": old_prefs}

        self._members_cache["preferences"][member_id_str][sport] = {
            "sessions": [{"attributes": s.attributes} for s in preferences.sessions],
            "target_hours": preferences.target_hours,
            "target_dates": preferences.target_dates
        }
        self._save_members_cache()
        logger.info(f"Saved {sport} preferences for member {member_id}")

    def clear_member_preferences(self, member_id: int, sport: Optional[str] = None):
        """Clear preferences for a specific member and sport."""
        if not self._members_cache:
            self._load_members_cache()
            self._migrate_preferences_if_needed()

        sport = sport or self._current_sport
        member_id_str = str(member_id)

        if "preferences" in self._members_cache and member_id_str in self._members_cache["preferences"]:
            member_prefs = self._members_cache["preferences"][member_id_str]

            if isinstance(member_prefs, dict) and sport in member_prefs:
                del member_prefs[sport]
                # Clean up if no sports left
                if not member_prefs:
                    del self._members_cache["preferences"][member_id_str]
            elif "sessions" in member_prefs and sport == "surf":
                # Old format, remove entirely for surf
                del self._members_cache["preferences"][member_id_str]

            self._save_members_cache()
            logger.info(f"Cleared {sport} preferences for member {member_id}")

    def has_member_preferences(self, member_id: int, sport: Optional[str] = None) -> bool:
        """Check if a member has preferences configured for a sport."""
        prefs = self.get_member_preferences(member_id, sport)
        return prefs is not None and len(prefs.sessions) > 0

    def get_member_sports_with_preferences(self, member_id: int) -> List[str]:
        """Get list of sports for which a member has preferences."""
        if not self._members_cache:
            self._load_members_cache()
            self._migrate_preferences_if_needed()

        member_prefs = self._members_cache.get("preferences", {}).get(str(member_id), {})

        if not member_prefs:
            return []

        # Handle old format
        if "sessions" in member_prefs:
            return ["surf"] if member_prefs.get("sessions") else []

        # New format - return sports with sessions
        return [sport for sport, data in member_prefs.items()
                if isinstance(data, dict) and data.get("sessions")]

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
        self.monitor = SessionMonitor(
            self.api,
            self.config.session,
            get_member_preferences=lambda mid: self.get_member_preferences(mid, self._current_sport),
            sport=self._current_sport,
            sport_config=self.get_sport_config()
        )
        logger.info(f"Bot initialized successfully for sport: {self._current_sport}")

    def run_once(self) -> int:
        """
        Run a single check for available sessions.

        Returns:
            Number of sessions booked
        """
        if not self.monitor:
            raise RuntimeError("Bot not initialized. Call initialize() first.")

        # Update monitor with current sport config
        self.monitor.sport = self._current_sport
        self.monitor.sport_config = self.get_sport_config()

        # If we have selected members, use multi-member check
        if self._selected_members:
            members = []
            for member_id in self._selected_members:
                member = self.get_member_by_id(member_id)
                if member:
                    members.append({
                        "member_id": member.member_id,
                        "social_name": member.social_name
                    })

            results = self.monitor.run_check_for_members(
                members,
                auto_book=self.config.bot.auto_book
            )
            return len([r for r in results if r.success])

        # Fallback to global config
        available = self.monitor.run_check(auto_book=self.config.bot.auto_book)
        return len([s for s in available if s.id in self.monitor.get_booked_sessions()])

    def run(self):
        """Run the bot continuously with configured interval."""
        if not self.monitor:
            raise RuntimeError("Bot not initialized. Call initialize() first.")

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
                        # Format sessions based on sport attributes
                        sessions_strs = []
                        for s in prefs.sessions:
                            attrs = "/".join(s.attributes.values())
                            sessions_strs.append(attrs)
                        member_names.append(f"{member.social_name} ({', '.join(sessions_strs)})")
                    else:
                        member_names.append(member.social_name)
            logger.info(f"Monitoring members: {', '.join(member_names)}")
        else:
            # Log sport-specific options
            for attr_name in sport_config.get_attributes():
                options = sport_config.get_options(attr_name)
                label = sport_config.attribute_labels.get(attr_name, attr_name)
                logger.info(f"Monitoring {label}: {options}")

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
