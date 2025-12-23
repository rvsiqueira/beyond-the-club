"""
Booking management service.

Handles creating, canceling, and swapping bookings.
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from .base import BaseService, ServiceContext
from .availability_service import AvailableSlot

logger = logging.getLogger(__name__)


class BookingService(BaseService):
    """
    Service for managing bookings.

    Responsibilities:
    - Create bookings for slots
    - List active bookings
    - Cancel bookings
    - Swap member in a booking
    - Find matching slots for members based on preferences
    """

    def __init__(
        self,
        context: ServiceContext,
        member_service=None,
        availability_service=None
    ):
        super().__init__(context)
        self._member_service = member_service
        self._availability_service = availability_service

    def set_member_service(self, member_service):
        """Set the member service."""
        self._member_service = member_service

    def set_availability_service(self, availability_service):
        """Set the availability service."""
        self._availability_service = availability_service

    def list_bookings(self) -> List[Dict[str, Any]]:
        """
        List all bookings for the current sport.

        Returns:
            List of booking dictionaries from API
        """
        self.require_initialized()
        return self.api.list_bookings(self.current_sport)

    def get_active_bookings(self) -> List[Dict[str, Any]]:
        """
        Get only active (AccessReady) bookings.

        Returns:
            List of active booking dictionaries
        """
        bookings = self.list_bookings()
        return [b for b in bookings if b.get("status") == "AccessReady"]

    def create_booking(
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
        self.require_initialized()

        sport_config = self.sport_config
        tags = list(sport_config.base_tags) + [slot.level, slot.wave_side]

        result = self.api.create_booking(
            package_id=slot.package_id,
            product_id=slot.product_id,
            member_id=member_id,
            tags=tags,
            interval=slot.interval,
            date=slot.date,
            sport=self.current_sport
        )

        logger.info(
            f"Booking created: {result.get('voucherCode')} for member {member_id} "
            f"at {slot.date} {slot.interval}"
        )
        return result

    def cancel_booking(self, voucher_code: str) -> dict:
        """
        Cancel a booking by voucher code.

        Args:
            voucher_code: The voucher code of the booking to cancel

        Returns:
            Cancellation response from API
        """
        self.require_initialized()

        result = self.api.cancel_booking(voucher_code, sport=self.current_sport)
        logger.info(f"Booking {voucher_code} cancelled")
        return result

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
        self.require_initialized()

        # Cancel the old booking
        logger.info(f"Cancelling booking {voucher_code}...")
        self.cancel_booking(voucher_code)

        # Create new booking immediately
        logger.info(f"Creating new booking for member {new_member_id}...")
        return self.create_booking(slot, new_member_id)

    def find_matching_slot(
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
        if not self._member_service or not self._availability_service:
            raise RuntimeError("Member and Availability services required")

        prefs = self._member_service.get_member_preferences(member_id, self.current_sport)
        if not prefs or not prefs.sessions:
            logger.warning(f"Member {member_id} has no preferences configured")
            return None

        # Get available slots
        if refresh_availability:
            slots = self._availability_service.scan_availability(member_id)
        else:
            slots = self._availability_service.get_slots_from_cache()

        if not slots:
            return None

        # Filter by target dates
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
            pref_combo = session_pref.get_combo_key()
            for slot in slots:
                if slot.combo_key == pref_combo and slot.available > 0:
                    return slot

        return None

    def get_booking_for_member(self, member_id: int) -> Optional[Dict[str, Any]]:
        """
        Get the active booking for a specific member.

        Args:
            member_id: Member ID to check

        Returns:
            Booking dictionary or None
        """
        bookings = self.get_active_bookings()
        for booking in bookings:
            member = booking.get("member", {})
            if member.get("memberId") == member_id:
                return booking
        return None

    def has_active_booking(self, member_id: int) -> bool:
        """Check if a member has an active booking."""
        return self.get_booking_for_member(member_id) is not None

    def get_bookings_by_date(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Group active bookings by date.

        Returns:
            Dictionary mapping date strings to lists of bookings
        """
        bookings = self.get_active_bookings()
        result = {}

        for booking in bookings:
            invitation = booking.get("invitation", {})
            date = invitation.get("date", "")
            if date:
                # Parse ISO date to just date part
                date_str = date.split("T")[0]
                if date_str not in result:
                    result[date_str] = []
                result[date_str].append(booking)

        return result
