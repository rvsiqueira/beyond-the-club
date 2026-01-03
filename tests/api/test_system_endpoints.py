"""
Integration tests for System API endpoints.

Tests health check and system status.
"""

import pytest
from unittest.mock import patch


class TestHealthCheck:
    """Tests for system health endpoints."""

    @pytest.mark.api
    def test_health_endpoint(self, api_client):
        """Test /health endpoint."""
        response = api_client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "beyond-the-club-api"

    @pytest.mark.api
    def test_root_endpoint(self, api_client):
        """Test root endpoint."""
        response = api_client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Beyond The Club API"
        assert "version" in data

    @pytest.mark.api
    def test_system_status(self, api_client, mock_services):
        """Test /api/v1/system/status endpoint."""
        with patch("api.deps.get_services", return_value=mock_services):
            response = api_client.get("/api/v1/system/status")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data

    @pytest.mark.api
    def test_docs_endpoint(self, api_client):
        """Test OpenAPI docs endpoint."""
        response = api_client.get("/docs")
        assert response.status_code == 200

    @pytest.mark.api
    def test_openapi_json(self, api_client):
        """Test OpenAPI JSON endpoint."""
        response = api_client.get("/openapi.json")

        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "paths" in data
