"""
Pytest configuration for E2E usage processing tests
Provides fixtures for database setup, mocking, and test isolation
"""

import pytest
import asyncio
import os
import sys
import logging
from datetime import datetime, date, timezone
from pathlib import Path

# Add backend path for imports
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch):
    """Set up test environment variables"""
    # Ensure we're in test mode
    monkeypatch.setenv("ENVIRONMENT", "test")
    
    # Database settings for testing
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test_usage_processing.db")
    
    # InfluxDB test settings
    monkeypatch.setenv("INFLUXDB_ENABLED", "true")
    monkeypatch.setenv("INFLUXDB_URL", "http://localhost:8086")
    monkeypatch.setenv("INFLUXDB_TOKEN", "test-token")
    monkeypatch.setenv("INFLUXDB_ORG", "test-org")
    monkeypatch.setenv("INFLUXDB_BUCKET", "test-bucket")
    monkeypatch.setenv("DUAL_WRITE_MODE", "true")
    
    # NBP service test settings
    monkeypatch.setenv("NBP_SERVICE_URL", "http://localhost:8001")
    
    # Webhook settings
    monkeypatch.setenv("OPENROUTER_WEBHOOK_SECRET", "test-webhook-secret")
    
    # Organization settings
    monkeypatch.setenv("ORGANIZATION_NAME", "Test Organization")
    
    # Usage markup
    monkeypatch.setenv("USAGE_MARKUP_MULTIPLIER", "1.3")
    
    logger.info("Test environment configured")
    
    yield
    
    # Cleanup
    logger.info("Test environment cleanup")


@pytest.fixture
def clean_database():
    """Clean database before and after tests"""
    def cleanup():
        try:
            # Remove test database file if it exists
            test_db_path = Path("test_usage_processing.db")
            if test_db_path.exists():
                test_db_path.unlink()
                logger.info("Removed test database file")
        except Exception as e:
            logger.warning(f"Failed to clean database: {e}")
    
    # Clean before test
    cleanup()
    
    yield
    
    # Clean after test
    cleanup()


@pytest.fixture
def mock_time_july_31():
    """Mock system time to July 31, 2025"""
    from unittest.mock import patch
    
    test_time = datetime(2025, 7, 31, 14, 30, 0, tzinfo=timezone.utc)
    test_date = date(2025, 7, 31)
    
    with patch('datetime.datetime') as mock_datetime:
        mock_datetime.now.return_value = test_time
        mock_datetime.utcnow.return_value = test_time
        mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
        
        with patch('datetime.date') as mock_date:
            mock_date.today.return_value = test_date
            mock_date.side_effect = lambda *args, **kw: date(*args, **kw)
            
            yield test_time


@pytest.fixture
def mock_time_august_1():
    """Mock system time to August 1, 2025"""
    from unittest.mock import patch
    
    test_time = datetime(2025, 8, 1, 14, 30, 0, tzinfo=timezone.utc)
    test_date = date(2025, 8, 1)
    
    with patch('datetime.datetime') as mock_datetime:
        mock_datetime.now.return_value = test_time
        mock_datetime.utcnow.return_value = test_time
        mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
        
        with patch('datetime.date') as mock_date:
            mock_date.today.return_value = test_date
            mock_date.side_effect = lambda *args, **kw: date(*args, **kw)
            
            yield test_time


@pytest.fixture
def mock_nbp_service():
    """Mock NBP service with controlled exchange rates"""
    from unittest.mock import patch, AsyncMock
    from decimal import Decimal
    
    # Import the mock service
    sys.path.insert(0, str(Path(__file__).parent / "mocks"))
    from nbp_mock import setup_nbp_mock_for_e2e_test
    
    # Set up the mock
    setup_nbp_mock_for_e2e_test()
    
    # Mock the currency converter functions
    async def mock_get_rate():
        return Decimal("4.50")
    
    async def mock_get_info():
        return {
            "rate": 4.50,
            "effective_date": "2025-08-01",
            "rate_source": "mock_nbp",
            "last_updated": datetime.now().isoformat(),
            "cached": False
        }
    
    async def mock_convert(usd_amount):
        return {
            "usd": usd_amount,
            "pln": usd_amount * 4.50,
            "rate": 4.50,
            "rate_source": "mock_nbp"
        }
    
    with patch('open_webui.utils.currency_converter.get_current_usd_pln_rate', side_effect=mock_get_rate), \
         patch('open_webui.utils.currency_converter.get_exchange_rate_info', side_effect=mock_get_info), \
         patch('open_webui.utils.currency_converter.convert_usd_to_pln', side_effect=mock_convert):
        
        logger.info("NBP service mocked with 4.50 PLN/USD rate")
        yield
        
        logger.info("NBP service mock restored")


