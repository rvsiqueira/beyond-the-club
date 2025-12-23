"""
Sports configuration endpoints.

Provides sport configuration and attribute information.
"""

from typing import List, Dict, Any

from fastapi import APIRouter, Query

from ..deps import ServicesDep
from src.config import SPORT_CONFIGS

router = APIRouter()


def get_levels_from_config(config: dict) -> List[str]:
    """Extract levels from config defaults."""
    defaults = config.get("defaults", {})
    level_str = defaults.get("level", "")
    if level_str:
        return level_str.split(",")
    return []


def get_wave_sides_from_config(config: dict) -> List[str]:
    """Extract wave sides from config defaults."""
    defaults = config.get("defaults", {})
    ws_str = defaults.get("wave_side", "")
    if ws_str:
        return ws_str.split(",")
    return []


def get_courts_from_config(config: dict) -> List[str]:
    """Extract courts from config defaults."""
    defaults = config.get("defaults", {})
    court_str = defaults.get("court", "")
    if court_str:
        return court_str.split(",")
    return []


@router.get("")
async def list_sports():
    """
    List available sports and their configurations.
    """
    sports = []
    for sport_key, config in SPORT_CONFIGS.items():
        levels = get_levels_from_config(config)
        wave_sides = get_wave_sides_from_config(config)
        courts = get_courts_from_config(config)

        sports.append({
            "key": sport_key,
            "name": config.get("name", sport_key),
            "base_tags": config.get("base_tags", []),
            "levels": levels,
            "wave_sides": wave_sides,
            "courts": courts,
            "attributes": [a.get("name") for a in config.get("attributes", [])]
        })

    return {
        "sports": sports,
        "default": "surf"
    }


@router.get("/{sport}")
async def get_sport_config(sport: str):
    """
    Get configuration for a specific sport.
    """
    if sport not in SPORT_CONFIGS:
        return {"error": f"Sport '{sport}' not found", "available": list(SPORT_CONFIGS.keys())}

    config = SPORT_CONFIGS[sport]
    levels = get_levels_from_config(config)
    wave_sides = get_wave_sides_from_config(config)
    courts = get_courts_from_config(config)

    return {
        "sport": sport,
        "name": config.get("name", sport),
        "base_tags": config.get("base_tags", []),
        "levels": levels,
        "wave_sides": wave_sides,
        "courts": courts,
        "attributes": config.get("attributes", [])
    }


@router.get("/{sport}/levels")
async def get_sport_levels(sport: str):
    """
    Get available levels for a sport.
    """
    if sport not in SPORT_CONFIGS:
        return {"error": f"Sport '{sport}' not found"}

    config = SPORT_CONFIGS[sport]
    levels = get_levels_from_config(config)

    return {
        "sport": sport,
        "levels": levels
    }


@router.get("/{sport}/wave-sides")
async def get_sport_wave_sides(sport: str):
    """
    Get available wave sides for a sport (Surf only).
    """
    if sport not in SPORT_CONFIGS:
        return {"error": f"Sport '{sport}' not found"}

    config = SPORT_CONFIGS[sport]
    wave_sides = get_wave_sides_from_config(config)

    return {
        "sport": sport,
        "wave_sides": wave_sides
    }


@router.get("/{sport}/combos")
async def get_sport_combos(sport: str):
    """
    Get all valid level/wave_side combinations for a sport.
    """
    if sport not in SPORT_CONFIGS:
        return {"error": f"Sport '{sport}' not found"}

    config = SPORT_CONFIGS[sport]
    combos = []

    if sport == "surf":
        levels = get_levels_from_config(config)
        wave_sides = get_wave_sides_from_config(config)
        for level in levels:
            for wave_side in wave_sides:
                combos.append({
                    "level": level,
                    "wave_side": wave_side,
                    "combo_key": f"{level}/{wave_side}"
                })
    elif sport == "tennis":
        courts = get_courts_from_config(config)
        for court in courts:
            combos.append({
                "court": court,
                "combo_key": court
            })

    return {
        "sport": sport,
        "combos": combos,
        "total": len(combos)
    }
