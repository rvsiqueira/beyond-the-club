"""Configuration module for BeyondTheClub bot."""

import os
from dataclasses import dataclass, field
from typing import List
from dotenv import load_dotenv

load_dotenv()


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
    """Surf session preferences."""
    # Session levels to monitor
    levels: List[str] = field(default_factory=lambda: os.getenv("SESSION_LEVELS", "Iniciante1,Iniciante2,Intermediario1").split(","))

    # Wave sides to monitor
    wave_sides: List[str] = field(default_factory=lambda: os.getenv("WAVE_SIDES", "Lado_esquerdo,Lado_direito").split(","))

    # Target hours (24h format) - comma separated, e.g., "08:00,10:00,14:00"
    target_hours: List[str] = field(default_factory=lambda: os.getenv("TARGET_HOURS", "").split(",") if os.getenv("TARGET_HOURS") else [])

    # Target dates (YYYY-MM-DD format) - comma separated
    target_dates: List[str] = field(default_factory=lambda: os.getenv("TARGET_DATES", "").split(",") if os.getenv("TARGET_DATES") else [])


@dataclass
class BotConfig:
    """Bot operation configuration."""
    check_interval_seconds: int = field(default_factory=lambda: int(os.getenv("CHECK_INTERVAL_SECONDS", "60")))
    max_retries: int = field(default_factory=lambda: int(os.getenv("MAX_RETRIES", "3")))
    auto_book: bool = field(default_factory=lambda: os.getenv("AUTO_BOOK", "true").lower() == "true")


@dataclass
class Config:
    """Main configuration container."""
    firebase: FirebaseConfig = field(default_factory=FirebaseConfig)
    auth: AuthConfig = field(default_factory=AuthConfig)
    session: SessionConfig = field(default_factory=SessionConfig)
    bot: BotConfig = field(default_factory=BotConfig)

    api_base_url: str = "https://api.beyondtheclub.tech/beyond/api/v1"


def load_config() -> Config:
    """Load configuration from environment variables."""
    return Config()
