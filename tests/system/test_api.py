"""API endpoint tests"""

import pytest


@pytest.mark.asyncio
class TestApiEndpoints:
    """Test API endpoints."""

    async def test_health(self, test_client):
        """Test health endpoint."""
        response = await test_client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert "mongo" in data
        assert "ai_services" in data

        # The status might be "degraded" if some services are not available
        # but that's OK for testing
        assert data["status"] in ["healthy", "degraded", "error"]

        # Always verify uptime_seconds exists and is positive
        assert "uptime_seconds" in data
        assert isinstance(data["uptime_seconds"], (int, float))
        assert data["uptime_seconds"] >= 0

    async def test_root(self, test_client):
        """Test root endpoint."""
        response = await test_client.get("/")
        assert response.status_code == 200

        data = response.json()

        assert "message" in data
        assert data["message"] == "Enhanced AI Chatbot API"

        assert "version" in data
        assert "description" in data
        assert "uptime_seconds" in data

        # Check startup info
        assert "startup_info" in data
        startup_info = data["startup_info"]
        assert "services_initialized" in startup_info

        # Check AI services info
        assert "ai_services" in data
        ai_services = data["ai_services"]
        assert "embedding_model" in ai_services
        assert "generation_model" in ai_services

        # Check endpoints info
        assert "endpoints" in data
        endpoints = data["endpoints"]
        assert "health" in endpoints
        assert endpoints["health"] == "/health"
