"""
Tests for NBP Service
"""
import pytest
from httpx import AsyncClient
from datetime import datetime

from app.main import app


@pytest.mark.asyncio
async def test_health_endpoint():
    """Test health check endpoint"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "mode" in data
        assert "timestamp" in data


@pytest.mark.asyncio
async def test_get_current_rate():
    """Test getting current USD/PLN rate"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/usd-pln-rate")
        assert response.status_code == 200
        data = response.json()
        assert data["currency"] == "USD"
        assert "rate" in data
        assert "date" in data
        assert "source" in data
        assert isinstance(data["rate"], float)


@pytest.mark.asyncio
async def test_get_rate_by_date():
    """Test getting USD/PLN rate for specific date"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/usd-pln-rate?date=2025-01-15")
        assert response.status_code == 200
        data = response.json()
        assert data["currency"] == "USD"
        assert data["date"] == "2025-01-15"
        assert isinstance(data["rate"], float)


@pytest.mark.asyncio
async def test_get_rate_range():
    """Test getting USD/PLN rates for date range"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            "/api/usd-pln-rate/range?start_date=2025-01-01&end_date=2025-01-07"
        )
        assert response.status_code == 200
        data = response.json()
        assert "rates" in data
        assert "count" in data
        assert len(data["rates"]) > 0
        # Check weekends are excluded
        assert data["count"] <= 5  # Max 5 business days in a week


@pytest.mark.asyncio
async def test_cache_clear():
    """Test cache clearing endpoint"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/api/cache/clear")
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Cache cleared successfully"