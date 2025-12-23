#!/usr/bin/env python3
"""
BeyondTheClub Sport Session Booking Bot

Monitors sport session availability and automatically books sessions
based on configured preferences.
"""

import argparse
import logging
import sys
from datetime import datetime

# Use compatibility layer that wraps services
from src.bot_compat import BeyondBot, Member, MemberPreferences, SessionPreference, AvailableSlot
from src.config import load_config, SportConfig, SPORT_CONFIGS


def get_sport_config(bot: BeyondBot) -> SportConfig:
    """Get the current sport configuration."""
    return bot.get_sport_config()


def display_members(members: list, bot: BeyondBot):
    """Display list of members with their preferences status and details."""
    sport = bot._current_sport
    print(f"\nMembros disponíveis ({sport.upper()}):")
    for i, m in enumerate(members, 1):
        titular = " (Titular)" if m.is_titular else ""
        prefs = bot.get_member_preferences(m.member_id, sport)

        print(f"  {i}. [{m.member_id}] {m.social_name}{titular} - Uso: {m.usage}/{m.limit}")

        if prefs and prefs.sessions:
            # Show all preferences
            for j, s in enumerate(prefs.sessions, 1):
                if s.level and s.wave_side:
                    combo = f"{s.level}/{s.wave_side}"
                else:
                    combo = "/".join(s.attributes.values())
                print(f"      {j}. {combo}")

            if prefs.target_hours:
                print(f"      Horários: {', '.join(prefs.target_hours)}")
            if prefs.target_dates:
                print(f"      Datas: {', '.join(prefs.target_dates)}")
        else:
            print(f"      Prefs: ✗ (não configurado)")


def display_member_preferences(bot: BeyondBot, member: Member, sport: str = None):
    """Display current preferences for a member."""
    sport = sport or bot._current_sport
    sport_config = bot.get_sport_config()
    prefs = bot.get_member_preferences(member.member_id, sport)

    if prefs and prefs.sessions:
        print(f"\n{member.social_name} possui preferências de {sport_config.name} configuradas:")
        for i, s in enumerate(prefs.sessions, 1):
            attrs_str = " / ".join(s.attributes.values())
            print(f"  {i}. {attrs_str}")
        if prefs.target_hours:
            print(f"  Horários: {', '.join(prefs.target_hours)}")
        if prefs.target_dates:
            print(f"  Datas: {', '.join(prefs.target_dates)}")
        return True
    return False


def configure_member_preferences(bot: BeyondBot, member: Member):
    """Interactive configuration of member preferences."""
    sport = bot._current_sport
    sport_config = bot.get_sport_config()

    # Check if already has preferences
    if display_member_preferences(bot, member, sport):
        keep = input("\nDeseja manter estas preferências? (s/n): ").strip().lower()
        if keep == 's':
            print("Preferências mantidas.")
            return
        print("Apagando preferências anteriores...")
        bot.clear_member_preferences(member.member_id, sport)

    print(f"\nConfigurando preferências de {sport_config.name} para {member.social_name}...")

    sessions = []
    attributes_list = sport_config.get_attributes()

    while True:
        print("\nAdicionar sessão de interesse:")
        selected_attrs = {}

        # Collect each attribute
        for attr_name in attributes_list:
            options = sport_config.get_options(attr_name)
            label = sport_config.attribute_labels.get(attr_name, attr_name)

            print(f"  {label} disponíveis:")
            for i, opt in enumerate(options, 1):
                print(f"    {i}. {opt}")

            choice = input(f"  {label} (número): ").strip()
            try:
                selected_attrs[attr_name] = options[int(choice) - 1]
            except (ValueError, IndexError):
                print("  Opção inválida!")
                break
        else:
            # All attributes collected successfully
            pref = SessionPreference(attributes=selected_attrs)
            sessions.append(pref)
            attrs_str = " / ".join(selected_attrs.values())
            print(f"  Adicionado: {attrs_str}")

            another = input("\nAdicionar outra? (s/n): ").strip().lower()
            if another != 's':
                break
            continue

        # If we broke out due to invalid input, ask to retry
        retry = input("\nTentar novamente? (s/n): ").strip().lower()
        if retry != 's':
            break

    if not sessions:
        print("Nenhuma sessão configurada!")
        return

    # Target hours
    hours_input = input("\nHorários preferidos (ex: 08:00,09:00 ou Enter para todos): ").strip()
    target_hours = [h.strip() for h in hours_input.split(",") if h.strip()] if hours_input else []

    # Target dates
    dates_input = input("Datas específicas (ex: 2025-01-15,2025-01-16 ou Enter para todas): ").strip()
    target_dates = [d.strip() for d in dates_input.split(",") if d.strip()] if dates_input else []

    # Save preferences
    prefs = MemberPreferences(
        sessions=sessions,
        target_hours=target_hours,
        target_dates=target_dates
    )
    bot.set_member_preferences(member.member_id, prefs, sport)

    print(f"\nPreferências de {sport_config.name} salvas para {member.social_name}:")
    for i, s in enumerate(sessions, 1):
        attrs_str = " / ".join(s.attributes.values())
        print(f"  {i}. {attrs_str} (prioridade {i})")
    if target_hours:
        print(f"  Horários: {', '.join(target_hours)}")
    if target_dates:
        print(f"  Datas: {', '.join(target_dates)}")


def select_members_interactive(bot: BeyondBot, members: list) -> list:
    """Interactive member selection."""
    display_members(members, bot)
    print("\nSelecione o(s) membro(s) para monitorar")
    print("  Exemplos: 1 | 1,2,3 | todos")
    choice = input("Sua escolha: ").strip().lower()

    if choice == "todos":
        return members

    selected = []
    try:
        indices = [int(i.strip()) for i in choice.split(",")]
        for idx in indices:
            if 1 <= idx <= len(members):
                selected.append(members[idx - 1])
            else:
                print(f"  Índice {idx} inválido, ignorando...")
    except ValueError:
        print("Entrada inválida!")
        return []

    return selected


def parse_member_argument(bot: BeyondBot, member_arg: str, members: list) -> list:
    """Parse --member argument and return list of members."""
    selected = []
    parts = [p.strip() for p in member_arg.split(",")]

    for part in parts:
        # Try by ID
        try:
            member_id = int(part)
            member = bot.get_member_by_id(member_id)
            if member:
                selected.append(member)
                continue
        except ValueError:
            pass

        # Try by name
        member = bot.get_member_by_name(part)
        if member:
            selected.append(member)
        else:
            print(f"Membro '{part}' não encontrado, ignorando...")

    return selected


def ensure_member_preferences(bot: BeyondBot, member: Member) -> bool:
    """Ensure member has preferences, configure if not."""
    sport = bot._current_sport
    if bot.has_member_preferences(member.member_id, sport):
        if display_member_preferences(bot, member, sport):
            keep = input("\nManter preferências? (s/n): ").strip().lower()
            if keep == 's':
                return True
            bot.clear_member_preferences(member.member_id, sport)

    sport_config = bot.get_sport_config()
    print(f"\n{member.social_name} não possui preferências de {sport_config.name} configuradas.")
    configure_member_preferences(bot, member)
    return bot.has_member_preferences(member.member_id, sport)


def setup_logging(verbose: bool = False):
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO

    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(
                f"beyondtheclub_{datetime.now().strftime('%Y%m%d')}.log"
            )
        ]
    )


def display_inscriptions(inscriptions: dict) -> None:
    """Display inscriptions in a readable format."""
    # Handle API response wrapper
    if isinstance(inscriptions, dict) and "value" in inscriptions:
        inscriptions_list = inscriptions["value"]
    elif isinstance(inscriptions, list):
        inscriptions_list = inscriptions
    else:
        print("\nNenhuma inscrição encontrada.")
        return

    if not inscriptions_list:
        print("\nNenhuma inscrição encontrada.")
        return

    # Group by member
    by_member = {}
    for item in inscriptions_list:
        insc = item.get("singleInscription") or item.get("recurrentInscription")
        if not insc:
            continue

        member = insc.get("member", {})
        member_id = member.get("memberId")
        if member_id not in by_member:
            by_member[member_id] = {
                "name": member.get("socialName", member.get("name", "N/A")),
                "is_titular": member.get("isTitular", False),
                "inscriptions": []
            }

        by_member[member_id]["inscriptions"].append({
            "id": insc.get("inscriptionId"),
            "benefit": insc.get("benefit", {}).get("name", "N/A"),
            "use_limit": insc.get("useLimit", 0),
            "remaining": insc.get("remainingUses", 0),
            "join_date": insc.get("joinDate", "N/A"),
            "is_recurrent": item.get("recurrentInscription") is not None,
        })

    print(f"\n=== Inscrições ({len(inscriptions_list)} total) ===\n")

    for member_id, data in by_member.items():
        titular = " (Titular)" if data["is_titular"] else ""
        print(f"  {data['name']}{titular} [{member_id}]:")

        for insc in data["inscriptions"]:
            status = f"{insc['remaining']}/{insc['use_limit']} usos restantes"
            tipo = "Recorrente" if insc["is_recurrent"] else "Avulso"
            print(f"    - [{insc['id']}] {insc['benefit']}")
            print(f"      {tipo} | {status} | Desde: {insc['join_date']}")

        print()


