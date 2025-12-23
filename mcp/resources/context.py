"""
Context resources for MCP.

Provides data context for Claude to understand the current state.
"""

import json
import logging

from ..context import get_services

logger = logging.getLogger(__name__)


async def get_members_resource() -> str:
    """
    Get members data as JSON resource.

    Returns:
        JSON string with members data
    """
    services = get_services()

    # Ensure API is initialized
    if not services.context.api:
        try:
            services.auth.initialize(use_cached=True)
        except Exception:
            return json.dumps({"error": "API not initialized"})

    members = services.members.get_members()

    result = []
    for m in members:
        prefs = services.members.get_member_preferences(m.member_id)
        prefs_data = None
        if prefs:
            prefs_data = {
                "sessions": [
                    {
                        "level": s.level,
                        "wave_side": s.wave_side,
                        "combo_key": s.get_combo_key()
                    }
                    for s in prefs.sessions
                ],
                "target_hours": prefs.target_hours,
                "target_dates": prefs.target_dates
            }

        result.append({
            "member_id": m.member_id,
            "name": m.name,
            "social_name": m.social_name,
            "is_titular": m.is_titular,
            "usage": m.usage,
            "limit": m.limit,
            "preferences": prefs_data
        })

    return json.dumps(result, indent=2, ensure_ascii=False)


async def get_bookings_resource() -> str:
    """
    Get active bookings as JSON resource.

    Returns:
        JSON string with bookings data
    """
    services = get_services()

    # Ensure API is initialized
    if not services.context.api:
        try:
            services.auth.initialize(use_cached=True)
        except Exception:
            return json.dumps({"error": "API not initialized"})

    bookings = services.bookings.get_active_bookings()

    result = []
    for b in bookings:
        member = b.get("member", {})
        invitation = b.get("invitation", {})
        tags = invitation.get("tags", [])

        level = wave_side = None
        for tag in tags:
            if "Iniciante" in tag or "Intermediario" in tag or "Avançado" in tag:
                level = tag
            elif "Lado_" in tag:
                wave_side = tag

        result.append({
            "voucher_code": b.get("voucherCode"),
            "access_code": b.get("accessCode", invitation.get("accessCode")),
            "member_id": member.get("memberId"),
            "member_name": member.get("socialName"),
            "date": invitation.get("date", "").split("T")[0],
            "interval": invitation.get("interval"),
            "level": level,
            "wave_side": wave_side,
            "status": b.get("status")
        })

    return json.dumps(result, indent=2, ensure_ascii=False)


async def get_availability_resource() -> str:
    """
    Get availability cache as JSON resource.

    Returns:
        JSON string with availability data
    """
    services = get_services()

    if not services.availability.is_cache_valid():
        return json.dumps({"error": "Cache not valid", "slots": []})

    slots = services.availability.get_slots_from_cache()

    # Filter to available only
    available = [s for s in slots if s.available > 0]

    result = [
        {
            "date": s.date,
            "interval": s.interval,
            "level": s.level,
            "wave_side": s.wave_side,
            "available": s.available,
            "max_quantity": s.max_quantity,
            "combo_key": s.combo_key
        }
        for s in available
    ]

    return json.dumps(result, indent=2, ensure_ascii=False)


async def get_preferences_resource() -> str:
    """
    Get all member preferences as JSON resource.

    Returns:
        JSON string with preferences data
    """
    services = get_services()

    members = services.members.get_members()

    result = {}
    for m in members:
        # Get preferences for all sports
        sports_prefs = {}
        for sport in ["surf", "tennis"]:
            prefs = services.members.get_member_preferences(m.member_id, sport)
            if prefs and prefs.sessions:
                sports_prefs[sport] = {
                    "sessions": [
                        {
                            "level": s.level,
                            "wave_side": s.wave_side,
                            "combo_key": s.get_combo_key()
                        }
                        for s in prefs.sessions
                    ],
                    "target_hours": prefs.target_hours,
                    "target_dates": prefs.target_dates
                }

        if sports_prefs:
            result[m.social_name] = {
                "member_id": m.member_id,
                "preferences": sports_prefs
            }

    return json.dumps(result, indent=2, ensure_ascii=False)
