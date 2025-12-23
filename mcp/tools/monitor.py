"""
Monitor tools for MCP.

Handles automatic monitoring and booking.
"""

import logging
from typing import Optional, List

from ..context import get_services

logger = logging.getLogger(__name__)

# Store monitor state
_monitor_state = {
    "running": False,
    "results": {},
    "messages": []
}


async def start_auto_monitor(
    member_names: Optional[List[str]] = None,
    target_dates: Optional[List[str]] = None,
    duration_minutes: int = 120,
    sport: str = "surf"
) -> str:
    """
    Start automatic monitoring and booking.

    Args:
        member_names: Optional list of member names to monitor
        target_dates: Optional list of target dates
        duration_minutes: Duration to run
        sport: Sport type

    Returns:
        Monitor start result
    """
    global _monitor_state

    if _monitor_state["running"]:
        return "⚠️ Um monitor já está em execução. Use check_monitor_status para ver o status."

    services = get_services()
    services.context.set_sport(sport)

    # Ensure API is initialized
    if not services.context.api:
        services.auth.initialize(use_cached=True)

    # Get members to monitor
    if member_names:
        member_ids = []
        for name in member_names:
            member = services.members.get_member_by_name(name)
            if member:
                # Verify has preferences
                prefs = services.members.get_member_preferences(member.member_id, sport)
                if prefs and prefs.sessions:
                    member_ids.append(member.member_id)
                else:
                    return f"❌ {name} não tem preferências configuradas."
            else:
                return f"❌ Membro '{name}' não encontrado."
    else:
        # Get all members without bookings and with preferences
        all_members = services.members.get_members_without_booking()
        member_ids = []
        for m in all_members:
            prefs = services.members.get_member_preferences(m.member_id, sport)
            if prefs and prefs.sessions:
                member_ids.append(m.member_id)

    if not member_ids:
        return "❌ Nenhum membro disponível para monitorar (sem preferências ou já agendados)."

    # Get member names for display
    member_info = []
    for mid in member_ids:
        member = services.members.get_member_by_id(mid)
        if member:
            member_info.append(member.social_name)

    # Status callback
    def on_status(msg: str, level: str):
        _monitor_state["messages"].append({"message": msg, "level": level})

    # Start monitor (this is synchronous, will block)
    _monitor_state["running"] = True
    _monitor_state["messages"] = []

    try:
        results = services.monitor.run_auto_monitor(
            member_ids=member_ids,
            target_dates=target_dates,
            duration_minutes=duration_minutes,
            check_interval_seconds=30,
            on_status_update=on_status
        )

        _monitor_state["results"] = results
        _monitor_state["running"] = False

        # Format results
        lines = ["✅ Monitor concluído!\n"]

        booked = []
        failed = []

        for mid, result in results.items():
            member = services.members.get_member_by_id(mid)
            name = member.social_name if member else str(mid)

            if result.get("success"):
                slot = result.get("slot", {})
                booked.append(
                    f"• {name}: {slot.get('date')} {slot.get('interval')} "
                    f"- Voucher: {result.get('voucher')}"
                )

                # Sync to graph
                services.graph.sync_booking(
                    voucher=result.get("voucher", ""),
                    access_code=result.get("access_code", ""),
                    member_id=mid,
                    date=slot.get("date", ""),
                    interval=slot.get("interval", ""),
                    level=slot.get("level"),
                    wave_side=slot.get("wave_side")
                )
            else:
                failed.append(f"• {name}: {result.get('error', 'Não encontrado')}")

        if booked:
            lines.append("🎉 Agendados:")
            lines.extend(booked)
            lines.append("")

        if failed:
            lines.append("⚠️ Não agendados:")
            lines.extend(failed)

        return "\n".join(lines)

    except Exception as e:
        _monitor_state["running"] = False
        return f"❌ Erro no monitor: {str(e)}"


async def check_monitor_status() -> str:
    """
    Check current monitor status.

    Returns:
        Monitor status
    """
    global _monitor_state

    if _monitor_state["running"]:
        msg_count = len(_monitor_state["messages"])
        recent = _monitor_state["messages"][-5:] if _monitor_state["messages"] else []

        lines = ["🔄 Monitor em execução...\n"]
        lines.append(f"📊 {msg_count} mensagens de status\n")

        if recent:
            lines.append("Últimas mensagens:")
            for m in recent:
                lines.append(f"  [{m['level']}] {m['message']}")

        return "\n".join(lines)

    elif _monitor_state["results"]:
        booked = sum(1 for r in _monitor_state["results"].values() if r.get("success"))
        total = len(_monitor_state["results"])

        return f"""✅ Monitor concluído

📊 Resultado: {booked}/{total} membros agendados

Use list_bookings para ver os agendamentos."""

    else:
        return "ℹ️ Nenhum monitor em execução. Use start_auto_monitor para iniciar."
