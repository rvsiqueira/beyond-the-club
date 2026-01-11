"""
Availability scanning and caching service.

Handles scanning available slots and managing the availability cache.
"""

import json
import logging
import os
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass

from .base import BaseService, ServiceContext
from ..packages import get_package_info
from ..config import get_sao_paulo_now

logger = logging.getLogger(__name__)

# Minimum minutes before session start to consider it bookable
# Sessions starting within this time window are ignored
SESSION_START_BUFFER_MINUTES = int(os.getenv("SESSION_START_BUFFER_MINUTES", "20"))

AVAILABILITY_CACHE_FILE = Path(__file__).parent.parent.parent / ".beyondtheclub_availability.json"


@dataclass
class AvailableSlot:
    """Represents an available time slot."""
    date: str
    interval: str
    level: str
    wave_side: str
    available: int
    max_quantity: int
    package_id: int
    product_id: int

    @property
    def combo_key(self) -> str:
        """Return the level/wave_side combo key."""
        return f"{self.level}/{self.wave_side}"

    def to_dict(self) -> dict:
        return {
            "date": self.date,
            "interval": self.interval,
            "level": self.level,
            "wave_side": self.wave_side,
            "available": self.available,
            "max": self.max_quantity,
            "packageId": self.package_id,
            "productId": self.product_id
        }


