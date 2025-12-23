"""
API v1 router.

Aggregates all v1 endpoints.
"""

from fastapi import APIRouter

from . import auth, members, availability, bookings, monitor, sports

router = APIRouter()

# Include all route modules
router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
router.include_router(members.router, prefix="/members", tags=["Members"])
router.include_router(availability.router, prefix="/availability", tags=["Availability"])
router.include_router(bookings.router, prefix="/bookings", tags=["Bookings"])
router.include_router(monitor.router, prefix="/monitor", tags=["Monitor"])
router.include_router(sports.router, prefix="/sports", tags=["Sports"])