@pytest.fixture
def test_client_setup():
    """Set up test client organization"""
    from utils.test_helpers import TestDatabaseSetup
    
    setup = TestDatabaseSetup()
    
    async def setup_client():
        result = await setup.setup_test_client()
        if not result["success"]:
            pytest.fail(f"Failed to setup test client: {result.get('error')}")
        return result
    
    async def cleanup_client():
        await setup.cleanup_test_client()
    
    return {
        "setup": setup_client,
        "cleanup": cleanup_client,
        "client_id": setup.test_client_id,
        "api_key": setup.test_api_key
    }


@pytest.fixture
def webhook_generator():
    """Create webhook test data generator"""
    sys.path.insert(0, str(Path(__file__).parent / "utils"))
    from test_helpers import WebhookTestGenerator
    
    return WebhookTestGenerator(webhook_secret="test-webhook-secret")


@pytest.fixture
def database_verifier():
    """Create database verification utility"""
    sys.path.insert(0, str(Path(__file__).parent / "utils"))
    from test_helpers import DatabaseVerifier
    
    return DatabaseVerifier()


@pytest.fixture
def api_test_client():
    """Create API test client"""
    sys.path.insert(0, str(Path(__file__).parent / "utils"))
    from test_helpers import APITestClient
    
    return APITestClient(base_url="http://localhost:8080")


# Test categorization markers
pytestmark = [
    pytest.mark.e2e,
    pytest.mark.database,
    pytest.mark.webhook,
    pytest.mark.batch
]


def pytest_configure(config):
    """Configure pytest with custom settings"""
    # Add custom markers
    config.addinivalue_line(
        "markers", "e2e: End-to-end integration tests"
    )
    config.addinivalue_line(
        "markers", "slow: Slow running tests (may take several minutes)"
    )
    config.addinivalue_line(
        "markers", "database: Tests requiring database access"
    )
    config.addinivalue_line(
        "markers", "influxdb: Tests requiring InfluxDB"
    )
    config.addinivalue_line(
        "markers", "webhook: Webhook processing tests"
    )
    config.addinivalue_line(
        "markers", "batch: Batch processing tests"
    )
    config.addinivalue_line(
        "markers", "nbp: NBP service integration tests"
    )


def pytest_collection_modifyitems(config, items):
    """Modify collected test items"""
    # Mark slow tests
    for item in items:
        if "e2e" in item.keywords:
            item.add_marker(pytest.mark.slow)
        
        if "batch" in item.keywords:
            item.add_marker(pytest.mark.slow)


@pytest.fixture(scope="session", autouse=True)
def test_session_setup():
    """Set up test session"""
    logger.info("🚀 Starting E2E test session")
    logger.info("=" * 60)
    
    # Create database tables
    try:
        from open_webui.internal.db import Base, engine
        
        # Import all models to ensure they're registered with Base
        from open_webui.models.organization_usage.database import ClientOrganization
        from open_webui.usage_tracking.models.database import (
            ClientDailyUsageDB,
            ClientUserDailyUsageDB,
            DailyExchangeRateDB
        )
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Created database tables for testing")
    except Exception as e:
        logger.warning(f"Could not create database tables: {e}")
    
    yield
    
    logger.info("=" * 60)
    logger.info("✅ E2E test session completed")


@pytest.fixture(autouse=True)
def test_case_setup(request):
    """Set up individual test case"""
    test_name = request.node.name
    logger.info(f"🧪 Starting test: {test_name}")
    
    yield
    
    logger.info(f"✅ Completed test: {test_name}")


# Async test configuration for pytest-asyncio
@pytest.fixture(scope="session")
def asyncio_mode():
    """Configure asyncio mode for pytest-asyncio"""
    return "auto"