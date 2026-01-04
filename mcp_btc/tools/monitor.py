"""
Monitor tools for MCP.

Handles automatic monitoring and booking.
"""

import logging
from typing import Optional, List

from ..context import get_services
from src.config import SESSION_FIXED_HOURS, get_valid_hours_for_level

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


async def get_session_options() -> str:
    """
    Get available session options with fixed hours per level.

    Returns:
        Formatted string with levels, wave sides, and valid hours for each level
    """
    lines = ["📋 Opções de Sessão Disponíveis\n"]

    lines.append("🎯 Níveis e Horários Fixos:")
    for level, hours in SESSION_FIXED_HOURS.items():
        lines.append(f"  • {level}: {', '.join(hours)}")

    lines.append("\n🌊 Lados de Onda:")
    lines.append("  • Lado_esquerdo")
    lines.append("  • Lado_direito")

    lines.append("\n💡 Use search_session para buscar uma sessão específica.")

    return "\n".join(lines)


async def search_session(
    member_name: str,
    level: str,
    target_date: str,
    target_hour: Optional[str] = None,
    wave_side: Optional[str] = None,
    auto_book: bool = True,
    duration_minutes: int = 120,
    sport: str = "surf"
) -> str:
    """
    Search for a specific session with fixed parameters.

    Unlike start_auto_monitor which uses member preferences, this function
    allows searching for a specific session:
    - Specific level (e.g., "Iniciante2") - required
    - Specific date (e.g., "2025-12-26") - required
    - Specific hour (optional - if not specified, searches all valid hours in order)
    - Wave side (optional - searches both sides if not specified)

    When hour is not specified, searches all valid hours for the level
    in sequence from earliest to latest, trying both wave sides for each hour.

    Args:
        member_name: Name of the member to book for
        level: Session level (Iniciante1, Iniciante2, Intermediario1, Intermediario2, Avançado1, Avançado2)
        target_date: Target date (YYYY-MM-DD format)
        target_hour: Target hour (HH:MM format) - optional, searches all valid hours if not specified
        wave_side: Wave side (Lado_esquerdo or Lado_direito) - optional
        auto_book: If True, book immediately when slot found (default: True)
        duration_minutes: How long to run the search (default: 120 min)
        sport: Sport type (default: "surf")

    Returns:
        Search result message
    """
    global _monitor_state

    if _monitor_state["running"]:
        return "⚠️ Um monitor já está em execução. Use check_monitor_status para ver o status."

    # Validate level
    valid_hours = get_valid_hours_for_level(level)
    if not valid_hours:
        return f"❌ Nível inválido: {level}\n\nNíveis válidos: {', '.join(SESSION_FIXED_HOURS.keys())}"

    # Validate hour for the level (only if specified)
    if target_hour and target_hour not in valid_hours:
        return f"❌ Horário {target_hour} inválido para {level}\n\nHorários válidos para {level}: {', '.join(valid_hours)}"

    # Validate wave_side if provided
    valid_sides = ["Lado_esquerdo", "Lado_direito"]
    if wave_side and wave_side not in valid_sides:
        return f"❌ Lado inválido: {wave_side}\n\nLados válidos: {', '.join(valid_sides)}"

    services = get_services()
    services.context.set_sport(sport)

    # Ensure API is initialized
    if not services.context.api:
        services.auth.initialize(use_cached=True)

    # Get member by name
    member = services.members.get_member_by_name(member_name)
    if not member:
        return f"❌ Membro '{member_name}' não encontrado."

    # Status callback
    def on_status(msg: str, level_type: str):
        _monitor_state["messages"].append({"message": msg, "level": level_type})

    # Start search
    _monitor_state["running"] = True
    _monitor_state["messages"] = []

    side_desc = wave_side if wave_side else "ambos os lados"
    hour_desc = target_hour if target_hour else f"qualquer ({', '.join(valid_hours)})"

    try:
        result = services.monitor.run_session_search(
            member_id=member.member_id,
            level=level,
            target_date=target_date,
            target_hour=target_hour,
            wave_side=wave_side,
            auto_book=auto_book,
            duration_minutes=duration_minutes,
            check_interval_seconds=30,
            on_status_update=on_status
        )

        _monitor_state["results"] = {member.member_id: result}
        _monitor_state["running"] = False

        if result.get("success"):
            if result.get("voucher"):
                slot = result.get("slot", {})
                slot_combo = f"{slot.get('level')}/{slot.get('wave_side')}"
                lines = [
                    "✅ Sessão agendada com sucesso!\n",
                    f"👤 Membro: {member.social_name}",
                    f"📅 Data: {slot.get('date')}",
                    f"⏰ Horário: {slot.get('interval')}",
                    f"🎯 Sessão: {slot_combo}",
                    f"🎫 Voucher: {result.get('voucher')}",
                    f"🔑 Código de Acesso: {result.get('access_code', 'N/A')}"
                ]

                # Sync to graph
                services.graph.sync_booking(
                    voucher=result.get("voucher", ""),
                    access_code=result.get("access_code", ""),
                    member_id=member.member_id,
                    date=slot.get("date", ""),
                    interval=slot.get("interval", ""),
                    level=slot.get("level"),
                    wave_side=slot.get("wave_side")
                )

                return "\n".join(lines)
            else:
                # Slot found but not booked (auto_book=False)
                slot = result.get("slot", {})
                slot_combo = f"{slot.get('level')}/{slot.get('wave_side')}"
                lines = [
                    "✅ Sessão encontrada (não agendada)\n",
                    f"👤 Membro: {member.social_name}",
                    f"📅 Data: {slot.get('date')}",
                    f"⏰ Horário: {slot.get('interval')}",
                    f"🎯 Sessão: {slot_combo}",
                    f"📊 Vagas disponíveis: {slot.get('available')}",
                    "\n💡 Use auto_book=True para agendar automaticamente."
                ]
                return "\n".join(lines)
        else:
            error = result.get("error", "Erro desconhecido")
            lines = [
                f"❌ Sessão não encontrada\n",
                f"👤 Membro: {member.social_name}",
                f"📅 Data buscada: {target_date}",
                f"⏰ Horário buscado: {hour_desc}",
                f"🎯 Nível buscado: {level} | Lado: {side_desc}",
                f"\n⚠️ Motivo: {error}"
            ]
            return "\n".join(lines)

    except Exception as e:
        _monitor_state["running"] = False
        return f"❌ Erro na busca: {str(e)}"


