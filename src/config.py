"""Configuration module for BeyondTheClub bot."""

import os
from dataclasses import dataclass, field
from typing import List, Dict, Any
from dotenv import load_dotenv

load_dotenv()


# Fixed session hours by level
# Each level has specific time slots available
SESSION_FIXED_HOURS = {
    "Iniciante1": ["13:00", "15:00"],
    "Iniciante2": ["09:00", "17:00"],
    "Intermediario1": ["10:00", "16:00"],
    "Intermediario2": ["08:00", "12:00", "18:00"],
    "Avançado1": ["11:00", "14:00"],
    "Avançado2": ["07:00", "19:00"],
}


def get_valid_hours_for_level(level: str) -> List[str]:
    """Get valid hours for a specific session level."""
    return SESSION_FIXED_HOURS.get(level, [])


def get_all_levels() -> List[str]:
    """Get all available session levels."""
    return list(SESSION_FIXED_HOURS.keys())


# Sport configuration definitions
SPORT_CONFIGS = {
    "surf": {
        "name": "Surf",
        "base_tags": ["Surf", "Agendamento"],
        "attributes": [
            {"name": "level", "env_var": "SURF_LEVELS", "label": "Nível"},
            {"name": "wave_side", "env_var": "SURF_WAVE_SIDES", "label": "Lado"},
        ],
        "defaults": {
            "level": "Iniciante1,Iniciante2,Intermediario1,Intermediario2,Avançado1,Avançado2",
            "wave_side": "Lado_esquerdo,Lado_direito",
        },
    },
    "tennis": {
        "name": "Tennis",
        "base_tags": ["Tennis", "Agendamento"],
        "attributes": [
            {"name": "court", "env_var": "TENNIS_COURTS", "label": "Quadra"},
        ],
        "defaults": {
            "court": "Quadra_Saibro",
        },
    },
}


@dataclass
class SportConfig:
    """Configuration for a specific sport."""
    sport: str
    name: str
    base_tags: List[str]
    options: Dict[str, List[str]]  # attribute_name -> list of options
    attribute_labels: Dict[str, str]  # attribute_name -> display label

    @classmethod
    def load(cls, sport: str) -> "SportConfig":
        """Load sport configuration from environment."""
        if sport not in SPORT_CONFIGS:
            raise ValueError(f"Unknown sport: {sport}. Available: {list(SPORT_CONFIGS.keys())}")

        config = SPORT_CONFIGS[sport]
        options = {}
        labels = {}

        for attr in config["attributes"]:
            attr_name = attr["name"]
            env_var = attr["env_var"]
            default = config["defaults"].get(attr_name, "")

            # Load from environment or use default
            value = os.getenv(env_var, default)
            options[attr_name] = [v.strip() for v in value.split(",") if v.strip()]
            labels[attr_name] = attr["label"]

        return cls(
            sport=sport,
            name=config["name"],
            base_tags=config["base_tags"],
            options=options,
            attribute_labels=labels,
        )

    def get_options(self, attribute: str) -> List[str]:
        """Get available options for an attribute."""
        return self.options.get(attribute, [])

    def get_attributes(self) -> List[str]:
        """Get list of attribute names for this sport."""
        return list(self.options.keys())


@dataclass
class FirebaseConfig:
    """Firebase authentication configuration."""
    api_key: str = field(default_factory=lambda: os.getenv("FIREBASE_API_KEY", "AIzaSyBIzRHrTwR6BLZUOhZx3QGz16npuFwqOhs"))
    project_id: str = field(default_factory=lambda: os.getenv("FIREBASE_PROJECT_ID", "beyondtheclub-8bfb3"))
    project_number: str = field(default_factory=lambda: os.getenv("FIREBASE_PROJECT_NUMBER", "409739711733"))
    app_id: str = field(default_factory=lambda: os.getenv("FIREBASE_APP_ID", "1:409739711733:android:7c8a81a9153eabb822a1bc"))
    android_cert: str = "30040D6B5C60B0CD9B82F45E1524EB291B37CC33"
    android_package: str = "br.com.beyondtheclub"


