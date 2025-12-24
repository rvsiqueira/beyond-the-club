"""
Members endpoints.

Handles member listing, preferences, and management.
"""

from typing import Optional, List, Dict, Any

from fastapi import APIRouter, HTTPException, status, Query
from pydantic import BaseModel, Field

from ..deps import ServicesDep, CurrentUser, SportDep, ensure_beyond_api

router = APIRouter()


# Request/Response models

class SessionPreferenceRequest(BaseModel):
    """Single session preference."""
    level: Optional[str] = Field(None, description="Level (Surf)")
    wave_side: Optional[str] = Field(None, description="Wave side (Surf)")
    court: Optional[str] = Field(None, description="Court (Tennis)")


class MemberPreferencesRequest(BaseModel):
    """Member preferences request."""
    sessions: List[SessionPreferenceRequest] = Field(..., description="Session preferences in priority order")
    target_hours: Optional[List[str]] = Field(None, description="Preferred hours (e.g., ['08:00', '09:00'])")
    target_dates: Optional[List[str]] = Field(None, description="Target dates (YYYY-MM-DD)")


class MemberResponse(BaseModel):
    """Member response."""
    member_id: int
    name: str
    social_name: str
    is_titular: bool
    usage: int
    limit: int
    has_booking: bool = False
    has_preferences: bool = False


class MemberDetailResponse(MemberResponse):
    """Member detail response with preferences."""
    preferences: Optional[Dict[str, Any]] = None


class MembersListResponse(BaseModel):
    """List of members response."""
    members: List[MemberResponse]
    sport: str
    total: int


# Endpoints

@router.get("", response_model=MembersListResponse)
async def list_members(
    services: ServicesDep,
    current_user: CurrentUser,
    sport: str = Query("surf", description="Sport (surf or tennis)"),
    refresh: bool = Query(False, description="Force refresh from API")
):
    """
    List all members for the authenticated user.

    Returns members with their usage status and booking info.
    """
    # Set sport context
    services.context.set_sport(sport)

    # Initialize Beyond API using user's tokens (no auto-SMS)
    ensure_beyond_api(services, current_user)

    # Get members
    members = services.members.get_members(force_refresh=refresh)

    # Get active bookings to check status
    try:
        active_bookings = services.bookings.get_active_bookings()
        booked_member_ids = {
            b.get("member", {}).get("memberId")
            for b in active_bookings
        }
    except Exception:
        booked_member_ids = set()

    result = []
    for m in members:
        # Check if member has preferences
        has_prefs = services.members.get_member_preferences(m.member_id, sport) is not None

        result.append(MemberResponse(
            member_id=m.member_id,
            name=m.name,
            social_name=m.social_name,
            is_titular=m.is_titular,
            usage=m.usage,
            limit=m.limit,
            has_booking=m.member_id in booked_member_ids,
            has_preferences=has_prefs
        ))

        # Sync to graph
        services.graph.sync_member(
            member_id=m.member_id,
            name=m.name,
            social_name=m.social_name,
            is_titular=m.is_titular
        )

    return MembersListResponse(
        members=result,
        sport=sport,
        total=len(result)
    )


@router.get("/{member_id}", response_model=MemberDetailResponse)
async def get_member(
    member_id: int,
    services: ServicesDep,
    current_user: CurrentUser,
    sport: str = Query("surf", description="Sport")
):
    """
    Get details for a specific member.

    Includes preferences for the specified sport.
    """
    services.context.set_sport(sport)

    member = services.members.get_member_by_id(member_id)
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Member {member_id} not found"
        )

    prefs = services.members.get_member_preferences(member_id, sport)
    prefs_dict = None
    if prefs:
        prefs_dict = {
            "sessions": [
                {
                    "level": s.level,
                    "wave_side": s.wave_side,
                    "attributes": s.attributes
                }
                for s in prefs.sessions
            ],
            "target_hours": prefs.target_hours,
            "target_dates": prefs.target_dates
        }

    # Check booking status
    has_booking_flag = False
    try:
        has_booking_flag = services.bookings.has_active_booking(member_id)
    except Exception:
        pass

    return MemberDetailResponse(
        member_id=member.member_id,
        name=member.name,
        social_name=member.social_name,
        is_titular=member.is_titular,
        usage=member.usage,
        limit=member.limit,
        has_booking=has_booking_flag,
        has_preferences=prefs is not None,
        preferences=prefs_dict
    )


@router.get("/{member_id}/preferences")
async def get_member_preferences(
    member_id: int,
    services: ServicesDep,
    current_user: CurrentUser,
    sport: str = Query("surf", description="Sport")
):
    """
    Get preferences for a specific member.
    """
    services.context.set_sport(sport)

    prefs = services.members.get_member_preferences(member_id, sport)
    if not prefs:
        return {"member_id": member_id, "sport": sport, "preferences": None}

    return {
        "member_id": member_id,
        "sport": sport,
        "preferences": {
            "sessions": [
                {
                    "priority": i + 1,
                    "level": s.level,
                    "wave_side": s.wave_side,
                    "attributes": s.attributes,
                    "combo_key": s.get_combo_key()
                }
                for i, s in enumerate(prefs.sessions)
            ],
            "target_hours": prefs.target_hours,
            "target_dates": prefs.target_dates
        }
    }


@router.put("/{member_id}/preferences")
async def set_member_preferences(
    member_id: int,
    request: MemberPreferencesRequest,
    services: ServicesDep,
    current_user: CurrentUser,
    sport: str = Query("surf", description="Sport")
):
    """
    Set preferences for a specific member.

    Replaces existing preferences for the specified sport.
    """
    from src.services import MemberPreferences, SessionPreference

    services.context.set_sport(sport)

    # Validate member exists
    member = services.members.get_member_by_id(member_id)
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Member {member_id} not found"
        )

    # Build preferences
    sessions = []
    for i, s in enumerate(request.sessions):
        attrs = {}
        if s.level:
            attrs["level"] = s.level
        if s.wave_side:
            attrs["wave_side"] = s.wave_side
        if s.court:
            attrs["court"] = s.court

        sessions.append(SessionPreference(
            level=s.level,
            wave_side=s.wave_side,
            attributes=attrs
        ))

        # Sync to graph
        services.graph.sync_member_preference(
            member_id=member_id,
            sport=sport,
            priority=i + 1,
            level=s.level,
            wave_side=s.wave_side,
            court=s.court,
            target_hours=request.target_hours
        )

    prefs = MemberPreferences(
        sessions=sessions,
        target_hours=request.target_hours,
        target_dates=request.target_dates
    )

    services.members.set_member_preferences(member_id, prefs, sport)

    return {
        "success": True,
        "member_id": member_id,
        "sport": sport,
        "sessions_count": len(sessions)
    }


@router.delete("/{member_id}/preferences")
async def delete_member_preferences(
    member_id: int,
    services: ServicesDep,
    current_user: CurrentUser,
    sport: str = Query("surf", description="Sport")
):
    """
    Delete preferences for a specific member.
    """
    services.context.set_sport(sport)

    services.members.clear_member_preferences(member_id, sport)
    services.graph.clear_member_preferences(member_id, sport)

    return {"success": True, "member_id": member_id, "sport": sport}


@router.get("/{member_id}/graph-summary")
async def get_member_graph_summary(
    member_id: int,
    services: ServicesDep,
    current_user: CurrentUser
):
    """
    Get full graph summary for a member.

    Includes preferences, booking history, and similar members.
    """
    summary = services.graph.get_member_summary(member_id)
    return summary
