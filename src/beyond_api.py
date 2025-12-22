"""Beyond The Club API client."""

import httpx
import logging
from dataclasses import dataclass, field
from typing import List, Optional, Callable, Dict, Any
from datetime import datetime
from urllib.parse import quote

logger = logging.getLogger(__name__)


@dataclass
class SportSession:
    """Represents a sport session slot (generic for all sports)."""
    id: str
    sport: str
    date: str
    time: str
    attributes: Dict[str, str]  # e.g., {"level": "Iniciante1", "wave_side": "Lado_esquerdo"} or {"court": "Quadra_Saibro"}
    available_spots: int
    total_spots: int
    is_available: bool
    raw_data: dict

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


# Alias for backwards compatibility
SurfSession = SportSession


@dataclass
class SessionDate:
    """Represents an available date with sessions."""
    date: str
    sessions: List[SportSession]


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

    def _build_tag_params(self, tags: List[str]) -> str:
        """Build URL-encoded tag parameters."""
        return "&".join([f"tags={quote(tag)}" for tag in tags])

    def get_schedule_status(self, sport: str = "surf") -> dict:
        """Get current schedule status for a sport."""
        url = f"{self.base_url}/schedules/{sport}/status"
        response = self._client.get(url, headers=self._get_headers())
        response.raise_for_status()
        return response.json()

    # Backwards compatibility alias
    def get_surf_status(self) -> dict:
        """Get current surf schedule status."""
        return self.get_schedule_status("surf")

    def get_available_dates(
        self,
        tags: List[str],
        sport: str = "surf",
        # Legacy parameters for backwards compatibility
        level: Optional[str] = None,
        wave_side: Optional[str] = None,
    ) -> List[dict]:
        """
        Get available dates for a sport with specified tags.

        Args:
            tags: List of tags to filter by (e.g., ["Surf", "Agendamento", "Iniciante1", "Lado_esquerdo"])
            sport: Sport type (surf, tennis, etc.)
            level: (Legacy) Session level for surf
            wave_side: (Legacy) Wave side for surf
        """
        # Handle legacy call pattern
        if level is not None and wave_side is not None:
            tags = ["Surf", "Agendamento", level, wave_side]
            sport = "surf"

        url = f"{self.base_url}/schedules/{sport}/dates"
        tag_params = self._build_tag_params(tags)
        full_url = f"{url}?{tag_params}"

        response = self._client.get(full_url, headers=self._get_headers())
        response.raise_for_status()

        data = response.json()
        logger.debug(f"Available dates for {sport} with tags {tags}: {data}")
        return data

    def get_sessions_for_date(
        self,
        date: str,
        tags: List[str],
        attributes: Dict[str, str],
        sport: str = "surf",
        # Legacy parameters for backwards compatibility
        level: Optional[str] = None,
        wave_side: Optional[str] = None,
    ) -> List[SportSession]:
        """
        Get available sessions for a specific date.

        Args:
            date: Date in YYYY-MM-DD format
            tags: List of tags to filter by
            attributes: Dict of attribute name -> value for the session
            sport: Sport type
            level: (Legacy) Session level for surf
            wave_side: (Legacy) Wave side for surf
        """
        # Handle legacy call pattern
        if level is not None and wave_side is not None:
            tags = ["Surf", "Agendamento", level, wave_side]
            attributes = {"level": level, "wave_side": wave_side}
            sport = "surf"

        url = f"{self.base_url}/schedules/{sport}/times"
        tag_params = self._build_tag_params(tags)
        full_url = f"{url}?date={date}&{tag_params}"

        response = self._client.get(full_url, headers=self._get_headers())
        response.raise_for_status()

        data = response.json()
        sessions = []

        for item in data if isinstance(data, list) else data.get("sessions", []):
            session = SportSession(
                id=str(item.get("id", "")),
                sport=sport,
                date=date,
                time=item.get("time", item.get("startTime", "")),
                attributes=attributes.copy(),
                available_spots=item.get("availableSpots", item.get("available", 0)),
                total_spots=item.get("totalSpots", item.get("capacity", 0)),
                is_available=item.get("isAvailable", item.get("available", 0) > 0),
                raw_data=item
            )
            sessions.append(session)

        return sessions

    def book_session(
        self,
        session_id: str,
        member_id: Optional[str] = None,
        sport: str = "surf"
    ) -> dict:
        """
        Book a session.

        Args:
            session_id: The session ID to book
            member_id: Optional member ID (uses authenticated user if not provided)
            sport: Sport type
        """
        url = f"{self.base_url}/schedules/{sport}/book"

        payload = {"sessionId": session_id}
        if member_id:
            payload["memberId"] = member_id

        headers = self._get_headers()
        headers["content-type"] = "application/json"

        response = self._client.post(url, json=payload, headers=headers)
        response.raise_for_status()

        logger.info(f"Successfully booked {sport} session {session_id}")
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

    def get_my_bookings(self, sport: str = "surf") -> List[dict]:
        """Get the current user's bookings for a sport."""
        url = f"{self.base_url}/schedules/{sport}/my-bookings"
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

    def get_intervals(
        self,
        date: str,
        tags: List[str],
        member_id: int,
        sport: str = "surf"
    ) -> dict:
        """
        Get available time intervals for a specific date.

        Args:
            date: Date in YYYY-MM-DD format
            tags: List of tags to filter by
            member_id: Member ID for the query
            sport: Sport type

        Returns:
            Dict with products containing available intervals
        """
        url = f"{self.base_url}/schedules/{sport}/intervals"
        tag_params = self._build_tag_params(tags)
        full_url = f"{url}?date={date}&{tag_params}&startDate={date}&endDate={date}&memberId={member_id}"

        response = self._client.get(full_url, headers=self._get_headers())
        response.raise_for_status()

        data = response.json()
        # API returns {"isFailure": false, "statusCode": 200, "value": [...]}
        if isinstance(data, dict) and "value" in data:
            return data["value"]
        return data

    def create_booking(
        self,
        package_id: int,
        product_id: int,
        member_id: int,
        tags: List[str],
        interval: str,
        date: str,
        sport: str = "surf"
    ) -> dict:
        """
        Create a new booking.

        Args:
            package_id: Package ID for the level/wave_side combination
            product_id: Product ID (usually same as package_id)
            member_id: Member ID to book for
            tags: List of tags (e.g., ["Surf", "Agendamento", "Iniciante2", "Lado_direito"])
            interval: Time slot (e.g., "09:00")
            date: Date in YYYY-MM-DD format
            sport: Sport type

        Returns:
            Booking response with voucherCode and accessCode
        """
        url = f"{self.base_url}/schedules/{sport}"

        payload = {
            "packageId": package_id,
            "productId": product_id,
            "memberId": member_id,
            "tags": tags,
            "invitation": {
                "interval": interval,
                "date": date
            }
        }

        headers = self._get_headers()
        headers["content-type"] = "application/json"

        response = self._client.post(url, json=payload, headers=headers)

        # Check for errors and log the response body
        if response.status_code >= 400:
            try:
                error_data = response.json()
                error_msg = error_data.get("error", {}).get("message", str(error_data))
                logger.error(f"Booking failed: {error_msg}")
                logger.error(f"Full error response: {error_data}")
            except Exception:
                logger.error(f"Booking failed with status {response.status_code}: {response.text}")
            response.raise_for_status()

        data = response.json()
        logger.info(f"Successfully created {sport} booking for member {member_id}")

        # API returns {"isFailure": false, "statusCode": 200, "value": {...}}
        if isinstance(data, dict) and "value" in data:
            return data["value"]
        return data

    def list_bookings(self, sport: str = "surf") -> List[dict]:
        """
        List all active bookings for the title.

        Args:
            sport: Sport type

        Returns:
            List of booking objects with voucherCode, member, invitation info
        """
        url = f"{self.base_url}/schedules/{sport}"
        response = self._client.get(url, headers=self._get_headers())
        response.raise_for_status()

        data = response.json()
        # API returns {"isFailure": false, "statusCode": 200, "value": [...]}
        if isinstance(data, dict) and "value" in data:
            return data["value"]
        return data if isinstance(data, list) else []

    def cancel_booking(self, voucher_code: str, sport: str = "surf") -> dict:
        """
        Cancel a booking by voucher code.

        Args:
            voucher_code: The voucher code of the booking to cancel
            sport: Sport type

        Returns:
            Cancellation response
        """
        url = f"{self.base_url}/schedules/{sport}/{voucher_code}/cancel"

        response = self._client.delete(url, headers=self._get_headers())
        response.raise_for_status()

        data = response.json()
        logger.info(f"Successfully cancelled {sport} booking {voucher_code}")

        # API returns {"isFailure": false, "statusCode": 200, "value": {...}}
        if isinstance(data, dict) and "value" in data:
            return data["value"]
        return data

    def close(self):
        """Close the HTTP client."""
        self._client.close()
