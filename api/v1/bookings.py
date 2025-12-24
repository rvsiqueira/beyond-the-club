"""
Bookings endpoints.

Handles booking creation, listing, and cancellation.
"""

from typing import Optional, List, Dict, Any

from fastapi import APIRouter, HTTPException, status, Query
from pydantic import BaseModel, Field

from ..deps import ServicesDep, CurrentUser, ensure_beyond_api

router = APIRouter()


# Request/Response models

class CreateBookingRequest(BaseModel):
    """Create booking request."""
    member_id: int = Field(..., description="Member ID to book for")
    date: str = Field(..., description="Date (YYYY-MM-DD)")
    interval: str = Field(..., description="Time interval (e.g., '08:00')")
    level: Optional[str] = Field(None, description="Level (Surf)")
    wave_side: Optional[str] = Field(None, description="Wave side (Surf)")
    court: Optional[str] = Field(None, description="Court (Tennis)")
    package_id: str = Field(..., description="Package ID from availability")
    product_id: str = Field(..., description="Product ID from availability")


class BookingResponse(BaseModel):
    """Booking response."""
    voucher_code: str
    access_code: str
    member_id: int
    member_name: str
    date: str
    interval: str
    level: Optional[str] = None
    wave_side: Optional[str] = None
    status: str


class BookingsListResponse(BaseModel):
    """List of bookings response."""
    bookings: List[BookingResponse]
    sport: str
    total: int


class SwapBookingRequest(BaseModel):
    """Swap booking request."""
    new_member_id: int = Field(..., description="New member to book for")


# Endpoints

@router.get("", response_model=BookingsListResponse)
async def list_bookings(
    services: ServicesDep,
    current_user: CurrentUser,
    sport: str = Query("surf", description="Sport"),
    active_only: bool = Query(True, description="Only show active bookings")
):
    """
    List all bookings.

    Returns active bookings by default.
    """
    services.context.set_sport(sport)

    # Initialize Beyond API using user's tokens (no auto-SMS)
    ensure_beyond_api(services, current_user)

    if active_only:
        bookings = services.bookings.get_active_bookings()
    else:
        bookings = services.bookings.list_bookings()

    result = []
    for b in bookings:
        member = b.get("member", {})
        invitation = b.get("invitation", {})

        # Extract interval - CLI uses "begin" field from invitation
        begin = invitation.get("begin", "")
        interval = begin[:5] if len(str(begin)) >= 5 else begin
        if not interval:
            # Fallback to other possible fields
            interval = invitation.get("interval", "") or invitation.get("time", "")

        # Tags come from booking root, not invitation (as CLI does)
        tags = b.get("tags", [])
        if not tags:
            # Fallback to invitation tags
            tags = invitation.get("tags", [])

        # Extract level and wave_side from tags
        level = None
        wave_side = None
        for tag in tags:
            if "Iniciante" in tag or "Intermediario" in tag or "Avançado" in tag or "Avancado" in tag:
                level = tag
            elif "Lado_" in tag:
                wave_side = tag

        booking_resp = BookingResponse(
            voucher_code=b.get("voucherCode", ""),
            access_code=b.get("accessCode", invitation.get("accessCode", "")),
            member_id=member.get("memberId", 0),
            member_name=member.get("socialName", ""),
            date=invitation.get("date", "").split("T")[0],
            interval=interval,
            level=level,
            wave_side=wave_side,
            status=b.get("status", "Unknown")
        )
        result.append(booking_resp)

        # Sync to graph
        if b.get("voucherCode"):
            services.graph.sync_booking(
                voucher=b.get("voucherCode"),
                access_code=booking_resp.access_code,
                member_id=member.get("memberId", 0),
                date=booking_resp.date,
                interval=booking_resp.interval,
                level=level,
                wave_side=wave_side,
                status=b.get("status", "Unknown")
            )

    return BookingsListResponse(
        bookings=result,
        sport=sport,
        total=len(result)
    )