def display_available_slots(slots: list) -> list:
    """Display available slots grouped by date and return numbered list."""
    if not slots:
        print("\nNenhum horário disponível encontrado.")
        return []

    # Group by date
    by_date = {}
    for slot in slots:
        if slot.date not in by_date:
            by_date[slot.date] = []
        by_date[slot.date].append(slot)

    # Sort dates
    sorted_dates = sorted(by_date.keys())

    print("\nHorários disponíveis:\n")
    numbered_slots = []
    idx = 1

    for date in sorted_dates:
        print(f"  {date}:")
        date_slots = sorted(by_date[date], key=lambda s: (s.interval, s.combo_key))
        for slot in date_slots:
            print(f"    {idx}. {slot.interval} - {slot.combo_key} ({slot.available}/{slot.max_quantity} vagas)")
            numbered_slots.append(slot)
            idx += 1
        print()

    return numbered_slots


def display_bookings(bookings: list, filter_status: str = None) -> list:
    """Display bookings grouped by status and return numbered list.

    Args:
        bookings: List of booking objects
        filter_status: If provided, only show bookings with this status (for selection)

    Returns:
        List of bookings (filtered if filter_status provided)
    """
    if not bookings:
        print("\nNenhum agendamento encontrado.")
        return []

    # Group by status
    by_status = {}
    for booking in bookings:
        status = booking.get("status", "Unknown")
        if status not in by_status:
            by_status[status] = []
        by_status[status].append(booking)

    # Status display order and labels (based on API response)
    status_order = ["AccessReady", "Scheduled", "Confirmed", "Pending", "Canceled", "Cancelled", "Completed", "Unknown"]
    status_labels = {
        "AccessReady": "Prontos para Acesso",
        "Scheduled": "Agendados",
        "Confirmed": "Confirmados",
        "Pending": "Pendentes",
        "Canceled": "Cancelados",
        "Cancelled": "Cancelados",
        "Completed": "Concluídos",
        "Unknown": "Outros"
    }

    print("\nAgendamentos:\n")
    numbered_bookings = []
    idx = 1

    for status in status_order:
        if status not in by_status:
            continue

        status_bookings = by_status[status]
        label = status_labels.get(status, status)
        print(f"  === {label} ({len(status_bookings)}) ===")

        for booking in status_bookings:
            voucher = booking.get("voucherCode", "N/A")
            member = booking.get("member", {})
            member_name = member.get("socialName", member.get("name", "N/A"))
            invitation = booking.get("invitation", {})
            date_raw = invitation.get("date", "N/A")
            # Parse date (comes as "2025-12-28T00:00:00")
            date = date_raw.split("T")[0] if "T" in str(date_raw) else date_raw
            begin = invitation.get("begin", "N/A")
            # Parse time (comes as "10:00:00")
            interval = begin[:5] if len(str(begin)) >= 5 else begin

            # Extract level/wave_side from tags or package info
            tags = booking.get("tags", [])
            level = ""
            wave_side = ""
            for tag in tags:
                if "Iniciante" in tag or "Intermediario" in tag or "Avançado" in tag or "Avancado" in tag:
                    level = tag
                elif "Lado_" in tag:
                    wave_side = tag

            combo = f"{level}/{wave_side}" if level and wave_side else "N/A"

            # Only number if we're showing all or if it matches the filter
            if filter_status is None or status == filter_status:
                print(f"    {idx}. [{voucher}] {member_name} - {date} {interval} ({combo})")
                numbered_bookings.append(booking)
                idx += 1
            else:
                print(f"       [{voucher}] {member_name} - {date} {interval} ({combo})")

        print()

    return numbered_bookings


def display_bookings_for_action(bookings: list, action_statuses: list = None) -> list:
    """Display bookings for action selection (cancel/swap), filtering by actionable statuses.

    Args:
        bookings: List of booking objects
        action_statuses: List of statuses that can be acted upon (default: AccessReady only)

    Returns:
        List of actionable bookings
    """
    if action_statuses is None:
        # Only AccessReady bookings can be cancelled/swapped
        action_statuses = ["AccessReady"]

    if not bookings:
        print("\nNenhum agendamento encontrado.")
        return []

    # Separate actionable and non-actionable
    actionable = []
    non_actionable = []

    for booking in bookings:
        status = booking.get("status", "Unknown")
        if status in action_statuses:
            actionable.append(booking)
        else:
            non_actionable.append(booking)

    if not actionable:
        print("\nNenhum agendamento ativo para esta ação.")
        if non_actionable:
            print(f"({len(non_actionable)} agendamento(s) cancelado(s)/concluído(s) não listado(s))")
        return []

    print("\nAgendamentos disponíveis para ação:\n")

    for i, booking in enumerate(actionable, 1):
        voucher = booking.get("voucherCode", "N/A")
        member = booking.get("member", {})
        member_name = member.get("socialName", member.get("name", "N/A"))
        invitation = booking.get("invitation", {})
        date_raw = invitation.get("date", "N/A")
        # Parse date (comes as "2025-12-28T00:00:00")
        date = date_raw.split("T")[0] if "T" in str(date_raw) else date_raw
        begin = invitation.get("begin", "N/A")
        # Parse time (comes as "10:00:00")
        interval = begin[:5] if len(str(begin)) >= 5 else begin

        tags = booking.get("tags", [])
        level = ""
        wave_side = ""
        for tag in tags:
            if "Iniciante" in tag or "Intermediario" in tag or "Avançado" in tag or "Avancado" in tag:
                level = tag
            elif "Lado_" in tag:
                wave_side = tag

        combo = f"{level}/{wave_side}" if level and wave_side else "N/A"

        print(f"  {i}. [{voucher}] {member_name} - {date} {interval} ({combo})")

    if non_actionable:
        print(f"\n  ({len(non_actionable)} agendamento(s) cancelado(s)/concluído(s) não listado(s))")

    return actionable


def select_slot_interactive(slots: list) -> AvailableSlot:
    """Interactive slot selection."""
    numbered_slots = display_available_slots(slots)
    if not numbered_slots:
        return None

    choice = input("Selecione o horário (número): ").strip()
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(numbered_slots):
            selected = numbered_slots[idx]
            print(f"\nHorário selecionado: {selected.date} {selected.interval} - {selected.combo_key}")
            return selected
        else:
            print("Índice inválido!")
            return None
    except ValueError:
        print("Entrada inválida!")
        return None


def select_booking_interactive(bookings: list) -> dict:
    """Interactive booking selection (shows all bookings)."""
    numbered_bookings = display_bookings(bookings)
    if not numbered_bookings:
        return None

    choice = input("\nSelecione o agendamento (número): ").strip()
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(numbered_bookings):
            return numbered_bookings[idx]
        else:
            print("Índice inválido!")
            return None
    except ValueError:
        print("Entrada inválida!")
        return None


def select_booking_for_action_interactive(bookings: list) -> dict:
    """Interactive booking selection for actions (cancel/swap) - only shows actionable bookings."""
    actionable_bookings = display_bookings_for_action(bookings)
    if not actionable_bookings:
        return None

    choice = input("\nSelecione o agendamento (número): ").strip()
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(actionable_bookings):
            return actionable_bookings[idx]
        else:
            print("Índice inválido!")
            return None
    except ValueError:
        print("Entrada inválida!")
        return None


def get_member_booking_status(members: list, bookings: list) -> dict:
    """
    Build a dict mapping member_id -> booking info for active bookings.

    Returns:
        Dict[member_id, dict with booking details]
    """
    member_bookings = {}

    for booking in bookings:
        status = booking.get("status", "")
        # Only consider active bookings (AccessReady)
        if status != "AccessReady":
            continue

        member = booking.get("member", {})
        member_id = member.get("memberId")
        if not member_id:
            continue

        invitation = booking.get("invitation", {})
        date_raw = invitation.get("date", "")
        date = date_raw.split("T")[0] if "T" in str(date_raw) else date_raw
        begin = invitation.get("begin", "")
        interval = begin[:5] if len(str(begin)) >= 5 else begin

        member_bookings[member_id] = {
            "date": date,
            "interval": interval,
            "voucher": booking.get("voucherCode", "")
        }

    return member_bookings


