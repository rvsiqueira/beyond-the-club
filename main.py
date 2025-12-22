#!/usr/bin/env python3
"""
BeyondTheClub Surf Session Booking Bot

Monitors surf session availability and automatically books sessions
based on configured preferences.
"""

import argparse
import logging
import sys
from datetime import datetime

from src.bot import BeyondBot, Member, MemberPreferences, SessionPreference
from src.config import load_config

# Available levels and wave sides
LEVELS = [
    "Iniciante1",
    "Iniciante2",
    "Intermediario1",
    "Intermediario2",
    "Avançado1",
    "Avançado2",
]
WAVE_SIDES = ["Lado_esquerdo", "Lado_direito"]


def display_members(members: list, bot: BeyondBot):
    """Display list of members with their preferences status."""
    print("\nMembros disponíveis:")
    for i, m in enumerate(members, 1):
        titular = " (Titular)" if m.is_titular else ""
        has_prefs = "✓" if bot.has_member_preferences(m.member_id) else "✗"
        print(f"  {i}. [{m.member_id}] {m.social_name}{titular} - Uso: {m.usage}/{m.limit} - Prefs: {has_prefs}")


def display_member_preferences(bot: BeyondBot, member: Member):
    """Display current preferences for a member."""
    prefs = bot.get_member_preferences(member.member_id)
    if prefs and prefs.sessions:
        print(f"\n{member.social_name} possui preferências configuradas:")
        for i, s in enumerate(prefs.sessions, 1):
            print(f"  {i}. {s.level} / {s.wave_side}")
        if prefs.target_hours:
            print(f"  Horários: {', '.join(prefs.target_hours)}")
        if prefs.target_dates:
            print(f"  Datas: {', '.join(prefs.target_dates)}")
        return True
    return False


def configure_member_preferences(bot: BeyondBot, member: Member):
    """Interactive configuration of member preferences."""
    # Check if already has preferences
    if display_member_preferences(bot, member):
        keep = input("\nDeseja manter estas preferências? (s/n): ").strip().lower()
        if keep == 's':
            print("Preferências mantidas.")
            return
        print("Apagando preferências anteriores...")
        bot.clear_member_preferences(member.member_id)

    print(f"\nConfigurando preferências para {member.social_name}...")

    sessions = []
    while True:
        print("\nAdicionar sessão de interesse:")
        print("  Níveis disponíveis:")
        for i, level in enumerate(LEVELS, 1):
            print(f"    {i}. {level}")
        level_choice = input("  Nível (número): ").strip()
        try:
            level = LEVELS[int(level_choice) - 1]
        except (ValueError, IndexError):
            print("  Opção inválida!")
            continue

        print("  Lados disponíveis:")
        for i, side in enumerate(WAVE_SIDES, 1):
            print(f"    {i}. {side}")
        side_choice = input("  Lado (número): ").strip()
        try:
            wave_side = WAVE_SIDES[int(side_choice) - 1]
        except (ValueError, IndexError):
            print("  Opção inválida!")
            continue

        sessions.append(SessionPreference(level=level, wave_side=wave_side))
        print(f"  Adicionado: {level} / {wave_side}")

        another = input("\nAdicionar outra? (s/n): ").strip().lower()
        if another != 's':
            break

    # Target hours
    hours_input = input("\nHorários preferidos (ex: 08:00,09:00 ou Enter para todos): ").strip()
    target_hours = [h.strip() for h in hours_input.split(",")] if hours_input else []

    # Target dates
    dates_input = input("Datas específicas (ex: 2025-01-15,2025-01-16 ou Enter para todas): ").strip()
    target_dates = [d.strip() for d in dates_input.split(",")] if dates_input else []

    # Save preferences
    prefs = MemberPreferences(
        sessions=sessions,
        target_hours=target_hours,
        target_dates=target_dates
    )
    bot.set_member_preferences(member.member_id, prefs)

    print(f"\nPreferências salvas para {member.social_name}:")
    for i, s in enumerate(sessions, 1):
        print(f"  {i}. {s.level} / {s.wave_side} (prioridade {i})")
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
    if bot.has_member_preferences(member.member_id):
        if display_member_preferences(bot, member):
            keep = input("\nManter preferências? (s/n): ").strip().lower()
            if keep == 's':
                return True
            bot.clear_member_preferences(member.member_id)

    print(f"\n{member.social_name} não possui preferências configuradas.")
    configure_member_preferences(bot, member)
    return bot.has_member_preferences(member.member_id)


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


def main():
    parser = argparse.ArgumentParser(
        description="BeyondTheClub Surf Session Booking Bot"
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
        help="Just check surf schedule status and exit"
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

    args = parser.parse_args()

    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    logger.info("=" * 60)
    logger.info("BeyondTheClub Surf Session Booking Bot")
    logger.info("=" * 60)

    try:
        config = load_config()

        if args.no_auto_book:
            config.bot.auto_book = False

        bot = BeyondBot(config)

        # Initialize (authenticate)
        logger.info("Initializing bot...")
        bot.initialize(
            sms_code=args.sms_code,
            use_cached=not args.no_cache
        )

        if args.check_status:
            # Just check status and exit
            status = bot.api.get_surf_status()
            logger.info(f"Surf schedule status: {status}")
            return 0

        if args.inscriptions:
            # Show inscriptions and exit
            response = bot.api.get_inscriptions()
            inscriptions = response.get("value", [])
            logger.info(f"Found {len(inscriptions)} inscription(s):")
            for i, insc in enumerate(inscriptions, 1):
                single = insc.get("singleInscription")
                recurrent = insc.get("recurrentInscription")
                data = single or recurrent
                if data:
                    join_date = data.get("joinDate", "N/A")
                    benefit = data.get("benefit", {}).get("name", "N/A")
                    member = data.get("member", {}).get("socialName", "N/A")
                    remaining = data.get("remainingUses", 0)
                    use_limit = data.get("useLimit", 0)
                    insc_status = "Disponível" if remaining > 0 else "Usado"
                    logger.info(f"  {i}. {join_date} - {member} - {benefit}")
                    logger.info(f"     Usos: {remaining}/{use_limit} - {insc_status}")
                if args.verbose:
                    logger.debug(f"     Raw data: {insc}")
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
