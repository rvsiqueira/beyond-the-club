"""Session monitoring and booking logic."""

import logging
from dataclasses import dataclass
from typing import List, Optional, Set, Dict, Callable, Any
from datetime import datetime, time
from itertools import product

from .beyond_api import BeyondAPI, SportSession
from .config import SessionConfig, SportConfig

# Alias for backwards compatibility
SurfSession = SportSession

logger = logging.getLogger(__name__)


@dataclass
class BookingTarget:
    """Represents a target session to book."""
    attributes: Dict[str, str]  # e.g., {"level": "Iniciante1", "wave_side": "Lado_esquerdo"}
    target_dates: List[str]  # YYYY-MM-DD format
    target_hours: List[str]  # HH:MM format

    # Backwards compatibility properties
    @property
    def level(self) -> str:
        return self.attributes.get("level", "")

    @property
    def wave_side(self) -> str:
        return self.attributes.get("wave_side", "")


@dataclass
class MemberBookingResult:
    """Result of a booking attempt for a member."""
    member_id: int
    member_name: str
    session: SportSession
    success: bool
    error: Optional[str] = None


class SessionMonitor:
    """Monitor and book sport sessions."""

    def __init__(
        self,
        api: BeyondAPI,
        config: SessionConfig,
        get_member_preferences: Optional[Callable[[int], Any]] = None,
        sport: str = "surf",
        sport_config: Optional[SportConfig] = None
    ):
        self.api = api
        self.config = config
        self.sport = sport
        self.sport_config = sport_config
        self._booked_sessions: Set[str] = set()
        self._member_booked: Dict[int, Set[str]] = {}  # member_id -> set of session_ids
        self._get_member_preferences = get_member_preferences

    def _build_tags(self, attributes: Dict[str, str]) -> List[str]:
        """Build API tags from sport config and attributes."""
        if self.sport_config:
            tags = list(self.sport_config.base_tags)
        else:
            # Fallback for surf
            tags = ["Surf", "Agendamento"]

        # Add attribute values to tags
        tags.extend(attributes.values())
        return tags

    def _format_attributes(self, attributes: Dict[str, str]) -> str:
        """Format attributes for logging."""
        return " / ".join(attributes.values())

    def _parse_time(self, time_str: str) -> Optional[time]:
        """Parse time string to time object."""
        try:
            # Try different formats
            for fmt in ["%H:%M", "%H:%M:%S", "%I:%M %p"]:
                try:
                    return datetime.strptime(time_str, fmt).time()
                except ValueError:
                    continue
            return None
        except Exception:
            return None

    def _is_target_time(self, session_time: str) -> bool:
        """Check if session time matches target hours."""
        if not self.config.target_hours or self.config.target_hours == ['']:
            # No specific hours configured, accept all
            return True

        parsed_time = self._parse_time(session_time)
        if not parsed_time:
            logger.warning(f"Could not parse session time: {session_time}")
            return True  # Accept if we can't parse

        for target_hour in self.config.target_hours:
            if not target_hour:
                continue
            target_time = self._parse_time(target_hour)
            if target_time and parsed_time.hour == target_time.hour:
                # Match by hour
                return True

        return False

    def _is_target_date(self, session_date: str) -> bool:
        """Check if session date matches target dates."""
        if not self.config.target_dates or self.config.target_dates == ['']:
            # No specific dates configured, accept all
            return True

        return session_date in self.config.target_dates

    def _is_target_time_for_member(self, session_time: str, target_hours: List[str]) -> bool:
        """Check if session time matches target hours for a member."""
        if not target_hours or target_hours == ['']:
            return True

        parsed_time = self._parse_time(session_time)
        if not parsed_time:
            return True

        for target_hour in target_hours:
            if not target_hour:
                continue
            target_time = self._parse_time(target_hour)
            if target_time and parsed_time.hour == target_time.hour:
                return True
        return False

    def _is_target_date_for_member(self, session_date: str, target_dates: List[str]) -> bool:
        """Check if session date matches target dates for a member."""
        if not target_dates or target_dates == ['']:
            return True
        return session_date in target_dates

    def find_sessions_for_member(
        self,
        member_id: int,
        member_name: str
    ) -> List[SportSession]:
        """Find available sessions for a specific member using their preferences."""
        if not self._get_member_preferences:
            logger.warning("No preference getter configured, using global config")
            return self.find_available_sessions()

        prefs = self._get_member_preferences(member_id)
        if not prefs or not prefs.sessions:
            logger.warning(f"No preferences for member {member_name}, skipping")
            return []

        available_sessions = []
        member_booked = self._member_booked.get(member_id, set())

        # Process sessions in priority order (first preference = highest priority)
        for pref in prefs.sessions:
            attributes = pref.attributes
            tags = self._build_tags(attributes)
            attrs_str = self._format_attributes(attributes)

            try:
                logger.info(f"[{member_name}] Checking {attrs_str}")

                dates_data = self.api.get_available_dates(tags, sport=self.sport)

                dates = []
                if isinstance(dates_data, list):
                    for item in dates_data:
                        if isinstance(item, str):
                            dates.append(item)
                        elif isinstance(item, dict):
                            date_val = item.get("date") or item.get("availableDate")
                            if date_val:
                                dates.append(date_val)
                elif isinstance(dates_data, dict):
                    dates = dates_data.get("dates", []) or dates_data.get("availableDates", [])

                logger.info(f"[{member_name}] Found {len(dates)} dates for {attrs_str}")

                for date in dates:
                    if not self._is_target_date_for_member(date, prefs.target_dates):
                        continue

                    try:
                        sessions = self.api.get_sessions_for_date(
                            date, tags, attributes, sport=self.sport
                        )

                        for session in sessions:
                            if not session.is_available:
                                continue

                            if session.id in member_booked:
                                continue

                            if not self._is_target_time_for_member(session.time, prefs.target_hours):
                                continue

                            logger.info(
                                f"[{member_name}] Found: {date} {session.time} "
                                f"({attrs_str}) - {session.available_spots} spots"
                            )
                            available_sessions.append(session)

                    except Exception as e:
                        logger.error(f"[{member_name}] Error getting sessions for {date}: {e}")

            except Exception as e:
                logger.error(f"[{member_name}] Error checking {attrs_str}: {e}")

        return available_sessions

    def book_session_for_member(
        self,
        session: SportSession,
        member_id: int,
        member_name: str
    ) -> MemberBookingResult:
        """Book a session for a specific member."""
        try:
            attrs_str = self._format_attributes(session.attributes)
            logger.info(
                f"[{member_name}] Booking: {session.date} {session.time} ({attrs_str})"
            )

            result = self.api.book_session(session.id, str(member_id), sport=self.sport)

            # Track booked session for this member
            if member_id not in self._member_booked:
                self._member_booked[member_id] = set()
            self._member_booked[member_id].add(session.id)
            self._booked_sessions.add(session.id)

            logger.info(f"[{member_name}] Successfully booked session {session.id}!")
            return MemberBookingResult(
                member_id=member_id,
                member_name=member_name,
                session=session,
                success=True
            )

        except Exception as e:
            logger.error(f"[{member_name}] Failed to book session {session.id}: {e}")
            return MemberBookingResult(
                member_id=member_id,
                member_name=member_name,
                session=session,
                success=False,
                error=str(e)
            )

    def run_check_for_members(
        self,
        members: List[Dict[str, Any]],
        auto_book: bool = True
    ) -> List[MemberBookingResult]:
        """
        Run availability check for multiple members.

        Args:
            members: List of dicts with 'member_id' and 'social_name' keys
            auto_book: If True, automatically book found sessions

        Returns:
            List of booking results
        """
        results = []

        for member in members:
            member_id = member["member_id"]
            member_name = member["social_name"]

            logger.info(f"Checking sessions for {member_name}...")
            available = self.find_sessions_for_member(member_id, member_name)

            if not available:
                logger.info(f"[{member_name}] No matching sessions found")
                continue

            logger.info(f"[{member_name}] Found {len(available)} matching sessions")

            if auto_book:
                # Book the first available (highest priority) session
                session = available[0]
                result = self.book_session_for_member(session, member_id, member_name)
                results.append(result)

                if result.success:
                    logger.info(f"[{member_name}] Booked: {session.date} {session.time}")
                else:
                    logger.warning(f"[{member_name}] Failed to book: {session.date} {session.time}")

        return results

    def _generate_attribute_combinations(self) -> List[Dict[str, str]]:
        """Generate all combinations of attributes for global config search."""
        if not self.sport_config:
            # Fallback for surf using legacy config
            combinations = []
            for level in self.config.levels:
                if not level:
                    continue
                for wave_side in self.config.wave_sides:
                    if not wave_side:
                        continue
                    combinations.append({"level": level, "wave_side": wave_side})
            return combinations

        # Use sport config to generate combinations
        attr_names = self.sport_config.get_attributes()
        if not attr_names:
            return []

        # Get all options for each attribute
        options_per_attr = []
        for attr_name in attr_names:
            options = self.sport_config.get_options(attr_name)
            if options:
                options_per_attr.append([(attr_name, opt) for opt in options])

        if not options_per_attr:
            return []

        # Generate all combinations
        combinations = []
        for combo in product(*options_per_attr):
            attr_dict = dict(combo)
            combinations.append(attr_dict)

        return combinations

    def find_available_sessions(self) -> List[SportSession]:
        """Find all available sessions matching the configured criteria."""
        available_sessions = []

        for attributes in self._generate_attribute_combinations():
            tags = self._build_tags(attributes)
            attrs_str = self._format_attributes(attributes)

            try:
                logger.info(f"Checking availability for {attrs_str}")

                # Get available dates
                dates_data = self.api.get_available_dates(tags, sport=self.sport)

                # Extract dates from response
                dates = []
                if isinstance(dates_data, list):
                    for item in dates_data:
                        if isinstance(item, str):
                            dates.append(item)
                        elif isinstance(item, dict):
                            date_val = item.get("date") or item.get("availableDate")
                            if date_val:
                                dates.append(date_val)
                elif isinstance(dates_data, dict):
                    dates = dates_data.get("dates", []) or dates_data.get("availableDates", [])

                logger.info(f"Found {len(dates)} available dates for {attrs_str}")

                # Check each date
                for date in dates:
                    if not self._is_target_date(date):
                        logger.debug(f"Skipping date {date} - not in target dates")
                        continue

                    try:
                        sessions = self.api.get_sessions_for_date(
                            date, tags, attributes, sport=self.sport
                        )

                        for session in sessions:
                            if not session.is_available:
                                continue

                            if session.id in self._booked_sessions:
                                logger.debug(f"Skipping already booked session {session.id}")
                                continue

                            if not self._is_target_time(session.time):
                                logger.debug(f"Skipping session at {session.time} - not target hour")
                                continue

                            logger.info(
                                f"Found available session: {date} {session.time} "
                                f"({attrs_str}) - {session.available_spots} spots"
                            )
                            available_sessions.append(session)

                    except Exception as e:
                        logger.error(f"Error getting sessions for date {date}: {e}")

            except Exception as e:
                logger.error(f"Error checking {attrs_str}: {e}")

        return available_sessions

    def book_session(self, session: SportSession) -> bool:
        """Attempt to book a session."""
        try:
            attrs_str = self._format_attributes(session.attributes)
            logger.info(
                f"Attempting to book session: {session.date} {session.time} ({attrs_str})"
            )

            result = self.api.book_session(session.id, sport=self.sport)

            self._booked_sessions.add(session.id)
            logger.info(f"Successfully booked session {session.id}!")
            logger.info(f"Booking result: {result}")

            return True

        except Exception as e:
            logger.error(f"Failed to book session {session.id}: {e}")
            return False

    def run_check(self, auto_book: bool = True) -> List[SportSession]:
        """
        Run a single check for available sessions.

        Args:
            auto_book: If True, automatically book found sessions

        Returns:
            List of available sessions found
        """
        logger.info(f"Running session availability check for {self.sport}...")

        available = self.find_available_sessions()

        if not available:
            logger.info("No matching available sessions found")
            return []

        logger.info(f"Found {len(available)} matching available sessions")

        if auto_book:
            for session in available:
                success = self.book_session(session)
                if success:
                    logger.info(f"Booked: {session.date} {session.time}")
                else:
                    logger.warning(f"Failed to book: {session.date} {session.time}")

        return available

    def get_booked_sessions(self) -> Set[str]:
        """Get the set of session IDs that have been booked this run."""
        return self._booked_sessions.copy()