def select_member_interactive_simple(members: list, bot: BeyondBot) -> Member:
    """Simple interactive member selection for booking with booking status."""
    # Get current bookings to show availability
    try:
        bookings = bot.api.list_bookings(bot._current_sport)
        member_bookings = get_member_booking_status(members, bookings)
    except Exception:
        member_bookings = {}

    print("\nMembros disponíveis:")
    for i, m in enumerate(members, 1):
        titular = " (Titular)" if m.is_titular else ""

        # Check if member has active booking
        booking_info = member_bookings.get(m.member_id)
        if booking_info:
            status = f"Agendado ({booking_info['date']} {booking_info['interval']})"
            print(f"  {i}. [{m.member_id}] {m.social_name}{titular} - Uso: {m.usage}/{m.limit} - {status}")
        else:
            print(f"  {i}. [{m.member_id}] {m.social_name}{titular} - Uso: {m.usage}/{m.limit} - Disponivel")

    choice = input("\nSelecione o membro (número): ").strip()
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(members):
            return members[idx]
        else:
            print("Índice inválido!")
            return None
    except ValueError:
        print("Entrada inválida!")
        return None


def setup_auto_monitor_interactive(bot: BeyondBot) -> dict:
    """
    Interactive setup for auto-monitor.

    Returns:
        Dict with configuration or None if cancelled:
        {
            "member_ids": [int, ...],
            "target_dates": [str, ...] or None,
            "duration_minutes": int,
            "check_interval_seconds": int
        }
    """
    sport = bot._current_sport

    print("\n" + "=" * 50)
    print("   ROBO DE MONITORAMENTO AUTOMATICO")
    print("=" * 50)

    # Step 1: Get members without active booking
    print("\nBuscando membros sem agendamento ativo...")
    try:
        available_members = bot.get_members_without_booking()
    except Exception as e:
        print(f"Erro ao buscar membros: {e}")
        return None

    if not available_members:
        print("\nNenhum membro disponivel (todos ja tem agendamento ativo).")
        return None

    # Show available members with preferences status
    print(f"\nMembros disponiveis para monitoramento ({len(available_members)}):\n")
    for i, m in enumerate(available_members, 1):
        titular = " (Titular)" if m.is_titular else ""
        prefs = bot.get_member_preferences(m.member_id, sport)

        if prefs and prefs.sessions:
            combos = [f"{s.level}/{s.wave_side}" for s in prefs.sessions]
            prefs_str = f"Prefs: {', '.join(combos[:2])}"
            if len(combos) > 2:
                prefs_str += f" +{len(combos)-2}"
            print(f"  {i}. [{m.member_id}] {m.social_name}{titular} - {prefs_str}")
        else:
            print(f"  {i}. [{m.member_id}] {m.social_name}{titular} - SEM PREFERENCIAS")

    # Step 2: Select members
    print("\nSelecione os membros para monitorar")
    print("  Exemplos: 1 | 1,2,3 | todos")
    choice = input("Sua escolha: ").strip().lower()

    selected_members = []
    if choice == "todos":
        selected_members = available_members
    else:
        try:
            indices = [int(i.strip()) for i in choice.split(",")]
            for idx in indices:
                if 1 <= idx <= len(available_members):
                    selected_members.append(available_members[idx - 1])
                else:
                    print(f"  Indice {idx} invalido, ignorando...")
        except ValueError:
            print("Entrada invalida!")
            return None

    if not selected_members:
        print("Nenhum membro selecionado!")
        return None

    # Validate that selected members have preferences
    members_without_prefs = []
    for m in selected_members:
        prefs = bot.get_member_preferences(m.member_id, sport)
        if not prefs or not prefs.sessions:
            members_without_prefs.append(m)

    if members_without_prefs:
        names = [m.social_name for m in members_without_prefs]
        print(f"\nATENCAO: Os seguintes membros NAO tem preferencias configuradas:")
        for name in names:
            print(f"  - {name}")
        print("\nVoce precisa configurar preferencias antes de monitorar.")
        configure = input("Deseja configurar agora? (s/n): ").strip().lower()
        if configure == 's':
            for m in members_without_prefs:
                configure_member_preferences(bot, m)
        else:
            # Remove members without preferences
            selected_members = [m for m in selected_members if m not in members_without_prefs]
            if not selected_members:
                print("Nenhum membro com preferencias configuradas!")
                return None

    print(f"\nMembros selecionados ({len(selected_members)}):")
    for m in selected_members:
        prefs = bot.get_member_preferences(m.member_id, sport)
        combos = [f"{s.level}/{s.wave_side}" for s in prefs.sessions] if prefs else []
        print(f"  - {m.social_name}: {', '.join(combos)}")

    # Step 3: Select dates
    print("\n--- Selecao de Datas ---")
    print("  1. Qualquer data disponivel")
    print("  2. Datas especificas")
    date_choice = input("Sua escolha (1 ou 2): ").strip()

    target_dates = None
    if date_choice == "2":
        # Get available dates first
        print("\nBuscando datas disponiveis...")
        sport_config = bot.get_sport_config()

        # Get dates from first combo to show options
        levels = sport_config.get_options("level")
        wave_sides = sport_config.get_options("wave_side")
        tags = list(sport_config.base_tags) + [levels[0], wave_sides[0]]

        try:
            dates_response = bot.api.get_available_dates(tags, sport=sport)
            if isinstance(dates_response, dict) and "value" in dates_response:
                dates_list = dates_response["value"]
            else:
                dates_list = dates_response

            available_dates = sorted(set(
                d.split("T")[0] for d in dates_list if isinstance(d, str)
            ))

            if available_dates:
                print("\nDatas disponiveis:")
                for i, d in enumerate(available_dates, 1):
                    print(f"  {i}. {d}")

                print("\nSelecione as datas (ex: 1 | 1,2,3 | 2025-12-26,2025-12-27)")
                dates_input = input("Sua escolha: ").strip()

                # Try parsing as indices first
                try:
                    indices = [int(i.strip()) for i in dates_input.split(",")]
                    target_dates = []
                    for idx in indices:
                        if 1 <= idx <= len(available_dates):
                            target_dates.append(available_dates[idx - 1])
                except ValueError:
                    # Try parsing as date strings
                    target_dates = [d.strip() for d in dates_input.split(",") if d.strip()]

                if target_dates:
                    print(f"\nDatas selecionadas: {', '.join(target_dates)}")
                else:
                    print("Usando qualquer data disponivel.")
                    target_dates = None
            else:
                print("Nenhuma data disponivel encontrada.")

        except Exception as e:
            print(f"Erro ao buscar datas: {e}")
            print("Usando qualquer data disponivel.")

    # Step 4: Configure timing
    print("\n--- Configuracao de Tempo ---")

    duration_input = input("Duracao do monitoramento em minutos (padrao: 120): ").strip()
    try:
        duration_minutes = int(duration_input) if duration_input else 120
    except ValueError:
        print("Valor invalido, usando 120 minutos.")
        duration_minutes = 120

    interval_input = input("Intervalo entre verificacoes em segundos (padrao: 30): ").strip()
    try:
        check_interval = int(interval_input) if interval_input else 30
    except ValueError:
        print("Valor invalido, usando 30 segundos.")
        check_interval = 30

    # Confirm
    print("\n" + "=" * 50)
    print("   RESUMO DA CONFIGURACAO")
    print("=" * 50)
    print(f"\nMembros ({len(selected_members)}):")
    for m in selected_members:
        prefs = bot.get_member_preferences(m.member_id, sport)
        combos = [f"{s.level}/{s.wave_side}" for s in prefs.sessions] if prefs else []
        print(f"  - {m.social_name}: {', '.join(combos)}")

    print(f"\nDatas: {', '.join(target_dates) if target_dates else 'Qualquer data disponivel'}")
    print(f"Duracao: {duration_minutes} minutos")
    print(f"Intervalo: {check_interval} segundos")
    print(f"Verificacoes estimadas: ~{(duration_minutes * 60) // check_interval}")

    confirm = input("\nIniciar monitoramento? (s/n): ").strip().lower()
    if confirm != 's':
        print("Monitoramento cancelado.")
        return None

    return {
        "member_ids": [m.member_id for m in selected_members],
        "target_dates": target_dates,
        "duration_minutes": duration_minutes,
        "check_interval_seconds": check_interval
    }


