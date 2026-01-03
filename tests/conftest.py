"""
Pytest configuration and shared fixtures.

This module provides common fixtures for testing:
- JWT authentication
- User management
- Service mocking
- API and MCP clients
"""

import os
import sys
import json
import tempfile
from pathlib import Path
from typing import Generator, AsyncGenerator
from unittest.mock import MagicMock, AsyncMock, patch
from dataclasses import dataclass

import pytest
import httpx
from fastapi.testclient import TestClient

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set test environment variables before imports
os.environ["JWT_SECRET_KEY"] = "test_jwt_secret_key_for_testing_only_32bytes!"
os.environ["MCP_API_KEY"] = "test_mcp_api_key_for_testing_only"
os.environ["ENVIRONMENT"] = "test"

from src.auth import JWTHandler, UserStore, User, PasswordHandler, normalize_phone


# =============================================================================
# Configuration
# =============================================================================

@pytest.fixture(scope="session")
def test_config():
    """Test configuration values."""
    return {
        "jwt_secret": "test_jwt_secret_key_for_testing_only_32bytes!",
        "mcp_api_key": "test_mcp_api_key_for_testing_only",
        "test_phone": "+5511999999999",
        "test_password": "TestPassword123!",
        "test_user_name": "Test User",
    }


# =============================================================================
# JWT Fixtures
# =============================================================================

@pytest.fixture
def jwt_handler(test_config) -> JWTHandler:
    """Create a JWTHandler with test secret."""
    return JWTHandler(secret_key=test_config["jwt_secret"])


@pytest.fixture
def valid_access_token(jwt_handler, test_config) -> str:
    """Create a valid access token."""
    return jwt_handler.create_access_token(
        user_id="test-user-id-123",
        phone=test_config["test_phone"],
        auth_type="password"
    )


@pytest.fixture
def valid_refresh_token(jwt_handler, test_config) -> str:
    """Create a valid refresh token."""
    return jwt_handler.create_refresh_token(
        user_id="test-user-id-123",
        phone=test_config["test_phone"],
        auth_type="password"
    )


@pytest.fixture
def token_pair(jwt_handler, test_config) -> dict:
    """Create access and refresh token pair."""
    access_token, refresh_token = jwt_handler.create_token_pair(
        user_id="test-user-id-123",
        phone=test_config["test_phone"],
        auth_type="password"
    )
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": 3600
    }


@pytest.fixture
def expired_token(jwt_handler, test_config) -> str:
    """Create an expired access token."""
    return jwt_handler.create_access_token(
        user_id="test-user-id-123",
        phone=test_config["test_phone"],
        auth_type="password",
        expires_in=-1  # Already expired
    )


# =============================================================================
# User Store Fixtures
# =============================================================================

@pytest.fixture
def temp_user_file() -> Generator[Path, None, None]:
    """Create a temporary file for user storage."""
    with tempfile.NamedTemporaryFile(
        mode='w', suffix='.json', delete=False
    ) as f:
        json.dump({}, f)
        temp_path = Path(f.name)

    yield temp_path

    # Cleanup
    if temp_path.exists():
        temp_path.unlink()


@pytest.fixture
def user_store(temp_user_file) -> UserStore:
    """Create a UserStore with temporary file."""
    return UserStore(file_path=temp_user_file)


@pytest.fixture
def password_handler() -> PasswordHandler:
    """Create a PasswordHandler."""
    return PasswordHandler()


@pytest.fixture
def sample_user(user_store, test_config) -> User:
    """Create a sample user in the store."""
    user = user_store.create_user(
        phone=test_config["test_phone"],
        password=test_config["test_password"],
        name=test_config["test_user_name"]
    )
    return user


# =============================================================================
# Mock Services
# =============================================================================

@dataclass
class MockMember:
    """Mock member for testing."""
    member_id: int
    name: str
    social_name: str
    is_titular: bool
    usage: int
    limit: int


@dataclass
class MockSlot:
    """Mock availability slot for testing."""
    date: str
    interval: str
    level: str
    wave_side: str
    available: int
    max_quantity: int
    package_id: str
    product_id: str

    @property
    def combo_key(self) -> str:
        return f"{self.level}|{self.wave_side}"


@pytest.fixture
def mock_members() -> list:
    """Sample members for testing."""
    return [
        MockMember(
            member_id=12345,
            name="Rafael Test",
            social_name="Rafael",
            is_titular=True,
            usage=2,
            limit=10
        ),
        MockMember(
            member_id=12346,
            name="Julia Test",
            social_name="Julia",
            is_titular=False,
            usage=1,
            limit=10
        )
    ]


