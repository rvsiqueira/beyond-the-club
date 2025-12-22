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

from src.bot import BeyondBot
from src.config import load_config


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
