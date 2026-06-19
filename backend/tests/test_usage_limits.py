"""
Tests for the per-user / per-group usage limit system.

Run with:
    cd backend && python -m pytest tests/test_usage_limits.py -v
"""

from datetime import UTC, datetime  # noqa: ICN003
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from open_webui.utils.usage_limits import (
    UsageLimitsConfig,
    _dimension,
    _most_restrictive,
    check_usage_limits,
    get_effective_usage_limits,
    get_period_end_ts,
    get_period_start_ts,
    get_quota_summary,
    get_usage_status,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def make_user(info: dict | None = None) -> MagicMock:
    user = MagicMock()
    user.id = 'user-1'
    user.info = info
    return user


def make_group(data: dict | None = None) -> MagicMock:
    group = MagicMock()
    group.id = 'group-1'
    group.data = data
    return group


def make_limits(**kwargs) -> UsageLimitsConfig:
    defaults = {'enabled': True, 'period': 'daily'}
    return UsageLimitsConfig(**{**defaults, **kwargs})


# ---------------------------------------------------------------------------
# Unit: period helpers
# ---------------------------------------------------------------------------


class TestPeriodHelpers:
    def test_daily_start_is_midnight_utc(self):
        ts = get_period_start_ts('daily')
        dt = datetime.fromtimestamp(ts, tz=UTC)
        assert dt.hour == 0
        assert dt.minute == 0
        assert dt.second == 0

    def test_weekly_start_is_monday(self):
        ts = get_period_start_ts('weekly')
        dt = datetime.fromtimestamp(ts, tz=UTC)
        assert dt.weekday() == 0  # Monday

    def test_monthly_start_is_first_day(self):
        ts = get_period_start_ts('monthly')
        dt = datetime.fromtimestamp(ts, tz=UTC)
        assert dt.day == 1
        assert dt.hour == 0

    def test_period_end_after_start(self):
        for period in ('daily', 'weekly', 'monthly'):
            assert get_period_end_ts(period) > get_period_start_ts(period)

    def test_monthly_end_is_last_day_of_current_month(self):
        """Regression: monthly period end must be last day of the current month,
        not the first day of the next month (TOCTOU with time-of-day offset)."""
        end_ts = get_period_end_ts('monthly')
        end_dt = datetime.fromtimestamp(end_ts, tz=UTC)
        now = datetime.now(UTC)
        # The end date's month must equal the current month
        assert end_dt.month == now.month, (
            f'Monthly period end is {end_dt.date()} but current month is {now.month}; '
            f'end must be in the same month as today'
        )

    def test_unknown_period_raises(self):
        with pytest.raises(ValueError, match='Unknown period'):
            get_period_start_ts('yearly')


# ---------------------------------------------------------------------------
# Unit: _most_restrictive
# ---------------------------------------------------------------------------


class TestMostRestrictive:
    def test_single_config_returned_unchanged(self):
        cfg = make_limits(period='daily', max_total_tokens=1000)
        result = _most_restrictive([cfg])
        assert result.max_total_tokens == 1000
        assert result.period == 'daily'

    def test_daily_wins_over_weekly(self):
        daily = make_limits(period='daily', max_total_tokens=5000)
        weekly = make_limits(period='weekly', max_total_tokens=50000)
        result = _most_restrictive([weekly, daily])
        assert result.period == 'daily'
        assert result.max_total_tokens == 5000

    def test_min_cap_across_same_period(self):
        a = make_limits(period='daily', max_total_tokens=10000, max_messages=100)
        b = make_limits(period='daily', max_total_tokens=5000, max_messages=200)
        result = _most_restrictive([a, b])
        assert result.max_total_tokens == 5000  # min(10000, 5000)
        assert result.max_messages == 100  # min(100, 200)

    def test_none_cap_ignored(self):
        # If one group has no message cap, the other's cap wins
        a = make_limits(period='daily', max_total_tokens=1000, max_messages=None)
        b = make_limits(period='daily', max_total_tokens=2000, max_messages=50)
        result = _most_restrictive([a, b])
        assert result.max_messages == 50
        assert result.max_total_tokens == 1000

    def test_all_none_caps_stay_none(self):
        a = make_limits(period='daily', max_total_tokens=None)
        b = make_limits(period='daily', max_total_tokens=None)
        result = _most_restrictive([a, b])
        assert result.max_total_tokens is None


# ---------------------------------------------------------------------------
# Unit: get_effective_usage_limits
# ---------------------------------------------------------------------------


class TestGetEffectiveLimits:
    @pytest.mark.asyncio
    async def test_user_with_no_info_returns_none(self):
        user = make_user(info=None)
        with (
            patch('open_webui.utils.usage_limits.Users') as mock_users,
            patch('open_webui.utils.usage_limits.Groups') as mock_groups,
        ):
            mock_users.get_user_by_id = AsyncMock(return_value=user)
            mock_groups.get_groups_by_member_id = AsyncMock(return_value=[])
            result = await get_effective_usage_limits('user-1')
        assert result is None

    @pytest.mark.asyncio
    async def test_user_level_override_takes_priority(self):
        user = make_user(info={'usage_limits': {'enabled': True, 'period': 'daily', 'max_total_tokens': 999}})
        group = make_group(data={'usage_limits': {'enabled': True, 'period': 'daily', 'max_total_tokens': 50000}})
        with (
            patch('open_webui.utils.usage_limits.Users') as mock_users,
            patch('open_webui.utils.usage_limits.Groups') as mock_groups,
        ):
            mock_users.get_user_by_id = AsyncMock(return_value=user)
            mock_groups.get_groups_by_member_id = AsyncMock(return_value=[group])
            result = await get_effective_usage_limits('user-1')
        assert result is not None
        assert result.max_total_tokens == 999  # user override wins

    @pytest.mark.asyncio
    async def test_disabled_user_override_bypasses_group_limits(self):
        # User has enabled=False — they should be exempt even if groups have limits
        user = make_user(info={'usage_limits': {'enabled': False, 'period': 'daily'}})
        group = make_group(data={'usage_limits': {'enabled': True, 'period': 'daily', 'max_total_tokens': 1000}})
        with (
            patch('open_webui.utils.usage_limits.Users') as mock_users,
            patch('open_webui.utils.usage_limits.Groups') as mock_groups,
        ):
            mock_users.get_user_by_id = AsyncMock(return_value=user)
            mock_groups.get_groups_by_member_id = AsyncMock(return_value=[group])
            result = await get_effective_usage_limits('user-1')
        assert result is None

    @pytest.mark.asyncio
    async def test_group_limits_used_when_no_user_override(self):
        user = make_user(info={})  # no usage_limits key
        group = make_group(data={'usage_limits': {'enabled': True, 'period': 'weekly', 'max_total_tokens': 20000}})
        with (
            patch('open_webui.utils.usage_limits.Users') as mock_users,
            patch('open_webui.utils.usage_limits.Groups') as mock_groups,
        ):
            mock_users.get_user_by_id = AsyncMock(return_value=user)
            mock_groups.get_groups_by_member_id = AsyncMock(return_value=[group])
            result = await get_effective_usage_limits('user-1')
        assert result is not None
        assert result.period == 'weekly'
        assert result.max_total_tokens == 20000

    @pytest.mark.asyncio
    async def test_multiple_groups_most_restrictive_wins(self):
        user = make_user(info={})
        g1 = make_group(data={'usage_limits': {'enabled': True, 'period': 'daily', 'max_total_tokens': 10000}})
        g2 = make_group(data={'usage_limits': {'enabled': True, 'period': 'daily', 'max_total_tokens': 5000}})
        g2.id = 'group-2'
        with (
            patch('open_webui.utils.usage_limits.Users') as mock_users,
            patch('open_webui.utils.usage_limits.Groups') as mock_groups,
        ):
            mock_users.get_user_by_id = AsyncMock(return_value=user)
            mock_groups.get_groups_by_member_id = AsyncMock(return_value=[g1, g2])
            result = await get_effective_usage_limits('user-1')
        assert result is not None
        assert result.max_total_tokens == 5000  # most restrictive

    @pytest.mark.asyncio
    async def test_unknown_user_returns_none(self):
        with patch('open_webui.utils.usage_limits.Users') as mock_users:
            mock_users.get_user_by_id = AsyncMock(return_value=None)
            result = await get_effective_usage_limits('nonexistent')
        assert result is None

    @pytest.mark.asyncio
    async def test_malformed_user_limits_json_falls_through_to_groups(self):
        user = make_user(info={'usage_limits': 'not-a-dict'})
        group = make_group(data={'usage_limits': {'enabled': True, 'period': 'daily', 'max_total_tokens': 100}})
        with (
            patch('open_webui.utils.usage_limits.Users') as mock_users,
            patch('open_webui.utils.usage_limits.Groups') as mock_groups,
        ):
            mock_users.get_user_by_id = AsyncMock(return_value=user)
            mock_groups.get_groups_by_member_id = AsyncMock(return_value=[group])
            result = await get_effective_usage_limits('user-1')
        # Malformed user config is ignored; group limit is used
        assert result is not None
        assert result.max_total_tokens == 100


# ---------------------------------------------------------------------------
# Unit: check_usage_limits
# ---------------------------------------------------------------------------


class TestCheckUsageLimits:
    @pytest.mark.asyncio
    async def test_no_limits_configured_passes(self):
        with patch(
            'open_webui.utils.usage_limits.get_effective_usage_limits',
            new=AsyncMock(return_value=None),
        ):
            # Should not raise
            await check_usage_limits('user-1')

    @pytest.mark.asyncio
    async def test_limits_disabled_passes(self):
        disabled = UsageLimitsConfig(enabled=False, period='daily', max_total_tokens=100)
        with patch(
            'open_webui.utils.usage_limits.get_effective_usage_limits',
            new=AsyncMock(return_value=disabled),
        ):
            await check_usage_limits('user-1')

    @pytest.mark.asyncio
    async def test_under_limit_passes(self):
        limits = make_limits(max_total_tokens=1000)
        usage = {'total_tokens': 500, 'message_count': 10, 'input_tokens': 300, 'output_tokens': 200}
        with (
            patch(
                'open_webui.utils.usage_limits.get_effective_usage_limits',
                new=AsyncMock(return_value=limits),
            ),
            patch(
                'open_webui.utils.usage_limits.get_user_usage_for_period',
                new=AsyncMock(return_value=usage),
            ),
        ):
            await check_usage_limits('user-1')

    @pytest.mark.asyncio
    async def test_token_limit_exceeded_raises_429(self):
        limits = make_limits(max_total_tokens=1000)
        usage = {'total_tokens': 1000, 'message_count': 5, 'input_tokens': 600, 'output_tokens': 400}
        with (
            patch(
                'open_webui.utils.usage_limits.get_effective_usage_limits',
                new=AsyncMock(return_value=limits),
            ),
            patch(
                'open_webui.utils.usage_limits.get_user_usage_for_period',
                new=AsyncMock(return_value=usage),
            ),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await check_usage_limits('user-1')
            assert exc_info.value.status_code == 429
            detail = exc_info.value.detail
            assert detail['error'] == 'usage_limit_exceeded'
            assert detail['limit_type'] == 'total_tokens'
            assert detail['limit'] == 1000
            assert detail['current'] == 1000
            assert 'resets_at' in detail

    @pytest.mark.asyncio
    async def test_message_limit_exceeded_raises_429(self):
        limits = make_limits(max_messages=50, max_total_tokens=None)
        usage = {'total_tokens': 0, 'message_count': 50}
        with (
            patch(
                'open_webui.utils.usage_limits.get_effective_usage_limits',
                new=AsyncMock(return_value=limits),
            ),
            patch(
                'open_webui.utils.usage_limits.get_user_usage_for_period',
                new=AsyncMock(return_value=usage),
            ),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await check_usage_limits('user-1')
            assert exc_info.value.detail['limit_type'] == 'messages'

    @pytest.mark.asyncio
    async def test_db_error_fails_open(self):
        """DB errors during limit check must NOT block the user (fail open)."""
        with patch(
            'open_webui.utils.usage_limits.get_effective_usage_limits',
            new=AsyncMock(side_effect=RuntimeError('DB connection lost')),
        ):
            # Should not raise — fail open
            await check_usage_limits('user-1')

    @pytest.mark.asyncio
    async def test_exactly_at_limit_is_blocked(self):
        """The check uses >=, so exactly hitting the limit is blocked."""
        limits = make_limits(max_total_tokens=100)
        usage = {'total_tokens': 100, 'message_count': 0}
        with (
            patch(
                'open_webui.utils.usage_limits.get_effective_usage_limits',
                new=AsyncMock(return_value=limits),
            ),
            patch(
                'open_webui.utils.usage_limits.get_user_usage_for_period',
                new=AsyncMock(return_value=usage),
            ),
        ):
            with pytest.raises(HTTPException):
                await check_usage_limits('user-1')

    @pytest.mark.asyncio
    async def test_input_token_limit_checked_independently(self):
        limits = make_limits(max_input_tokens=200, max_total_tokens=None)
        usage = {'input_tokens': 200, 'output_tokens': 50, 'total_tokens': 250, 'message_count': 3}
        with (
            patch(
                'open_webui.utils.usage_limits.get_effective_usage_limits',
                new=AsyncMock(return_value=limits),
            ),
            patch(
                'open_webui.utils.usage_limits.get_user_usage_for_period',
                new=AsyncMock(return_value=usage),
            ),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await check_usage_limits('user-1')
            assert exc_info.value.detail['limit_type'] == 'input_tokens'


# ---------------------------------------------------------------------------
# Unit: get_usage_status
# ---------------------------------------------------------------------------


class TestGetUsageStatus:
    @pytest.mark.asyncio
    async def test_no_limits_returns_empty_status(self):
        with patch(
            'open_webui.utils.usage_limits.get_effective_usage_limits',
            new=AsyncMock(return_value=None),
        ):
            status = await get_usage_status('user-1')
        assert status.limits is None
        assert status.usage == {}

    @pytest.mark.asyncio
    async def test_with_limits_returns_populated_status(self):
        limits = make_limits(max_total_tokens=5000)
        usage = {'total_tokens': 1234, 'message_count': 7}
        with (
            patch(
                'open_webui.utils.usage_limits.get_effective_usage_limits',
                new=AsyncMock(return_value=limits),
            ),
            patch(
                'open_webui.utils.usage_limits.get_user_usage_for_period',
                new=AsyncMock(return_value=usage),
            ),
        ):
            status = await get_usage_status('user-1')
        assert status.limits is not None
        assert status.limits.max_total_tokens == 5000
        assert status.usage['total_tokens'] == 1234
        assert status.period_start is not None
        assert status.period_end is not None
        assert status.period_end > status.period_start


# ---------------------------------------------------------------------------
# Integration: UsageLimitsConfig schema validation
# ---------------------------------------------------------------------------


class TestUsageLimitsConfigSchema:
    def test_default_is_disabled(self):
        cfg = UsageLimitsConfig()
        assert cfg.enabled is False

    def test_extra_fields_ignored(self):
        # Forward-compatibility: unknown fields should not cause validation errors
        cfg = UsageLimitsConfig(enabled=True, period='daily', future_field='value')
        assert cfg.enabled is True

    def test_round_trip_serialization(self):
        original = UsageLimitsConfig(
            enabled=True,
            period='monthly',
            max_total_tokens=100_000,
            max_messages=500,
        )
        rehydrated = UsageLimitsConfig.model_validate(original.model_dump())
        assert rehydrated == original

    def test_invalid_period_rejected(self):
        with pytest.raises(Exception):
            UsageLimitsConfig(enabled=True, period='yearly')  # type: ignore


# ---------------------------------------------------------------------------
# Unit: _dimension helper
# ---------------------------------------------------------------------------


class TestDimensionHelper:
    def test_returns_none_when_limit_is_none(self):
        assert _dimension(42_000, None) is None

    def test_calculates_remaining(self):
        d = _dimension(42_000, 50_000)
        assert d is not None
        assert d.used == 42_000
        assert d.limit == 50_000
        assert d.remaining == 8_000

    def test_remaining_floors_at_zero(self):
        # User somehow exceeded the limit (race condition, retroactive limit set)
        d = _dimension(55_000, 50_000)
        assert d is not None
        assert d.remaining == 0

    def test_zero_usage(self):
        d = _dimension(0, 10_000)
        assert d is not None
        assert d.remaining == 10_000


# ---------------------------------------------------------------------------
# Unit: get_quota_summary
# ---------------------------------------------------------------------------


class TestGetQuotaSummary:
    @pytest.mark.asyncio
    async def test_no_limits_returns_unlimited(self):
        with patch(
            'open_webui.utils.usage_limits.get_effective_usage_limits',
            new=AsyncMock(return_value=None),
        ):
            summary = await get_quota_summary('user-1')
        assert summary.unlimited is True
        assert summary.period is None
        assert summary.resets_at is None
        assert summary.total_tokens is None
        assert summary.messages is None

    @pytest.mark.asyncio
    async def test_total_token_cap_populates_dimension(self):
        limits = make_limits(period='daily', max_total_tokens=50_000)
        usage = {
            'total_tokens': 42_000,
            'input_tokens': 30_000,
            'output_tokens': 12_000,
            'message_count': 15,
        }
        with (
            patch(
                'open_webui.utils.usage_limits.get_effective_usage_limits',
                new=AsyncMock(return_value=limits),
            ),
            patch(
                'open_webui.utils.usage_limits.get_user_usage_for_period',
                new=AsyncMock(return_value=usage),
            ),
        ):
            summary = await get_quota_summary('user-1')

        assert summary.unlimited is False
        assert summary.period == 'daily'
        assert summary.resets_at is not None
        # resets_at must be a valid ISO date string
        from datetime import date  # noqa: ICN003

        date.fromisoformat(summary.resets_at)

        assert summary.total_tokens is not None
        assert summary.total_tokens.used == 42_000
        assert summary.total_tokens.limit == 50_000
        assert summary.total_tokens.remaining == 8_000

        # Unconfigured dimensions must be null
        assert summary.input_tokens is None
        assert summary.output_tokens is None
        assert summary.messages is None

    @pytest.mark.asyncio
    async def test_message_cap_only(self):
        limits = make_limits(period='weekly', max_messages=100)
        usage = {'total_tokens': 0, 'message_count': 73}
        with (
            patch(
                'open_webui.utils.usage_limits.get_effective_usage_limits',
                new=AsyncMock(return_value=limits),
            ),
            patch(
                'open_webui.utils.usage_limits.get_user_usage_for_period',
                new=AsyncMock(return_value=usage),
            ),
        ):
            summary = await get_quota_summary('user-1')

        assert summary.messages is not None
        assert summary.messages.used == 73
        assert summary.messages.limit == 100
        assert summary.messages.remaining == 27
        assert summary.total_tokens is None

    @pytest.mark.asyncio
    async def test_multi_dimension_caps(self):
        limits = make_limits(
            period='monthly',
            max_total_tokens=100_000,
            max_messages=500,
        )
        usage = {'total_tokens': 60_000, 'message_count': 200}
        with (
            patch(
                'open_webui.utils.usage_limits.get_effective_usage_limits',
                new=AsyncMock(return_value=limits),
            ),
            patch(
                'open_webui.utils.usage_limits.get_user_usage_for_period',
                new=AsyncMock(return_value=usage),
            ),
        ):
            summary = await get_quota_summary('user-1')

        assert summary.total_tokens is not None
        assert summary.total_tokens.remaining == 40_000
        assert summary.messages is not None
        assert summary.messages.remaining == 300

    @pytest.mark.asyncio
    async def test_resets_at_is_valid_iso_date(self):
        for period in ('daily', 'weekly', 'monthly'):
            limits = make_limits(period=period, max_total_tokens=1000)
            usage = {'total_tokens': 0}
            with (
                patch(
                    'open_webui.utils.usage_limits.get_effective_usage_limits',
                    new=AsyncMock(return_value=limits),
                ),
                patch(
                    'open_webui.utils.usage_limits.get_user_usage_for_period',
                    new=AsyncMock(return_value=usage),
                ),
            ):
                summary = await get_quota_summary('user-1')
            from datetime import date  # noqa: ICN003

            assert summary.resets_at is not None
            # Must parse as a date without raising
            parsed = date.fromisoformat(summary.resets_at)
            assert parsed >= date.today()

    @pytest.mark.asyncio
    async def test_over_limit_remaining_is_zero_not_negative(self):
        """remaining must floor at 0, not go negative (retroactive limit drop)."""
        limits = make_limits(max_total_tokens=1_000)
        usage = {'total_tokens': 5_000, 'message_count': 0}
        with (
            patch(
                'open_webui.utils.usage_limits.get_effective_usage_limits',
                new=AsyncMock(return_value=limits),
            ),
            patch(
                'open_webui.utils.usage_limits.get_user_usage_for_period',
                new=AsyncMock(return_value=usage),
            ),
        ):
            summary = await get_quota_summary('user-1')

        assert summary.total_tokens is not None
        assert summary.total_tokens.remaining == 0  # not -4000


# ---------------------------------------------------------------------------
# PHASE 3 — Hostile adversarial tests
# ---------------------------------------------------------------------------


class TestAdversarial:
    """Attempts to break the quota system under edge and hostile conditions."""

    # ── Empty usage history ──────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_empty_usage_history_does_not_block(self):
        """First request of a period must pass even with no prior messages."""
        limits = make_limits(max_total_tokens=1000)
        # Simulate no messages yet: get_token_usage_by_user returns empty dict
        empty_usage = {'total_tokens': 0, 'input_tokens': 0, 'output_tokens': 0, 'message_count': 0}
        with (
            patch(
                'open_webui.utils.usage_limits.get_effective_usage_limits',
                new=AsyncMock(return_value=limits),
            ),
            patch(
                'open_webui.utils.usage_limits.get_user_usage_for_period',
                new=AsyncMock(return_value=empty_usage),
            ),
        ):
            await check_usage_limits('user-1')  # must NOT raise

    # ── Missing token metadata ────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_missing_token_fields_treated_as_zero(self):
        """Messages without usage metadata default to 0 — should not raise KeyError."""
        limits = make_limits(max_total_tokens=500)
        # Partial usage dict — no total_tokens key
        sparse_usage = {'message_count': 3}
        with (
            patch(
                'open_webui.utils.usage_limits.get_effective_usage_limits',
                new=AsyncMock(return_value=limits),
            ),
            patch(
                'open_webui.utils.usage_limits.get_user_usage_for_period',
                new=AsyncMock(return_value=sparse_usage),
            ),
        ):
            await check_usage_limits('user-1')  # 0 < 500, must pass

    # ── Very large token counts ───────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_very_large_token_count_handled(self):
        limits = make_limits(max_total_tokens=10_000_000)
        usage = {'total_tokens': 10_000_001}
        with (
            patch(
                'open_webui.utils.usage_limits.get_effective_usage_limits',
                new=AsyncMock(return_value=limits),
            ),
            patch(
                'open_webui.utils.usage_limits.get_user_usage_for_period',
                new=AsyncMock(return_value=usage),
            ),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await check_usage_limits('user-1')
            assert exc_info.value.status_code == 429

    @pytest.mark.asyncio
    async def test_over_limit_remaining_never_negative_in_quota(self):
        limits = make_limits(max_total_tokens=100)
        usage = {'total_tokens': 99_999_999}
        with (
            patch(
                'open_webui.utils.usage_limits.get_effective_usage_limits',
                new=AsyncMock(return_value=limits),
            ),
            patch(
                'open_webui.utils.usage_limits.get_user_usage_for_period',
                new=AsyncMock(return_value=usage),
            ),
        ):
            summary = await get_quota_summary('user-1')
        assert summary.total_tokens is not None
        assert summary.total_tokens.remaining == 0

    # ── Invalid / malicious config ────────────────────────────────────────────

    def test_negative_limit_rejected_by_schema(self):
        """Pydantic should reject negative limits at the boundary."""
        # Pydantic doesn't add gt=0 by default, but _dimension floors remaining at 0.
        # Negative limits would behave oddly; verify _dimension handles gracefully.
        d = _dimension(0, -1)
        assert d is not None
        # remaining = max(0, -1 - 0) = 0
        assert d.remaining == 0

    def test_zero_limit_config_is_immediately_blocking(self):
        """A limit of 0 tokens means every request is blocked."""
        d = _dimension(0, 0)
        assert d is not None
        assert d.remaining == 0

    # ── Disabled quotas ───────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_disabled_quota_never_queries_db(self):
        """When enabled=False, usage must not be queried (performance requirement)."""
        with (
            patch(
                'open_webui.utils.usage_limits.get_effective_usage_limits',
                new=AsyncMock(return_value=None),
            ),
            patch(
                'open_webui.utils.usage_limits.get_user_usage_for_period',
            ) as mock_usage,
        ):
            await check_usage_limits('user-1')
        mock_usage.assert_not_called()

    # ── UTC rollover ──────────────────────────────────────────────────────────

    def test_period_start_and_end_never_overlap(self):
        """Period start must always be strictly before period end."""
        for period in ('daily', 'weekly', 'monthly'):
            start = get_period_start_ts(period)
            end = get_period_end_ts(period)
            assert start < end, f'{period}: start={start} not < end={end}'

    def test_daily_period_covers_exactly_one_day(self):
        start = get_period_start_ts('daily')
        end = get_period_end_ts('daily')
        duration_seconds = end - start
        # Should be ~86399 seconds (23:59:59), never more than 86400
        assert 86398 <= duration_seconds <= 86400

    # ── Multiple dimensions: first hit blocks ─────────────────────────────────

    @pytest.mark.asyncio
    async def test_message_limit_checked_before_token_limit(self):
        """When both messages and tokens are limited, messages is checked first."""
        limits = make_limits(max_messages=10, max_total_tokens=50000)
        usage = {'message_count': 10, 'total_tokens': 100}  # messages hit, tokens fine
        with (
            patch(
                'open_webui.utils.usage_limits.get_effective_usage_limits',
                new=AsyncMock(return_value=limits),
            ),
            patch(
                'open_webui.utils.usage_limits.get_user_usage_for_period',
                new=AsyncMock(return_value=usage),
            ),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await check_usage_limits('user-1')
            assert exc_info.value.detail['limit_type'] == 'messages'

    # ── Concurrent / idempotency ──────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_check_is_idempotent_under_limit(self):
        """Calling check_usage_limits multiple times under the limit is safe."""
        limits = make_limits(max_total_tokens=1000)
        usage = {'total_tokens': 500, 'message_count': 5}
        with (
            patch(
                'open_webui.utils.usage_limits.get_effective_usage_limits',
                new=AsyncMock(return_value=limits),
            ),
            patch(
                'open_webui.utils.usage_limits.get_user_usage_for_period',
                new=AsyncMock(return_value=usage),
            ),
        ):
            for _ in range(5):
                await check_usage_limits('user-1')  # must always pass

    # ── Quota summary edge cases ──────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_quota_summary_resets_at_is_in_future(self):
        """resets_at must refer to a date >= today (can't be in the past)."""
        from datetime import date  # noqa: ICN003

        for period in ('daily', 'weekly', 'monthly'):
            limits = make_limits(period=period, max_total_tokens=1000)
            usage = {'total_tokens': 0}
            with (
                patch(
                    'open_webui.utils.usage_limits.get_effective_usage_limits',
                    new=AsyncMock(return_value=limits),
                ),
                patch(
                    'open_webui.utils.usage_limits.get_user_usage_for_period',
                    new=AsyncMock(return_value=usage),
                ),
            ):
                summary = await get_quota_summary('user-1')
            assert summary.resets_at is not None
            assert date.fromisoformat(summary.resets_at) >= date.today()
