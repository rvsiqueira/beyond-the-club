"""
User storage and management.

Stores users in a JSON file for simplicity.
Can be replaced with a database in the future.
"""

import json
import logging
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional, List
from dataclasses import dataclass, asdict, field

from .password import PasswordHandler, normalize_phone

logger = logging.getLogger(__name__)

# Default storage path
DEFAULT_USERS_FILE = Path(__file__).parent.parent.parent / "data" / "users.json"


@dataclass
class User:
    """User data model."""
    user_id: str
    phone: str  # Normalized phone number (primary identifier)
    password_hash: Optional[str] = None  # None for phone-only auth
    name: Optional[str] = None
    email: Optional[str] = None
    member_ids: List[int] = field(default_factory=list)  # Linked Beyond members
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    last_login: Optional[str] = None
    is_active: bool = True

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "User":
        # Handle missing fields gracefully
        return cls(
            user_id=data.get("user_id", str(uuid.uuid4())),
            phone=data["phone"],
            password_hash=data.get("password_hash"),
            name=data.get("name"),
            email=data.get("email"),
            member_ids=data.get("member_ids", []),
            created_at=data.get("created_at", datetime.utcnow().isoformat()),
            updated_at=data.get("updated_at", datetime.utcnow().isoformat()),
            last_login=data.get("last_login"),
            is_active=data.get("is_active", True)
        )

    def has_password(self) -> bool:
        """Check if user has a password set."""
        return self.password_hash is not None


