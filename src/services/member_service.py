"""
Member management service.

Handles member data, preferences, and caching.
Cache is per-user (phone) to ensure data isolation.
"""

import json
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
from dataclasses import dataclass, asdict, field

from .base import BaseService, ServiceContext

logger = logging.getLogger(__name__)

# Directory for per-user member caches
MEMBERS_CACHE_DIR = Path(__file__).parent.parent.parent / "data" / "members_cache"
PREFERENCES_CACHE_FILE = Path(__file__).parent.parent.parent / ".beyondtheclub_preferences.json"


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

    def get_combo_key(self) -> str:
        """Get combo key from attributes (e.g., 'Iniciante1/Lado_esquerdo')."""
        if self.level and self.wave_side:
            return f"{self.level}/{self.wave_side}"
        elif self.court:
            return self.court
        else:
            return "/".join(self.attributes.values())


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


class MemberService(BaseService):
    """
    Service for managing members and their preferences.

    Members cache is per-user (identified by phone) to ensure data isolation.
    Preferences cache is global (member preferences are shared).

    Responsibilities:
    - Load/save member cache per user
    - Refresh members from API
    - Manage member preferences (per sport)
    - Find members by ID or name
    """

    def __init__(self, context: ServiceContext):
        super().__init__(context)
        self._members_cache: Dict[str, Any] = {}
        self._prefs_cache: Dict[str, Any] = {}
        self._members_loaded = False
        self._prefs_loaded = False
        self._current_user_phone: Optional[str] = None

    def _get_user_cache_file(self, phone: str) -> Path:
        """Get the cache file path for a specific user."""
        # Sanitize phone for filename (remove + and spaces)
        safe_phone = phone.replace("+", "").replace(" ", "").replace("-", "")
        return MEMBERS_CACHE_DIR / f"members_{safe_phone}.json"

    def _ensure_cache_dir(self):
        """Ensure the cache directory exists."""
        MEMBERS_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    def set_current_user(self, phone: str):
        """Set the current user for member operations."""
        if self._current_user_phone != phone:
            # Reset cache when user changes
            self._members_cache = {}
            self._members_loaded = False
            self._current_user_phone = phone
            logger.debug(f"Switched member cache context to user {phone}")

    def _load_members_cache(self) -> Dict[str, Any]:
        """Load members cache from file for current user."""
        if not self._current_user_phone:
            logger.warning("No current user set, returning empty members cache")
            return {"members": [], "last_updated": None}

        if self._members_loaded:
            return self._members_cache

        try:
            cache_file = self._get_user_cache_file(self._current_user_phone)
            if not cache_file.exists():
                self._members_cache = {"members": [], "last_updated": None}
            else:
                self._members_cache = json.loads(cache_file.read_text())
            self._members_loaded = True
            logger.debug(f"Loaded members cache for {self._current_user_phone}: {len(self._members_cache.get('members', []))} members")
            return self._members_cache
        except Exception as e:
            logger.warning(f"Could not load members cache for {self._current_user_phone}: {e}")
            self._members_cache = {"members": [], "last_updated": None}
            self._members_loaded = True
            return self._members_cache

    def _load_prefs_cache(self) -> Dict[str, Any]:
        """Load preferences cache from file."""
        if self._prefs_loaded:
            return self._prefs_cache

        try:
            if not PREFERENCES_CACHE_FILE.exists():
                self._prefs_cache = {"preferences": {}, "last_updated": None}
            else:
                self._prefs_cache = json.loads(PREFERENCES_CACHE_FILE.read_text())
            self._prefs_loaded = True
            self._migrate_preferences_if_needed()
            return self._prefs_cache
        except Exception as e:
            logger.warning(f"Could not load preferences cache: {e}")
            self._prefs_cache = {"preferences": {}, "last_updated": None}
            self._prefs_loaded = True
            return self._prefs_cache

    def _save_members_cache(self):
        """Save members cache to file for current user."""
        if not self._current_user_phone:
            logger.warning("No current user set, cannot save members cache")
            return

        try:
            self._ensure_cache_dir()
            cache_file = self._get_user_cache_file(self._current_user_phone)
            self._members_cache["last_updated"] = datetime.now().isoformat()
            cache_file.write_text(json.dumps(self._members_cache, indent=2))
            logger.debug(f"Members cache saved for {self._current_user_phone}")
        except Exception as e:
            logger.warning(f"Could not save members cache for {self._current_user_phone}: {e}")

    def _save_prefs_cache(self):
        """Save preferences cache to file."""
        try:
            self._prefs_cache["last_updated"] = datetime.now().isoformat()
            PREFERENCES_CACHE_FILE.write_text(json.dumps(self._prefs_cache, indent=2))
            logger.debug("Preferences cache saved")
        except Exception as e:
            logger.warning(f"Could not save preferences cache: {e}")

    def _migrate_preferences_if_needed(self):
        """Migrate old flat preferences to per-sport format."""
        if not self._prefs_cache.get("preferences"):
            return

        migrated = False
        for member_id, prefs in self._prefs_cache["preferences"].items():
            # Check if already in new format (has sport keys)
            if isinstance(prefs, dict) and "sessions" in prefs:
                # Old format: {sessions: [...], target_hours: [...], target_dates: [...]}
                # Migrate to: {surf: {sessions: [...], ...}}
                self._prefs_cache["preferences"][member_id] = {"surf": prefs}
                migrated = True
                logger.info(f"Migrated preferences for member {member_id} to multi-sport format")

        if migrated:
            self._save_prefs_cache()

    def refresh_members(self) -> List[Member]:
        """Fetch members from API and update cache for current user."""
        self.require_initialized()

        if not self._current_user_phone:
            logger.warning("No current user set, cannot refresh members")
            return []

        response = self.api.get_schedule_status(self.current_sport)
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

        # Update members cache for this user
        self._load_members_cache()
        self._members_cache["members"] = [asdict(m) for m in members]
        self._save_members_cache()

        logger.info(f"Refreshed {len(members)} members from API for user {self._current_user_phone}")
        return members

    def get_members(self, force_refresh: bool = False) -> List[Member]:
        """Get members list (from cache or API) for current user."""
        self._load_members_cache()

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

    def get_member_preferences(
        self,
        member_id: int,
        sport: Optional[str] = None
    ) -> Optional[MemberPreferences]:
        """Get preferences for a specific member and sport."""
        self._load_prefs_cache()

        sport = sport or self.current_sport
        member_prefs = self._prefs_cache.get("preferences", {}).get(str(member_id))

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

    def set_member_preferences(
        self,
        member_id: int,
        preferences: MemberPreferences,
        sport: Optional[str] = None
    ):
        """Set preferences for a specific member and sport."""
        self._load_prefs_cache()

        sport = sport or self.current_sport

        if "preferences" not in self._prefs_cache:
            self._prefs_cache["preferences"] = {}

        member_id_str = str(member_id)
        if member_id_str not in self._prefs_cache["preferences"]:
            self._prefs_cache["preferences"][member_id_str] = {}

        # Ensure it's in new format
        if "sessions" in self._prefs_cache["preferences"][member_id_str]:
            # Migrate old format
            old_prefs = self._prefs_cache["preferences"][member_id_str]
            self._prefs_cache["preferences"][member_id_str] = {"surf": old_prefs}

        self._prefs_cache["preferences"][member_id_str][sport] = {
            "sessions": [{"attributes": s.attributes} for s in preferences.sessions],
            "target_hours": preferences.target_hours,
            "target_dates": preferences.target_dates
        }
        self._save_prefs_cache()
        logger.info(f"Saved {sport} preferences for member {member_id}")

    def clear_member_preferences(self, member_id: int, sport: Optional[str] = None):
        """Clear preferences for a specific member and sport."""
        self._load_prefs_cache()

        sport = sport or self.current_sport
        member_id_str = str(member_id)

        if "preferences" in self._prefs_cache and member_id_str in self._prefs_cache["preferences"]:
            member_prefs = self._prefs_cache["preferences"][member_id_str]

            if isinstance(member_prefs, dict) and sport in member_prefs:
                del member_prefs[sport]
                # Clean up if no sports left
                if not member_prefs:
                    del self._prefs_cache["preferences"][member_id_str]
            elif "sessions" in member_prefs and sport == "surf":
                # Old format, remove entirely for surf
                del self._prefs_cache["preferences"][member_id_str]

            self._save_prefs_cache()
            logger.info(f"Cleared {sport} preferences for member {member_id}")

    def has_member_preferences(self, member_id: int, sport: Optional[str] = None) -> bool:
        """Check if a member has preferences configured for a sport."""
        prefs = self.get_member_preferences(member_id, sport)
        return prefs is not None and len(prefs.sessions) > 0

    def get_member_sports_with_preferences(self, member_id: int) -> List[str]:
        """Get list of sports for which a member has preferences."""
        self._load_prefs_cache()

        member_prefs = self._prefs_cache.get("preferences", {}).get(str(member_id), {})

        if not member_prefs:
            return []

        # Handle old format
        if "sessions" in member_prefs:
            return ["surf"] if member_prefs.get("sessions") else []

        # New format - return sports with sessions
        return [sport for sport, data in member_prefs.items()
                if isinstance(data, dict) and data.get("sessions")]

    def get_members_without_booking(self) -> List[Member]:
        """
        Get members that don't have an active booking.

        Returns:
            List of members without active (AccessReady) bookings
        """
        self.require_initialized()

        members = self.get_members()
        bookings = self.api.list_bookings(self.current_sport)

        # Get member IDs with active bookings
        booked_member_ids = set()
        for booking in bookings:
            status = booking.get("status", "")
            if status == "AccessReady":
                member = booking.get("member", {})
                member_id = member.get("memberId")
                if member_id:
                    booked_member_ids.add(member_id)

        # Filter out members with active bookings
        available_members = [m for m in members if m.member_id not in booked_member_ids]
        return available_members
