"""
Per-user and per-group token/message usage quota enforcement.

Usage limits are configured per user (highest priority) or per group (inherited
when no user-level override exists). The most restrictive group limit wins when
a user belongs to multiple groups with limits configured.

Limits are checked as a pre-flight step inside generate_chat_completion() before
any LLM call is made. The check fails open on DB errors to avoid blocking
legitimate users due to transient infrastructure issues.

Known limitation — TOCTOU race condition:
  The check-then-act pattern (read usage → enforce → LLM call → write usage)
  means that concurrent requests from the same user can all pass the pre-flight
  check before any of them write their usage back to the database. The maximum
  overshoot per burst is bounded by (N_concurrent × tokens_per_request). For
  typical chat-UI usage (one request at a time), this is negligible. Eliminating
  it would require an atomic counter (Redis INCR or a dedicated DB row with
  SELECT FOR UPDATE), which is out of scope for this initial implementation.
  Treat configured limits as soft caps with a small burst tolerance.

Known limitation — cross-period dimension merging:
  When a user belongs to groups with different periods (e.g. Group A enforces a
  daily message cap and Group B enforces a weekly token cap), only the shortest-
  period group's limits are applied. The longer-period cap is silently ignored.
  All limits WITHIN the shortest period are merged correctly (minimum across
  groups for each dimension).
"""

import logging
from datetime import UTC, datetime, timedelta  # noqa: ICN003
from typing import Literal

from fastapi import HTTPException
from open_webui.models.chat_messages import ChatMessages
from open_webui.models.groups import Groups
from open_webui.models.users import Users
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)


class UsageLimitsConfig(BaseModel):
    """Schema for per-user or per-group usage limit configuration.

    Stored in:
      User.info['usage_limits']   — user-level override (highest priority)
      Group.data['usage_limits']  — group default (inheritable)
    """

    enabled: bool = False
    period: Literal['daily', 'weekly', 'monthly'] = 'daily'

    # Optional per-period caps (None = unlimited for that dimension)
    max_messages: int | None = Field(default=None, ge=0)
    max_input_tokens: int | None = Field(default=None, ge=0)
    max_output_tokens: int | None = Field(default=None, ge=0)
    max_total_tokens: int | None = Field(default=None, ge=0)

    model_config = {'extra': 'ignore'}


class UsageStatus(BaseModel):
    """Current usage snapshot for a user, paired with their effective limits."""

    limits: UsageLimitsConfig | None = None
    period_start: int | None = None
    period_end: int | None = None
    usage: dict = Field(default_factory=dict)


class QuotaDimension(BaseModel):
    """Quota figures for one trackable dimension (tokens or messages)."""

    used: int
    limit: int
    remaining: int


class QuotaSummary(BaseModel):
    """Clean, pre-computed quota summary for the GET /user/quota endpoint.

    When no limits are configured, ``unlimited`` is True and all dimension
    fields are None — the frontend can gate on that flag without inspecting
    every field.
    """

    unlimited: bool = False
    period: Literal['daily', 'weekly', 'monthly'] | None = None
    resets_at: str | None = None  # ISO 8601 date, e.g. "2026-07-01"

    total_tokens: QuotaDimension | None = None
    input_tokens: QuotaDimension | None = None
    output_tokens: QuotaDimension | None = None
    messages: QuotaDimension | None = None


# ---------------------------------------------------------------------------
# Period helpers
# ---------------------------------------------------------------------------

_PERIOD_ORDER = {'daily': 0, 'weekly': 1, 'monthly': 2}


def get_period_start_ts(period: str) -> int:
    """UTC Unix timestamp for the start of the current billing period."""
    now = datetime.now(UTC)
    if period == 'daily':
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == 'weekly':
        # ISO weeks start on Monday
        start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == 'monthly':
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        raise ValueError(f'Unknown period: {period!r}')
    return int(start.timestamp())