class UserStore:
    """
    JSON-based user storage.

    Thread-safe for basic operations.
    Users are indexed by phone number (primary key).
    """

    def __init__(self, file_path: Optional[Path] = None):
        """
        Initialize user store.

        Args:
            file_path: Path to users JSON file (default: data/users.json)
        """
        self.file_path = file_path or DEFAULT_USERS_FILE
        self.password_handler = PasswordHandler()
        self._ensure_file()

    def _ensure_file(self):
        """Ensure the storage file and directory exist."""
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.file_path.exists():
            self._save_all({})

    def _load_all(self) -> dict[str, dict]:
        """Load all users from file."""
        try:
            with open(self.file_path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}

    def _save_all(self, users: dict[str, dict]):
        """Save all users to file."""
        with open(self.file_path, "w") as f:
            json.dump(users, f, indent=2, ensure_ascii=False)

    def create_user(
        self,
        phone: str,
        password: Optional[str] = None,
        name: Optional[str] = None,
        email: Optional[str] = None,
        member_ids: Optional[List[int]] = None
    ) -> User:
        """
        Create a new user.

        Args:
            phone: Phone number (will be normalized)
            password: Optional password (None for phone-only auth)
            name: Optional display name
            email: Optional email address
            member_ids: Optional list of Beyond member IDs to link

        Returns:
            Created User object

        Raises:
            ValueError: If phone is invalid or user already exists
        """
        normalized_phone = normalize_phone(phone)
        if not normalized_phone:
            raise ValueError(f"Invalid phone number: {phone}")

        users = self._load_all()

        if normalized_phone in users:
            raise ValueError(f"User with phone {normalized_phone} already exists")

        password_hash = None
        if password:
            password_hash = self.password_handler.hash(password)

        user = User(
            user_id=str(uuid.uuid4()),
            phone=normalized_phone,
            password_hash=password_hash,
            name=name,
            email=email,
            member_ids=member_ids or []
        )

        users[normalized_phone] = user.to_dict()
        self._save_all(users)

        logger.info(f"Created user: {normalized_phone}")
        return user

    def get_by_phone(self, phone: str) -> Optional[User]:
        """
        Get user by phone number.

        Args:
            phone: Phone number (will be normalized)

        Returns:
            User if found, None otherwise
        """
        normalized = normalize_phone(phone)
        if not normalized:
            return None

        users = self._load_all()
        data = users.get(normalized)

        if data:
            return User.from_dict(data)
        return None

    def get_by_id(self, user_id: str) -> Optional[User]:
        """
        Get user by user ID.

        Args:
            user_id: User's unique ID

        Returns:
            User if found, None otherwise
        """
        users = self._load_all()
        for data in users.values():
            if data.get("user_id") == user_id:
                return User.from_dict(data)
        return None

    def update_user(self, user: User) -> User:
        """
        Update an existing user.

        Args:
            user: User object with updated fields

        Returns:
            Updated User object

        Raises:
            ValueError: If user doesn't exist
        """
        users = self._load_all()

        if user.phone not in users:
            raise ValueError(f"User {user.phone} not found")

        user.updated_at = datetime.utcnow().isoformat()
        users[user.phone] = user.to_dict()
        self._save_all(users)

        logger.debug(f"Updated user: {user.phone}")
        return user

    def set_password(self, phone: str, password: str) -> User:
        """
        Set or update a user's password.

        Args:
            phone: User's phone number
            password: New password

        Returns:
            Updated User object

        Raises:
            ValueError: If user doesn't exist
        """
        user = self.get_by_phone(phone)
        if not user:
            raise ValueError(f"User with phone {phone} not found")

        user.password_hash = self.password_handler.hash(password)
        return self.update_user(user)

    def verify_password(self, phone: str, password: str) -> Optional[User]:
        """
        Verify a user's password.

        Args:
            phone: User's phone number
            password: Password to verify

        Returns:
            User if password is valid, None otherwise
        """
        user = self.get_by_phone(phone)
        if not user or not user.password_hash:
            return None

        if self.password_handler.verify(password, user.password_hash):
            return user
        return None

    def record_login(self, phone: str) -> Optional[User]:
        """
        Record a user login.

        Args:
            phone: User's phone number

        Returns:
            Updated User object or None if not found
        """
        user = self.get_by_phone(phone)
        if not user:
            return None

        user.last_login = datetime.utcnow().isoformat()
        return self.update_user(user)

    def link_member(self, phone: str, member_id: int) -> User:
        """
        Link a Beyond member ID to a user.

        Args:
            phone: User's phone number
            member_id: Beyond member ID to link

        Returns:
            Updated User object

        Raises:
            ValueError: If user doesn't exist
        """
        user = self.get_by_phone(phone)
        if not user:
            raise ValueError(f"User with phone {phone} not found")

        if member_id not in user.member_ids:
            user.member_ids.append(member_id)
            return self.update_user(user)

        return user

    def unlink_member(self, phone: str, member_id: int) -> User:
        """
        Unlink a Beyond member ID from a user.

        Args:
            phone: User's phone number
            member_id: Beyond member ID to unlink

        Returns:
            Updated User object

        Raises:
            ValueError: If user doesn't exist
        """
        user = self.get_by_phone(phone)
        if not user:
            raise ValueError(f"User with phone {phone} not found")

        if member_id in user.member_ids:
            user.member_ids.remove(member_id)
            return self.update_user(user)

        return user

    def list_users(self, active_only: bool = True) -> List[User]:
        """
        List all users.

        Args:
            active_only: If True, only return active users

        Returns:
            List of User objects
        """
        users = self._load_all()
        result = [User.from_dict(data) for data in users.values()]

        if active_only:
            result = [u for u in result if u.is_active]

        return result

    def delete_user(self, phone: str, hard_delete: bool = False) -> bool:
        """
        Delete a user.

        Args:
            phone: User's phone number
            hard_delete: If True, permanently remove. If False, just deactivate.

        Returns:
            True if deleted, False if not found
        """
        normalized = normalize_phone(phone)
        if not normalized:
            return False

        users = self._load_all()

        if normalized not in users:
            return False

        if hard_delete:
            del users[normalized]
            logger.info(f"Hard deleted user: {normalized}")
        else:
            users[normalized]["is_active"] = False
            users[normalized]["updated_at"] = datetime.utcnow().isoformat()
            logger.info(f"Soft deleted user: {normalized}")

        self._save_all(users)
        return True

    def user_exists(self, phone: str) -> bool:
        """
        Check if a user exists.

        Args:
            phone: Phone number to check

        Returns:
            True if user exists
        """
        return self.get_by_phone(phone) is not None


# Module-level helper function for convenience
_default_store: Optional[UserStore] = None


def get_user_store() -> UserStore:
    """Get or create the default user store."""
    global _default_store
    if _default_store is None:
        _default_store = UserStore()
    return _default_store


def get_user_by_phone(phone: str) -> Optional[dict]:
    """
    Get user by phone number.

    Returns user data as dict or None if not found.
    """
    store = get_user_store()
    user = store.get_by_phone(phone)
    if user:
        return user.to_dict()
    return None
