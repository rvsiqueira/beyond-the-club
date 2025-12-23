"""
Password handling utilities.

Uses bcrypt for secure password hashing.
"""

import logging
from typing import Optional

import bcrypt

logger = logging.getLogger(__name__)

# bcrypt work factor (higher = more secure but slower)
# 12 is a good balance for 2024
BCRYPT_ROUNDS = 12


class PasswordHandler:
    """
    Handles password hashing and verification using bcrypt.

    Usage:
        handler = PasswordHandler()
        hashed = handler.hash("my_password")
        is_valid = handler.verify("my_password", hashed)
    """

    def __init__(self, rounds: int = BCRYPT_ROUNDS):
        """
        Initialize password handler.

        Args:
            rounds: bcrypt work factor (default: 12)
        """
        self.rounds = rounds

    def hash(self, password: str) -> str:
        """
        Hash a password using bcrypt.

        Args:
            password: Plain text password

        Returns:
            Hashed password string (includes salt)
        """
        if not password:
            raise ValueError("Password cannot be empty")

        # Generate salt and hash
        salt = bcrypt.gensalt(rounds=self.rounds)
        hashed = bcrypt.hashpw(password.encode("utf-8"), salt)

        return hashed.decode("utf-8")

    def verify(self, password: str, hashed: str) -> bool:
        """
        Verify a password against a hash.

        Args:
            password: Plain text password to verify
            hashed: Previously hashed password

        Returns:
            True if password matches, False otherwise
        """
        if not password or not hashed:
            return False

        try:
            return bcrypt.checkpw(
                password.encode("utf-8"),
                hashed.encode("utf-8")
            )
        except Exception as e:
            logger.warning(f"Password verification error: {e}")
            return False

    def needs_rehash(self, hashed: str) -> bool:
        """
        Check if a hash needs to be rehashed (e.g., rounds changed).

        Args:
            hashed: Previously hashed password

        Returns:
            True if hash should be regenerated
        """
        try:
            # Extract rounds from hash
            # bcrypt hash format: $2b$rounds$salt+hash
            parts = hashed.split("$")
            if len(parts) >= 3:
                current_rounds = int(parts[2])
                return current_rounds != self.rounds
            return True
        except Exception:
            return True


def normalize_phone(phone: str) -> Optional[str]:
    """
    Normalize a phone number to a standard format.

    Removes spaces, dashes, parentheses and ensures it starts with +.

    Args:
        phone: Phone number in any format

    Returns:
        Normalized phone number or None if invalid

    Examples:
        normalize_phone("(11) 99999-9999") -> "+5511999999999"
        normalize_phone("+55 11 99999-9999") -> "+5511999999999"
        normalize_phone("11999999999") -> "+5511999999999"
    """
    if not phone:
        return None

    # Remove all non-digit characters except +
    cleaned = "".join(c for c in phone if c.isdigit() or c == "+")

    # If doesn't start with +, assume Brazilian number
    if not cleaned.startswith("+"):
        # Add Brazil country code if not present
        if len(cleaned) == 11:  # 11 digits = DDD + number
            cleaned = "+55" + cleaned
        elif len(cleaned) == 13 and cleaned.startswith("55"):
            cleaned = "+" + cleaned
        else:
            # Invalid format
            return None

    # Validate minimum length (country code + area code + number)
    if len(cleaned) < 12:
        return None

    return cleaned