def show_menu(sport: str = "surf") -> str:
    """Show interactive menu and return selected action."""
    menu_options = [
        ("book", "Agendar sessao (selecionar horario -> membro)"),
        ("auto-monitor", "Robo automatico de monitoramento"),
        ("list-bookings", "Listar agendamentos ativos"),
        ("cancel", "Cancelar um agendamento"),
        ("swap", "Trocar membro de um agendamento"),
        ("scan-availability", "Escanear horarios disponiveis"),
        ("list-members", "Listar membros disponiveis"),
        ("configure", "Configurar preferencias de um membro"),
        ("check-status", "Verificar status do sistema"),
        ("inscriptions", "Ver inscricoes do usuario"),
        ("book-test", "Agendamento manual (teste)"),
        ("book-any-member", "Agendar com qualquer membro do titulo"),
        ("explore-packages", "Explorar packages da API"),
        ("debug-token", "Mostrar token de autenticacao"),
        ("exit", "Sair"),
    ]

    print("\n" + "=" * 50)
    print(f"   BEYOND THE CLUB - Menu Principal ({sport.upper()})")
    print("=" * 50)
    print()

    for i, (_, label) in enumerate(menu_options, 1):
        print(f"  {i:2}. {label}")

    print()
    choice = input("Selecione uma opcao (numero): ").strip()

    try:
        idx = int(choice) - 1
        if 0 <= idx < len(menu_options):
            return menu_options[idx][0]
        else:
            print("Opcao invalida!")
            return None
    except ValueError:
        print("Entrada invalida!")
        return None


