"""
Package ID mappings for Beyond The Club.

These mappings are fixed and don't change - they map level/wave_side combinations
to their respective packageId and productId in the Beyond API.

This file should be committed to git so deployments have this data available
without needing to fetch from the availability API.
"""

from typing import Dict, Optional
from dataclasses import dataclass


@dataclass
class PackageInfo:
    """Package information for a session type."""
    package_id: int
    product_id: int


# Surf session packages - maps "level/wave_side" to package IDs
SURF_PACKAGES: Dict[str, PackageInfo] = {
    # Iniciante 1
    "Iniciante1/Lado_esquerdo": PackageInfo(package_id=16, product_id=16),
    "Iniciante1/Lado_direito": PackageInfo(package_id=14, product_id=14),

    # Iniciante 2
    "Iniciante2/Lado_esquerdo": PackageInfo(package_id=17, product_id=17),
    "Iniciante2/Lado_direito": PackageInfo(package_id=15, product_id=15),

    # Intermediario 1
    "Intermediario1/Lado_esquerdo": PackageInfo(package_id=20, product_id=20),
    "Intermediario1/Lado_direito": PackageInfo(package_id=18, product_id=18),

    # Intermediario 2
    "Intermediario2/Lado_esquerdo": PackageInfo(package_id=21, product_id=21),
    "Intermediario2/Lado_direito": PackageInfo(package_id=19, product_id=19),

    # Avancado 1
    "Avançado1/Lado_esquerdo": PackageInfo(package_id=22, product_id=22),
    "Avançado1/Lado_direito": PackageInfo(package_id=24, product_id=24),

    # Avancado 2
    "Avançado2/Lado_esquerdo": PackageInfo(package_id=23, product_id=23),
    "Avançado2/Lado_direito": PackageInfo(package_id=25, product_id=25),
}

# Tennis packages (placeholder - add when needed)
TENNIS_PACKAGES: Dict[str, PackageInfo] = {
    # "Quadra_Saibro": PackageInfo(package_id=XX, product_id=XX),
}

# All packages by sport
PACKAGES_BY_SPORT: Dict[str, Dict[str, PackageInfo]] = {
    "surf": SURF_PACKAGES,
    "tennis": TENNIS_PACKAGES,
}


def get_package_info(combo_key: str, sport: str = "surf") -> Optional[PackageInfo]:
    """
    Get package info for a combo key.

    Args:
        combo_key: The combo key (e.g., "Iniciante1/Lado_esquerdo")
        sport: The sport type

    Returns:
        PackageInfo or None if not found
    """
    packages = PACKAGES_BY_SPORT.get(sport, {})
    return packages.get(combo_key)


def get_package_ids(level: str, wave_side: str, sport: str = "surf") -> Optional[PackageInfo]:
    """
    Get package IDs for a level/wave_side combination.

    Args:
        level: Session level (e.g., "Iniciante1")
        wave_side: Wave side (e.g., "Lado_esquerdo")
        sport: The sport type

    Returns:
        PackageInfo or None if not found
    """
    combo_key = f"{level}/{wave_side}"
    return get_package_info(combo_key, sport)


def get_all_combo_keys(sport: str = "surf") -> list:
    """Get all available combo keys for a sport."""
    packages = PACKAGES_BY_SPORT.get(sport, {})
    return list(packages.keys())
