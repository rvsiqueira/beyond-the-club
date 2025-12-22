"""Beyond The Club API client."""

import httpx
import logging
from dataclasses import dataclass
from typing import List, Optional, Callable
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class SurfSession:
    """Represents a surf session slot."""
    id: str
    date: str
    time: str
    level: str
    wave_side: str
    available_spots: int
    total_spots: int
    is_available: bool
    raw_data: dict


@dataclass
class SessionDate:
    """Represents an available date with sessions."""
    date: str
    sessions: List[SurfSession]


class BeyondAPI:
    """Client for Beyond The Club API."""

    def __init__(self, base_url: str, token_provider: Callable[[], str]):
        """
        Initialize the API client.

        Args:
            base_url: The API base URL
            token_provider: A callable that returns a valid auth token
        """
        self.base_url = base_url
        self._get_token = token_provider
        self._client = httpx.Client(timeout=30.0)

    def _get_headers(self) -> dict:
        """Get headers for API requests."""
        return {
            "accept": "application/json",
            "accept-encoding": "gzip",
            "authorization": f"Bearer {self._get_token()}",
            "connection": "Keep-Alive",
            "host": "api.beyondtheclub.tech",
            "user-agent": "okhttp/4.12.0",
        }

    def get_surf_status(self) -> dict:
        """Get current surf schedule status."""
        url = f"{self.base_url}/schedules/surf/status"
        response = self._client.get(url, headers=self._get_headers())
        response.raise_for_status()
        return response.json()

    def get_available_dates(self, level: str, wave_side: str) -> List[dict]:
        """
        Get available dates for a specific level and wave side.

        Args:
            level: Session level (Iniciante1, Iniciante2, Intermediario1)
            wave_side: Wave side (Lado_esquerdo, Lado_direito)
        """
        url = f"{self.base_url}/schedules/surf/dates"
        params = {
            "tags": ["Surf", "Agendamento", level, wave_side]
        }

        # Build URL with multiple tags
        tag_params = "&".join([f"tags={tag}" for tag in params["tags"]])
        full_url = f"{url}?{tag_params}"

        response = self._client.get(full_url, headers=self._get_headers())
        response.raise_for_status()

        data = response.json()
        logger.debug(f"Available dates for {level}/{wave_side}: {data}")
        return data

    def get_sessions_for_date(self, date: str, level: str, wave_side: str) -> List[SurfSession]:
        """
        Get available sessions for a specific date.

        Args:
            date: Date in YYYY-MM-DD format
            level: Session level
            wave_side: Wave side
        """
        url = f"{self.base_url}/schedules/surf/times"
        params = {
            "date": date,
            "tags": ["Surf", "Agendamento", level, wave_side]
        }

        tag_params = "&".join([f"tags={tag}" for tag in params["tags"]])
        full_url = f"{url}?date={date}&{tag_params}"

        response = self._client.get(full_url, headers=self._get_headers())
        response.raise_for_status()

        data = response.json()
        sessions = []

        for item in data if isinstance(data, list) else data.get("sessions", []):
            session = SurfSession(
                id=str(item.get("id", "")),
                date=date,
                time=item.get("time", item.get("startTime", "")),
                level=level,
                wave_side=wave_side,
                available_spots=item.get("availableSpots", item.get("available", 0)),
                total_spots=item.get("totalSpots", item.get("capacity", 0)),
                is_available=item.get("isAvailable", item.get("available", 0) > 0),
                raw_data=item
            )
            sessions.append(session)

        return sessions

    def book_session(self, session_id: str, member_id: Optional[str] = None) -> dict:
        """
        Book a surf session.

        Args:
            session_id: The session ID to book
            member_id: Optional member ID (uses authenticated user if not provided)
        """
        url = f"{self.base_url}/schedules/surf/book"

        payload = {"sessionId": session_id}
        if member_id:
            payload["memberId"] = member_id

        headers = self._get_headers()
        headers["content-type"] = "application/json"

        response = self._client.post(url, json=payload, headers=headers)
        response.raise_for_status()

        logger.info(f"Successfully booked session {session_id}")
        return response.json()

    def get_member_preferences(self) -> dict:
        """Get the current member's preferences."""
        url = f"{self.base_url}/members/me/preferences"
        response = self._client.get(url, headers=self._get_headers())
        response.raise_for_status()
        return response.json()

    def accept_terms(self, term_version: str = "1.0") -> dict:
        """Accept the terms of service."""
        url = f"{self.base_url}/accept-terms"
        params = {"termVersion": term_version}
        response = self._client.get(url, headers=self._get_headers(), params=params)
        response.raise_for_status()
        return response.json()

    def check_pin_exists(self) -> bool:
        """Check if user has a PIN set."""
        url = f"{self.base_url}/pin/exists"
        response = self._client.get(url, headers=self._get_headers())
        response.raise_for_status()
        data = response.json()
        return data.get("exists", False)

    def get_my_bookings(self) -> List[dict]:
        """Get the current user's bookings."""
        url = f"{self.base_url}/schedules/surf/my-bookings"
        response = self._client.get(url, headers=self._get_headers())
        response.raise_for_status()
        return response.json()

    def get_inscriptions(self, tags: str = "surf") -> List[dict]:
        """
        Get the current user's inscriptions.

        Args:
            tags: Filter by tags (default: "surf")

        Returns:
            List of inscription objects
        """
        url = f"{self.base_url}/inscriptions"
        params = {"tags": tags}
        response = self._client.get(url, headers=self._get_headers(), params=params)
        response.raise_for_status()
        return response.json()

    def close(self):
        """Close the HTTP client."""
        self._client.close()
