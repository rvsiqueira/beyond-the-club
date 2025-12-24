"""
Booking tools for MCP.

Handles booking creation, cancellation, and listing.
"""

import json
import logging
from typing import Optional, List

from ..context import get_services

logger = logging.getLogger(__name__)


async def book_session(
    member_name: str,
    date: str,
    time: str,
    level: Optional[str] = None,
    wave_side: Optional[str] = None,
    sport: str = "surf"
) -> str:
    """
    Book a session for a member.

    Args:
        member_name: Member's name
        date: Session date (YYYY-MM-DD)
        time: Session time (e.g., '08:00')
        level: Optional level override
        wave_side: Optional wave side override
        sport: Sport type

    Returns:
        Booking result as formatted string
    """
    services = get_services()
    services.context.set_sport(sport)

    # Ensure API is initialized
    if not services.context.api:
        services.auth.initialize(use_cached=True)

    # Find member by name
    member = services.members.get_member_by_name(member_name)
    if not member:
        return f"❌ Membro '{member_name}' não encontrado. Use get_members para ver a lista."

    # Check if already has booking
    if services.bookings.has_active_booking(member.member_id):
        return f"❌ {member.social_name} já possui um agendamento ativo."

    # Get member preferences if level/wave_side not specified
    if not level or not wave_side:
        prefs = services.members.get_member_preferences(member.member_id, sport)
        if prefs and prefs.sessions:
            pref = prefs.sessions[0]
            level = level or pref.level
            wave_side = wave_side or pref.wave_side

    if not level or not wave_side:
        return f"❌ {member.social_name} não tem preferências configuradas e level/wave_side não foram especificados."

    # Find matching slot
    slot = services.availability.find_slot_for_combo(
        level=level,
        wave_side=wave_side,
        member_id=member.member_id,
        target_dates=[date],
        target_hours=[time]
    )

    if not slot:
        # Try scanning for fresh data
        services.availability.scan_availability()
        slot = services.availability.find_slot_for_combo(
            level=level,
            wave_side=wave_side,
            member_id=member.member_id,
            target_dates=[date],
            target_hours=[time]
        )

    if not slot:
        return f"❌ Nenhum slot disponível para {level}/{wave_side} em {date} às {time}."

    # Create booking
    try:
        result = services.bookings.create_booking(slot, member.member_id)
        voucher = result.get("voucherCode", "N/A")
        access = result.get("accessCode", result.get("invitation", {}).get("accessCode", "N/A"))

        # Sync to graph
        services.graph.sync_booking(
            voucher=voucher,
            access_code=access,
            member_id=member.member_id,
            date=date,
            interval=time,
            level=level,
            wave_side=wave_side
        )

        return f"""✅ Reserva confirmada!

📋 Detalhes:
• Membro: {member.social_name}
• Data: {date}
• Horário: {time}
• Sessão: {level}/{wave_side}
• Voucher: {voucher}
• Código de acesso: {access}"""

    except Exception as e:
        return f"❌ Erro ao criar reserva: {str(e)}"


async def cancel_booking(voucher_code: str) -> str:
    """
    Cancel a booking.

    Args:
        voucher_code: Booking voucher code

    Returns:
        Cancellation result
    """
    services = get_services()

    # Ensure API is initialized
    if not services.context.api:
        services.auth.initialize(use_cached=True)

    try:
        services.bookings.cancel_booking(voucher_code)
        services.graph.cancel_booking(voucher_code)
        return f"✅ Reserva {voucher_code} cancelada com sucesso."
    except Exception as e:
        return f"❌ Erro ao cancelar reserva: {str(e)}"


