"""
Integration tests for MCP Server authentication.

Tests session creation, validation, and SSE authentication.
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


class TestMCPHealth:
    """Tests for MCP health endpoint."""

    @pytest.mark.mcp
    def test_health_endpoint(self, mcp_client):
        """Test MCP health check."""
        response = mcp_client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "mcp-server"
        assert "active_sessions" in data


class TestMCPSessionCreation:
    """Tests for MCP session creation."""

    @pytest.mark.mcp
    def test_create_session_without_api_key(self, mcp_client):
        """Test session creation without API key fails."""
        response = mcp_client.post(
            "/auth/session",
            json={"caller_id": "+5511999999999"}
        )

        # When MCP_API_KEY is set, should return 401
        assert response.status_code == 401
        data = response.json()
        assert "error" in data

    @pytest.mark.mcp
    def test_create_session_without_caller_id(self, mcp_client, test_config):
        """Test session creation without caller_id fails."""
        response = mcp_client.post(
            "/auth/session",
            headers={"X-API-Key": test_config["mcp_api_key"]},
            json={}
        )

        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "caller_id is required"

    @pytest.mark.mcp
    def test_create_session_invalid_api_key(self, mcp_client):
        """Test session creation with invalid API key."""
        response = mcp_client.post(
            "/auth/session",
            headers={"X-API-Key": "wrong_api_key"},
            json={"caller_id": "+5511999999999"}
        )

        assert response.status_code == 401
        data = response.json()
        assert "Invalid API key" in data["error"]

    @pytest.mark.mcp
    def test_create_session_success(self, mcp_client, test_config):
        """Test successful session creation."""
        # Mock the authenticate_request function
        with patch("mcp_btc.sse_server.authenticate_request") as mock_auth:
            mock_session = MagicMock()
            mock_session.token = "sess_test_token_12345"
            mock_session.expires_at = 9999999999
            mock_session.created_at = 9999999399
            mock_session.caller_id = "+5511999999999"
            mock_session.user_name = "Test User"
            mock_session.has_beyond_token = True
            mock_session.member_ids = [12345]

            mock_auth.return_value = (True, "Success", mock_session)

            response = mcp_client.post(
                "/auth/session",
                headers={"X-API-Key": test_config["mcp_api_key"]},
                json={"caller_id": "+5511999999999"}
            )

        assert response.status_code == 200
        data = response.json()
        assert "session_token" in data
        assert data["session_token"].startswith("sess_")
        assert data["expires_in"] == 600
        assert data["user"]["phone"] == "+5511999999999"

    @pytest.mark.mcp
    def test_create_session_new_user(self, mcp_client, test_config):
        """Test session creation for new user (auto-created)."""
        with patch("mcp_btc.sse_server.authenticate_request") as mock_auth:
            mock_session = MagicMock()
            mock_session.token = "sess_new_user_token"
            mock_session.expires_at = 9999999999
            mock_session.created_at = 9999999399
            mock_session.caller_id = "+5511888888888"
            mock_session.user_name = None  # New user, no name
            mock_session.has_beyond_token = False
            mock_session.member_ids = []

            mock_auth.return_value = (True, "User created", mock_session)

            response = mcp_client.post(
                "/auth/session",
                headers={"X-API-Key": test_config["mcp_api_key"]},
                json={"caller_id": "+5511888888888"}
            )

        assert response.status_code == 200
        data = response.json()
        assert data["user"]["has_beyond_token"] is False
        assert data["user"]["member_ids"] == []


class TestMCPSessionValidation:
    """Tests for MCP session validation."""

    @pytest.mark.mcp
    def test_validate_session_no_token(self, mcp_client):
        """Test validation without token."""
        response = mcp_client.get("/auth/validate")

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        assert "Missing Bearer token" in data["error"]

    @pytest.mark.mcp
    def test_validate_session_invalid_token(self, mcp_client):
        """Test validation with invalid token."""
        with patch("mcp_btc.sse_server.validate_session_token") as mock_validate:
            mock_validate.return_value = None

            response = mcp_client.get(
                "/auth/validate",
                headers={"Authorization": "Bearer invalid_token"}
            )

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False

    @pytest.mark.mcp
    def test_validate_session_valid_token(self, mcp_client):
        """Test validation with valid token."""
        with patch("mcp_btc.sse_server.validate_session_token") as mock_validate:
            mock_session = MagicMock()
            mock_session.caller_id = "+5511999999999"
            mock_session.user_name = "Test User"
            mock_session.has_beyond_token = True
            mock_session.member_ids = [12345]
            mock_session.expires_at = 9999999999

            mock_validate.return_value = mock_session

            response = mcp_client.get(
                "/auth/validate",
                headers={"Authorization": "Bearer sess_valid_token"}
            )

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert data["user"]["phone"] == "+5511999999999"


class TestMCPSessionLogout:
    """Tests for MCP session logout."""

    @pytest.mark.mcp
    def test_logout_no_token(self, mcp_client):
        """Test logout without token."""
        response = mcp_client.post("/auth/logout")

        assert response.status_code == 401

    @pytest.mark.mcp
    def test_logout_success(self, mcp_client):
        """Test successful logout."""
        with patch("mcp_btc.sse_server.get_session_manager") as mock_manager:
            mock_manager.return_value.invalidate_session.return_value = True

            response = mcp_client.post(
                "/auth/logout",
                headers={"Authorization": "Bearer sess_valid_token"}
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestMCPSSEAuthentication:
    """Tests for MCP SSE endpoint authentication."""

    @pytest.mark.mcp
    def test_sse_no_auth_with_api_key_configured(self, mcp_client):
        """Test SSE access without auth when API key is configured."""
        with patch("mcp_btc.sse_server.get_session_manager") as mock_manager:
            mock_manager.return_value._api_key = "configured_key"

            response = mcp_client.get("/sse")

        assert response.status_code == 401
        data = response.json()
        assert "Authorization required" in data["error"]

    @pytest.mark.mcp
    def test_sse_invalid_token(self, mcp_client):
        """Test SSE access with invalid token."""
        with patch("mcp_btc.sse_server.validate_session_token") as mock_validate:
            mock_validate.return_value = None

            response = mcp_client.get(
                "/sse",
                headers={"Authorization": "Bearer invalid_token"}
            )

        assert response.status_code == 401
        data = response.json()
        assert "Invalid or expired" in data["error"]


class TestMCPMessagesAuthentication:
    """Tests for MCP messages endpoint authentication."""

    @pytest.mark.mcp
    def test_messages_no_auth(self, mcp_client):
        """Test messages endpoint without auth."""
        with patch("mcp_btc.sse_server.get_session_manager") as mock_manager:
            mock_manager.return_value._api_key = "configured_key"

            response = mcp_client.post(
                "/messages/",
                json={"method": "test"}
            )

        assert response.status_code == 401

    @pytest.mark.mcp
    def test_messages_invalid_token(self, mcp_client):
        """Test messages endpoint with invalid token."""
        with patch("mcp_btc.sse_server.validate_session_token") as mock_validate:
            mock_validate.return_value = None

            response = mcp_client.post(
                "/messages/",
                headers={"Authorization": "Bearer invalid_token"},
                json={"method": "test"}
            )

        assert response.status_code == 401