async def check_session_availability(
    member_name: str,
    level: str,
    target_date: str,
    wave_side: Optional[str] = None,
    target_hour: Optional[str] = None,
    sport: str = "surf"
) -> str:
    """
    Check availability for a session (single check, no monitoring).

    Use this to find available slots and present options to the user.
    Returns all available slots so the user can choose which one to book.

    Args:
        member_name: Name of the member to check for
        level: Session level (Iniciante1, Iniciante2, etc.)
        target_date: Target date (YYYY-MM-DD format)
        wave_side: Wave side (optional - checks both if not specified)
        target_hour: Target hour (optional - checks all valid hours if not specified)
        sport: Sport type (default: "surf")

    Returns:
        List of available slots for the user to choose from
    """
    # Validate level
    valid_hours = get_valid_hours_for_level(level)
    if not valid_hours:
        return f"❌ Nível inválido: {level}\n\nNíveis válidos: {', '.join(SESSION_FIXED_HOURS.keys())}"

    # Validate hour if provided
    if target_hour and target_hour not in valid_hours:
        return f"❌ Horário {target_hour} inválido para {level}\n\nHorários válidos: {', '.join(valid_hours)}"

    services = get_services()
    services.context.set_sport(sport)

    # Ensure API is initialized
    if not services.context.api:
        services.auth.initialize(use_cached=True)

    # Get member by name
    member = services.members.get_member_by_name(member_name)
    if not member:
        return f"❌ Membro '{member_name}' não encontrado."

    result = services.monitor.check_session_availability(
        member_id=member.member_id,
        level=level,
        target_date=target_date,
        wave_side=wave_side,
        target_hour=target_hour
    )

    if not result.get("success"):
        return f"❌ Erro: {result.get('error', 'Erro desconhecido')}"

    available_slots = result.get("available_slots", [])

    if not available_slots:
        checked_hours = result.get("checked_hours", [])
        checked_sides = result.get("checked_sides", [])
        lines = [
            f"❌ Nenhuma sessão disponível\n",
            f"👤 Membro: {member.social_name}",
            f"📅 Data: {target_date}",
            f"🎯 Nível: {level}",
            f"⏰ Horários verificados: {', '.join(checked_hours)}",
            f"🌊 Lados verificados: {', '.join(checked_sides)}",
            "\n💡 Você pode tentar outra data ou usar search_session para monitorar até encontrar."
        ]
        return "\n".join(lines)

    # Format available options
    lines = [
        f"✅ Sessões disponíveis para {member.social_name}\n",
        f"📅 Data: {target_date}",
        f"🎯 Nível: {level}\n",
        "🌊 Opções encontradas:"
    ]

    for slot in available_slots:
        side_name = "Esquerdo" if slot["wave_side"] == "Lado_esquerdo" else "Direito"
        lines.append(f"  • {slot['hour']} - Lado {side_name} ({slot['available']} vagas)")

    lines.append("\n💡 Para reservar, diga qual horário e lado você prefere.")
    lines.append("💡 Para monitorar, use search_session com o horário e lado desejados.")

    return "\n".join(lines)


