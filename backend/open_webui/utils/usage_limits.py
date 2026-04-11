import logging
from datetime import datetime
from typing import Optional

from open_webui.models.chat_messages import ChatMessages
from open_webui.models.usage_ledger import UsageLedger
from open_webui.models.groups import Groups

log = logging.getLogger(__name__)


def get_period_start(period: str) -> int:
    """Get the epoch timestamp for the start of the current period."""
    now = datetime.now()  # Uses server timezone (TZ env var)

    if period == 'daily':
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == 'monthly':
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    return int(start.timestamp())


def get_user_usage_limit(user_id: str) -> Optional[dict]:
    """
    Get the effective usage limit for a user based on their group memberships.

    Returns the limit from the highest-priority group (lowest priority number).
    Groups without usage_limits configured are skipped.

    Returns None if no limits are configured for any of the user's groups.

    Expected permissions.usage_limits format:
    {
        "token_limit": 1000000,       # max total tokens per period
        "limit_period": "daily",       # "daily" or "monthly"
        "soft_limit": 800000,          # optional: warn at this threshold
        "priority": 10                 # lower = higher priority
    }
    """
    user_groups = Groups.get_groups_by_member_id(user_id)
    if not user_groups:
        return None

    best_limit = None
    best_priority = float('inf')

    for group in user_groups:
        permissions = group.permissions or {}
        usage_limits = permissions.get('usage_limits')
        if not usage_limits:
            continue

        token_limit = usage_limits.get('token_limit')
        if token_limit is None:
            continue

        priority = usage_limits.get('priority', 100)
        if priority < best_priority:
            best_priority = priority
            best_limit = {
                'token_limit': token_limit,
                'limit_period': usage_limits.get('limit_period', 'daily'),
                'soft_limit': usage_limits.get('soft_limit'),
                'group_name': group.name,
            }

    return best_limit


def check_usage_limit(user_id: str) -> dict:
    """
    Check whether a user has exceeded their usage limit.
    Reads from chat_message table (same source as analytics).
    """
    limit = get_user_usage_limit(user_id)

    # No limits configured — always allow
    if limit is None:
        return {
            'allowed': True,
            'warning': False,
            'usage': None,
            'limit': None,
            'message': None,
        }

    period_start = get_period_start(limit['limit_period'])

    # Sum usage from chat_message (normal chats) + usage_ledger (temp chats)
    cm_usage = ChatMessages.get_token_usage_by_user(start_date=period_start)
    cm_user = cm_usage.get(user_id, {'input_tokens': 0, 'output_tokens': 0, 'total_tokens': 0})
    ledger_usage = UsageLedger.get_user_usage_since(user_id, period_start)

    user_usage = {
        'input_tokens': cm_user['input_tokens'] + ledger_usage['input_tokens'],
        'output_tokens': cm_user['output_tokens'] + ledger_usage['output_tokens'],
        'total_tokens': cm_user['total_tokens'] + ledger_usage['total_tokens'],
    }
    total_tokens = user_usage['total_tokens']

    token_limit = limit['token_limit']
    soft_limit = limit.get('soft_limit')
    period_label = limit['limit_period']

    log.info(
        f'[USAGE_LIMIT] user={user_id} period={period_label} '
        f'usage={total_tokens}/{token_limit} '
        f'(input={user_usage["input_tokens"]}, output={user_usage["output_tokens"]}) '
        f'group={limit.get("group_name", "?")} soft_limit={soft_limit}'
    )

    # Hard limit exceeded
    if total_tokens >= token_limit:
        log.warning(f'[USAGE_LIMIT] BLOCKED user={user_id} ({total_tokens}/{token_limit})')
        return {
            'allowed': False,
            'warning': False,
            'usage': user_usage,
            'limit': limit,
            'message': (
                f'You have reached your {period_label} token limit '
                f'({total_tokens:,} / {token_limit:,} tokens). '
                f'Your limit resets at the start of the next {period_label} period.'
            ),
        }

    # Soft limit warning
    if soft_limit and total_tokens >= soft_limit:
        remaining = token_limit - total_tokens
        log.info(f'[USAGE_LIMIT] WARNING user={user_id} ({total_tokens}/{token_limit})')
        return {
            'allowed': True,
            'warning': True,
            'usage': user_usage,
            'limit': limit,
            'message': (
                f'You are approaching your {period_label} token limit '
                f'({total_tokens:,} / {token_limit:,} tokens). '
                f'{remaining:,} tokens remaining.'
            ),
        }

    # Under limits
    return {
        'allowed': True,
        'warning': False,
        'usage': user_usage,
        'limit': limit,
        'message': None,
    }
