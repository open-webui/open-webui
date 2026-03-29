"""
Abstract base classes for integration tests.
"""

from abc import ABC
from fastapi.testclient import TestClient


class AbstractIntegrationTest(ABC):
    """Base class for integration tests."""

    BASE_PATH: str = ""

    @classmethod
    def setup_class(cls):
        """Set up test class."""
        from open_webui.main import app

        cls.app = app
        cls.fast_api_client = TestClient(app)

    @classmethod
    def teardown_class(cls):
        """Tear down test class."""
        pass

    def create_url(self, path: str) -> str:
        """Create full URL from base path and relative path."""
        base = self.BASE_PATH.rstrip("/")
        path = path.lstrip("/")
        if path:
            return f"{base}/{path}"
        return base


class AbstractPostgresTest(AbstractIntegrationTest):
    """Base class for tests that require PostgreSQL."""

    @classmethod
    def setup_class(cls):
        """Set up PostgreSQL test environment."""
        super().setup_class()
        # TODO: Set up test database
        # For now, tests will use whatever DB is configured

    @classmethod
    def teardown_class(cls):
        """Tear down PostgreSQL test environment."""
        # TODO: Clean up test database
        super().teardown_class()