@dataclass
class AuthConfig:
    """Authentication credentials."""
    admin_email: str = field(default_factory=lambda: os.getenv("ADMIN_EMAIL", ""))
    admin_password: str = field(default_factory=lambda: os.getenv("ADMIN_PASSWORD", ""))
    phone_number: str = field(default_factory=lambda: os.getenv("PHONE_NUMBER", ""))


@dataclass
class SessionConfig:
    """Session preferences (legacy/fallback for surf)."""
    # Session levels to monitor (fallback to SURF_LEVELS)
    levels: List[str] = field(default_factory=lambda: _get_surf_levels())

    # Wave sides to monitor (fallback to SURF_WAVE_SIDES)
    wave_sides: List[str] = field(default_factory=lambda: _get_surf_wave_sides())

    # Target hours (24h format) - comma separated, e.g., "08:00,10:00,14:00"
    target_hours: List[str] = field(default_factory=lambda: os.getenv("TARGET_HOURS", "").split(",") if os.getenv("TARGET_HOURS") else [])

    # Target dates (YYYY-MM-DD format) - comma separated
    target_dates: List[str] = field(default_factory=lambda: os.getenv("TARGET_DATES", "").split(",") if os.getenv("TARGET_DATES") else [])


def _get_surf_levels() -> List[str]:
    """Get surf levels with fallback chain: SURF_LEVELS -> SESSION_LEVELS -> default."""
    value = os.getenv("SURF_LEVELS") or os.getenv("SESSION_LEVELS", "Iniciante1,Iniciante2,Intermediario1")
    return [v.strip() for v in value.split(",") if v.strip()]


def _get_surf_wave_sides() -> List[str]:
    """Get surf wave sides with fallback chain: SURF_WAVE_SIDES -> WAVE_SIDES -> default."""
    value = os.getenv("SURF_WAVE_SIDES") or os.getenv("WAVE_SIDES", "Lado_esquerdo,Lado_direito")
    return [v.strip() for v in value.split(",") if v.strip()]


@dataclass
class BotConfig:
    """Bot operation configuration."""
    check_interval_seconds: int = field(default_factory=lambda: int(os.getenv("CHECK_INTERVAL_SECONDS", "60")))
    max_retries: int = field(default_factory=lambda: int(os.getenv("MAX_RETRIES", "3")))
    auto_book: bool = field(default_factory=lambda: os.getenv("AUTO_BOOK", "true").lower() == "true")
    # Minimum minutes before session start to consider it bookable
    # Sessions starting within this time window are ignored
    session_start_buffer_minutes: int = field(default_factory=lambda: int(os.getenv("SESSION_START_BUFFER_MINUTES", "20")))


@dataclass
class Config:
    """Main configuration container."""
    firebase: FirebaseConfig = field(default_factory=FirebaseConfig)
    auth: AuthConfig = field(default_factory=AuthConfig)
    session: SessionConfig = field(default_factory=SessionConfig)
    bot: BotConfig = field(default_factory=BotConfig)

    api_base_url: str = "https://api.beyondtheclub.tech/beyond/api/v1"

    def get_available_sports(self) -> List[str]:
        """Get list of available sports from environment."""
        sports_str = os.getenv("SPORTS", "surf")
        return [s.strip().lower() for s in sports_str.split(",") if s.strip()]

    def get_sport_config(self, sport: str) -> SportConfig:
        """Get configuration for a specific sport."""
        return SportConfig.load(sport)


def load_config() -> Config:
    """Load configuration from environment variables."""
    return Config()


def get_available_sports() -> List[str]:
    """Get list of available sports from environment."""
    sports_str = os.getenv("SPORTS", "surf")
    return [s.strip().lower() for s in sports_str.split(",") if s.strip()]