def execute_menu_action(action: str, args, bot: BeyondBot) -> str:
    """Execute a menu action. Returns 'exit' to quit, None otherwise."""
    sport = args.sport
    sport_config = bot.get_sport_config()

    if action == "list-bookings":
        bookings = bot.api.list_bookings(sport)
        display_bookings(bookings)

    elif action == "cancel":
        bookings = bot.api.list_bookings(sport)
        booking = select_booking_for_action_interactive(bookings)
        if booking:
            voucher = booking.get("voucherCode")
            member_name = booking.get("member", {}).get("socialName", "N/A")
            invitation = booking.get("invitation", {})
            date_raw = invitation.get("date", "N/A")
            date = date_raw.split("T")[0] if "T" in str(date_raw) else date_raw
            begin = invitation.get("begin", "N/A")
            interval = begin[:5] if len(str(begin)) >= 5 else begin

            print(f"\nCancelando agendamento {voucher} ({member_name} - {date} {interval})...")
            confirm = input("Confirmar? (s/n): ").strip().lower()
            if confirm == 's':
                bot.api.cancel_booking(voucher, sport=sport)
                print(f"\n✓ Agendamento cancelado: {voucher}")

    elif action == "swap":
        bookings = bot.api.list_bookings(sport)
        booking = select_booking_for_action_interactive(bookings)
        if booking:
            voucher = booking.get("voucherCode")
            old_member_name = booking.get("member", {}).get("socialName", "N/A")
            invitation = booking.get("invitation", {})
            date_raw = invitation.get("date", "N/A")
            date = date_raw.split("T")[0] if "T" in str(date_raw) else date_raw
            begin = invitation.get("begin", "N/A")
            interval = begin[:5] if len(str(begin)) >= 5 else begin

            tags = booking.get("tags", [])
            level = ""
            wave_side = ""
            for tag in tags:
                if "Iniciante" in tag or "Intermediario" in tag or "Avançado" in tag or "Avancado" in tag:
                    level = tag
                elif "Lado_" in tag:
                    wave_side = tag

            members = bot.get_members()
            new_member = select_member_interactive_simple(members, bot)
            if new_member:
                cache = bot.get_availability_cache()
                pkg = cache.get("packages", {}).get(f"{level}/{wave_side}", {})

                slot = AvailableSlot(
                    date=date,
                    interval=interval,
                    level=level,
                    wave_side=wave_side,
                    available=1,
                    max_quantity=20,
                    package_id=pkg.get("packageId", 0),
                    product_id=pkg.get("productId", 0)
                )

                print(f"\nSubstituindo {old_member_name} por {new_member.social_name}...")
                confirm = input("Confirmar? (s/n): ").strip().lower()
                if confirm == 's':
                    result = bot.swap_booking(voucher, new_member.member_id, slot)
                    print(f"\n✓ Agendamento trocado!")
                    print(f"  Novo voucher: {result.get('voucherCode', 'N/A')}")
                    print(f"  Access Code: {result.get('accessCode', 'N/A')}")

    elif action == "scan-availability":
        print("Escaneando disponibilidade...")
        slots = bot.scan_availability()
        display_available_slots(slots)
        cache = bot.get_availability_cache()
        print(f"\nSalvo em .beyondtheclub_availability.json")
        print(f"Escaneado em: {cache.get('scanned_at', 'N/A')}")

    elif action == "list-members":
        members = bot.get_members(force_refresh=False)
        display_members(members, bot)

    elif action == "configure":
        members = bot.get_members()
        display_members(members, bot)
        choice = input("\nSelecione o membro para configurar (número): ").strip()
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(members):
                configure_member_preferences(bot, members[idx])
        except ValueError:
            print("Entrada inválida!")

    elif action == "check-status":
        status = bot.api.get_schedule_status(sport)
        print(f"\n{sport.upper()} schedule status:")
        import json
        print(json.dumps(status, indent=2, ensure_ascii=False))

    elif action == "inscriptions":
        inscriptions = bot.api.get_inscriptions(tags=sport)
        display_inscriptions(inscriptions)

    elif action == "book":
        # Interactive booking flow
        if bot.is_availability_cache_valid():
            cache = bot.get_availability_cache()
            print(f"\nCache de disponibilidade valido (atualizado em {cache.get('scanned_at', 'N/A')[:19]})")
            refresh = input("Atualizar antes de continuar? (s/n): ").strip().lower()
            if refresh == 's':
                print("Escaneando disponibilidade...")
                slots = bot.scan_availability()
            else:
                slots = bot.get_slots_from_cache()
        else:
            print("\nEscaneando disponibilidade...")
            slots = bot.scan_availability()

        if not slots:
            print("Nenhum horario disponivel!")
            return None

        display_available_slots(slots)
        slot = select_slot_interactive(slots)
        if not slot:
            return None

        print(f"\nHorario selecionado: {slot.date} {slot.interval} - {slot.combo_key}")

        members = bot.get_members()
        member = select_member_interactive_simple(members, bot)
        if not member:
            return None

        print(f"\nConfirmando agendamento:")
        print(f"  Membro: {member.social_name} ({member.member_id})")
        print(f"  Data: {slot.date} {slot.interval}")
        print(f"  Onda: {slot.level} / {slot.wave_side}")

        confirm = input("\nConfirmar? (s/n): ").strip().lower()
        if confirm == 's':
            result = bot.create_booking_for_slot(slot, member.member_id)
            print(f"\n✓ Agendamento criado!")
            print(f"  Voucher: {result.get('voucherCode', 'N/A')}")
            print(f"  Access Code: {result.get('accessCode', 'N/A')}")

    elif action == "book-test":
        # Manual booking test
        members = bot.get_members()
        member = select_member_interactive_simple(members, bot)
        if not member:
            return None

        levels = sport_config.get_options("level")
        print("\nNiveis disponiveis:")
        for i, lvl in enumerate(levels, 1):
            print(f"  {i}. {lvl}")
        choice = input("Selecione o nivel (numero): ").strip()
        try:
            level = levels[int(choice) - 1]
        except:
            print("Invalido!")
            return None

        wave_sides = sport_config.get_options("wave_side")
        print("\nLados disponiveis:")
        for i, ws in enumerate(wave_sides, 1):
            print(f"  {i}. {ws}")
        choice = input("Selecione o lado (numero): ").strip()
        try:
            wave_side = wave_sides[int(choice) - 1]
        except:
            print("Invalido!")
            return None

        tags = list(sport_config.base_tags) + [level, wave_side]
        dates_response = bot.api.get_available_dates(tags, sport=sport)
        if isinstance(dates_response, dict) and "value" in dates_response:
            dates_list = dates_response["value"]
        else:
            dates_list = dates_response

        dates = [d.split("T")[0] if "T" in str(d) else d for d in dates_list]
        print(f"\nDatas disponiveis: {', '.join(dates)}")
        date = input("Digite a data (YYYY-MM-DD): ").strip()

        intervals_data = bot.api.get_intervals(date, tags, member.member_id, sport)
        if isinstance(intervals_data, list) and intervals_data:
            pkg = intervals_data[0]
            package_id = pkg.get("packageId")
            products = pkg.get("products", [])
            if products:
                product_id = products[0].get("productId", package_id)
                invitation = products[0].get("invitation", {})
                solos = invitation.get("solos", [])
                available_intervals = [s.get("interval") for s in solos if s.get("isAvailable")]
                print(f"Horarios disponiveis: {', '.join(available_intervals)}")

        interval = input("Digite o horario (HH:MM): ").strip()

        print(f"\nConfirmando agendamento:")
        print(f"  Membro: {member.social_name} ({member.member_id})")
        print(f"  Data: {date} {interval}")
        print(f"  Onda: {level} / {wave_side}")

        confirm = input("\nConfirmar? (s/n): ").strip().lower()
        if confirm == 's':
            result = bot.api.create_booking(
                package_id=package_id,
                product_id=product_id,
                member_id=member.member_id,
                tags=tags,
                interval=interval,
                date=date,
                sport=sport
            )
            print(f"\n✓ Agendamento criado!")
            print(f"  Voucher: {result.get('voucherCode', 'N/A')}")
            print(f"  Access Code: {result.get('accessCode', 'N/A')}")

    elif action == "book-any-member":
        # Book with any member from title
        levels = sport_config.get_options("level")
        wave_sides = sport_config.get_options("wave_side")
        level = levels[0]
        wave_side = wave_sides[0]
        tags = list(sport_config.base_tags) + [level, wave_side]

        dates_response = bot.api.get_available_dates(tags, sport=sport)
        if isinstance(dates_response, dict) and "value" in dates_response:
            dates_list = dates_response["value"]
        else:
            dates_list = dates_response

        if not dates_list:
            print("Nenhuma data disponivel!")
            return None

        date_str = dates_list[0]
        if isinstance(date_str, str) and "T" in date_str:
            date_str = date_str.split("T")[0]

        standard_members = bot.get_members()
        intervals_data = bot.api.get_intervals(date_str, tags, standard_members[0].member_id, sport)

        all_members_from_api = []
        if isinstance(intervals_data, list) and intervals_data:
            pkg = intervals_data[0]
            for m in pkg.get("members", []):
                all_members_from_api.append({
                    "member_id": m.get("memberId"),
                    "name": m.get("name", ""),
                    "is_titular": m.get("isTitular", False)
                })

        print(f"\n=== Todos os Membros do Titulo ===\n")
        try:
            bookings = bot.api.list_bookings(sport)
            member_bookings = get_member_booking_status([], bookings)
        except:
            member_bookings = {}

        for i, m in enumerate(all_members_from_api, 1):
            titular = " (Titular)" if m["is_titular"] else ""
            booking = member_bookings.get(m["member_id"])
            status = f"Agendado ({booking['date']} {booking['interval']})" if booking else "Disponivel"
            print(f"  {i}. [{m['member_id']}] {m['name']}{titular} - {status}")

        choice = input("\nSelecione o membro (numero): ").strip()
        try:
            selected_member = all_members_from_api[int(choice) - 1]
        except:
            print("Invalido!")
            return None

        if bot.is_availability_cache_valid():
            slots = bot.get_slots_from_cache()
        else:
            print("Escaneando disponibilidade...")
            slots = bot.scan_availability()

        display_available_slots(slots)
        slot = select_slot_interactive(slots)
        if not slot:
            return None

        print(f"\nConfirmando agendamento:")
        print(f"  Membro: {selected_member['name']} ({selected_member['member_id']})")
        print(f"  Data: {slot.date} {slot.interval}")
        print(f"  Onda: {slot.level} / {slot.wave_side}")

        confirm = input("\nConfirmar? (s/n): ").strip().lower()
        if confirm == 's':
            result = bot.create_booking_for_slot(slot, selected_member["member_id"])
            print(f"\n✓ Agendamento criado!")
            print(f"  Voucher: {result.get('voucherCode', 'N/A')}")
            print(f"  Access Code: {result.get('accessCode', 'N/A')}")

    elif action == "explore-packages":
        levels = sport_config.get_options("level")
        wave_sides = sport_config.get_options("wave_side")
        members = bot.get_members()
        member_id = members[0].member_id

        print("\n=== Explorando Packages da API ===\n")
        all_packages = {}

        for level in levels:
            for wave_side in wave_sides:
                combo_key = f"{level}/{wave_side}"
                tags = list(sport_config.base_tags) + [level, wave_side]

                dates_response = bot.api.get_available_dates(tags, sport=sport)
                if isinstance(dates_response, dict) and "value" in dates_response:
                    dates_list = dates_response["value"]
                else:
                    dates_list = dates_response

                if not dates_list:
                    continue

                date_str = dates_list[0]
                if isinstance(date_str, str) and "T" in date_str:
                    date_str = date_str.split("T")[0]

                intervals_data = bot.api.get_intervals(date_str, tags, member_id, sport)

                print(f"\n--- {combo_key} ({date_str}) ---")
                if isinstance(intervals_data, list):
                    for pkg in intervals_data:
                        pkg_id = pkg.get("packageId")
                        pkg_name = pkg.get("name", "N/A")
                        products = pkg.get("products", [])

                        print(f"  Package {pkg_id}: {pkg_name}")
                        for prod in products:
                            prod_id = prod.get("productId")
                            prod_name = prod.get("name", "N/A")
                            invitation = prod.get("invitation", {})
                            solos = invitation.get("solos", [])
                            print(f"    Product {prod_id}: {prod_name}")
                            print(f"      Solos: {len(solos)} intervalos")

                            for key in pkg.keys():
                                if key not in ["packageId", "name", "products"]:
                                    print(f"      Extra: {key} = {pkg.get(key)}")

                        all_packages[combo_key] = {"packageId": pkg_id, "packageName": pkg_name}

        print("\n\n=== Resumo de Packages ===")
        for combo, data in all_packages.items():
            print(f"  {combo}: package={data['packageId']} ({data['packageName']})")

    elif action == "debug-token":
        token = bot.firebase_auth.get_valid_token()
        print(f"\n=== Token de Autenticacao ===")
        print(f"Bearer {token[:50]}...{token[-20:]}")

    elif action == "auto-monitor":
        # Interactive auto-monitor setup
        config = setup_auto_monitor_interactive(bot)
        if config:
            print("\n" + "=" * 50)
            print("   MONITORAMENTO INICIADO")
            print("=" * 50)
            print("\nPressione Ctrl+C para interromper.\n")

            def print_status(msg: str, level: str = "info"):
                prefix = ""
                if level == "error":
                    prefix = "ERRO: "
                elif level == "warning":
                    prefix = "AVISO: "
                print(f"{prefix}{msg}")

            try:
                results = bot.run_auto_monitor(
                    member_ids=config["member_ids"],
                    target_dates=config["target_dates"],
                    duration_minutes=config["duration_minutes"],
                    check_interval_seconds=config["check_interval_seconds"],
                    on_status_update=print_status
                )

                # Show final summary
                print("\n" + "=" * 50)
                print("   RESULTADO FINAL")
                print("=" * 50)

                successes = [r for r in results.values() if r.get("success")]
                failures = [r for r in results.values() if not r.get("success")]

                if successes:
                    print(f"\nAgendamentos realizados ({len(successes)}):")
                    for r in successes:
                        print(f"  - {r.get('member_name')}: {r['slot']['date']} {r['slot']['interval']}")
                        print(f"    Voucher: {r['voucher']} | Access: {r['access_code']}")

                if failures:
                    print(f"\nFalhas ({len(failures)}):")
                    for member_id, r in results.items():
                        if not r.get("success"):
                            member = bot.get_member_by_id(member_id)
                            name = member.social_name if member else str(member_id)
                            print(f"  - {name}: {r.get('error', 'Nao agendado')}")

            except KeyboardInterrupt:
                print("\n\nMonitoramento interrompido pelo usuario.")

    return None


