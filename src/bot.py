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
AVAILABILITY_CACHE_FILE = Path(__file__).parent.parent / ".beyondtheclub_availability.json"


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


@dataclass
class AvailableSlot:
    """Represents an available time slot."""
    date: str
    interval: str
    level: str
    wave_side: str
    available: int
    max_quantity: int
    package_id: int
    product_id: int

    @property
    def combo_key(self) -> str:
        """Return the level/wave_side combo key."""
        return f"{self.level}/{self.wave_side}"

    def to_dict(self) -> dict:
        return {
            "date": self.date,
            "interval": self.interval,
            "level": self.level,
            "wave_side": self.wave_side,
            "available": self.available,
            "max": self.max_quantity,
            "packageId": self.package_id,
            "productId": self.product_id
        }


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

    # --- Availability Cache Methods ---

    def _load_availability_cache(self) -> Dict[str, Any]:
        """Load availability cache from file."""
        try:
            if not AVAILABILITY_CACHE_FILE.exists():
                return {"scanned_at": None, "dates": {}, "packages": {}}

            data = json.loads(AVAILABILITY_CACHE_FILE.read_text())
            return data
        except Exception as e:
            logger.warning(f"Could not load availability cache: {e}")
            return {"scanned_at": None, "dates": {}, "packages": {}}

    def _save_availability_cache(self, cache: Dict[str, Any]):
        """Save availability cache to file."""
        try:
            cache["scanned_at"] = datetime.now().isoformat()
            AVAILABILITY_CACHE_FILE.write_text(json.dumps(cache, indent=2))
            logger.debug("Availability cache saved")
        except Exception as e:
            logger.warning(f"Could not save availability cache: {e}")

    def is_availability_cache_valid(self) -> bool:
        """
        Check if availability cache is valid (has dates >= today).

        Returns:
            True if cache exists and all dates are >= today
        """
        cache = self._load_availability_cache()
        if not cache.get("dates"):
            return False

        today = datetime.now().strftime("%Y-%m-%d")
        for date_str in cache["dates"].keys():
            if date_str < today:
                return False

        return True

    def get_availability_cache(self) -> Dict[str, Any]:
        """Get the availability cache."""
        return self._load_availability_cache()

    def scan_availability(self) -> List[AvailableSlot]:
        """
        Scan all level/wave_side combinations and return available slots.

        Returns:
            List of AvailableSlot objects
        """
        if not self.api:
            raise RuntimeError("Bot not initialized. Call initialize() first.")

        sport_config = self.get_sport_config()
        members = self.get_members()
        if not members:
            raise RuntimeError("No members found")

        # Use any member for the intervals query
        any_member_id = members[0].member_id

        all_slots = []
        cache = {"scanned_at": None, "dates": {}, "packages": {}}

        # Get all level/wave_side combinations
        levels = sport_config.get_options("level")
        wave_sides = sport_config.get_options("wave_side")

        for level in levels:
            for wave_side in wave_sides:
                combo_key = f"{level}/{wave_side}"
                tags = list(sport_config.base_tags) + [level, wave_side]

                logger.info(f"Scanning {combo_key}...")

                try:
                    # Get available dates for this combination
                    dates_response = self.api.get_available_dates(tags, sport=self._current_sport)

                    # Handle API response wrapper
                    if isinstance(dates_response, dict) and "value" in dates_response:
                        dates_list = dates_response["value"]
                    else:
                        dates_list = dates_response

                    # Parse dates (they come as "2025-12-26T00:00:00")
                    dates = []
                    for date_item in dates_list:
                        if isinstance(date_item, str):
                            # Extract just the date part
                            date_str = date_item.split("T")[0]
                            dates.append(date_str)

                    logger.info(f"  Found {len(dates)} dates for {combo_key}")

                    for date in dates:
                        try:
                            # Get intervals for this date
                            intervals_data = self.api.get_intervals(
                                date=date,
                                tags=tags,
                                member_id=any_member_id,
                                sport=self._current_sport
                            )

                            # Parse the packages from response
                            # Structure: value[] -> each has packageId and products[]
                            packages_list = intervals_data if isinstance(intervals_data, list) else []

                            for package in packages_list:
                                package_id = package.get("packageId")
                                products = package.get("products", [])

                                for product in products:
                                    product_id = product.get("productId", package_id)

                                    # Store package mapping
                                    cache["packages"][combo_key] = {
                                        "packageId": package_id,
                                        "productId": product_id
                                    }

                                    invitation = product.get("invitation", {})
                                    solos = invitation.get("solos", [])

                                    for solo in solos:
                                        if solo.get("isAvailable", False):
                                            slot = AvailableSlot(
                                                date=date,
                                                interval=solo.get("interval", ""),
                                                level=level,
                                                wave_side=wave_side,
                                                available=solo.get("availableQuantity", 0),
                                                max_quantity=solo.get("maxQuantity", 0),
                                                package_id=package_id,
                                                product_id=product_id
                                            )
                                            all_slots.append(slot)

                                            # Add to cache
                                            if date not in cache["dates"]:
                                                cache["dates"][date] = {}
                                            if combo_key not in cache["dates"][date]:
                                                cache["dates"][date][combo_key] = []

                                            cache["dates"][date][combo_key].append({
                                                "interval": slot.interval,
                                                "available": slot.available,
                                                "max": slot.max_quantity
                                            })

                        except Exception as e:
                            logger.error(f"Error getting intervals for {date} {combo_key}: {e}")

                except Exception as e:
                    logger.error(f"Error scanning {combo_key}: {e}")

        # Save cache
        self._save_availability_cache(cache)
        logger.info(f"Scan complete. Found {len(all_slots)} available slots.")

        return all_slots

    def get_slots_from_cache(self) -> List[AvailableSlot]:
        """
        Get available slots from cache.

        Returns:
            List of AvailableSlot objects from cache
        """
        cache = self._load_availability_cache()
        slots = []

        packages = cache.get("packages", {})

        for date, combos in cache.get("dates", {}).items():
            for combo_key, intervals in combos.items():
                parts = combo_key.split("/")
                if len(parts) != 2:
                    continue
                level, wave_side = parts

                pkg = packages.get(combo_key, {})
                package_id = pkg.get("packageId", 0)
                product_id = pkg.get("productId", 0)

                for interval_data in intervals:
                    slot = AvailableSlot(
                        date=date,
                        interval=interval_data.get("interval", ""),
                        level=level,
                        wave_side=wave_side,
                        available=interval_data.get("available", 0),
                        max_quantity=interval_data.get("max", 0),
                        package_id=package_id,
                        product_id=product_id
                    )
                    slots.append(slot)

        # Sort by date and interval
        slots.sort(key=lambda s: (s.date, s.interval, s.combo_key))
        return slots

    def create_booking_for_slot(
        self,
        slot: AvailableSlot,
        member_id: int
    ) -> dict:
        """
        Create a booking for a specific slot and member.

        Args:
            slot: The AvailableSlot to book
            member_id: The member ID to book for

        Returns:
            Booking response with voucherCode and accessCode
        """
        if not self.api:
            raise RuntimeError("Bot not initialized. Call initialize() first.")

        sport_config = self.get_sport_config()
        tags = list(sport_config.base_tags) + [slot.level, slot.wave_side]

        return self.api.create_booking(
            package_id=slot.package_id,
            product_id=slot.product_id,
            member_id=member_id,
            tags=tags,
            interval=slot.interval,
            date=slot.date,
            sport=self._current_sport
        )

    def swap_booking(
        self,
        voucher_code: str,
        new_member_id: int,
        slot: AvailableSlot
    ) -> dict:
        """
        Swap a booking from one member to another atomically.

        Args:
            voucher_code: The voucher code of the booking to cancel
            new_member_id: The new member ID to book for
            slot: The slot info for the new booking

        Returns:
            New booking response
        """
        if not self.api:
            raise RuntimeError("Bot not initialized. Call initialize() first.")

        # Cancel the old booking
        logger.info(f"Cancelling booking {voucher_code}...")
        self.api.cancel_booking(voucher_code, sport=self._current_sport)

        # Create new booking immediately
        logger.info(f"Creating new booking for member {new_member_id}...")
        return self.create_booking_for_slot(slot, new_member_id)

    def get_members_without_booking(self) -> List[Member]:
        """
        Get members that don't have an active booking.

        Returns:
            List of members without active (AccessReady) bookings
        """
        if not self.api:
            raise RuntimeError("Bot not initialized. Call initialize() first.")

        members = self.get_members()
        bookings = self.api.list_bookings(self._current_sport)

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

    def find_matching_slot_for_member(
        self,
        member_id: int,
        target_dates: Optional[List[str]] = None,
        refresh_availability: bool = True
    ) -> Optional[AvailableSlot]:
        """
        Find the first available slot matching member's preferences.

        Args:
            member_id: Member ID to find slot for
            target_dates: Optional list of specific dates (None = any date >= today)
            refresh_availability: If True, scan availability; if False, use cache

        Returns:
            First matching AvailableSlot or None
        """
        prefs = self.get_member_preferences(member_id, self._current_sport)
        if not prefs or not prefs.sessions:
            logger.warning(f"Member {member_id} has no preferences configured")
            return None

        # Get available slots
        if refresh_availability:
            slots = self.scan_availability()
        else:
            slots = self.get_slots_from_cache()

        if not slots:
            return None

        # Filter by target dates if specified
        today = datetime.now().strftime("%Y-%m-%d")
        if target_dates:
            slots = [s for s in slots if s.date in target_dates and s.date >= today]
        else:
            slots = [s for s in slots if s.date >= today]

        # Filter by target hours if configured in preferences
        if prefs.target_hours:
            slots = [s for s in slots if s.interval in prefs.target_hours]

        # Filter by target dates from preferences (additional filter)
        if prefs.target_dates:
            slots = [s for s in slots if s.date in prefs.target_dates]

        # Sort slots by date and interval
        slots.sort(key=lambda s: (s.date, s.interval))

        # Find first slot matching any preference (in priority order)
        for session_pref in prefs.sessions:
            pref_combo = f"{session_pref.level}/{session_pref.wave_side}"
            for slot in slots:
                if slot.combo_key == pref_combo and slot.available > 0:
                    return slot

        return None

    def run_auto_monitor(
        self,
        member_ids: List[int],
        target_dates: Optional[List[str]] = None,
        duration_minutes: int = 120,
        check_interval_seconds: int = 30,
        on_status_update: Optional[callable] = None
    ) -> Dict[int, dict]:
        """
        Run automatic monitoring and booking for selected members.

        OPTIMIZED: Only scans availability for each member's preferences,
        not all combinations. Tries to book immediately when slot is found.

        Args:
            member_ids: List of member IDs to monitor (without active bookings)
            target_dates: Optional list of specific dates (None = any date)
            duration_minutes: How long to run the monitor (default: 120 min)
            check_interval_seconds: How often to check (default: 30 sec)
            on_status_update: Optional callback for status updates

        Returns:
            Dict mapping member_id -> booking result (or error info)
        """
        if not self.api:
            raise RuntimeError("Bot not initialized. Call initialize() first.")

        results = {}
        pending_members = list(member_ids)  # Preserve order
        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)

        # Helper to log and optionally callback
        def status_update(msg: str, level: str = "info"):
            if level == "info":
                logger.info(msg)
            elif level == "error":
                logger.error(msg)
            elif level == "warning":
                logger.warning(msg)
            if on_status_update:
                on_status_update(msg, level)

        status_update(f"Auto-monitor iniciado para {len(pending_members)} membro(s)")
        status_update(f"Duracao: {duration_minutes} min | Intervalo: {check_interval_seconds}s")
        if target_dates:
            status_update(f"Datas alvo: {', '.join(target_dates)}")
        else:
            status_update("Datas alvo: Qualquer data disponivel")

        check_count = 0
        while pending_members and time.time() < end_time:
            check_count += 1
            elapsed = int(time.time() - start_time)
            remaining = int((end_time - time.time()) / 60)

            status_update(f"\n=== Check #{check_count} | {elapsed}s decorridos | {remaining} min restantes ===")
            status_update(f"Membros pendentes: {len(pending_members)}")

            # Process each pending member
            members_to_remove = []

            for member_id in pending_members:
                member = self.get_member_by_id(member_id)
                if not member:
                    status_update(f"Membro {member_id} nao encontrado", "warning")
                    members_to_remove.append(member_id)
                    continue

                prefs = self.get_member_preferences(member_id, self._current_sport)
                if not prefs or not prefs.sessions:
                    status_update(f"{member.social_name}: Sem preferencias configuradas", "warning")
                    members_to_remove.append(member_id)
                    results[member_id] = {"error": "Sem preferencias configuradas"}
                    continue

                status_update(f"\n{member.social_name}: Buscando slots...")

                # Try each preference in priority order
                booked = False
                for pref_idx, session_pref in enumerate(prefs.sessions, 1):
                    combo_key = f"{session_pref.level}/{session_pref.wave_side}"
                    status_update(f"  [{pref_idx}/{len(prefs.sessions)}] Verificando {combo_key}...")

                    try:
                        # Fast search for this specific combo
                        slot = self._find_slot_for_combo(
                            level=session_pref.level,
                            wave_side=session_pref.wave_side,
                            member_id=member_id,
                            target_dates=target_dates,
                            target_hours=prefs.target_hours
                        )

                        if slot:
                            status_update(f"  Slot encontrado! {slot.date} {slot.interval} ({slot.combo_key})")

                            try:
                                result = self.create_booking_for_slot(slot, member_id)
                                voucher = result.get("voucherCode", "N/A")
                                access = result.get("accessCode", result.get("invitation", {}).get("accessCode", "N/A"))

                                status_update(f"  AGENDADO! Voucher: {voucher} | Access: {access}")

                                results[member_id] = {
                                    "success": True,
                                    "voucher": voucher,
                                    "access_code": access,
                                    "slot": slot.to_dict(),
                                    "member_name": member.social_name
                                }
                                members_to_remove.append(member_id)
                                booked = True
                                break  # Stop checking other preferences

                            except Exception as e:
                                error_msg = str(e)
                                # Check if it's a "already booked" error
                                if "ja possui" in error_msg.lower() or "already" in error_msg.lower():
                                    status_update(f"  Membro ja possui agendamento ativo", "warning")
                                    members_to_remove.append(member_id)
                                    results[member_id] = {"error": "Ja possui agendamento ativo"}
                                    booked = True
                                    break
                                else:
                                    status_update(f"  Erro ao agendar: {e}", "error")
                                    # Continue to next preference
                        else:
                            status_update(f"  Nenhum slot disponivel para {combo_key}")

                    except Exception as e:
                        status_update(f"  Erro ao buscar {combo_key}: {e}", "error")

                if not booked:
                    pref_combos = [f"{s.level}/{s.wave_side}" for s in prefs.sessions]
                    status_update(f"  Nenhum slot encontrado para preferencias: {pref_combos}")

            # Remove processed members
            for mid in members_to_remove:
                if mid in pending_members:
                    pending_members.remove(mid)

            # Wait before next check
            if pending_members and time.time() < end_time:
                status_update(f"\nAguardando {check_interval_seconds}s para proximo check...")
                time.sleep(check_interval_seconds)

        # Final summary
        if not pending_members:
            status_update("\nTodos os membros foram agendados!")
        else:
            remaining_names = []
            for mid in pending_members:
                m = self.get_member_by_id(mid)
                remaining_names.append(m.social_name if m else str(mid))
            status_update(f"\nTempo esgotado. Membros nao agendados: {', '.join(remaining_names)}")

        return results

    def _find_slot_for_combo(
        self,
        level: str,
        wave_side: str,
        member_id: int,
        target_dates: Optional[List[str]] = None,
        target_hours: Optional[List[str]] = None
    ) -> Optional[AvailableSlot]:
        """
        Fast search for available slot for a specific level/wave_side combo.

        Only queries the API for this specific combination, not all combos.

        Args:
            level: Session level (e.g., "Iniciante2")
            wave_side: Wave side (e.g., "Lado_esquerdo")
            member_id: Member ID for the query
            target_dates: Optional list of specific dates
            target_hours: Optional list of specific hours

        Returns:
            First available AvailableSlot or None
        """
        sport_config = self.get_sport_config()
        tags = list(sport_config.base_tags) + [level, wave_side]
        combo_key = f"{level}/{wave_side}"
        today = datetime.now().strftime("%Y-%m-%d")

        # Get available dates for this combo
        try:
            dates_response = self.api.get_available_dates(tags, sport=self._current_sport)
            if isinstance(dates_response, dict) and "value" in dates_response:
                dates_list = dates_response["value"]
            else:
                dates_list = dates_response

            # Parse and filter dates
            available_dates = []
            for date_item in dates_list:
                if isinstance(date_item, str):
                    date_str = date_item.split("T")[0]
                    # Filter by today and target dates
                    if date_str >= today:
                        if target_dates is None or date_str in target_dates:
                            available_dates.append(date_str)

            if not available_dates:
                return None

            # Sort dates
            available_dates.sort()

            # Check each date for available intervals
            for date in available_dates:
                try:
                    intervals_data = self.api.get_intervals(
                        date=date,
                        tags=tags,
                        member_id=member_id,
                        sport=self._current_sport
                    )

                    # Parse intervals
                    packages_list = intervals_data if isinstance(intervals_data, list) else []

                    for package in packages_list:
                        package_id = package.get("packageId")
                        products = package.get("products", [])

                        for product in products:
                            product_id = product.get("productId", package_id)
                            invitation = product.get("invitation", {})
                            solos = invitation.get("solos", [])

                            # Sort solos by interval to get earliest first
                            solos_sorted = sorted(solos, key=lambda s: s.get("interval", ""))

                            for solo in solos_sorted:
                                if not solo.get("isAvailable", False):
                                    continue

                                interval = solo.get("interval", "")

                                # Filter by target hours if specified
                                if target_hours and interval not in target_hours:
                                    continue

                                available_qty = solo.get("availableQuantity", 0)
                                if available_qty > 0:
                                    return AvailableSlot(
                                        date=date,
                                        interval=interval,
                                        level=level,
                                        wave_side=wave_side,
                                        available=available_qty,
                                        max_quantity=solo.get("maxQuantity", 0),
                                        package_id=package_id,
                                        product_id=product_id
                                    )

                except Exception as e:
                    logger.error(f"Error getting intervals for {date} {combo_key}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error getting dates for {combo_key}: {e}")

        return None
