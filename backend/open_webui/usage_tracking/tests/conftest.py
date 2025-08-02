"""
Pytest configuration for usage tracking tests
"""

import pytest
import asyncio
import os
import sys

# Add specific paths for imports without loading the entire open_webui module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def clean_env(monkeypatch):
    """Clean environment variables for testing"""
    # Remove any existing InfluxDB variables
    env_vars_to_remove = [
        "INFLUXDB_ENABLED",
        "INFLUXDB_URL",
        "INFLUXDB_TOKEN",
        "INFLUXDB_ORG",
        "INFLUXDB_BUCKET",
        "INFLUXDB_USE_CLOUD",
        "INFLUXDB_CLOUD_URL",
        "INFLUXDB_CLOUD_TOKEN",
        "INFLUXDB_CLOUD_ORG",
        "INFLUXDB_CLOUD_BUCKET",
        "DUAL_WRITE_MODE",
        "CLIENT_ORG_ID"
    ]
    
    for var in env_vars_to_remove:
        monkeypatch.delenv(var, raising=False)
    
    return monkeypatch