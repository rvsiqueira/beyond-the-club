"""
Availability endpoints.

Handles slot availability scanning and querying.
"""

from typing import Optional, List

from fastapi import APIRouter, HTTPException, status, Query, BackgroundTasks
from pydantic import BaseModel, Field

from ..deps import ServicesDep, CurrentUser, ensure_beyond_api

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
    cache_valid: bool
    cache_updated_at: Optional[str] = None


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
):
    """
    Get available slots from cache.

    ALWAYS returns cached data immediately - NEVER triggers a scan.
    Use POST /availability/scan to refresh the cache.
    """
    services.context.set_sport(sport)

    # Get cache data - NO API calls, NO scanning
    cache = services.availability.get_cache()
    cache_updated_at = cache.get("scanned_at")

    # Check cache validity (all dates >= today)
    from datetime import datetime
    today = datetime.now().strftime("%Y-%m-%d")
    cache_valid = bool(cache.get("dates")) and all(
        d >= today for d in cache.get("dates", {}).keys()
    )

    # Load slots from cache (fast, no API calls)
    slots = services.availability.get_slots_from_cache() if cache.get("dates") else []

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
            package_id=str(s.package_id),
            product_id=str(s.product_id),
            combo_key=s.combo_key
        )
        for s in slots
    ]

    return AvailabilityResponse(
        slots=result,
        sport=sport,
        total=len(result),
        from_cache=True,
        cache_valid=cache_valid,
        cache_updated_at=cache_updated_at
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

    # Initialize Beyond API using user's tokens (no auto-SMS)
    ensure_beyond_api(services, current_user)

    # Full scan
    slots = services.availability.scan_availability()

    # Get updated cache info
    cache = services.availability.get_cache()
    cache_updated_at = cache.get("scanned_at")

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
            package_id=str(s.package_id),
            product_id=str(s.product_id),
            combo_key=s.combo_key
        )
        for s in available_slots
    ]

    return AvailabilityResponse(
        slots=result,
        sport=sport,
        total=len(result),
        from_cache=False,
        cache_valid=True,
        cache_updated_at=cache_updated_at
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
    Returns from cache only - never triggers a scan.
    """
    services.context.set_sport(sport)

    # Get from cache only - no API calls
    cache = services.availability.get_cache()
    slots = services.availability.get_slots_from_cache() if cache.get("dates") else []

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
    Returns from cache only - never triggers a scan.
    """
    services.context.set_sport(sport)

    # Get member preferences (from local file, no API)
    prefs = services.members.get_member_preferences(member_id, sport)
    if not prefs or not prefs.sessions:
        return {
            "member_id": member_id,
            "slots": [],
            "message": "No preferences configured"
        }

    # Get available slots from cache only - no API calls
    cache = services.availability.get_cache()
    all_slots = services.availability.get_slots_from_cache() if cache.get("dates") else []

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
            package_id=str(s.package_id),
            product_id=str(s.product_id),
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