def main():
    parser = argparse.ArgumentParser(
        description="BeyondTheClub Sport Session Booking Bot"
    )
    parser.add_argument(
        "--sport",
        type=str,
        default="surf",
        choices=list(SPORT_CONFIGS.keys()),
        help="Sport to monitor (default: surf)"
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run once instead of continuously"
    )
    parser.add_argument(
        "--no-auto-book",
        action="store_true",
        help="Don't automatically book sessions, just report availability"
    )
    parser.add_argument(
        "--sms-code",
        type=str,
        help="SMS verification code (skip interactive prompt)"
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Don't use cached tokens, force re-authentication"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    parser.add_argument(
        "--check-status",
        action="store_true",
        help="Just check schedule status and exit"
    )
    parser.add_argument(
        "--inscriptions",
        action="store_true",
        help="Show user's inscriptions and exit"
    )
    parser.add_argument(
        "--list-members",
        action="store_true",
        help="List available members and exit"
    )
    parser.add_argument(
        "--refresh-members",
        action="store_true",
        help="Force refresh members list from API"
    )
    parser.add_argument(
        "--configure",
        action="store_true",
        help="Configure session preferences for a member"
    )
    parser.add_argument(
        "--member",
        type=str,
        help="Member(s) to monitor (ID, name, or comma-separated list)"
    )
    parser.add_argument(
        "--scan-availability",
        action="store_true",
        help="Scan all level/wave_side combinations and cache available slots"
    )
    parser.add_argument(
        "--list-bookings",
        action="store_true",
        help="List all active bookings for the title"
    )
    parser.add_argument(
        "--cancel",
        action="store_true",
        help="Cancel a booking (interactive selection)"
    )
    parser.add_argument(
        "--swap",
        action="store_true",
        help="Swap member in a booking (cancel + recreate)"
    )
    parser.add_argument(
        "--book",
        action="store_true",
        help="Interactive booking: select slot then member"
    )
    parser.add_argument(
        "--book-test",
        action="store_true",
        help="Manual booking test with full attribute selection"
    )
    parser.add_argument(
        "--debug-token",
        action="store_true",
        help="Print current auth token and example curl command"
    )
    parser.add_argument(
        "--explore-packages",
        action="store_true",
        help="Explore all packages from API intervals response"
    )
    parser.add_argument(
        "--book-any-member",
        action="store_true",
        help="Book using ALL members from intervals API (including non-active)"
    )
    parser.add_argument(
        "--menu",
        action="store_true",
        help="Show interactive menu with all available commands"
    )
    parser.add_argument(
        "--auto-monitor",
        action="store_true",
        help="Run automatic monitoring and booking bot (interactive setup)"
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=120,
        help="Duration in minutes for auto-monitor (default: 120)"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=30,
        help="Check interval in seconds for auto-monitor (default: 30)"
    )
    parser.add_argument(
        "--dates",
        type=str,
        help="Specific dates for auto-monitor (comma-separated, e.g. 2025-12-26,2025-12-27)"
    )

    args = parser.parse_args()

    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    sport_name = SPORT_CONFIGS.get(args.sport, {}).get("name", args.sport.title())
    logger.info("=" * 60)
    logger.info(f"BeyondTheClub {sport_name} Session Booking Bot")
    logger.info("=" * 60)

    try:
        config = load_config()

        if args.no_auto_book:
            config.bot.auto_book = False

        bot = BeyondBot(config)
        bot.set_sport(args.sport)

        # Initialize (authenticate)
        logger.info("Initializing bot...")
        bot.initialize(
            sms_code=args.sms_code,
            use_cached=not args.no_cache
        )

        if args.check_status:
            # Just check status and exit
            status = bot.api.get_schedule_status(args.sport)
            logger.info(f"{sport_name} schedule status: {status}")
            return 0

        if args.inscriptions:
            # Show inscriptions and exit
            inscriptions = bot.api.get_inscriptions(args.sport)
            display_inscriptions(inscriptions)
            return 0

        if args.list_members:
            # List members and exit
            members = bot.get_members(force_refresh=args.refresh_members)
            if not members:
                logger.info("Cache vazio, buscando membros da API...")
                members = bot.get_members(force_refresh=True)
            display_members(members, bot)
            return 0

        if args.configure:
            # Configure member preferences
            members = bot.get_members(force_refresh=args.refresh_members)
            if not members:
                members = bot.get_members(force_refresh=True)
            display_members(members, bot)
            choice = input("\nSelecione o membro para configurar (número): ").strip()
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(members):
                    configure_member_preferences(bot, members[idx])
                else:
                    print("Índice inválido!")
                    return 1
            except ValueError:
                print("Entrada inválida!")
                return 1
            return 0

        # Handle --auto-monitor
        if args.auto_monitor:
            # Parse target dates if provided
            target_dates = None
            if args.dates:
                target_dates = [d.strip() for d in args.dates.split(",") if d.strip()]

            # Interactive setup for member selection
            config = setup_auto_monitor_interactive(bot)
            if not config:
                return 1

            # Override duration/interval from CLI args if provided
            duration_minutes = args.duration if args.duration != 120 else config["duration_minutes"]
            check_interval = args.interval if args.interval != 30 else config["check_interval_seconds"]
            if target_dates:
                config["target_dates"] = target_dates

            print("\n" + "=" * 50)
            print("   MONITORAMENTO INICIADO")
            print("=" * 50)
            print("\nPressione Ctrl+C para interromper.\n")

            def print_status(msg: str, level: str = "info"):
                prefix = ""
                if level == "error":
                    prefix = "ERRO: "
                elif level == "warning":
                    prefix = "AVISO: "
                print(f"{prefix}{msg}")

            try:
                results = bot.run_auto_monitor(
                    member_ids=config["member_ids"],
                    target_dates=config["target_dates"],
                    duration_minutes=duration_minutes,
                    check_interval_seconds=check_interval,
                    on_status_update=print_status
                )

                # Show final summary
                print("\n" + "=" * 50)
                print("   RESULTADO FINAL")
                print("=" * 50)

                successes = [r for r in results.values() if r.get("success")]
                failures = [r for r in results.values() if not r.get("success")]

                if successes:
                    print(f"\nAgendamentos realizados ({len(successes)}):")
                    for r in successes:
                        print(f"  - {r.get('member_name')}: {r['slot']['date']} {r['slot']['interval']}")
                        print(f"    Voucher: {r['voucher']} | Access: {r['access_code']}")

                if failures:
                    print(f"\nFalhas ({len(failures)}):")
                    for member_id, r in results.items():
                        if not r.get("success"):
                            member = bot.get_member_by_id(member_id)
                            name = member.social_name if member else str(member_id)
                            print(f"  - {name}: {r.get('error', 'Nao agendado')}")

            except KeyboardInterrupt:
                print("\n\nMonitoramento interrompido pelo usuario.")

            return 0

        # Handle --menu: interactive menu loop
        if args.menu:
            while True:
                action = show_menu(args.sport)
                if action is None:
                    continue
                if action == "exit":
                    print("\nAte logo!")
                    return 0

                try:
                    execute_menu_action(action, args, bot)
                except Exception as e:
                    print(f"\nErro: {e}")
                    import traceback
                    traceback.print_exc()

                input("\nPressione Enter para voltar ao menu...")

        if args.debug_token:
            # Print token and example curl
            token = bot.firebase_auth.get_valid_token()
            print(f"\n=== Token de Autenticação ===")
            print(f"Bearer {token[:50]}...{token[-20:]}")
            print(f"\n=== Curl para teste de booking ===")
            print(f'''curl -X POST "https://api.beyondtheclub.tech/beyond/api/v1/schedules/surf" \\
  -H "accept: application/json" \\
  -H "accept-encoding: gzip" \\
  -H "authorization: Bearer {token}" \\
  -H "connection: Keep-Alive" \\
  -H "host: api.beyondtheclub.tech" \\
  -H "user-agent: okhttp/4.12.0" \\
  -H "content-type: application/json" \\
  -d '{{
    "packageId": 16,
    "productId": 16,
    "memberId": 12869,
    "tags": ["Surf", "Agendamento", "Intermediario2", "Lado_direito"],
    "invitation": {{
      "interval": "08:00",
      "date": "2025-12-28"
    }}
  }}'
''')
            return 0

        if args.explore_packages:
            # Explore all packages from intervals API
            import json
            sport_config = bot.get_sport_config()
            members = bot.get_members()
            member_id = members[0].member_id

            levels = sport_config.get_options("level")
            wave_sides = sport_config.get_options("wave_side")

            print("\n=== Explorando Packages da API ===\n")

            all_packages = {}

            for level in levels:
                for wave_side in wave_sides:
                    combo_key = f"{level}/{wave_side}"
                    tags = list(sport_config.base_tags) + [level, wave_side]

                    # Get available dates
                    dates_response = bot.api.get_available_dates(tags, sport=args.sport)
                    if isinstance(dates_response, dict) and "value" in dates_response:
                        dates_list = dates_response["value"]
                    else:
                        dates_list = dates_response

                    if not dates_list:
                        continue

                    # Get first date
                    date_str = dates_list[0]
                    if isinstance(date_str, str) and "T" in date_str:
                        date_str = date_str.split("T")[0]

                    # Get raw intervals
                    intervals_data = bot.api.get_intervals(
                        date=date_str,
                        tags=tags,
                        member_id=member_id,
                        sport=args.sport
                    )

                    print(f"\n--- {combo_key} ({date_str}) ---")
                    if isinstance(intervals_data, list):
                        for pkg in intervals_data:
                            pkg_id = pkg.get("packageId")
                            pkg_name = pkg.get("name", "N/A")
                            products = pkg.get("products", [])

                            print(f"  Package {pkg_id}: {pkg_name}")

                            for prod in products:
                                prod_id = prod.get("productId")
                                prod_name = prod.get("name", "N/A")
                                invitation = prod.get("invitation", {})
                                solos = invitation.get("solos", [])

                                print(f"    Product {prod_id}: {prod_name}")
                                print(f"      Solos: {len(solos)} intervalos")

                                # Check for any special fields
                                for key in pkg.keys():
                                    if key not in ["packageId", "name", "products"]:
                                        print(f"      Extra field: {key} = {pkg.get(key)}")

                            all_packages[combo_key] = {
                                "packageId": pkg_id,
                                "packageName": pkg_name,
                                "raw": pkg
                            }

            print("\n\n=== Resumo de Packages ===")
            for combo, data in all_packages.items():
                print(f"  {combo}: package={data['packageId']} ({data['packageName']})")

            return 0

        if args.book_any_member:
            # Book using ALL members from intervals API (including non-active like Pelagio)
            import json
            sport_config = bot.get_sport_config()

            # First, get members from intervals API
            levels = sport_config.get_options("level")
            wave_sides = sport_config.get_options("wave_side")

            # Pick first combo to get members list
            level = levels[0]
            wave_side = wave_sides[0]
            tags = list(sport_config.base_tags) + [level, wave_side]

            # Get available dates
            dates_response = bot.api.get_available_dates(tags, sport=args.sport)
            if isinstance(dates_response, dict) and "value" in dates_response:
                dates_list = dates_response["value"]
            else:
                dates_list = dates_response

            if not dates_list:
                print("Nenhuma data disponível!")
                return 1

            date_str = dates_list[0]
            if isinstance(date_str, str) and "T" in date_str:
                date_str = date_str.split("T")[0]

            # Use any member to get intervals (just to fetch the full response)
            standard_members = bot.get_members()
            any_member_id = standard_members[0].member_id

            intervals_data = bot.api.get_intervals(
                date=date_str,
                tags=tags,
                member_id=any_member_id,
                sport=args.sport
            )

            # Extract ALL members from intervals response
            all_members_from_api = []
            if isinstance(intervals_data, list) and intervals_data:
                pkg = intervals_data[0]
                members_list = pkg.get("members", [])
                for m in members_list:
                    all_members_from_api.append({
                        "member_id": m.get("memberId"),
                        "name": m.get("name", ""),
                        "is_titular": m.get("isTitular", False)
                    })

            print(f"\n=== Todos os Membros do Título (da API intervals) ===\n")
            print(f"Membros encontrados: {len(all_members_from_api)}")

            # Get current bookings to show status
            try:
                bookings = bot.api.list_bookings(args.sport)
                member_bookings = get_member_booking_status([], bookings)  # empty members list is fine
            except:
                member_bookings = {}

            for i, m in enumerate(all_members_from_api, 1):
                titular = " (Titular)" if m["is_titular"] else ""
                booking = member_bookings.get(m["member_id"])
                if booking:
                    status = f"Agendado ({booking['date']} {booking['interval']})"
                else:
                    status = "Disponivel"
                print(f"  {i}. [{m['member_id']}] {m['name']}{titular} - {status}")

            # Select member
            choice = input("\nSelecione o membro (número): ").strip()
            try:
                idx = int(choice) - 1
                if not (0 <= idx < len(all_members_from_api)):
                    print("Índice inválido!")
                    return 1
                selected_member = all_members_from_api[idx]
            except ValueError:
                print("Entrada inválida!")
                return 1

            print(f"\nMembro selecionado: {selected_member['name']} ({selected_member['member_id']})")

            # Now get available slots
            if bot.is_availability_cache_valid():
                cache = bot.get_availability_cache()
                print(f"\nCache de disponibilidade válido (atualizado em {cache.get('scanned_at', 'N/A')[:19]})")
                refresh = input("Atualizar antes de continuar? (s/n): ").strip().lower()
                if refresh == 's':
                    print("Escaneando disponibilidade...")
                    slots = bot.scan_availability()
                else:
                    slots = bot.get_slots_from_cache()
            else:
                print("\nEscaneando disponibilidade...")
                slots = bot.scan_availability()

            if not slots:
                print("Nenhum horário disponível!")
                return 1

            display_available_slots(slots)

            # Select slot
            slot = select_slot_interactive(slots)
            if not slot:
                return 1

            print(f"\nConfirmando agendamento:")
            print(f"  Membro: {selected_member['name']} ({selected_member['member_id']})")
            print(f"  Data: {slot.date} {slot.interval}")
            print(f"  Onda: {slot.level} / {slot.wave_side}")
            print(f"  Package: {slot.package_id}")

            confirm = input("\nConfirmar? (s/n): ").strip().lower()
            if confirm != 's':
                print("Agendamento cancelado.")
                return 0

            # Create booking
            try:
                result = bot.create_booking_for_slot(slot, selected_member["member_id"])
                print(f"\n✓ Agendamento criado!")
                print(f"  Voucher: {result.get('voucherCode', 'N/A')}")
                print(f"  Access Code: {result.get('accessCode', 'N/A')}")
            except Exception as e:
                print(f"\n✗ Erro ao criar agendamento: {e}")
                return 1

            return 0

        if args.scan_availability:
            # Scan all level/wave_side combinations
            print("Escaneando disponibilidade...")
            slots = bot.scan_availability()
            display_available_slots(slots)

            cache = bot.get_availability_cache()
            print(f"\nSalvo em .beyondtheclub_availability.json")
            print(f"Escaneado em: {cache.get('scanned_at', 'N/A')}")
            return 0

        if args.list_bookings:
            # List all active bookings
            bookings = bot.api.list_bookings(args.sport)
            display_bookings(bookings)
            return 0

        if args.cancel:
            # Cancel a booking (interactive) - only show AccessReady bookings
            bookings = bot.api.list_bookings(args.sport)
            booking = select_booking_for_action_interactive(bookings)
            if not booking:
                return 1

            voucher = booking.get("voucherCode")
            member_name = booking.get("member", {}).get("socialName", "N/A")
            invitation = booking.get("invitation", {})
            date_raw = invitation.get("date", "N/A")
            date = date_raw.split("T")[0] if "T" in str(date_raw) else date_raw
            begin = invitation.get("begin", "N/A")
            interval = begin[:5] if len(str(begin)) >= 5 else begin

            print(f"\nCancelando agendamento {voucher} ({member_name} - {date} {interval})...")
            confirm = input("Confirmar? (s/n): ").strip().lower()
            if confirm != 's':
                print("Cancelamento abortado.")
                return 0

            bot.api.cancel_booking(voucher, sport=args.sport)
            print(f"\n Agendamento cancelado: {voucher}")
            return 0

        if args.swap:
            # Swap member in a booking - only show AccessReady bookings
            bookings = bot.api.list_bookings(args.sport)
            booking = select_booking_for_action_interactive(bookings)
            if not booking:
                return 1

            voucher = booking.get("voucherCode")
            old_member_name = booking.get("member", {}).get("socialName", "N/A")
            invitation = booking.get("invitation", {})
            date_raw = invitation.get("date", "N/A")
            date = date_raw.split("T")[0] if "T" in str(date_raw) else date_raw
            begin = invitation.get("begin", "N/A")
            interval = begin[:5] if len(str(begin)) >= 5 else begin

            # Extract level/wave_side from tags
            tags = booking.get("tags", [])
            level = ""
            wave_side = ""
            for tag in tags:
                if "Iniciante" in tag or "Intermediario" in tag or "Avançado" in tag or "Avancado" in tag:
                    level = tag
                elif "Lado_" in tag:
                    wave_side = tag

            # Get package info from cache
            cache = bot.get_availability_cache()
            combo_key = f"{level}/{wave_side}"
            pkg = cache.get("packages", {}).get(combo_key, {})
            package_id = pkg.get("packageId", 0)
            product_id = pkg.get("productId", 0)

            if not package_id:
                print(f"\nPackageId não encontrado para {combo_key}.")
                print("Execute --scan-availability primeiro para popular o cache.")
                return 1

            # Create slot from booking info
            slot = AvailableSlot(
                date=date,
                interval=interval,
                level=level,
                wave_side=wave_side,
                available=1,
                max_quantity=20,
                package_id=package_id,
                product_id=product_id
            )

            # Select new member
            members = bot.get_members(force_refresh=args.refresh_members)
            new_member = select_member_interactive_simple(members, bot)
            if not new_member:
                return 1

            print(f"\nSubstituindo {old_member_name} por {new_member.social_name} no agendamento {date} {interval}...")
            confirm = input("Confirmar? (s/n): ").strip().lower()
            if confirm != 's':
                print("Operação abortada.")
                return 0

            result = bot.swap_booking(voucher, new_member.member_id, slot)

            new_voucher = result.get("voucherCode", "N/A")
            access_code = result.get("invitation", {}).get("accessCode", "N/A")

            print(f"\n Agendamento cancelado: {voucher}")
            print(f" Novo agendamento criado: {new_voucher}")
            print(f"  {new_member.social_name} - {date} {interval} ({combo_key}) - Access: {access_code}")
            return 0

        if args.book:
            # Interactive booking: select slot then member
            # Check cache validity
            cache_valid = bot.is_availability_cache_valid()
            cache = bot.get_availability_cache()

            if cache_valid and cache.get("dates"):
                scanned_at = cache.get("scanned_at", "N/A")
                dates = list(cache.get("dates", {}).keys())
                print(f"\nCache de disponibilidade encontrado (atualizado em {scanned_at}).")
                print(f"Datas disponíveis: {', '.join(sorted(dates))}")

                refresh = input("\nAtualizar disponibilidade antes de continuar? (s/n): ").strip().lower()
                if refresh == 's':
                    print("\nEscaneando disponibilidade...")
                    slots = bot.scan_availability()
                else:
                    print("\nUsando cache existente...")
                    slots = bot.get_slots_from_cache()
            else:
                if cache.get("dates"):
                    print("\nCache de disponibilidade contém datas expiradas.")
                else:
                    print("\nCache de disponibilidade não encontrado.")
                print("Escaneando disponibilidade...")
                slots = bot.scan_availability()

            # Select slot
            slot = select_slot_interactive(slots)
            if not slot:
                return 1

            # Select member
            members = bot.get_members(force_refresh=args.refresh_members)
            member = select_member_interactive_simple(members, bot)
            if not member:
                return 1

            print(f"\nConfirmando agendamento:")
            print(f"  Membro: {member.social_name} ({member.member_id})")
            print(f"  Data: {slot.date} {slot.interval}")
            print(f"  Onda: {slot.level} / {slot.wave_side}")

            confirm = input("\nConfirmar? (s/n): ").strip().lower()
            if confirm != 's':
                print("Agendamento cancelado.")
                return 0

            result = bot.create_booking_for_slot(slot, member.member_id)

            voucher = result.get("voucherCode", "N/A")
            access_code = result.get("invitation", {}).get("accessCode", "N/A")

            print(f"\n Agendamento criado!")
            print(f"  Voucher: {voucher}")
            print(f"  Access Code: {access_code}")
            return 0

        if args.book_test:
            # Manual booking test with full attribute selection
            members = bot.get_members(force_refresh=args.refresh_members)
            member = select_member_interactive_simple(members, bot)
            if not member:
                return 1

            sport_config = bot.get_sport_config()

            # Select level
            levels = sport_config.get_options("level")
            print("\nNíveis disponíveis:")
            for i, lv in enumerate(levels, 1):
                print(f"  {i}. {lv}")
            choice = input("Selecione o nível (número): ").strip()
            try:
                level = levels[int(choice) - 1]
            except (ValueError, IndexError):
                print("Opção inválida!")
                return 1

            # Select wave_side
            wave_sides = sport_config.get_options("wave_side")
            print("\nLados disponíveis:")
            for i, ws in enumerate(wave_sides, 1):
                print(f"  {i}. {ws}")
            choice = input("Selecione o lado (número): ").strip()
            try:
                wave_side = wave_sides[int(choice) - 1]
            except (ValueError, IndexError):
                print("Opção inválida!")
                return 1

            tags = list(sport_config.base_tags) + [level, wave_side]

            # Get available dates
            print(f"\nBuscando datas para {level}/{wave_side}...")
            dates_response = bot.api.get_available_dates(tags, sport=args.sport)

            # Handle API response wrapper
            if isinstance(dates_response, dict) and "value" in dates_response:
                dates_list = dates_response["value"]
            else:
                dates_list = dates_response

            dates = [d.split("T")[0] for d in dates_list if isinstance(d, str)]
            if not dates:
                print("Nenhuma data disponível!")
                return 1

            print("\nDatas disponíveis:")
            for i, d in enumerate(dates, 1):
                print(f"  {i}. {d}")
            choice = input("Selecione a data (número): ").strip()
            try:
                date = dates[int(choice) - 1]
            except (ValueError, IndexError):
                print("Opção inválida!")
                return 1

            # Get intervals
            print(f"\nBuscando horários para {date}...")
            intervals_data = bot.api.get_intervals(
                date=date,
                tags=tags,
                member_id=member.member_id,
                sport=args.sport
            )

            # Parse the packages from response
            # Structure: value[] -> each has packageId and products[]
            packages_list = intervals_data if isinstance(intervals_data, list) else []
            available_intervals = []

            for package in packages_list:
                package_id = package.get("packageId")
                products = package.get("products", [])

                for product in products:
                    product_id = product.get("productId", package_id)
                    invitation = product.get("invitation", {})
                    solos = invitation.get("solos", [])

                    for solo in solos:
                        if solo.get("isAvailable", False):
                            available_intervals.append({
                                "interval": solo.get("interval"),
                                "available": solo.get("availableQuantity", 0),
                                "max": solo.get("maxQuantity", 0),
                                "packageId": package_id,
                                "productId": product_id
                            })

            if not available_intervals:
                print("Nenhum horário disponível!")
                return 1

            print("\nHorários disponíveis:")
            for i, iv in enumerate(available_intervals, 1):
                print(f"  {i}. {iv['interval']} ({iv['available']}/{iv['max']} vagas)")
            choice = input("Selecione o horário (número): ").strip()
            try:
                selected = available_intervals[int(choice) - 1]
            except (ValueError, IndexError):
                print("Opção inválida!")
                return 1

            print(f"\nConfirmando agendamento:")
            print(f"  Membro: {member.social_name} ({member.member_id})")
            print(f"  Data: {date} {selected['interval']}")
            print(f"  Onda: {level} / {wave_side}")

            confirm = input("\nConfirmar? (s/n): ").strip().lower()
            if confirm != 's':
                print("Agendamento cancelado.")
                return 0

            result = bot.api.create_booking(
                package_id=selected["packageId"],
                product_id=selected["productId"],
                member_id=member.member_id,
                tags=tags,
                interval=selected["interval"],
                date=date,
                sport=args.sport
            )

            voucher = result.get("voucherCode", "N/A")
            access_code = result.get("invitation", {}).get("accessCode", "N/A")

            print(f"\n Agendamento criado!")
            print(f"  Voucher: {voucher}")
            print(f"  Access Code: {access_code}")
            return 0

        # Determine which members to monitor
        members = bot.get_members(force_refresh=args.refresh_members)
        if not members:
            logger.info("Cache vazio, buscando membros da API...")
            members = bot.get_members(force_refresh=True)
        selected_members = []

        if args.member:
            # Parse --member argument
            selected_members = parse_member_argument(bot, args.member, members)
            if not selected_members:
                logger.error("Nenhum membro válido selecionado!")
                return 1
        else:
            # Interactive selection
            selected_members = select_members_interactive(bot, members)
            if not selected_members:
                logger.error("Nenhum membro selecionado!")
                return 1

        # Ensure all selected members have preferences
        for member in selected_members:
            if not ensure_member_preferences(bot, member):
                logger.error(f"Falha ao configurar preferências para {member.social_name}")
                return 1

        # Store selected members for monitoring
        bot._selected_members = [m.member_id for m in selected_members]
        logger.info(f"Monitorando para: {', '.join(m.social_name for m in selected_members)}")

        if args.once:
            # Run once
            booked = bot.run_once()
            logger.info(f"Check complete. Booked {booked} session(s).")
        else:
            # Run continuously
            bot.run()

        bot.close()
        return 0

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        return 0
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