class AvailabilityService(BaseService):
    """
    Service for scanning and managing slot availability.

    Responsibilities:
    - Scan all level/wave_side combinations for availability
    - Manage availability cache
    - Find slots matching specific criteria
    - Fast targeted search for specific combos
    """

    def __init__(self, context: ServiceContext, member_service=None):
        super().__init__(context)
        self._member_service = member_service

    def set_member_service(self, member_service):
        """Set the member service for getting member IDs."""
        self._member_service = member_service

    def _load_cache(self) -> Dict[str, Any]:
        """Load availability cache from file."""
        try:
            if not AVAILABILITY_CACHE_FILE.exists():
                return {"scanned_at": None, "dates": {}, "packages": {}}

            data = json.loads(AVAILABILITY_CACHE_FILE.read_text())
            return data
        except Exception as e:
            logger.warning(f"Could not load availability cache: {e}")
            return {"scanned_at": None, "dates": {}, "packages": {}}

    def _save_cache(self, cache: Dict[str, Any]):
        """Save availability cache to file."""
        try:
            cache["scanned_at"] = datetime.now(timezone.utc).isoformat()
            AVAILABILITY_CACHE_FILE.write_text(json.dumps(cache, indent=2))
            logger.debug("Availability cache saved")
        except Exception as e:
            logger.warning(f"Could not save availability cache: {e}")

    def is_cache_valid(self) -> bool:
        """
        Check if availability cache is valid (has dates >= today).

        Returns:
            True if cache exists and all dates are >= today
        """
        cache = self._load_cache()
        if not cache.get("dates"):
            return False

        today = datetime.now().strftime("%Y-%m-%d")
        for date_str in cache["dates"].keys():
            if date_str < today:
                return False

        return True

    def get_cache(self) -> Dict[str, Any]:
        """Get the availability cache."""
        return self._load_cache()

    def scan_availability(self, member_id: Optional[int] = None) -> List[AvailableSlot]:
        """
        Scan all level/wave_side combinations and return available slots.

        Args:
            member_id: Optional member ID to use for API queries.
                      If not provided, uses first available member.

        Returns:
            List of AvailableSlot objects
        """
        self.require_initialized()

        sport_config = self.sport_config

        # Get member ID for queries
        if member_id is None:
            if self._member_service:
                members = self._member_service.get_members()
                if not members:
                    raise RuntimeError("No members found")
                member_id = members[0].member_id
            else:
                raise RuntimeError("No member_id provided and no member service available")

        all_slots = []
        cache = {"scanned_at": None, "dates": {}, "packages": {}}

        # Get all level/wave_side combinations
        levels = sport_config.get_options("level")
        wave_sides = sport_config.get_options("wave_side")

        for level in levels:
            for wave_side in wave_sides:
                combo_key = f"{level}/{wave_side}"
                tags = list(sport_config.base_tags) + [level, wave_side]

                logger.info(f"Scanning {combo_key}...")

                try:
                    # Get available dates for this combination
                    dates_response = self.api.get_available_dates(tags, sport=self.current_sport)

                    # Handle API response wrapper
                    if isinstance(dates_response, dict) and "value" in dates_response:
                        dates_list = dates_response["value"]
                    else:
                        dates_list = dates_response

                    # Parse dates (they come as "2025-12-26T00:00:00")
                    dates = []
                    for date_item in dates_list:
                        if isinstance(date_item, str):
                            date_str = date_item.split("T")[0]
                            dates.append(date_str)

                    logger.info(f"  Found {len(dates)} dates for {combo_key}")

                    for date in dates:
                        try:
                            intervals_data = self.api.get_intervals(
                                date=date,
                                tags=tags,
                                member_id=member_id,
                                sport=self.current_sport
                            )

                            packages_list = intervals_data if isinstance(intervals_data, list) else []

                            for package in packages_list:
                                package_id = package.get("packageId")
                                products = package.get("products", [])

                                for product in products:
                                    product_id = product.get("productId", package_id)

                                    # Store package mapping
                                    cache["packages"][combo_key] = {
                                        "packageId": package_id,
                                        "productId": product_id
                                    }

                                    invitation = product.get("invitation", {})
                                    solos = invitation.get("solos", [])

                                    for solo in solos:
                                        if solo.get("isAvailable", False):
                                            slot = AvailableSlot(
                                                date=date,
                                                interval=solo.get("interval", ""),
                                                level=level,
                                                wave_side=wave_side,
                                                available=solo.get("availableQuantity", 0),
                                                max_quantity=solo.get("maxQuantity", 0),
                                                package_id=package_id,
                                                product_id=product_id
                                            )
                                            all_slots.append(slot)

                                            # Add to cache
                                            if date not in cache["dates"]:
                                                cache["dates"][date] = {}
                                            if combo_key not in cache["dates"][date]:
                                                cache["dates"][date][combo_key] = []

                                            cache["dates"][date][combo_key].append({
                                                "interval": slot.interval,
                                                "available": slot.available,
                                                "max": slot.max_quantity
                                            })

                        except Exception as e:
                            logger.error(f"Error getting intervals for {date} {combo_key}: {e}")

                except Exception as e:
                    logger.error(f"Error scanning {combo_key}: {e}")

        # Save cache
        self._save_cache(cache)
        logger.info(f"Scan complete. Found {len(all_slots)} available slots.")

        return all_slots

    def get_slots_from_cache(self) -> List[AvailableSlot]:
        """
        Get available slots from cache.

        Uses fixed package mapping from config when cache doesn't have package info.

        Returns:
            List of AvailableSlot objects from cache
        """
        cache = self._load_cache()
        slots = []

        packages_from_cache = cache.get("packages", {})

        for date, combos in cache.get("dates", {}).items():
            for combo_key, intervals in combos.items():
                parts = combo_key.split("/")
                if len(parts) != 2:
                    continue
                level, wave_side = parts

                # First try cache, then fall back to fixed config
                pkg_from_cache = packages_from_cache.get(combo_key, {})
                package_id = pkg_from_cache.get("packageId", 0)
                product_id = pkg_from_cache.get("productId", 0)

                # If not in cache, use fixed config
                if package_id == 0 or product_id == 0:
                    pkg_info = get_package_info(combo_key, self.current_sport)
                    if pkg_info:
                        package_id = pkg_info.package_id
                        product_id = pkg_info.product_id

                for interval_data in intervals:
                    slot = AvailableSlot(
                        date=date,
                        interval=interval_data.get("interval", ""),
                        level=level,
                        wave_side=wave_side,
                        available=interval_data.get("available", 0),
                        max_quantity=interval_data.get("max", 0),
                        package_id=package_id,
                        product_id=product_id
                    )
                    slots.append(slot)

        # Sort by date and interval
        slots.sort(key=lambda s: (s.date, s.interval, s.combo_key))
        return slots

    def find_slot_for_combo(
        self,
        level: str,
        wave_side: str,
        member_id: int,
        target_dates: Optional[List[str]] = None,
        target_hours: Optional[List[str]] = None
    ) -> Optional[AvailableSlot]:
        """
        Fast search for available slot for a specific level/wave_side combo.

        Only queries the API for this specific combination, not all combos.

        Args:
            level: Session level (e.g., "Iniciante2")
            wave_side: Wave side (e.g., "Lado_esquerdo")
            member_id: Member ID for the query
            target_dates: Optional list of specific dates
            target_hours: Optional list of specific hours

        Returns:
            First available AvailableSlot or None
        """
        self.require_initialized()

        sport_config = self.sport_config
        tags = list(sport_config.base_tags) + [level, wave_side]
        combo_key = f"{level}/{wave_side}"
        today = datetime.now().strftime("%Y-%m-%d")

        # Get available dates for this combo
        try:
            dates_response = self.api.get_available_dates(tags, sport=self.current_sport)
            if isinstance(dates_response, dict) and "value" in dates_response:
                dates_list = dates_response["value"]
            else:
                dates_list = dates_response

            # Parse and filter dates
            available_dates = []
            for date_item in dates_list:
                if isinstance(date_item, str):
                    date_str = date_item.split("T")[0]
                    # Filter by today and target dates
                    if date_str >= today:
                        if target_dates is None or date_str in target_dates:
                            available_dates.append(date_str)

            if not available_dates:
                return None

            # Sort dates
            available_dates.sort()

            # Check each date for available intervals
            for date in available_dates:
                try:
                    intervals_data = self.api.get_intervals(
                        date=date,
                        tags=tags,
                        member_id=member_id,
                        sport=self.current_sport
                    )

                    packages_list = intervals_data if isinstance(intervals_data, list) else []

                    for package in packages_list:
                        package_id = package.get("packageId")
                        products = package.get("products", [])

                        for product in products:
                            product_id = product.get("productId", package_id)
                            invitation = product.get("invitation", {})
                            solos = invitation.get("solos", [])

                            # Sort solos by interval to get earliest first
                            solos_sorted = sorted(solos, key=lambda s: s.get("interval", ""))

                            for solo in solos_sorted:
                                if not solo.get("isAvailable", False):
                                    continue

                                interval = solo.get("interval", "")

                                # Filter by target hours if specified
                                if target_hours and interval not in target_hours:
                                    continue

                                available_qty = solo.get("availableQuantity", 0)
                                if available_qty > 0:
                                    # Check if session has already started or will start too soon
                                    # Use São Paulo timezone (BRT = UTC-3) since Beyond The Club operates in Brazil
                                    try:
                                        session_datetime = datetime.strptime(f"{date} {interval}", "%Y-%m-%d %H:%M")
                                        now_brt = get_sao_paulo_now().replace(tzinfo=None)  # Remove tz for comparison
                                        min_start_time = now_brt + timedelta(minutes=SESSION_START_BUFFER_MINUTES)
                                        if session_datetime < min_start_time:
                                            logger.debug(
                                                f"Skipping slot {date} {interval} - session starts too soon "
                                                f"(session: {session_datetime}, min: {min_start_time})"
                                            )
                                            continue
                                    except ValueError as e:
                                        logger.warning(f"Could not parse session datetime {date} {interval}: {e}")

                                    return AvailableSlot(
                                        date=date,
                                        interval=interval,
                                        level=level,
                                        wave_side=wave_side,
                                        available=available_qty,
                                        max_quantity=solo.get("maxQuantity", 0),
                                        package_id=package_id,
                                        product_id=product_id
                                    )

                except Exception as e:
                    logger.error(f"Error getting intervals for {date} {combo_key}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error getting dates for {combo_key}: {e}")

        return None

    def refresh_slot_availability(
        self,
        date: str,
        interval: str,
        level: str,
        wave_side: str,
        member_id: int
    ) -> Optional[int]:
        """
        Refresh availability for a specific slot in the cache.

        Called after booking/cancel to update just the affected slot.

        Args:
            date: Date of the slot (YYYY-MM-DD)
            interval: Time interval (e.g., "08:00")
            level: Level (e.g., "Iniciante2")
            wave_side: Wave side (e.g., "Lado_esquerdo")
            member_id: Member ID for the API query

        Returns:
            New available quantity or None if error
        """
        self.require_initialized()

        sport_config = self.sport_config
        tags = list(sport_config.base_tags) + [level, wave_side]
        combo_key = f"{level}/{wave_side}"

        try:
            # Get intervals for this date/combo
            intervals_data = self.api.get_intervals(
                date=date,
                tags=tags,
                member_id=member_id,
                sport=self.current_sport
            )

            packages_list = intervals_data if isinstance(intervals_data, list) else []
            new_available = None

            for package in packages_list:
                products = package.get("products", [])

                for product in products:
                    invitation = product.get("invitation", {})
                    solos = invitation.get("solos", [])

                    for solo in solos:
                        if solo.get("interval") == interval:
                            new_available = solo.get("availableQuantity", 0)
                            break

            if new_available is not None:
                # Update cache
                cache = self._load_cache()

                if date in cache.get("dates", {}):
                    if combo_key in cache["dates"][date]:
                        for slot_data in cache["dates"][date][combo_key]:
                            if slot_data.get("interval") == interval:
                                old_available = slot_data.get("available", 0)
                                slot_data["available"] = new_available
                                logger.info(
                                    f"Updated availability for {date} {interval} {combo_key}: "
                                    f"{old_available} -> {new_available}"
                                )
                                break

                self._save_cache(cache)

            return new_available

        except Exception as e:
            logger.error(f"Error refreshing slot availability for {date} {interval} {combo_key}: {e}")
            return None

    def filter_slots(
        self,
        slots: List[AvailableSlot],
        target_dates: Optional[List[str]] = None,
        target_hours: Optional[List[str]] = None,
        combo_keys: Optional[List[str]] = None,
        min_available: int = 1
    ) -> List[AvailableSlot]:
        """
        Filter slots by various criteria.

        Args:
            slots: List of slots to filter
            target_dates: Only include these dates
            target_hours: Only include these hours
            combo_keys: Only include these level/wave_side combos
            min_available: Minimum available quantity

        Returns:
            Filtered list of slots
        """
        now_brt = datetime.now()  # Server runs in BRT
        today = now_brt.strftime("%Y-%m-%d")
        min_start_time = now_brt + timedelta(minutes=SESSION_START_BUFFER_MINUTES)
        result = []

        for slot in slots:
            # Filter past dates
            if slot.date < today:
                continue

            # Filter by target dates
            if target_dates and slot.date not in target_dates:
                continue

            # Filter by target hours
            if target_hours and slot.interval not in target_hours:
                continue

            # Filter by combo keys
            if combo_keys and slot.combo_key not in combo_keys:
                continue

            # Filter by availability
            if slot.available < min_available:
                continue

            # Filter sessions that have already started or will start too soon
            try:
                session_datetime = datetime.strptime(f"{slot.date} {slot.interval}", "%Y-%m-%d %H:%M")
                if session_datetime < min_start_time:
                    logger.debug(
                        f"Filtering out slot {slot.date} {slot.interval} - session starts too soon"
                    )
                    continue
            except ValueError:
                pass  # If we can't parse, include the slot

            result.append(slot)

        return result