def get_period_end_ts(period: str) -> int:
    """UTC Unix timestamp for the end of the current billing period (inclusive)."""
    now = datetime.now(UTC)
    if period == 'daily':
        end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
    elif period == 'weekly':
        days_to_sunday = 6 - now.weekday()
        end = (now + timedelta(days=days_to_sunday)).replace(hour=23, minute=59, second=59, microsecond=999999)
    elif period == 'monthly':
        # Reset to midnight before subtracting 1 µs so the result is the last
        # microsecond of the current month, not the first day of the next month.
        if now.month == 12:
            first_of_next = now.replace(year=now.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            first_of_next = now.replace(month=now.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0)
        end = first_of_next - timedelta(microseconds=1)
    else:
        raise ValueError(f'Unknown period: {period!r}')
    return int(end.timestamp())


# ---------------------------------------------------------------------------
# Effective limit resolution
# ---------------------------------------------------------------------------


def _most_restrictive(configs: list[UsageLimitsConfig]) -> UsageLimitsConfig:
    """Merge a list of enabled UsageLimitsConfig into the tightest combined limit.

    - Period: shortest wins (daily < weekly < monthly).
    - Caps: minimum non-None value across all configs.
    """

    def _min_cap(*values: int | None) -> int | None:
        non_none = [v for v in values if v is not None]
        return min(non_none) if non_none else None

    # Sort so the shortest period comes first (do not mutate the caller's list)
    configs = sorted(configs, key=lambda c: _PERIOD_ORDER.get(c.period, 99))
    effective_period = configs[0].period

    # Only compare limits from configs that share the most restrictive period
    same_period = [c for c in configs if c.period == effective_period]

    return UsageLimitsConfig(
        enabled=True,
        period=effective_period,
        max_messages=_min_cap(*[c.max_messages for c in same_period]),
        max_input_tokens=_min_cap(*[c.max_input_tokens for c in same_period]),
        max_output_tokens=_min_cap(*[c.max_output_tokens for c in same_period]),
        max_total_tokens=_min_cap(*[c.max_total_tokens for c in same_period]),
    )


async def get_effective_usage_limits(
    user_id: str,
    db: AsyncSession | None = None,
) -> UsageLimitsConfig | None:
    """Resolve the effective usage limits for a user.

    Priority order:
      1. User-level override (user.info['usage_limits'])
      2. Most restrictive limit across the user's groups
      3. None (unlimited)

    If a user has an explicit user-level config with enabled=False, that is
    treated as "no limit" for this user, even if groups have limits set.
    """
    user = await Users.get_user_by_id(user_id, db=db)
    if not user:
        return None

    # ── 1. User-level override ────────────────────────────────────────────
    raw_user_limits = (user.info or {}).get('usage_limits')
    if raw_user_limits is not None:
        try:
            user_limits = UsageLimitsConfig.model_validate(raw_user_limits)
            return user_limits if user_limits.enabled else None
        except Exception:
            log.warning('Ignoring malformed usage_limits for user %s', user_id)

    # ── 2. Group-level limits ─────────────────────────────────────────────
    groups = await Groups.get_groups_by_member_id(user_id, db=db)
    enabled_group_limits: list[UsageLimitsConfig] = []
    for group in groups:
        raw_group_limits = (group.data or {}).get('usage_limits')
        if raw_group_limits is None:
            continue
        try:
            gl = UsageLimitsConfig.model_validate(raw_group_limits)
            if gl.enabled:
                enabled_group_limits.append(gl)
        except Exception:
            log.warning('Ignoring malformed usage_limits for group %s', group.id)

    if not enabled_group_limits:
        return None

    return _most_restrictive(enabled_group_limits)


# ---------------------------------------------------------------------------
# Usage query
# ---------------------------------------------------------------------------


async def get_user_usage_for_period(
    user_id: str,
    period: str,
    db: AsyncSession | None = None,
) -> dict[str, int]:
    """Return current-period token/message stats for a single user."""
    start_date = get_period_start_ts(period)
    usage_map = await ChatMessages.get_token_usage_by_user(
        start_date=start_date,
        user_id=user_id,
        db=db,
    )
    return usage_map.get(
        user_id,
        {
            'input_tokens': 0,
            'output_tokens': 0,
            'total_tokens': 0,
            'message_count': 0,
        },
    )


# ---------------------------------------------------------------------------
# Enforcement
# ---------------------------------------------------------------------------


async def check_usage_limits(
    user_id: str,
    db: AsyncSession | None = None,
) -> None:
    """Pre-flight usage limit check. Call this before invoking the LLM.

    Raises HTTPException(429) with a structured detail payload when any
    configured limit is exceeded. The detail dict includes:
      - error: "usage_limit_exceeded"
      - limit_type: which dimension was hit
      - period: "daily" | "weekly" | "monthly"
      - limit: the configured cap
      - current: the user's current usage value
      - resets_at: Unix timestamp when the period resets

    Fails open on unexpected errors to avoid blocking users due to DB
    transient failures.
    """
    try:
        limits = await get_effective_usage_limits(user_id, db=db)
        if not limits or not limits.enabled:
            return

        usage = await get_user_usage_for_period(user_id, limits.period, db=db)
        period_end = get_period_end_ts(limits.period)

        retry_after = str(max(0, period_end - int(datetime.now(UTC).timestamp())))

        def _exceeded(limit: int | None, key: str, label: str) -> None:
            if limit is None:
                return
            current = usage.get(key, 0)
            if current >= limit:
                raise HTTPException(
                    status_code=429,
                    headers={'Retry-After': retry_after},
                    detail={
                        'error': 'usage_limit_exceeded',
                        'limit_type': label,
                        'period': limits.period,
                        'limit': limit,
                        'current': current,
                        'resets_at': period_end,
                    },
                )

        _exceeded(limits.max_messages, 'message_count', 'messages')
        _exceeded(limits.max_total_tokens, 'total_tokens', 'total_tokens')
        _exceeded(limits.max_input_tokens, 'input_tokens', 'input_tokens')
        _exceeded(limits.max_output_tokens, 'output_tokens', 'output_tokens')

    except HTTPException:
        raise
    except Exception:
        log.exception('Usage limit check failed for user %s — allowing request', user_id)


# ---------------------------------------------------------------------------
# Status helpers (used by self-service endpoints)
# ---------------------------------------------------------------------------


async def get_usage_status(
    user_id: str,
    db: AsyncSession | None = None,
) -> UsageStatus:
    """Build a UsageStatus payload for the /user/usage endpoint (raw numbers)."""
    limits = await get_effective_usage_limits(user_id, db=db)
    if not limits or not limits.enabled:
        return UsageStatus()

    usage = await get_user_usage_for_period(user_id, limits.period, db=db)
    return UsageStatus(
        limits=limits,
        period_start=get_period_start_ts(limits.period),
        period_end=get_period_end_ts(limits.period),
        usage=usage,
    )


def _period_end_date_str(period: str) -> str:
    """ISO 8601 date string for the last day of the current billing period."""
    return datetime.fromtimestamp(get_period_end_ts(period), tz=UTC).date().isoformat()


def _dimension(used: int, limit: int | None) -> QuotaDimension | None:
    """Build a QuotaDimension only when the cap is configured."""
    if limit is None:
        return None
    return QuotaDimension(used=used, limit=limit, remaining=max(0, limit - used))


async def get_quota_summary(
    user_id: str,
    db: AsyncSession | None = None,
) -> QuotaSummary:
    """Build a clean, pre-computed quota summary for the /user/quota endpoint.

    Returns a flat, human-readable structure with ``remaining`` already
    calculated and ``resets_at`` as an ISO date string so the frontend can
    render a quota card without any arithmetic.

    Example response when daily token cap is 50 000 and 42 000 are used::

        {
          "unlimited": false,
          "period": "daily",
          "resets_at": "2026-06-20",
          "total_tokens": {"used": 42000, "limit": 50000, "remaining": 8000},
          "input_tokens": null,
          "output_tokens": null,
          "messages": null
        }
    """
    limits = await get_effective_usage_limits(user_id, db=db)
    if not limits or not limits.enabled:
        return QuotaSummary(unlimited=True)

    usage = await get_user_usage_for_period(user_id, limits.period, db=db)

    return QuotaSummary(
        unlimited=False,
        period=limits.period,
        resets_at=_period_end_date_str(limits.period),
        total_tokens=_dimension(usage.get('total_tokens', 0), limits.max_total_tokens),
        input_tokens=_dimension(usage.get('input_tokens', 0), limits.max_input_tokens),
        output_tokens=_dimension(usage.get('output_tokens', 0), limits.max_output_tokens),
        messages=_dimension(usage.get('message_count', 0), limits.max_messages),
    )
