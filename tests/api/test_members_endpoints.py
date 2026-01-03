"""
Integration tests for Members API endpoints.

Tests member listing, preferences, and graph operations.
"""

import pytest
from unittest.mock import patch, MagicMock
from dataclasses import dataclass

from src.auth import User


@dataclass
class MockSession:
    """Mock session preference for testing."""
    level: str
    wave_side: str
    attributes: dict = None

    def __post_init__(self):
        if self.attributes is None:
            self.attributes = {}

    def get_combo_key(self) -> str:
        return f"{self.level}|{self.wave_side}"


@dataclass
class MockMemberPreferences:
    """Mock member preferences for testing."""
    sessions: list
    target_hours: list
    target_dates: list


class TestMembersList:
    """Tests for member listing endpoints."""

    @pytest.mark.api
    def test_list_members_cached(self, api_client, mock_services, mock_members, jwt_handler, test_config):
        """Test listing members from cache."""
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
        mock_services.members.get_members.return_value = mock_members
        mock_services.bookings.get_active_bookings.return_value = []

        with patch("api.deps.get_services", return_value=mock_services):
            response = api_client.get(
                "/api/v1/members",
                headers={"Authorization": f"Bearer {token}"}
            )

        assert response.status_code == 200
        data = response.json()
        assert len(data["members"]) == 2
        assert data["members"][0]["name"] == "Rafael Test"

    @pytest.mark.api
    def test_list_members_with_refresh(self, api_client, mock_services, mock_members, jwt_handler, test_config):
        """Test listing members with force refresh."""
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
        mock_services.members.get_members.return_value = mock_members
        mock_services.bookings.get_active_bookings.return_value = []
        mock_services.beyond_tokens.get_valid_id_token.return_value = "valid_token"
        mock_services.beyond_tokens.get_token.return_value = MagicMock(
            id_token="valid_token",
            refresh_token="refresh",
            expires_at=9999999999
        )

        with patch("api.deps.get_services", return_value=mock_services):
            response = api_client.get(
                "/api/v1/members?refresh=true",
                headers={"Authorization": f"Bearer {token}"}
            )

        assert response.status_code == 200

    @pytest.mark.api
    def test_list_members_unauthorized(self, api_client, mock_services):
        """Test listing members without auth."""
        with patch("api.deps.get_services", return_value=mock_services):
            response = api_client.get("/api/v1/members")

        assert response.status_code == 401


class TestMemberDetails:
    """Tests for member detail endpoints."""

    @pytest.mark.api
    def test_get_member_by_id(self, api_client, mock_services, mock_members, jwt_handler, test_config):
        """Test getting specific member."""
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
        mock_services.members.get_member_by_id.return_value = mock_members[0]
        mock_services.bookings.has_active_booking.return_value = False

        with patch("api.deps.get_services", return_value=mock_services):
            response = api_client.get(
                "/api/v1/members/12345",
                headers={"Authorization": f"Bearer {token}"}
            )

        assert response.status_code == 200
        data = response.json()
        assert data["member_id"] == 12345
        assert data["name"] == "Rafael Test"

    @pytest.mark.api
    def test_get_member_not_found(self, api_client, mock_services, jwt_handler, test_config):
        """Test getting non-existent member."""
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
        mock_services.members.get_member_by_id.return_value = None

        with patch("api.deps.get_services", return_value=mock_services):
            response = api_client.get(
                "/api/v1/members/99999",
                headers={"Authorization": f"Bearer {token}"}
            )

        assert response.status_code == 404


class TestMemberPreferences:
    """Tests for member preferences endpoints."""

    @pytest.mark.api
    def test_get_preferences(self, api_client, mock_services, jwt_handler, test_config):
        """Test getting member preferences."""
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
        mock_services.members.get_member_preferences.return_value = MockMemberPreferences(
            sessions=[MockSession(level="Intermediario2", wave_side="Lado_direito")],
            target_hours=["08:00", "10:00"],
            target_dates=["2026-01-10"]
        )

        with patch("api.deps.get_services", return_value=mock_services):
            response = api_client.get(
                "/api/v1/members/12345/preferences",
                headers={"Authorization": f"Bearer {token}"}
            )

        assert response.status_code == 200
        data = response.json()
        assert data["preferences"] is not None
        assert len(data["preferences"]["sessions"]) == 1
        assert "08:00" in data["preferences"]["target_hours"]

    @pytest.mark.api
    def test_get_preferences_not_set(self, api_client, mock_services, jwt_handler, test_config):
        """Test getting preferences when not set."""
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
        mock_services.members.get_member_preferences.return_value = None

        with patch("api.deps.get_services", return_value=mock_services):
            response = api_client.get(
                "/api/v1/members/12345/preferences",
                headers={"Authorization": f"Bearer {token}"}
            )

        # API returns 200 with preferences=None when not set
        assert response.status_code == 200
        data = response.json()
        assert data["preferences"] is None

    @pytest.mark.api
    def test_set_preferences(self, api_client, mock_services, jwt_handler, test_config):
        """Test setting member preferences."""
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
            response = api_client.put(
                "/api/v1/members/12345/preferences",
                json={
                    "sessions": [
                        {"level": "Avançado1", "wave_side": "Lado_esquerdo"}
                    ],
                    "target_hours": ["08:00", "10:00"],
                    "target_dates": []
                },
                headers={"Authorization": f"Bearer {token}"}
            )

        assert response.status_code == 200
        mock_services.members.set_member_preferences.assert_called_once()
        mock_services.graph.sync_member_preference.assert_called_once()

    @pytest.mark.api
    def test_delete_preferences(self, api_client, mock_services, jwt_handler, test_config):
        """Test deleting member preferences."""
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
            response = api_client.delete(
                "/api/v1/members/12345/preferences",
                headers={"Authorization": f"Bearer {token}"}
            )

        assert response.status_code == 200
        mock_services.members.clear_member_preferences.assert_called_once()


class TestMemberGraph:
    """Tests for member graph endpoints."""

    @pytest.mark.api
    def test_get_graph_summary(self, api_client, mock_services, jwt_handler, test_config):
        """Test getting member graph summary."""
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
        mock_services.graph.get_member_summary.return_value = {
            "member_id": 12345,
            "bookings": [],
            "preferences": [],
            "similar_members": []
        }

        with patch("api.deps.get_services", return_value=mock_services):
            response = api_client.get(
                "/api/v1/members/12345/graph-summary",
                headers={"Authorization": f"Bearer {token}"}
            )

        assert response.status_code == 200
        data = response.json()
        assert data["member_id"] == 12345
