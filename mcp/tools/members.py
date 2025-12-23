"""
Members tools for MCP.

Handles member listing and preferences.
"""

import logging
from typing import Optional

from ..context import get_services

logger = logging.getLogger(__name__)


async def get_members(sport: str = "surf") -> str:
    """
    Get list of all members.

    Args:
        sport: Sport context

    Returns:
        Formatted member list
    """
    services = get_services()
    services.context.set_sport(sport)

    # Ensure API is initialized
    if not services.context.api:
        services.auth.initialize(use_cached=True)

    members = services.members.get_members()

    if not members:
        return "❌ Nenhum membro encontrado."

    # Get active bookings
    try:
        active_bookings = services.bookings.get_active_bookings()
        booked_ids = {b.get("member", {}).get("memberId") for b in active_bookings}
    except Exception:
        booked_ids = set()

    lines = [f"👥 Membros ({sport.upper()}):\n"]

    for m in members:
        titular = " (Titular)" if m.is_titular else ""
        booked = " ✅ Agendado" if m.member_id in booked_ids else ""
        usage_status = f"Uso: {m.usage}/{m.limit}"

        prefs = services.members.get_member_preferences(m.member_id, sport)
        prefs_str = ""
        if prefs and prefs.sessions:
            combos = [s.get_combo_key() for s in prefs.sessions]
            prefs_str = f"\n  🎯 Preferências: {', '.join(combos)}"
            if prefs.target_hours:
                prefs_str += f"\n  ⏰ Horários: {', '.join(prefs.target_hours)}"

        lines.append(f"• {m.social_name}{titular}{booked}")
        lines.append(f"  📊 {usage_status}{prefs_str}")
        lines.append("")

        # Sync to graph
        services.graph.sync_member(
            member_id=m.member_id,
            name=m.name,
            social_name=m.social_name,
            is_titular=m.is_titular
        )

    lines.append(f"Total: {len(members)} membros")
    return "\n".join(lines)


async def get_member_preferences(
    member_name: str,
    sport: str = "surf"
) -> str:
    """
    Get a member's preferences.

    Args:
        member_name: Member's name
        sport: Sport context

    Returns:
        Formatted preferences
    """
    services = get_services()
    services.context.set_sport(sport)

    member = services.members.get_member_by_name(member_name)
    if not member:
        return f"❌ Membro '{member_name}' não encontrado."

    prefs = services.members.get_member_preferences(member.member_id, sport)

    if not prefs or not prefs.sessions:
        return f"ℹ️ {member.social_name} não tem preferências configuradas para {sport}."

    lines = [f"🎯 Preferências de {member.social_name} ({sport.upper()}):\n"]

    for i, session in enumerate(prefs.sessions, 1):
        combo = session.get_combo_key()
        lines.append(f"  {i}. {combo}")

    if prefs.target_hours:
        lines.append(f"\n⏰ Horários preferidos: {', '.join(prefs.target_hours)}")

    if prefs.target_dates:
        lines.append(f"📅 Datas alvo: {', '.join(prefs.target_dates)}")

    # Get graph summary
    try:
        similar = services.graph.find_similar_members(member.member_id, sport)
        if similar:
            lines.append("\n👥 Membros com preferências similares:")
            for s in similar[:3]:
                lines.append(f"  • {s.get('name')} ({int(s.get('similarity', 0) * 100)}%)")
    except Exception:
        pass

    return "\n".join(lines)