@router.post("", response_model=BookingResponse)
async def create_booking(
    request: CreateBookingRequest,
    services: ServicesDep,
    current_user: CurrentUser,
    sport: str = Query("surf", description="Sport")
):
    """
    Create a new booking.

    Books a specific slot for a member.
    """
    from src.services import AvailableSlot

    services.context.set_sport(sport)

    # Initialize Beyond API using user's tokens (no auto-SMS)
    ensure_beyond_api(services, current_user)

    # Verify member exists
    member = services.members.get_member_by_id(request.member_id)
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Member {request.member_id} not found"
        )

    # Check if member already has booking
    if services.bookings.has_active_booking(request.member_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Member already has an active booking"
        )

    # Create slot object
    slot = AvailableSlot(
        date=request.date,
        interval=request.interval,
        level=request.level or "",
        wave_side=request.wave_side or "",
        available=1,  # Assume available
        max_quantity=6,
        package_id=request.package_id,
        product_id=request.product_id
    )

    try:
        result = services.bookings.create_booking(slot, request.member_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    voucher = result.get("voucherCode", "")
    access = result.get("accessCode", result.get("invitation", {}).get("accessCode", ""))

    # Sync to graph
    services.graph.sync_booking(
        voucher=voucher,
        access_code=access,
        member_id=request.member_id,
        date=request.date,
        interval=request.interval,
        level=request.level,
        wave_side=request.wave_side,
        court=request.court
    )

    # Force refresh members cache to update usage counts
    services.members.refresh_members()

    # Refresh availability for this specific slot
    if request.level and request.wave_side:
        services.availability.refresh_slot_availability(
            date=request.date,
            interval=request.interval,
            level=request.level,
            wave_side=request.wave_side,
            member_id=request.member_id
        )

    return BookingResponse(
        voucher_code=voucher,
        access_code=access,
        member_id=request.member_id,
        member_name=member.social_name,
        date=request.date,
        interval=request.interval,
        level=request.level,
        wave_side=request.wave_side,
        status="AccessReady"
    )


@router.get("/{voucher_code}")
async def get_booking(
    voucher_code: str,
    services: ServicesDep,
    current_user: CurrentUser,
    sport: str = Query("surf", description="Sport")
):
    """
    Get a specific booking by voucher code.
    """
    services.context.set_sport(sport)

    # Initialize Beyond API using user's tokens (no auto-SMS)
    ensure_beyond_api(services, current_user)

    bookings = services.bookings.list_bookings()

    for b in bookings:
        if b.get("voucherCode") == voucher_code:
            member = b.get("member", {})
            invitation = b.get("invitation", {})

            # Extract interval from begin field
            begin = invitation.get("begin", "")
            interval = begin[:5] if len(str(begin)) >= 5 else begin
            if not interval:
                interval = invitation.get("interval", "")

            # Tags from booking root
            tags = b.get("tags", [])
            if not tags:
                tags = invitation.get("tags", [])

            level = None
            wave_side = None
            for tag in tags:
                if "Iniciante" in tag or "Intermediario" in tag or "Avançado" in tag or "Avancado" in tag:
                    level = tag
                elif "Lado_" in tag:
                    wave_side = tag

            return {
                "voucher_code": voucher_code,
                "access_code": b.get("accessCode", invitation.get("accessCode", "")),
                "member": member,
                "invitation": invitation,
                "date": invitation.get("date", "").split("T")[0],
                "interval": interval,
                "level": level,
                "wave_side": wave_side,
                "status": b.get("status", "Unknown"),
                "tags": tags
            }

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Booking {voucher_code} not found"
    )


@router.delete("/{voucher_code}")
async def cancel_booking(
    voucher_code: str,
    services: ServicesDep,
    current_user: CurrentUser,
    sport: str = Query("surf", description="Sport")
):
    """
    Cancel a booking.
    """
    services.context.set_sport(sport)

    # Initialize Beyond API using user's tokens (no auto-SMS)
    ensure_beyond_api(services, current_user)

    # Get booking details before canceling (for slot refresh)
    bookings = services.bookings.list_bookings()
    booking_info = None
    for b in bookings:
        if b.get("voucherCode") == voucher_code:
            invitation = b.get("invitation", {})
            member = b.get("member", {})
            tags = b.get("tags", []) or invitation.get("tags", [])

            begin = invitation.get("begin", "")
            interval = begin[:5] if len(str(begin)) >= 5 else begin

            level = None
            wave_side = None
            for tag in tags:
                if "Iniciante" in tag or "Intermediario" in tag or "Avançado" in tag or "Avancado" in tag:
                    level = tag
                elif "Lado_" in tag:
                    wave_side = tag

            booking_info = {
                "date": invitation.get("date", "").split("T")[0],
                "interval": interval,
                "level": level,
                "wave_side": wave_side,
                "member_id": member.get("memberId")
            }
            break

    try:
        result = services.bookings.cancel_booking(voucher_code)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    # Update graph
    services.graph.cancel_booking(voucher_code)

    # Force refresh members cache to update usage counts
    services.members.refresh_members()

    # Refresh availability for this specific slot
    if booking_info and booking_info.get("level") and booking_info.get("wave_side"):
        services.availability.refresh_slot_availability(
            date=booking_info["date"],
            interval=booking_info["interval"],
            level=booking_info["level"],
            wave_side=booking_info["wave_side"],
            member_id=booking_info["member_id"]
        )

    return {"success": True, "voucher_code": voucher_code, "result": result}