async def book_specific_slot(
    member_name: str,
    level: str,
    wave_side: str,
    target_date: str,
    target_hour: str,
    sport: str = "surf"
) -> str:
    """
    Book a specific slot directly (no monitoring, immediate booking).

    Use this after check_session_availability when the user has chosen a slot.

    Args:
        member_name: Name of the member to book for
        level: Session level
        wave_side: Wave side (Lado_esquerdo or Lado_direito)
        target_date: Date (YYYY-MM-DD)
        target_hour: Hour (HH:MM)
        sport: Sport type

    Returns:
        Booking result
    """
    # Validate level
    valid_hours = get_valid_hours_for_level(level)
    if not valid_hours:
        return f"❌ Nível inválido: {level}"

    if target_hour not in valid_hours:
        return f"❌ Horário {target_hour} inválido para {level}"

    valid_sides = ["Lado_esquerdo", "Lado_direito"]
    if wave_side not in valid_sides:
        return f"❌ Lado inválido: {wave_side}"

    services = get_services()
    services.context.set_sport(sport)

    if not services.context.api:
        services.auth.initialize(use_cached=True)

    member = services.members.get_member_by_name(member_name)
    if not member:
        return f"❌ Membro '{member_name}' não encontrado."

    # Check availability first
    slot = services.availability.find_slot_for_combo(
        level=level,
        wave_side=wave_side,
        member_id=member.member_id,
        target_dates=[target_date],
        target_hours=[target_hour]
    )

    if not slot or slot.date != target_date or slot.interval != target_hour:
        return f"❌ Sessão não disponível: {level}/{wave_side} em {target_date} às {target_hour}"

    # Book the slot
    try:
        result = services.bookings.create_booking(slot, member.member_id)
        voucher = result.get("voucherCode", "N/A")
        access = result.get("accessCode", result.get("invitation", {}).get("accessCode", "N/A"))

        # Sync to graph
        services.graph.sync_booking(
            voucher=voucher,
            access_code=access,
            member_id=member.member_id,
            date=slot.date,
            interval=slot.interval,
            level=slot.level,
            wave_side=slot.wave_side
        )

        side_name = "Esquerdo" if wave_side == "Lado_esquerdo" else "Direito"
        lines = [
            "✅ Sessão reservada com sucesso!\n",
            f"👤 Membro: {member.social_name}",
            f"📅 Data: {target_date}",
            f"⏰ Horário: {target_hour}",
            f"🎯 Nível: {level}",
            f"🌊 Lado: {side_name}",
            f"🎫 Voucher: {voucher}",
            f"🔑 Código de Acesso: {access}"
        ]
        return "\n".join(lines)

    except Exception as e:
        error_msg = str(e)
        if "ja possui" in error_msg.lower() or "already" in error_msg.lower():
            return f"❌ {member.social_name} já possui um agendamento ativo."
        return f"❌ Erro ao reservar: {error_msg}"
