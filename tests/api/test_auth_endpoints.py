"""
Integration tests for Auth API endpoints.

Tests registration, login, token refresh, and user management.
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from src.auth import User
from src.services.user_auth_service import AuthResult, AuthTokens


class TestAuthRegistration:
    """Tests for user registration endpoints."""

    @pytest.mark.api
    def test_register_success(self, api_client, mock_services):
        """Test successful user registration."""
        mock_services.user_auth.register.return_value = AuthResult(
            success=True,
            tokens=AuthTokens(
                access_token="test_access_token",
                refresh_token="test_refresh_token"
            ),
            user=User(
                user_id="new-user-id",
                phone="+5511999999999",
                name="New User",
                password_hash="hashed",
                member_ids=[],
                is_active=True
            )
        )

        with patch("api.deps.get_services", return_value=mock_services):
            response = api_client.post(
                "/api/v1/auth/register",
                json={
                    "phone": "+5511999999999",
                    "password": "SecurePassword123!",
                    "name": "New User"
                }
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["tokens"]["access_token"] is not None
        assert data["user"]["phone"] == "+5511999999999"

    @pytest.mark.api
    def test_register_duplicate_phone(self, api_client, mock_services):
        """Test registration with existing phone fails."""
        mock_services.user_auth.register.return_value = AuthResult(
            success=False,
            error="Phone already registered"
        )

        with patch("api.deps.get_services", return_value=mock_services):
            response = api_client.post(
                "/api/v1/auth/register",
                json={
                    "phone": "+5511999999999",
                    "password": "SecurePassword123!",
                    "name": "New User"
                }
            )

        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()

    @pytest.mark.api
    def test_register_invalid_phone(self, api_client, mock_services):
        """Test registration with invalid phone format."""
        mock_services.user_auth.register.return_value = AuthResult(
            success=False,
            error="Invalid phone format"
        )

        with patch("api.deps.get_services", return_value=mock_services):
            response = api_client.post(
                "/api/v1/auth/register",
                json={
                    "phone": "invalid",
                    "password": "SecurePassword123!",
                    "name": "New User"
                }
            )

        assert response.status_code == 400


class TestAuthLogin:
    """Tests for login endpoints."""

    @pytest.mark.api
    def test_login_password_success(self, api_client, mock_services):
        """Test successful password login."""
        mock_services.user_auth.login_password.return_value = AuthResult(
            success=True,
            tokens=AuthTokens(
                access_token="test_access_token",
                refresh_token="test_refresh_token"
            ),
            user=User(
                user_id="user-id",
                phone="+5511999999999",
                name="Test User",
                password_hash="hashed",
                member_ids=[],
                is_active=True
            )
        )

        with patch("api.deps.get_services", return_value=mock_services):
            response = api_client.post(
                "/api/v1/auth/login",
                json={
                    "phone": "+5511999999999",
                    "password": "CorrectPassword"
                }
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["tokens"]["access_token"] is not None

    @pytest.mark.api
    def test_login_password_wrong_password(self, api_client, mock_services):
        """Test login with wrong password."""
        mock_services.user_auth.login_password.return_value = AuthResult(
            success=False,
            error="Invalid phone or password"
        )

        with patch("api.deps.get_services", return_value=mock_services):
            response = api_client.post(
                "/api/v1/auth/login",
                json={
                    "phone": "+5511999999999",
                    "password": "WrongPassword"
                }
            )

        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower()

    @pytest.mark.api
    def test_login_phone_only_success(self, api_client, mock_services):
        """Test phone-only login for voice agents."""
        mock_services.user_auth.login_phone_only.return_value = AuthResult(
            success=True,
            tokens=AuthTokens(
                access_token="test_access_token",
                refresh_token="test_refresh_token"
            ),
            user=User(
                user_id="user-id",
                phone="+5511999999999",
                name="Test User",
                password_hash=None,
                member_ids=[],
                is_active=True
            )
        )

        with patch("api.deps.get_services", return_value=mock_services):
            response = api_client.post(
                "/api/v1/auth/login/phone",
                json={
                    "phone": "+5511999999999",
                    "auto_create": False
                }
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @pytest.mark.api
    def test_login_phone_only_auto_create(self, api_client, mock_services):
        """Test phone-only login with auto-create."""
        mock_services.user_auth.login_phone_only.return_value = AuthResult(
            success=True,
            tokens=AuthTokens(
                access_token="test_access_token",
                refresh_token="test_refresh_token"
            ),
            user=User(
                user_id="new-user-id",
                phone="+5511888888888",
                name="New User",
                password_hash=None,
                member_ids=[],
                is_active=True
            )
        )

        with patch("api.deps.get_services", return_value=mock_services):
            response = api_client.post(
                "/api/v1/auth/login/phone",
                json={
                    "phone": "+5511888888888",
                    "auto_create": True
                }
            )

        assert response.status_code == 200
        mock_services.graph.sync_user.assert_called_once()


class TestTokenRefresh:
    """Tests for token refresh endpoint."""

    @pytest.mark.api
    def test_refresh_token_success(self, api_client, mock_services):
        """Test successful token refresh."""
        mock_services.user_auth.refresh_token.return_value = AuthResult(
            success=True,
            tokens=AuthTokens(
                access_token="new_access_token",
                refresh_token="new_refresh_token"
            )
        )

        with patch("api.deps.get_services", return_value=mock_services):
            response = api_client.post(
                "/api/v1/auth/refresh",
                json={"refresh_token": "valid_refresh_token"}
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["tokens"]["access_token"] == "new_access_token"

    @pytest.mark.api
    def test_refresh_token_expired(self, api_client, mock_services):
        """Test refresh with expired token."""
        mock_services.user_auth.refresh_token.return_value = AuthResult(
            success=False,
            error="Token expired"
        )

        with patch("api.deps.get_services", return_value=mock_services):
            response = api_client.post(
                "/api/v1/auth/refresh",
                json={"refresh_token": "expired_token"}
            )

        assert response.status_code == 401


class TestCurrentUser:
    """Tests for current user endpoint."""

    @pytest.mark.api
    def test_get_me_authenticated(self, api_client, mock_services, jwt_handler, test_config):
        """Test getting current user info."""
        # Create a real token
        token = jwt_handler.create_access_token(
            user_id="user-123",
            phone=test_config["test_phone"],
            auth_type="password"
        )

        mock_services.jwt.verify_token.return_value = MagicMock(
            user_id="user-123",
            phone=test_config["test_phone"],
            token_type="access"
        )
        mock_services.users.get_by_id.return_value = User(
            user_id="user-123",
            phone=test_config["test_phone"],
            name="Test User",
            password_hash="hashed",
            member_ids=[12345],
            is_active=True
        )

        with patch("api.deps.get_services", return_value=mock_services):
            response = api_client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {token}"}
            )

        assert response.status_code == 200
        data = response.json()
        assert data["phone"] == test_config["test_phone"]
        assert data["name"] == "Test User"

    @pytest.mark.api
    def test_get_me_no_token(self, api_client, mock_services):
        """Test accessing /me without token."""
        with patch("api.deps.get_services", return_value=mock_services):
            response = api_client.get("/api/v1/auth/me")

        assert response.status_code == 401

    @pytest.mark.api
    def test_get_me_invalid_token(self, api_client, mock_services):
        """Test accessing /me with invalid token."""
        mock_services.jwt.verify_token.return_value = None

        with patch("api.deps.get_services", return_value=mock_services):
            response = api_client.get(
                "/api/v1/auth/me",
                headers={"Authorization": "Bearer invalid_token"}
            )

        assert response.status_code == 401


class TestMemberLinking:
    """Tests for member linking endpoints."""

    @pytest.mark.api
    def test_link_member_success(self, api_client, mock_services, jwt_handler, test_config):
        """Test linking member to user."""
        token = jwt_handler.create_access_token(
            user_id="user-123",
            phone=test_config["test_phone"],
            auth_type="password"
        )

        mock_services.jwt.verify_token.return_value = MagicMock(
            user_id="user-123",
            phone=test_config["test_phone"],
            token_type="access"
        )
        mock_services.users.get_by_id.return_value = User(
            user_id="user-123",
            phone=test_config["test_phone"],
            name="Test User",
            password_hash="hashed",
            member_ids=[],
            is_active=True
        )
        mock_services.user_auth.link_member_to_user.return_value = AuthResult(
            success=True,
            user=User(
                user_id="user-123",
                phone=test_config["test_phone"],
                name="Test User",
                password_hash="hashed",
                member_ids=[12345],
                is_active=True
            )
        )

        with patch("api.deps.get_services", return_value=mock_services):
            response = api_client.post(
                "/api/v1/auth/link-member/12345",
                headers={"Authorization": f"Bearer {token}"}
            )

        assert response.status_code == 200
        mock_services.graph.link_user_to_member.assert_called_once()


class TestBeyondAuth:
    """Tests for Beyond API authentication endpoints."""

    @pytest.mark.api
    def test_request_sms(self, api_client, mock_services, jwt_handler, test_config):
        """Test requesting SMS verification."""
        token = jwt_handler.create_access_token(
            user_id="user-123",
            phone=test_config["test_phone"],
            auth_type="password"
        )

        mock_services.jwt.verify_token.return_value = MagicMock(
            user_id="user-123",
            phone=test_config["test_phone"],
            token_type="access"
        )
        mock_services.users.get_by_id.return_value = User(
            user_id="user-123",
            phone=test_config["test_phone"],
            name="Test User",
            password_hash="hashed",
            member_ids=[],
            is_active=True
        )
        mock_services.beyond_tokens.request_sms.return_value = "session_info_data"

        with patch("api.deps.get_services", return_value=mock_services):
            response = api_client.post(
                "/api/v1/auth/beyond/request-sms",
                json={"phone": "+5511999999999"},
                headers={"Authorization": f"Bearer {token}"}
            )

        assert response.status_code == 200
        data = response.json()
        assert "session_info" in data

    @pytest.mark.api
    def test_verify_sms(self, api_client, mock_services, jwt_handler, test_config):
        """Test verifying SMS code."""
        token = jwt_handler.create_access_token(
            user_id="user-123",
            phone=test_config["test_phone"],
            auth_type="password"
        )

        mock_services.jwt.verify_token.return_value = MagicMock(
            user_id="user-123",
            phone=test_config["test_phone"],
            token_type="access"
        )
        mock_services.users.get_by_id.return_value = User(
            user_id="user-123",
            phone=test_config["test_phone"],
            name="Test User",
            password_hash="hashed",
            member_ids=[],
            is_active=True
        )
        # Mock tokens returned from verify_sms
        mock_tokens = MagicMock()
        mock_tokens.id_token = "mock_id_token"
        mock_tokens.refresh_token = "mock_refresh_token"
        mock_services.beyond_tokens.verify_sms.return_value = mock_tokens
        mock_services.auth.initialize_with_tokens.return_value = True
        mock_services.members.set_current_user.return_value = None

        with patch("api.deps.get_services", return_value=mock_services):
            response = api_client.post(
                "/api/v1/auth/beyond/verify-sms",
                json={
                    "phone": "+5511999999999",
                    "code": "123456",
                    "session_info": "session_data"
                },
                headers={"Authorization": f"Bearer {token}"}
            )

        assert response.status_code == 200

    @pytest.mark.api
    def test_beyond_status(self, api_client, mock_services, jwt_handler, test_config):
        """Test checking Beyond API status."""
        token = jwt_handler.create_access_token(
            user_id="user-123",
            phone=test_config["test_phone"],
            auth_type="password"
        )

        mock_services.jwt.verify_token.return_value = MagicMock(
            user_id="user-123",
            phone=test_config["test_phone"],
            token_type="access"
        )
        mock_services.users.get_by_id.return_value = User(
            user_id="user-123",
            phone=test_config["test_phone"],
            name="Test User",
            password_hash="hashed",
            member_ids=[],
            is_active=True
        )
        mock_services.beyond_tokens.get_valid_id_token.return_value = "mock_id_token"
        mock_token = MagicMock()
        mock_token.expires_at = 9999999999
        mock_services.beyond_tokens.get_token.return_value = mock_token

        with patch("api.deps.get_services", return_value=mock_services):
            response = api_client.get(
                "/api/v1/auth/beyond/status",
                headers={"Authorization": f"Bearer {token}"}
            )

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
