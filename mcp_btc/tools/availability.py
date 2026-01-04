"""
Availability tools for MCP.

Handles checking and scanning slot availability.
"""

import logging
from typing import Optional
from datetime import datetime

from ..context import get_services

logger = logging.getLogger(__name__)


async def check_availability(
    sport: str = "surf",
    date: Optional[str] = None,
    level: Optional[str] = None,
    wave_side: Optional[str] = None
) -> str:
    """
    Check available slots.

    Args:
        sport: Sport type
        date: Optional date filter (YYYY-MM-DD)
        level: Optional level filter
        wave_side: Optional wave side filter

    Returns:
        Formatted availability list
    """
    services = get_services()
    services.context.set_sport(sport)

    # Ensure API is initialized
    if not services.context.api:
        services.auth.initialize(use_cached=True)

    # Get slots (from cache if valid)
    if services.availability.is_cache_valid():
        slots = services.availability.get_slots_from_cache()
        from_cache = True
    else:
        slots = services.availability.scan_availability()
        from_cache = False

    # Filter slots
    today = datetime.now().strftime("%Y-%m-%d")
    slots = [s for s in slots if s.date >= today and s.available > 0]

    if date:
        slots = [s for s in slots if s.date == date]
    if level:
        slots = [s for s in slots if s.level == level]
    if wave_side:
        slots = [s for s in slots if s.wave_side == wave_side]

    if not slots:
        filters = []
        if date:
            filters.append(f"data={date}")
        if level:
            filters.append(f"nível={level}")
        if wave_side:
            filters.append(f"lado={wave_side}")
        filter_str = ", ".join(filters) if filters else "nenhum filtro"
        return f"❌ Nenhum slot disponível ({filter_str})."

    # Group by date
    by_date = {}
    for slot in slots:
        if slot.date not in by_date:
            by_date[slot.date] = []
        by_date[slot.date].append(slot)

    lines = [f"📅 Disponibilidade ({sport.upper()})"]
    if from_cache:
        lines.append("(dados do cache)\n")
    else:
        lines.append("(dados atualizados)\n")

    for date_str in sorted(by_date.keys()):
        lines.append(f"📆 {date_str}:")
        date_slots = sorted(by_date[date_str], key=lambda s: (s.interval, s.combo_key))

        for slot in date_slots:
            lines.append(
                f"  • {slot.interval} - {slot.level}/{slot.wave_side} "
                f"({slot.available}/{slot.max_quantity} vagas)"
            )
        lines.append("")

    lines.append(f"Total: {len(slots)} slots disponíveis")
    return "\n".join(lines)


async def scan_availability(sport: str = "surf") -> str:
    """
    Force a fresh availability scan.

    Args:
        sport: Sport type

    Returns:
        Scan result summary
    """
    services = get_services()
    services.context.set_sport(sport)

    # Ensure API is initialized
    if not services.context.api:
        services.auth.initialize(use_cached=True)

    # Force scan
    slots = services.availability.scan_availability()

    # Filter to available only
    available = [s for s in slots if s.available > 0]

    # Get unique dates
    dates = sorted(set(s.date for s in available))

    # Get unique combos
    combos = set(s.combo_key for s in available)

    # Sync to graph
    for slot in available:
        services.graph.sync_available_slot(
            date=slot.date,
            interval=slot.interval,
            available=slot.available,
            max_quantity=slot.max_quantity,
            level=slot.level,
            wave_side=slot.wave_side
        )

    return f"""✅ Scan completo ({sport.upper()})

📊 Resumo:
• Total de slots: {len(available)}
• Datas disponíveis: {len(dates)}
• Combinações com vagas: {len(combos)}

📆 Datas:
{chr(10).join(f'  • {d}' for d in dates)}

🏄 Sessões:
{chr(10).join(f'  • {c}' for c in sorted(combos))}"""