async def swap_booking(
    voucher_code: str,
    new_member_name: str,
    sport: str = "surf"
) -> str:
    """
    Swap a booking to a different member.

    Args:
        voucher_code: Current booking voucher code
        new_member_name: Name of the new member to transfer to
        sport: Sport type

    Returns:
        Swap result as formatted string
    """
    services = get_services()
    services.context.set_sport(sport)

    # Ensure API is initialized
    if not services.context.api:
        services.auth.initialize(use_cached=True)

    # Find new member
    new_member = services.members.get_member_by_name(new_member_name)
    if not new_member:
        return f"❌ Membro '{new_member_name}' não encontrado. Use get_members para ver a lista."

    # Check if new member already has booking
    if services.bookings.has_active_booking(new_member.member_id):
        return f"❌ {new_member.social_name} já possui um agendamento ativo."

    # Get original booking details
    bookings = services.bookings.list_bookings()
    original = None
    for b in bookings:
        if b.get("voucherCode") == voucher_code:
            original = b
            break

    if not original:
        return f"❌ Reserva {voucher_code} não encontrada."

    # Extract slot info
    invitation = original.get("invitation", {})
    tags = original.get("tags", []) or invitation.get("tags", [])

    level = wave_side = None
    for tag in tags:
        if "Iniciante" in tag or "Intermediario" in tag or "Avançado" in tag or "Avancado" in tag:
            level = tag
        elif "Lado_" in tag:
            wave_side = tag

    date = invitation.get("date", "").split("T")[0]
    begin = invitation.get("begin", "")
    interval = begin[:5] if len(str(begin)) >= 5 else begin or invitation.get("interval", "")

    # Find matching slot from cache
    if not services.availability.is_cache_valid():
        services.availability.scan_availability()

    slots = services.availability.get_slots_from_cache()
    matching_slot = None
    for s in slots:
        if s.date == date and s.interval == interval and s.level == level and s.wave_side == wave_side:
            matching_slot = s
            break

    if not matching_slot:
        return f"❌ Não foi possível encontrar o slot correspondente para swap."

    try:
        result = services.bookings.swap_booking(
            voucher_code=voucher_code,
            new_member_id=new_member.member_id,
            slot=matching_slot
        )

        new_voucher = result.get("voucherCode", "N/A")
        new_access = result.get("accessCode", result.get("invitation", {}).get("accessCode", "N/A"))

        # Update graph
        services.graph.cancel_booking(voucher_code)
        services.graph.sync_booking(
            voucher=new_voucher,
            access_code=new_access,
            member_id=new_member.member_id,
            date=date,
            interval=interval,
            level=level,
            wave_side=wave_side
        )

        old_member_name = original.get("member", {}).get("socialName", "N/A")

        return f"""✅ Swap realizado com sucesso!

📋 Detalhes:
• De: {old_member_name}
• Para: {new_member.social_name}
• Data: {date} às {interval}
• Sessão: {level}/{wave_side}
• Novo Voucher: {new_voucher}
• Código de acesso: {new_access}"""

    except Exception as e:
        return f"❌ Erro ao fazer swap: {str(e)}"


async def list_bookings(
    member_name: Optional[str] = None,
    sport: str = "surf"
) -> str:
    """
    List active bookings.

    Args:
        member_name: Optional filter by member name
        sport: Sport type

    Returns:
        Formatted list of bookings
    """
    services = get_services()
    services.context.set_sport(sport)

    # Ensure API is initialized
    if not services.context.api:
        services.auth.initialize(use_cached=True)

    bookings = services.bookings.get_active_bookings()

    if not bookings:
        return "📋 Nenhum agendamento ativo encontrado."

    # Filter by member if specified
    if member_name:
        member = services.members.get_member_by_name(member_name)
        if member:
            bookings = [
                b for b in bookings
                if b.get("member", {}).get("memberId") == member.member_id
            ]

    if not bookings:
        return f"📋 Nenhum agendamento ativo para '{member_name}'."

    lines = ["📋 Agendamentos ativos:\n"]

    for b in bookings:
        member = b.get("member", {})
        invitation = b.get("invitation", {})
        tags = invitation.get("tags", [])

        # Extract level/wave_side
        level = wave_side = None
        for tag in tags:
            if "Iniciante" in tag or "Intermediario" in tag or "Avançado" in tag:
                level = tag
            elif "Lado_" in tag:
                wave_side = tag

        date = invitation.get("date", "").split("T")[0]
        interval = invitation.get("interval", "")

        lines.append(f"""• {member.get('socialName', 'N/A')}
  📅 {date} às {interval}
  🏄 {level}/{wave_side}
  🎫 Voucher: {b.get('voucherCode', 'N/A')}
  🔑 Acesso: {b.get('accessCode', invitation.get('accessCode', 'N/A'))}
""")

    return "\n".join(lines)
