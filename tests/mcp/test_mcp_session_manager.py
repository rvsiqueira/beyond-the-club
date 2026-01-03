"""
Unit tests for MCP Session Manager.

Tests session creation, validation, expiration, and cleanup.
"""

import pytest
import time
import os
from unittest.mock import patch, MagicMock

# Ensure environment is set before importing MCP modules
os.environ["MCP_API_KEY"] = "test_mcp_api_key_for_testing_only"


class TestSessionManager:
    """Tests for MCP SessionManager class."""

    @pytest.fixture
    def session_manager(self):
        """Create a SessionManager instance for testing."""
        from mcp_btc.auth import SessionManager
        return SessionManager()

    @pytest.mark.unit
    def test_create_session(self, session_manager):
        """Test creating a new session."""
        session = session_manager.create_session(
            caller_id="+5511999999999",
            user_name="Test User",
            has_beyond_token=True,
            member_ids=[12345]
        )

        assert session is not None
        assert session.token.startswith("sess_")
        assert session.caller_id == "+5511999999999"
        assert session.user_name == "Test User"
        assert session.has_beyond_token is True
        assert 12345 in session.member_ids

    @pytest.mark.unit
    def test_get_session(self, session_manager):
        """Test getting a session by token."""
        session = session_manager.create_session(
            caller_id="+5511999999999",
            user_name="Test User"
        )

        retrieved = session_manager.get_session(session.token)

        assert retrieved is not None
        assert retrieved.caller_id == "+5511999999999"

    @pytest.mark.unit
    def test_get_session_invalid_token(self, session_manager):
        """Test getting a session with invalid token."""
        result = session_manager.get_session("invalid_token")
        assert result is None

    @pytest.mark.unit
    def test_invalidate_session(self, session_manager):
        """Test invalidating a session."""
        session = session_manager.create_session(
            caller_id="+5511999999999"
        )

        # Invalidate
        result = session_manager.invalidate_session(session.token)
        assert result is True

        # Should no longer be retrievable
        retrieved = session_manager.get_session(session.token)
        assert retrieved is None

    @pytest.mark.unit
    def test_invalidate_nonexistent_session(self, session_manager):
        """Test invalidating a session that doesn't exist."""
        result = session_manager.invalidate_session("nonexistent_token")
        assert result is False

    @pytest.mark.unit
    def test_get_active_sessions_count(self, session_manager):
        """Test counting active sessions."""
        initial_count = session_manager.get_active_sessions_count()

        session_manager.create_session(caller_id="+5511111111111")
        session_manager.create_session(caller_id="+5511222222222")

        assert session_manager.get_active_sessions_count() == initial_count + 2

    @pytest.mark.unit
    def test_api_key_validation(self, session_manager):
        """Test API key validation."""
        # With configured API key
        assert session_manager.validate_api_key("test_mcp_api_key_for_testing_only") is True
        assert session_manager.validate_api_key("wrong_key") is False
        assert session_manager.validate_api_key(None) is False
        assert session_manager.validate_api_key("") is False

    @pytest.mark.unit
    def test_session_without_api_key(self):
        """Test manager without API key (dev mode)."""
        from mcp_btc.auth import SessionManager

        # Temporarily remove API key
        original_key = os.environ.get("MCP_API_KEY")
        os.environ.pop("MCP_API_KEY", None)

        try:
            dev_manager = SessionManager()
            # Should allow any API key in dev mode
            assert dev_manager.validate_api_key(None) is True
            assert dev_manager.validate_api_key("anything") is True
        finally:
            # Restore API key
            if original_key:
                os.environ["MCP_API_KEY"] = original_key

    @pytest.mark.unit
    def test_session_token_uniqueness(self, session_manager):
        """Test that session tokens are unique."""
        tokens = set()
        for _ in range(50):
            session = session_manager.create_session(caller_id="+5511999999999")
            assert session.token not in tokens
            tokens.add(session.token)

    @pytest.mark.unit
    def test_session_has_expiry(self, session_manager):
        """Test session has expiry time set."""
        session = session_manager.create_session(caller_id="+5511999999999")

        # Session should have expiry in the future
        assert session.expires_at > session.created_at
        assert session.expires_at > time.time()


class TestGetSessionManager:
    """Tests for get_session_manager singleton."""

    @pytest.mark.unit
    def test_get_session_manager_returns_same_instance(self):
        """Test that get_session_manager returns singleton."""
        from mcp_btc.auth import get_session_manager

        manager1 = get_session_manager()
        manager2 = get_session_manager()

        assert manager1 is manager2

    @pytest.mark.unit
    def test_validate_session_token_with_singleton(self):
        """Test validate_session_token uses singleton manager."""
        from mcp_btc.auth import get_session_manager, validate_session_token

        # Create session using singleton manager
        manager = get_session_manager()
        session = manager.create_session(
            caller_id="+5511999999999",
            user_name="Test User"
        )

        # Validate using module-level function
        validated = validate_session_token(session.token)

        assert validated is not None
        assert validated.caller_id == "+5511999999999"

    @pytest.mark.unit
    def test_validate_session_token_invalid(self):
        """Test validate_session_token returns None for invalid token."""
        from mcp_btc.auth import validate_session_token

        result = validate_session_token("invalid_token_12345")
        assert result is None


class TestAuthenticateRequest:
    """Tests for the authenticate_request function."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_authenticate_invalid_api_key(self):
        """Test authentication with invalid API key."""
        from mcp_btc.auth import authenticate_request

        success, message, session = await authenticate_request(
            api_key="invalid_key",
            caller_id="+5511999999999"
        )

        assert success is False
        assert "Invalid API key" in message
        assert session is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_authenticate_valid_api_key_returns_session(self):
        """Test authentication with valid API key creates session."""
        from mcp_btc.auth import authenticate_request, get_session_manager

        # Get initial session count
        manager = get_session_manager()
        initial_count = manager.get_active_sessions_count()

        success, message, session = await authenticate_request(
            api_key="test_mcp_api_key_for_testing_only",
            caller_id="+5511999999999"
        )

        assert success is True
        assert session is not None
        assert session.caller_id == "+5511999999999"
        assert manager.get_active_sessions_count() > initial_count
