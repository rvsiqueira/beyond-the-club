"""
Pytest configuration for MCP tests.

Separate conftest to avoid import issues with main conftest.
"""

import os
import sys
from pathlib import Path

import pytest
from starlette.testclient import TestClient

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Set test environment variables before imports
os.environ["JWT_SECRET_KEY"] = "test_jwt_secret_key_for_testing_only_32bytes!"
os.environ["MCP_API_KEY"] = "test_mcp_api_key_for_testing_only"
os.environ["ENVIRONMENT"] = "test"


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


@pytest.fixture
def mcp_app():
    """Create MCP Starlette app for testing."""
    from mcp_btc.sse_server import app
    return app


@pytest.fixture
def mcp_client(mcp_app) -> TestClient:
    """Create synchronous test client for MCP."""
    return TestClient(mcp_app)


def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers", "mcp: mark test as MCP endpoint test"
    )
    config.addinivalue_line(
        "markers", "unit: mark test as unit test"
    )
