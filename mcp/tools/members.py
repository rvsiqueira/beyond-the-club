"""
Members tools for MCP.

Handles member listing and preferences.
"""

import logging
from typing import Optional, List

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


async def set_member_preferences(
    member_name: str,
    sessions: List[dict],
    target_hours: Optional[List[str]] = None,
    target_dates: Optional[List[str]] = None,
    sport: str = "surf"
) -> str:
    """
    Set preferences for a member.

    Args:
        member_name: Member's name
        sessions: List of session preferences, each with 'level' and 'wave_side' keys
                  Example: [{"level": "Avançado2", "wave_side": "Lado_direito"}]
        target_hours: Optional preferred hours (e.g., ["08:00", "09:00"])
        target_dates: Optional target dates (YYYY-MM-DD)
        sport: Sport type

    Returns:
        Result message
    """
    from src.services import MemberPreferences, SessionPreference

    services = get_services()
    services.context.set_sport(sport)

    # Find member
    member = services.members.get_member_by_name(member_name)
    if not member:
        return f"❌ Membro '{member_name}' não encontrado."

    if not sessions:
        return "❌ É necessário informar pelo menos uma sessão de preferência."

    # Build session preferences
    session_prefs = []
    for i, s in enumerate(sessions):
        attrs = {}
        if s.get("level"):
            attrs["level"] = s["level"]
        if s.get("wave_side"):
            attrs["wave_side"] = s["wave_side"]
        if s.get("court"):
            attrs["court"] = s["court"]

        session_prefs.append(SessionPreference(attributes=attrs))

        # Sync to graph
        services.graph.sync_member_preference(
            member_id=member.member_id,
            sport=sport,
            priority=i + 1,
            level=s.get("level"),
            wave_side=s.get("wave_side"),
            court=s.get("court"),
            target_hours=target_hours
        )

    prefs = MemberPreferences(
        sessions=session_prefs,
        target_hours=target_hours,
        target_dates=target_dates
    )

    services.members.set_member_preferences(member.member_id, prefs, sport)

    # Format response
    combos = []
    for s in sessions:
        if s.get("level") and s.get("wave_side"):
            combos.append(f"{s['level']}/{s['wave_side']}")
        elif s.get("court"):
            combos.append(s["court"])

    result = f"""✅ Preferências salvas para {member.social_name}!

🎯 Sessões configuradas:
"""
    for i, combo in enumerate(combos, 1):
        result += f"  {i}. {combo}\n"

    if target_hours:
        result += f"\n⏰ Horários: {', '.join(target_hours)}"

    if target_dates:
        result += f"\n📅 Datas: {', '.join(target_dates)}"

    return result


async def delete_member_preferences(
    member_name: str,
    sport: str = "surf"
) -> str:
    """
    Delete all preferences for a member.

    Args:
        member_name: Member's name
        sport: Sport type

    Returns:
        Result message
    """
    services = get_services()
    services.context.set_sport(sport)

    # Find member
    member = services.members.get_member_by_name(member_name)
    if not member:
        return f"❌ Membro '{member_name}' não encontrado."

    # Check if has preferences
    prefs = services.members.get_member_preferences(member.member_id, sport)
    if not prefs or not prefs.sessions:
        return f"ℹ️ {member.social_name} não tem preferências configuradas para {sport}."

    # Delete preferences
    services.members.clear_member_preferences(member.member_id, sport)
    services.graph.clear_member_preferences(member.member_id, sport)

    return f"✅ Preferências de {member.social_name} para {sport} foram removidas."
