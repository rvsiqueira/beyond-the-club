"""
Availability endpoints.

Handles slot availability scanning and querying.
"""

from typing import Optional, List

from fastapi import APIRouter, HTTPException, status, Query, BackgroundTasks
from pydantic import BaseModel, Field

from ..deps import ServicesDep, CurrentUser

router = APIRouter()


# Response models

class SlotResponse(BaseModel):
    """Available slot response."""
    date: str
    interval: str
    level: Optional[str] = None
    wave_side: Optional[str] = None
    court: Optional[str] = None
    available: int
    max_quantity: int
    package_id: str
    product_id: str
    combo_key: str


class AvailabilityResponse(BaseModel):
    """Availability scan response."""
    slots: List[SlotResponse]
    sport: str
    total: int
    from_cache: bool


class DateAvailabilityResponse(BaseModel):
    """Dates with availability."""
    dates: List[str]
    sport: str
    level: Optional[str] = None
    wave_side: Optional[str] = None


# Endpoints

@router.get("", response_model=AvailabilityResponse)
async def get_availability(
    services: ServicesDep,
    current_user: CurrentUser,
    sport: str = Query("surf", description="Sport"),
    date: Optional[str] = Query(None, description="Filter by date (YYYY-MM-DD)"),
    level: Optional[str] = Query(None, description="Filter by level"),
    wave_side: Optional[str] = Query(None, description="Filter by wave side"),
    use_cache: bool = Query(True, description="Use cached data if available")
):
    """
    Get available slots.

    Returns cached data by default, use use_cache=false to force refresh.
    """
    services.context.set_sport(sport)

    # Ensure API is initialized
    if not services.context.api:
        try:
            services.auth.initialize(use_cached=True)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Beyond API not available: {str(e)}"
            )

    from_cache = False

    # Try cache first
    if use_cache and services.availability.is_cache_valid():
        slots = services.availability.get_slots_from_cache()
        from_cache = True
    else:
        # Full scan
        slots = services.availability.scan_availability()

    # Apply filters
    if date:
        slots = [s for s in slots if s.date == date]
    if level:
        slots = [s for s in slots if s.level == level]
    if wave_side:
        slots = [s for s in slots if s.wave_side == wave_side]

    # Filter to available slots only
    slots = [s for s in slots if s.available > 0]

    result = [
        SlotResponse(
            date=s.date,
            interval=s.interval,
            level=s.level,
            wave_side=s.wave_side,
            court=getattr(s, "court", None),
            available=s.available,
            max_quantity=s.max_quantity,
            package_id=s.package_id,
            product_id=s.product_id,
            combo_key=s.combo_key
        )
        for s in slots
    ]

    # Sync to graph
    for s in slots:
        services.graph.sync_available_slot(
            date=s.date,
            interval=s.interval,
            available=s.available,
            max_quantity=s.max_quantity,
            level=s.level,
            wave_side=s.wave_side
        )

    return AvailabilityResponse(
        slots=result,
        sport=sport,
        total=len(result),
        from_cache=from_cache
    )


@router.post("/scan", response_model=AvailabilityResponse)
async def scan_availability(
    services: ServicesDep,
    current_user: CurrentUser,
    sport: str = Query("surf", description="Sport"),
    background_tasks: BackgroundTasks = None
):
    """
    Force a fresh availability scan.

    Scans all level/wave_side combinations and updates cache.
    """
    services.context.set_sport(sport)

    if not services.context.api:
        try:
            services.auth.initialize(use_cached=True)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Beyond API not available: {str(e)}"
            )

    # Full scan
    slots = services.availability.scan_availability()

    # Filter to available only
    available_slots = [s for s in slots if s.available > 0]

    result = [
        SlotResponse(
            date=s.date,
            interval=s.interval,
            level=s.level,
            wave_side=s.wave_side,
            court=getattr(s, "court", None),
            available=s.available,
            max_quantity=s.max_quantity,
            package_id=s.package_id,
            product_id=s.product_id,
            combo_key=s.combo_key
        )
        for s in available_slots
    ]

    return AvailabilityResponse(
        slots=result,
        sport=sport,
        total=len(result),
        from_cache=False
    )


@router.get("/dates", response_model=DateAvailabilityResponse)
async def get_available_dates(
    services: ServicesDep,
    current_user: CurrentUser,
    sport: str = Query("surf", description="Sport"),
    level: Optional[str] = Query(None, description="Level filter"),
    wave_side: Optional[str] = Query(None, description="Wave side filter")
):
    """
    Get dates that have availability for given criteria.
    """
    services.context.set_sport(sport)

    if not services.context.api:
        try:
            services.auth.initialize(use_cached=True)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Beyond API not available: {str(e)}"
            )

    # Get from cache if valid
    if services.availability.is_cache_valid():
        slots = services.availability.get_slots_from_cache()
    else:
        slots = services.availability.scan_availability()

    # Apply filters
    if level:
        slots = [s for s in slots if s.level == level]
    if wave_side:
        slots = [s for s in slots if s.wave_side == wave_side]

    # Get unique dates with availability
    dates = sorted(set(s.date for s in slots if s.available > 0))

    return DateAvailabilityResponse(
        dates=dates,
        sport=sport,
        level=level,
        wave_side=wave_side
    )


@router.get("/for-member/{member_id}")
async def get_availability_for_member(
    member_id: int,
    services: ServicesDep,
    current_user: CurrentUser,
    sport: str = Query("surf", description="Sport"),
    date: Optional[str] = Query(None, description="Target date")
):
    """
    Get available slots matching a member's preferences.
    """
    services.context.set_sport(sport)

    if not services.context.api:
        try:
            services.auth.initialize(use_cached=True)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Beyond API not available: {str(e)}"
            )

    # Get member preferences
    prefs = services.members.get_member_preferences(member_id, sport)
    if not prefs or not prefs.sessions:
        return {
            "member_id": member_id,
            "slots": [],
            "message": "No preferences configured"
        }

    # Get available slots
    if services.availability.is_cache_valid():
        all_slots = services.availability.get_slots_from_cache()
    else:
        all_slots = services.availability.scan_availability()

    # Filter by date if specified
    if date:
        all_slots = [s for s in all_slots if s.date == date]

    # Filter by preferences
    pref_combos = [s.get_combo_key() for s in prefs.sessions]
    matching = [s for s in all_slots if s.combo_key in pref_combos and s.available > 0]

    # Filter by target hours
    if prefs.target_hours:
        matching = [s for s in matching if s.interval in prefs.target_hours]

    result = [
        SlotResponse(
            date=s.date,
            interval=s.interval,
            level=s.level,
            wave_side=s.wave_side,
            court=getattr(s, "court", None),
            available=s.available,
            max_quantity=s.max_quantity,
            package_id=s.package_id,
            product_id=s.product_id,
            combo_key=s.combo_key
        )
        for s in matching
    ]

    return {
        "member_id": member_id,
        "sport": sport,
        "preference_combos": pref_combos,
        "slots": result,
        "total": len(result)
    }