@router.post("/{voucher_code}/swap")
async def swap_booking(
    voucher_code: str,
    request: SwapBookingRequest,
    services: ServicesDep,
    current_user: CurrentUser,
    sport: str = Query("surf", description="Sport")
):
    """
    Swap a booking to a different member.

    Cancels the original booking and creates a new one for the new member.
    """
    from src.services import AvailableSlot

    services.context.set_sport(sport)

    # Initialize Beyond API using user's tokens (no auto-SMS)
    ensure_beyond_api(services, current_user)

    # Get original booking details
    bookings = services.bookings.list_bookings()
    original = None
    for b in bookings:
        if b.get("voucherCode") == voucher_code:
            original = b
            break

    if not original:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Booking {voucher_code} not found"
        )

    # Verify new member exists
    new_member = services.members.get_member_by_id(request.new_member_id)
    if not new_member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Member {request.new_member_id} not found"
        )

    # Extract slot info from original booking
    invitation = original.get("invitation", {})

    # Tags from booking root
    tags = original.get("tags", [])
    if not tags:
        tags = invitation.get("tags", [])

    level = None
    wave_side = None
    for tag in tags:
        if "Iniciante" in tag or "Intermediario" in tag or "Avançado" in tag or "Avancado" in tag:
            level = tag
        elif "Lado_" in tag:
            wave_side = tag

    # We need package_id and product_id - get from availability
    # For now, scan to find the matching slot
    date = invitation.get("date", "").split("T")[0]

    # Extract interval from begin field
    begin = invitation.get("begin", "")
    interval = begin[:5] if len(str(begin)) >= 5 else begin
    if not interval:
        interval = invitation.get("interval", "")

    if not services.availability.is_cache_valid():
        services.availability.scan_availability()

    slots = services.availability.get_slots_from_cache()
    matching_slot = None
    for s in slots:
        if s.date == date and s.interval == interval and s.level == level and s.wave_side == wave_side:
            matching_slot = s
            break

    if not matching_slot:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not find matching slot for swap"
        )

    try:
        result = services.bookings.swap_booking(
            voucher_code=voucher_code,
            new_member_id=request.new_member_id,
            slot=matching_slot
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    new_voucher = result.get("voucherCode", "")
    new_access = result.get("accessCode", result.get("invitation", {}).get("accessCode", ""))

    # Update graph
    services.graph.cancel_booking(voucher_code)
    services.graph.sync_booking(
        voucher=new_voucher,
        access_code=new_access,
        member_id=request.new_member_id,
        date=date,
        interval=interval,
        level=level,
        wave_side=wave_side
    )

    # Force refresh members cache to update usage counts
    services.members.refresh_members()

    return {
        "success": True,
        "old_voucher": voucher_code,
        "new_voucher": new_voucher,
        "new_access_code": new_access,
        "new_member_id": request.new_member_id,
        "new_member_name": new_member.social_name
    }


@router.get("/by-date/{date}")
async def get_bookings_by_date(
    date: str,
    services: ServicesDep,
    current_user: CurrentUser,
    sport: str = Query("surf", description="Sport")
):
    """
    Get bookings for a specific date.
    """
    services.context.set_sport(sport)

    # Initialize Beyond API using user's tokens (no auto-SMS)
    ensure_beyond_api(services, current_user)

    bookings_by_date = services.bookings.get_bookings_by_date()
    bookings = bookings_by_date.get(date, [])

    return {
        "date": date,
        "sport": sport,
        "bookings": bookings,
        "total": len(bookings)
    }
