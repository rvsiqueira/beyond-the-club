"""
User authentication service.

Provides our own authentication system independent of Firebase.
Supports multiple auth types: password, phone-only (voice), SMS OTP (future).
"""

import logging
from typing import Optional, List
from dataclasses import dataclass

from ..auth import JWTHandler, TokenPayload, UserStore, User
from ..auth.password import normalize_phone

logger = logging.getLogger(__name__)


@dataclass
class AuthTokens:
    """Authentication tokens response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 3600  # seconds

    def to_dict(self) -> dict:
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "token_type": self.token_type,
            "expires_in": self.expires_in
        }


@dataclass
class AuthResult:
    """Authentication result."""
    success: bool
    tokens: Optional[AuthTokens] = None
    user: Optional[User] = None
    error: Optional[str] = None

    def to_dict(self) -> dict:
        result = {"success": self.success}
        if self.tokens:
            result["tokens"] = self.tokens.to_dict()
        if self.user:
            result["user"] = {
                "user_id": self.user.user_id,
                "phone": self.user.phone,
                "name": self.user.name,
                "member_ids": self.user.member_ids
            }
        if self.error:
            result["error"] = self.error
        return result


class UserAuthService:
    """
    Service for user authentication.

    Handles:
    - User registration (phone + password)
    - Login with password
    - Login with phone only (voice agent / caller ID)
    - Token refresh
    - User management
    """

    def __init__(
        self,
        jwt_handler: Optional[JWTHandler] = None,
        user_store: Optional[UserStore] = None
    ):
        """
        Initialize auth service.

        Args:
            jwt_handler: Optional JWT handler (creates default if not provided)
            user_store: Optional user store (creates default if not provided)
        """
        self.jwt = jwt_handler or JWTHandler()
        self.users = user_store or UserStore()

    def register(
        self,
        phone: str,
        password: str,
        name: Optional[str] = None,
        email: Optional[str] = None,
        member_ids: Optional[List[int]] = None
    ) -> AuthResult:
        """
        Register a new user with phone and password.

        Args:
            phone: Phone number
            password: Password
            name: Optional display name
            email: Optional email
            member_ids: Optional Beyond member IDs to link

        Returns:
            AuthResult with tokens if successful
        """
        try:
            # Validate phone
            normalized = normalize_phone(phone)
            if not normalized:
                return AuthResult(success=False, error="Invalid phone number format")

            # Check if user exists
            if self.users.user_exists(phone):
                return AuthResult(success=False, error="User already exists")

            # Validate password
            if not password or len(password) < 6:
                return AuthResult(success=False, error="Password must be at least 6 characters")

            # Create user
            user = self.users.create_user(
                phone=phone,
                password=password,
                name=name,
                email=email,
                member_ids=member_ids
            )

            # Generate tokens
            access, refresh = self.jwt.create_token_pair(
                user_id=user.user_id,
                phone=user.phone,
                auth_type="password"
            )

            tokens = AuthTokens(access_token=access, refresh_token=refresh)

            logger.info(f"User registered: {normalized}")
            return AuthResult(success=True, tokens=tokens, user=user)

        except Exception as e:
            logger.error(f"Registration failed: {e}")
            return AuthResult(success=False, error=str(e))

    def login_password(self, phone: str, password: str) -> AuthResult:
        """
        Login with phone and password.

        Args:
            phone: Phone number
            password: Password

        Returns:
            AuthResult with tokens if successful
        """
        try:
            # Verify credentials
            user = self.users.verify_password(phone, password)
            if not user:
                return AuthResult(success=False, error="Invalid phone or password")

            if not user.is_active:
                return AuthResult(success=False, error="Account is deactivated")

            # Record login
            self.users.record_login(user.phone)

            # Generate tokens
            access, refresh = self.jwt.create_token_pair(
                user_id=user.user_id,
                phone=user.phone,
                auth_type="password"
            )

            tokens = AuthTokens(access_token=access, refresh_token=refresh)

            logger.info(f"User logged in: {user.phone}")
            return AuthResult(success=True, tokens=tokens, user=user)

        except Exception as e:
            logger.error(f"Login failed: {e}")
            return AuthResult(success=False, error=str(e))

    def login_phone_only(self, phone: str, auto_create: bool = False) -> AuthResult:
        """
        Login with phone number only (for voice agent / caller ID).

        This is a lower-security auth method intended for voice interfaces
        where the caller ID is the only available identifier.

        Args:
            phone: Phone number (from caller ID)
            auto_create: If True, create user if doesn't exist

        Returns:
            AuthResult with tokens if successful
        """
        try:
            normalized = normalize_phone(phone)
            if not normalized:
                return AuthResult(success=False, error="Invalid phone number format")

            user = self.users.get_by_phone(phone)

            if not user:
                if auto_create:
                    # Auto-create user for voice agent
                    user = self.users.create_user(phone=phone)
                    logger.info(f"Auto-created user for phone: {normalized}")
                else:
                    return AuthResult(success=False, error="User not found")

            if not user.is_active:
                return AuthResult(success=False, error="Account is deactivated")

            # Record login
            self.users.record_login(user.phone)

            # Generate tokens with phone_only auth type (limited permissions)
            access, refresh = self.jwt.create_token_pair(
                user_id=user.user_id,
                phone=user.phone,
                auth_type="phone_only"
            )

            tokens = AuthTokens(access_token=access, refresh_token=refresh)

            logger.info(f"Phone-only login: {user.phone}")
            return AuthResult(success=True, tokens=tokens, user=user)

        except Exception as e:
            logger.error(f"Phone login failed: {e}")
            return AuthResult(success=False, error=str(e))

    def refresh_token(self, refresh_token: str) -> AuthResult:
        """
        Refresh an access token.

        Args:
            refresh_token: Valid refresh token

        Returns:
            AuthResult with new access token if successful
        """
        try:
            # Verify refresh token
            payload = self.jwt.verify_token(refresh_token)
            if not payload:
                return AuthResult(success=False, error="Invalid or expired refresh token")

            if payload.token_type != "refresh":
                return AuthResult(success=False, error="Invalid token type")

            # Get user
            user = self.users.get_by_id(payload.user_id)
            if not user:
                return AuthResult(success=False, error="User not found")

            if not user.is_active:
                return AuthResult(success=False, error="Account is deactivated")

            # Generate new access token
            access = self.jwt.create_access_token(
                user_id=user.user_id,
                phone=user.phone,
                auth_type=payload.auth_type
            )

            tokens = AuthTokens(
                access_token=access,
                refresh_token=refresh_token  # Return same refresh token
            )

            return AuthResult(success=True, tokens=tokens, user=user)

        except Exception as e:
            logger.error(f"Token refresh failed: {e}")
            return AuthResult(success=False, error=str(e))

    def verify_access_token(self, access_token: str) -> Optional[TokenPayload]:
        """
        Verify an access token.

        Args:
            access_token: Token to verify

        Returns:
            TokenPayload if valid, None otherwise
        """
        payload = self.jwt.verify_token(access_token)
        if payload and payload.token_type == "access":
            return payload
        return None

    def get_current_user(self, access_token: str) -> Optional[User]:
        """
        Get the user associated with an access token.

        Args:
            access_token: Valid access token

        Returns:
            User if token is valid, None otherwise
        """
        payload = self.verify_access_token(access_token)
        if payload:
            return self.users.get_by_id(payload.user_id)
        return None

    def change_password(
        self,
        phone: str,
        current_password: str,
        new_password: str
    ) -> AuthResult:
        """
        Change a user's password.

        Args:
            phone: User's phone number
            current_password: Current password for verification
            new_password: New password to set

        Returns:
            AuthResult indicating success or failure
        """
        try:
            # Verify current password
            user = self.users.verify_password(phone, current_password)
            if not user:
                return AuthResult(success=False, error="Current password is incorrect")

            # Validate new password
            if not new_password or len(new_password) < 6:
                return AuthResult(success=False, error="New password must be at least 6 characters")

            # Update password
            self.users.set_password(phone, new_password)

            logger.info(f"Password changed for: {user.phone}")
            return AuthResult(success=True, user=user)

        except Exception as e:
            logger.error(f"Password change failed: {e}")
            return AuthResult(success=False, error=str(e))

    def link_member_to_user(
        self,
        phone: str,
        member_id: int
    ) -> AuthResult:
        """
        Link a Beyond member ID to a user account.

        Args:
            phone: User's phone number
            member_id: Beyond member ID to link

        Returns:
            AuthResult with updated user
        """
        try:
            user = self.users.link_member(phone, member_id)
            logger.info(f"Linked member {member_id} to user {phone}")
            return AuthResult(success=True, user=user)

        except ValueError as e:
            return AuthResult(success=False, error=str(e))

    def get_user_by_phone(self, phone: str) -> Optional[User]:
        """
        Get a user by phone number.

        Args:
            phone: Phone number

        Returns:
            User if found, None otherwise
        """
        return self.users.get_by_phone(phone)

    def user_exists(self, phone: str) -> bool:
        """
        Check if a user exists.

        Args:
            phone: Phone number

        Returns:
            True if user exists
        """
        return self.users.user_exists(phone)
