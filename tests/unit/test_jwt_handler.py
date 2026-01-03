"""
Unit tests for JWT Handler.

Tests token creation, validation, refresh, and expiration.
"""

import pytest
import time

from src.auth import JWTHandler
from src.auth.jwt_handler import TokenPayload


class TestJWTHandler:
    """Tests for JWTHandler class."""

    @pytest.mark.unit
    def test_create_access_token(self, jwt_handler, test_config):
        """Test creating an access token."""
        token = jwt_handler.create_access_token(
            user_id="user-123",
            phone=test_config["test_phone"],
            auth_type="password"
        )

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 50  # JWT tokens are long

    @pytest.mark.unit
    def test_create_refresh_token(self, jwt_handler, test_config):
        """Test creating a refresh token."""
        token = jwt_handler.create_refresh_token(
            user_id="user-123",
            phone=test_config["test_phone"],
            auth_type="password"
        )

        assert token is not None
        assert isinstance(token, str)

    @pytest.mark.unit
    def test_create_token_pair(self, jwt_handler, test_config):
        """Test creating token pair."""
        access_token, refresh_token = jwt_handler.create_token_pair(
            user_id="user-123",
            phone=test_config["test_phone"],
            auth_type="password"
        )

        assert access_token is not None
        assert refresh_token is not None
        assert isinstance(access_token, str)
        assert isinstance(refresh_token, str)

    @pytest.mark.unit
    def test_verify_valid_access_token(self, jwt_handler, valid_access_token):
        """Test verifying a valid access token."""
        payload = jwt_handler.verify_token(valid_access_token)

        assert payload is not None
        assert payload.user_id == "test-user-id-123"
        assert payload.token_type == "access"

    @pytest.mark.unit
    def test_verify_valid_refresh_token(self, jwt_handler, valid_refresh_token):
        """Test verifying a valid refresh token."""
        payload = jwt_handler.verify_token(valid_refresh_token)

        assert payload is not None
        assert payload.user_id == "test-user-id-123"
        assert payload.token_type == "refresh"

    @pytest.mark.unit
    def test_verify_expired_token(self, jwt_handler, expired_token):
        """Test that expired tokens are rejected."""
        payload = jwt_handler.verify_token(expired_token)
        assert payload is None

    @pytest.mark.unit
    def test_verify_invalid_token(self, jwt_handler):
        """Test that invalid tokens are rejected."""
        payload = jwt_handler.verify_token("invalid.token.here")
        assert payload is None

    @pytest.mark.unit
    def test_verify_tampered_token(self, jwt_handler, valid_access_token):
        """Test that tampered tokens are rejected."""
        # Modify the token signature
        parts = valid_access_token.split('.')
        parts[-1] = parts[-1][:-5] + "xxxxx"  # Tamper with signature
        tampered = '.'.join(parts)

        payload = jwt_handler.verify_token(tampered)
        assert payload is None

    @pytest.mark.unit
    def test_verify_wrong_secret(self, valid_access_token):
        """Test token verified with wrong secret fails."""
        other_handler = JWTHandler(secret_key="different_secret_key")
        payload = other_handler.verify_token(valid_access_token)
        assert payload is None

    @pytest.mark.unit
    def test_refresh_access_token(self, jwt_handler, valid_refresh_token):
        """Test refreshing an access token."""
        new_access = jwt_handler.refresh_access_token(valid_refresh_token)

        assert new_access is not None
        payload = jwt_handler.verify_token(new_access)
        assert payload is not None
        assert payload.token_type == "access"

    @pytest.mark.unit
    def test_refresh_with_access_token_fails(self, jwt_handler, valid_access_token):
        """Test that access tokens cannot be used to refresh."""
        new_access = jwt_handler.refresh_access_token(valid_access_token)
        assert new_access is None

    @pytest.mark.unit
    def test_refresh_with_expired_token_fails(self, jwt_handler, test_config):
        """Test that expired refresh tokens cannot refresh."""
        expired_refresh = jwt_handler.create_refresh_token(
            user_id="user-123",
            phone=test_config["test_phone"],
            auth_type="password",
            expires_in=-1
        )

        new_access = jwt_handler.refresh_access_token(expired_refresh)
        assert new_access is None

    @pytest.mark.unit
    def test_token_payload_contains_correct_data(self, jwt_handler, test_config):
        """Test token payload has all required fields."""
        token = jwt_handler.create_access_token(
            user_id="user-123",
            phone=test_config["test_phone"],
            auth_type="phone_only"
        )

        payload = jwt_handler.verify_token(token)

        assert payload.user_id == "user-123"
        assert payload.phone == test_config["test_phone"]
        assert payload.auth_type == "phone_only"
        assert payload.token_type == "access"
        assert payload.exp is not None
        assert payload.iat is not None

    @pytest.mark.unit
    def test_custom_expiration_time(self, jwt_handler, test_config):
        """Test custom token expiration."""
        # Create token that expires in 60 seconds
        token = jwt_handler.create_access_token(
            user_id="user-123",
            phone=test_config["test_phone"],
            auth_type="password",
            expires_in=60
        )

        payload = jwt_handler.verify_token(token)
        assert payload is not None

        # Check expiration is approximately 60 seconds from now
        now = int(time.time())
        assert 55 <= (payload.exp - now) <= 65

    @pytest.mark.unit
    def test_get_token_expiry(self, jwt_handler, valid_access_token):
        """Test getting token expiry time."""
        expiry = jwt_handler.get_token_expiry(valid_access_token)

        assert expiry is not None
        assert isinstance(expiry, int)
        assert expiry > time.time()  # Expiry is in the future

    @pytest.mark.unit
    def test_is_token_expired(self, jwt_handler, valid_access_token, expired_token):
        """Test checking if token is expired."""
        assert jwt_handler.is_token_expired(valid_access_token) is False
        assert jwt_handler.is_token_expired(expired_token) is True

    @pytest.mark.unit
    def test_auth_types(self, jwt_handler, test_config):
        """Test different auth types are preserved."""
        for auth_type in ["password", "phone_only", "sms_otp"]:
            token = jwt_handler.create_access_token(
                user_id="user-123",
                phone=test_config["test_phone"],
                auth_type=auth_type
            )

            payload = jwt_handler.verify_token(token)
            assert payload.auth_type == auth_type

    @pytest.mark.unit
    def test_default_secret_warning(self, caplog):
        """Test warning is logged when using default secret."""
        import logging
        caplog.set_level(logging.WARNING)

        # Temporarily unset the env var
        import os
        original = os.environ.pop("JWT_SECRET_KEY", None)

        try:
            handler = JWTHandler()
            # Should log a warning about default key
            assert any("default" in r.message.lower() for r in caplog.records)
        finally:
            if original:
                os.environ["JWT_SECRET_KEY"] = original
