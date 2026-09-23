"""Recurrence calculations isolated from application/DB imports for worker processes."""

import logging
from datetime import datetime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

from anyio import fail_after, to_process, to_thread
from dateutil.rrule import HOURLY, MINUTELY, SECONDLY, rruleset, rrulestr
from open_webui.constants import ERROR_MESSAGES

log = logging.getLogger(__name__)
RRULE_TIMEOUT_SECONDS = 2


class RecurrenceEvaluationTimeout(ValueError):
    """The evaluation budget expired; the schedule may still have occurrences."""


def _resolve_tz(tz: str = None) -> Optional[ZoneInfo]:
    """Safely resolve a timezone string to ZoneInfo.

    Returns None (→ server-local fallback) when *tz* is empty, None,
    or an unrecognised IANA key.  Logs a warning on bad keys so
    misconfiguration is visible in the server logs.
    """
    if not tz:
        return None
    try:
        return ZoneInfo(tz)
    except (KeyError, Exception):
        log.warning('Unknown timezone %r — falling back to server time', tz)
        return None


def _parse_rule(s: str, now: Optional[datetime] = None):
    """Parse RRULE with clock-aligned DTSTART for sub-daily frequencies.

    SECONDLY/MINUTELY/HOURLY rules use a fixed epoch DTSTART (2000-01-01 00:00)
    so intervals snap to clock boundaries (e.g. every 5min = :00, :05, :10).
    """
    upper = s.upper()
    if 'EXRULE' in upper:
        raise ValueError('EXRULE is not supported in recurrence rules')

    parsed = rrulestr(s, ignoretz=True)
    rules = parsed._rrule if isinstance(parsed, rruleset) else [parsed]
    if len(rules) > 1:
        raise ValueError('only one RRULE is supported per recurrence rule')

    rule = rules[0]
    start = rule._dtstart.replace(tzinfo=None)
    anchor = now or datetime.now()
    parts = s.split()
    stripped = '\n'.join(part for part in parts if not part.upper().startswith('DTSTART')) or s
    has_dtstart = any(part.upper().startswith('DTSTART') for part in parts)
    step = {
        SECONDLY: timedelta(seconds=rule._interval),
        MINUTELY: timedelta(minutes=rule._interval),
        HOURLY: timedelta(hours=rule._interval),
    }.get(rule._freq)

    if step is None:
        if not rule._dtstart.tzinfo:
            return parsed
        return rrulestr(stripped, dtstart=start, ignoretz=True)

    if rule._interval < 1:
        raise ValueError('RRULE INTERVAL must be a positive integer')
    dtstart = None
    if has_dtstart:
        emitted = ((anchor - start) // step) if anchor > start else 0
        emitted *= len(rule._byminute or (0,)) * len(rule._bysecond or (0,))
        if emitted <= 100_000:
            if rule._dtstart.tzinfo:
                dtstart = start
            else:
                return parsed
    if not has_dtstart or dtstart is None:
        epoch = datetime(2000, 1, 1)
        dtstart = epoch + ((anchor - epoch) // step) * step

    return rrulestr(stripped, dtstart=dtstart, ignoretz=True)


def _next_occurrences(s: str, now: datetime, n: int) -> list[datetime]:
    rule = _parse_rule(s, now)
    occurrences = []
    for _ in range(n):
        now = rule.after(now)
        if now is None:
            break
        occurrences.append(now)
    return occurrences


async def _get_next_occurrences(s: str, now: datetime, n: int) -> list[datetime]:
    # A result-count or date limit cannot bound work before the first match.
    try:
        with fail_after(RRULE_TIMEOUT_SECONDS):
            try:
                return await to_process.run_sync(_next_occurrences, s, now, n, cancellable=True)
            except (NotImplementedError, OSError):
                # Fall back to worker thread on Windows SelectorEventLoop or environments lacking subprocess worker support
                return await to_thread.run_sync(_next_occurrences, s, now, n)
    except TimeoutError as e:
        raise RecurrenceEvaluationTimeout('Schedule took too long to evaluate; simplify its recurrence rule.') from e


async def validate_rrule(s: str, tz: str = None) -> None:
    """Raise ValueError if the RRULE is malformed or exhausted.

    When *tz* is provided the "now" reference uses the user's local
    clock so that near-future schedules are not incorrectly rejected
    on servers whose system clock is ahead (e.g. UTC vs US timezones).
    """
    upper = s.upper()
    if 'COUNT=' in upper and 'DTSTART' not in upper:
        raise ValueError(ERROR_MESSAGES.AUTOMATION_COUNT_REQUIRES_DTSTART)
    zi = _resolve_tz(tz)
    now = datetime.now(zi).replace(tzinfo=None) if zi else datetime.now()
    try:
        occurrences = await _get_next_occurrences(s, now, 1)
    except RecurrenceEvaluationTimeout:
        raise
    except Exception as e:
        raise ValueError(ERROR_MESSAGES.AUTOMATION_INVALID_RRULE(e))
    if not occurrences:
        raise ValueError(ERROR_MESSAGES.AUTOMATION_NO_FUTURE_RUNS)


async def next_run_ns(s: str, tz: str = None) -> Optional[int]:
    """Next occurrence as epoch nanoseconds, respecting user timezone."""
    zi = _resolve_tz(tz)
    now = datetime.now(zi) if zi else datetime.now()
    now_naive = now.replace(tzinfo=None)
    occurrences = await _get_next_occurrences(s, now_naive, 1)
    if not occurrences:
        return None
    dt = occurrences[0]
    if zi:
        dt = dt.replace(tzinfo=zi)
    return int(dt.timestamp() * 1_000_000_000)


async def next_n_runs_ns(s: str, n: int = 5, tz: str = None) -> list[int]:
    """Compute next N occurrences for UI preview.

    Uses the user's timezone for the starting "now" so that the
    preview matches the user's local clock (same as next_run_ns).
    """
    zi = _resolve_tz(tz)
    result = []
    now = datetime.now(zi).replace(tzinfo=None) if zi else datetime.now()
    for dt in await _get_next_occurrences(s, now, n):
        if zi:
            dt_tz = dt.replace(tzinfo=zi)
            result.append(int(dt_tz.timestamp() * 1_000_000_000))
        else:
            result.append(int(dt.timestamp() * 1_000_000_000))
    return result


async def rrule_interval_seconds(s: str) -> Optional[int]:
    """Approximate interval between recurrences in seconds.

    Returns None for one-shot (COUNT=1) schedules or rules
    with fewer than two future occurrences.
    """
    s = '\n'.join(part for part in s.split() if not part.upper().startswith('DTSTART')) or s
    now = datetime.now()
    occurrences = await _get_next_occurrences(s, now, 2)
    if len(occurrences) < 2:
        return None
    return int((occurrences[1] - occurrences[0]).total_seconds())
