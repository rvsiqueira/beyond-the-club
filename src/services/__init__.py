"""
Services layer for Beyond The Club.

This module provides the core business logic as reusable services
that can be consumed by CLI, API, MCP, or any other interface.
"""

from .base import BaseService, ServiceContext
from .auth_service import AuthService
from .member_service import MemberService, Member, MemberPreferences, SessionPreference
from .availability_service import AvailabilityService, AvailableSlot
from .booking_service import BookingService
from .monitor_service import MonitorService
from .user_auth_service import UserAuthService, AuthTokens, AuthResult

__all__ = [
    # Base
    "BaseService",
    "ServiceContext",
    # Services
    "AuthService",
    "UserAuthService",
    "MemberService",
    "AvailabilityService",
    "BookingService",
    "MonitorService",
    # Data classes
    "Member",
    "MemberPreferences",
    "SessionPreference",
    "AvailableSlot",
    "AuthTokens",
    "AuthResult",
]


def create_services(context: ServiceContext = None):
    """
    Factory function to create all services with proper dependencies.

    Args:
        context: Optional ServiceContext (creates one if not provided)

    Returns:
        Tuple of (context, auth, members, availability, bookings, monitor)
    """
    if context is None:
        context = ServiceContext.create()

    auth_service = AuthService(context)
    member_service = MemberService(context)
    availability_service = AvailabilityService(context, member_service)
    booking_service = BookingService(context, member_service, availability_service)
    monitor_service = MonitorService(
        context, member_service, availability_service, booking_service
    )

    return (
        context,
        auth_service,
        member_service,
        availability_service,
        booking_service,
        monitor_service
    )
