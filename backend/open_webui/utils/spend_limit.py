"""
Spend Limit Utilities

This module provides utilities for checking and enforcing user spend limits.
"""

import logging
from typing import Optional, Tuple

from fastapi import HTTPException, status

from open_webui.models.users import Users
from open_webui.models.user_usage import UserUsages
from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS.get("MAIN", logging.INFO))


class SpendLimitExceeded(HTTPException):
    """Exception raised when a user exceeds their spend limit."""

    def __init__(self, limit_type: str, current_spend: float, limit: float):
        detail = {
            "error": "spend_limit_exceeded",
            "message": f"You have exceeded your {limit_type} spend limit",
            "limit_type": limit_type,
            "current_spend": round(current_spend, 4),
            "limit": round(limit, 2),
        }
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=detail,
        )


def check_user_spend_limit(user_id: str) -> Tuple[bool, Optional[dict]]:
    """
    Check if a user has exceeded their spend limits.

    Args:
        user_id: The user's ID

    Returns:
        Tuple of (is_within_limit, spend_info)
        - is_within_limit: True if user can make requests
        - spend_info: Dict with current spend and limits info

    Raises:
        SpendLimitExceeded: If user has exceeded their limit
    """
    try:
        user = Users.get_user_by_id(user_id)
        if not user:
            return True, None

        # Skip if spend limits not enabled for this user
        if not user.spend_limit_enabled:
            return True, None

        # Get current spend
        spend_summary = UserUsages.get_user_spend_summary(user_id)

        spend_info = {
            "daily_spend": spend_summary.daily_spend,
            "monthly_spend": spend_summary.monthly_spend,
            "daily_limit": user.spend_limit_daily,
            "monthly_limit": user.spend_limit_monthly,
            "limits_enabled": True,
        }

        # Check daily limit
        if user.spend_limit_daily is not None:
            if spend_summary.daily_spend >= user.spend_limit_daily:
                raise SpendLimitExceeded(
                    limit_type="daily",
                    current_spend=spend_summary.daily_spend,
                    limit=user.spend_limit_daily,
                )

        # Check monthly limit
        if user.spend_limit_monthly is not None:
            if spend_summary.monthly_spend >= user.spend_limit_monthly:
                raise SpendLimitExceeded(
                    limit_type="monthly",
                    current_spend=spend_summary.monthly_spend,
                    limit=user.spend_limit_monthly,
                )

        return True, spend_info

    except SpendLimitExceeded:
        raise
    except Exception as e:
        log.error(f"Error checking spend limit for user {user_id}: {e}")
        # On error, allow the request (fail open)
        return True, None


async def enforce_spend_limit(user) -> None:
    """
    Enforce spend limits for a user before processing a chat request.

    This function should be called at the start of chat completion endpoints.

    Args:
        user: The user model

    Raises:
        SpendLimitExceeded: If user has exceeded their spend limit
    """
    if not user or not user.id:
        return

    # Admins can optionally bypass spend limits
    # Uncomment the following if admins should bypass:
    # if user.role == "admin":
    #     return

    check_user_spend_limit(user.id)
