"""
User mocking utilities for tests.
"""

from contextlib import contextmanager
from unittest.mock import patch
from typing import Optional, Dict, Any


DEFAULT_USER = {
    "id": "test-user-id",
    "email": "test@example.com",
    "name": "Test User",
    "role": "user",
    "profile_image_url": None,
}


@contextmanager
def mock_webui_user(user: Optional[Dict[str, Any]] = None):
    """
    Mock authenticated WebUI user for testing.

    Args:
        user: User data dict. If None, uses DEFAULT_USER.

    Usage:
        with mock_webui_user():
            response = client.get("/api/v1/auths")
    """
    if user is None:
        user = DEFAULT_USER.copy()

    # Mock the get_current_user dependency
    with patch(
        "open_webui.apps.webui.routers.auths.get_verified_user", return_value=user
    ):
        with patch(
            "open_webui.apps.webui.routers.models.get_verified_user", return_value=user
        ):
            with patch(
                "open_webui.apps.webui.routers.users.get_admin_user", return_value=user
            ):
                yield user


@contextmanager
def mock_admin_user(user: Optional[Dict[str, Any]] = None):
    """
    Mock authenticated admin user for testing.

    Args:
        user: User data dict. If None, creates admin user.

    Usage:
        with mock_admin_user():
            response = client.delete("/api/v1/users/some-id")
    """
    if user is None:
        user = DEFAULT_USER.copy()
        user["role"] = "admin"

    with mock_webui_user(user):
        yield user
