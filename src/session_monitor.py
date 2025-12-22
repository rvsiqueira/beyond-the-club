"""Session monitoring and booking logic."""

import logging
from dataclasses import dataclass
from typing import List, Optional, Set
from datetime import datetime, time

from .beyond_api import BeyondAPI, SurfSession
from .config import SessionConfig

logger = logging.getLogger(__name__)


@dataclass
class BookingTarget:
    """Represents a target session to book."""
    level: str
    wave_side: str
    target_dates: List[str]  # YYYY-MM-DD format
    target_hours: List[str]  # HH:MM format


class SessionMonitor:
    """Monitor and book surf sessions."""

    def __init__(self, api: BeyondAPI, config: SessionConfig):
        self.api = api
        self.config = config
        self._booked_sessions: Set[str] = set()

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

    def find_available_sessions(self) -> List[SurfSession]:
        """Find all available sessions matching the configured criteria."""
        available_sessions = []

        for level in self.config.levels:
            if not level:
                continue

            for wave_side in self.config.wave_sides:
                if not wave_side:
                    continue

                try:
                    logger.info(f"Checking availability for {level} / {wave_side}")

                    # Get available dates
                    dates_data = self.api.get_available_dates(level, wave_side)

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

                    logger.info(f"Found {len(dates)} available dates for {level}/{wave_side}")

                    # Check each date
                    for date in dates:
                        if not self._is_target_date(date):
                            logger.debug(f"Skipping date {date} - not in target dates")
                            continue

                        try:
                            sessions = self.api.get_sessions_for_date(date, level, wave_side)

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
                                    f"({level}/{wave_side}) - {session.available_spots} spots"
                                )
                                available_sessions.append(session)

                        except Exception as e:
                            logger.error(f"Error getting sessions for date {date}: {e}")

                except Exception as e:
                    logger.error(f"Error checking {level}/{wave_side}: {e}")

        return available_sessions

    def book_session(self, session: SurfSession) -> bool:
        """Attempt to book a session."""
        try:
            logger.info(
                f"Attempting to book session: {session.date} {session.time} "
                f"({session.level}/{session.wave_side})"
            )

            result = self.api.book_session(session.id)

            self._booked_sessions.add(session.id)
            logger.info(f"Successfully booked session {session.id}!")
            logger.info(f"Booking result: {result}")

            return True

        except Exception as e:
            logger.error(f"Failed to book session {session.id}: {e}")
            return False

    def run_check(self, auto_book: bool = True) -> List[SurfSession]:
        """
        Run a single check for available sessions.

        Args:
            auto_book: If True, automatically book found sessions

        Returns:
            List of available sessions found
        """
        logger.info("Running session availability check...")

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