@pytest.fixture
def mock_slots() -> list:
    """Sample availability slots for testing."""
    return [
        MockSlot(
            date="2026-01-10",
            interval="08:00",
            level="Intermediario2",
            wave_side="Lado_direito",
            available=3,
            max_quantity=6,
            package_id="pkg-123",
            product_id="prod-456"
        ),
        MockSlot(
            date="2026-01-10",
            interval="10:00",
            level="Avançado1",
            wave_side="Lado_esquerdo",
            available=2,
            max_quantity=6,
            package_id="pkg-124",
            product_id="prod-457"
        )
    ]


@pytest.fixture
def mock_services(mock_members, mock_slots):
    """Create mock services container."""
    services = MagicMock()

    # Mock user auth service
    services.user_auth = MagicMock()
    services.user_auth.register = MagicMock()
    services.user_auth.login_password = MagicMock()
    services.user_auth.login_phone_only = MagicMock()
    services.user_auth.refresh_token = MagicMock()
    services.user_auth.get_user_by_phone = MagicMock(return_value=None)

    # Mock member service
    services.members = MagicMock()
    services.members.get_members = MagicMock(return_value=mock_members)
    services.members.get_member_by_id = MagicMock()
    services.members.get_member_preferences = MagicMock(return_value=None)
    services.members.set_member_preferences = MagicMock()
    services.members.set_current_user = MagicMock()

    # Mock availability service
    services.availability = MagicMock()
    services.availability.get_slots_from_cache = MagicMock(return_value=mock_slots)
    services.availability.scan_availability = MagicMock()

    # Mock booking service
    services.bookings = MagicMock()
    services.bookings.get_active_bookings = MagicMock(return_value=[])
    services.bookings.create_booking = MagicMock()
    services.bookings.cancel_booking = MagicMock()

    # Mock monitor service
    services.monitor = MagicMock()

    # Mock graph service
    services.graph = MagicMock()
    services.graph.sync_user = MagicMock()
    services.graph.sync_member = MagicMock()

    # Mock beyond tokens
    services.beyond_tokens = MagicMock()
    services.beyond_tokens.get_valid_id_token = MagicMock(return_value="mock_token")
    services.beyond_tokens.has_valid_token = MagicMock(return_value=True)

    # Mock auth service
    services.auth = MagicMock()
    services.auth.initialize_with_tokens = MagicMock(return_value=True)
    services.auth.is_authenticated = MagicMock(return_value=True)

    # Mock JWT handler
    services.jwt = MagicMock()

    # Mock user store
    services.users = MagicMock()

    # Mock config
    services.config = MagicMock()
    services.config.sports = ["surf", "tennis"]

    return services


# =============================================================================
# API Client Fixtures
# =============================================================================

@pytest.fixture
def api_app():
    """Create FastAPI app for testing."""
    from api.main import app
    return app


@pytest.fixture
def api_client(api_app) -> TestClient:
    """Create synchronous test client for API."""
    return TestClient(api_app)


@pytest.fixture
async def async_api_client(api_app) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Create async test client for API."""
    async with httpx.AsyncClient(
        app=api_app,
        base_url="http://test"
    ) as client:
        yield client


@pytest.fixture
def authenticated_client(api_client, valid_access_token) -> TestClient:
    """Create authenticated test client."""
    api_client.headers["Authorization"] = f"Bearer {valid_access_token}"
    return api_client


# =============================================================================
# MCP Client Fixtures
# =============================================================================

@pytest.fixture
def mcp_app():
    """Create MCP Starlette app for testing."""
    from mcp_btc.sse_server import app
    return app


@pytest.fixture
def mcp_client(mcp_app) -> TestClient:
    """Create synchronous test client for MCP."""
    return TestClient(mcp_app)


@pytest.fixture
async def async_mcp_client(mcp_app) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Create async test client for MCP."""
    async with httpx.AsyncClient(
        app=mcp_app,
        base_url="http://test"
    ) as client:
        yield client


# =============================================================================
# Utility Fixtures
# =============================================================================

@pytest.fixture
def temp_data_dir() -> Generator[Path, None, None]:
    """Create a temporary data directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def mock_beyond_api_response():
    """Sample Beyond API response data."""
    return {
        "members": [
            {
                "memberId": 12345,
                "name": "Rafael Test",
                "socialName": "Rafael",
                "isTitular": True,
                "usage": 2,
                "limit": 10
            }
        ],
        "availability": [
            {
                "date": "2026-01-10",
                "intervals": [
                    {
                        "time": "08:00",
                        "slots": [
                            {
                                "level": "Intermediario2",
                                "waveSide": "Lado_direito",
                                "available": 3,
                                "maxQuantity": 6
                            }
                        ]
                    }
                ]
            }
        ]
    }


# =============================================================================
# Pytest Configuration
# =============================================================================

def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers", "unit: mark test as unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "api: mark test as API endpoint test"
    )
    config.addinivalue_line(
        "markers", "mcp: mark test as MCP endpoint test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
