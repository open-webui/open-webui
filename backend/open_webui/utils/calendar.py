"""
Calendar utilities.

RRULE expansion reusing the automation infra.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

log = logging.getLogger(__name__)

# Frequencies whose occurrences are exactly dtstart + k*interval, so the anchor can be moved
# forward in whole intervals without changing which occurrences fall in the query window.
_FIXED_PERIODS = {
    'SECONDLY': timedelta(seconds=1),
    'MINUTELY': timedelta(minutes=1),
    'HOURLY': timedelta(hours=1),
    'DAILY': timedelta(days=1),
    'WEEKLY': timedelta(weeks=1),
}

# Occurrences walked per event before giving up. A security budget, not a capacity estimate:
# it bounds a rule that cannot be re-anchored, at the cost of under-reporting a pathological one.
_MAX_SCAN = 50_000


def _anchor_near(rrule_str: str, dtstart: datetime, target: datetime) -> datetime:
    """Skip whole intervals so enumeration does not start decades before the query window.

    Applies only to plain fixed-period rules, where the occurrence set at and after *target* is
    unchanged by the move. COUNT is excluded because it counts from dtstart.
    """
    if dtstart >= target:
        return dtstart

    # Upper-cased because dateutil treats rule names case-insensitively, so a lowercase 'count='
    # would otherwise slip past the exclusions below and be re-anchored.
    parts = dict(p.split('=', 1) for p in rrule_str.upper().replace('RRULE:', '').split(';') if '=' in p)
    period = _FIXED_PERIODS.get(parts.get('FREQ', ''))
    if period is None or 'COUNT' in parts or any(key.startswith('BY') for key in parts):
        return dtstart
    try:
        interval = int(parts.get('INTERVAL', '1'))
    except ValueError:
        return dtstart
    if interval < 1:
        return dtstart

    step = period * interval
    return dtstart + ((target - dtstart) // step) * step


def expand_recurring_event(
    event_dict: dict,
    range_start_ns: int,
    range_end_ns: int,
    tz: Optional[str] = None,
    max_instances: int = 5000,
) -> list[dict]:
    """Expand a recurring event into individual instances within a date range.

    Takes an event dict (from CalendarEventModel.model_dump()) and produces
    one dict per occurrence, with adjusted start_at / end_at.
    """
    from dateutil.rrule import rrulestr

    rrule_str = event_dict.get('rrule')
    if not rrule_str:
        return [event_dict]

    # An EXRULE that cancels its RRULE makes the ruleset advance forever without yielding, which
    # an occurrence budget cannot catch. Nothing in the product emits one.
    if 'EXRULE' in rrule_str.upper():
        log.warning(f'Rejected EXRULE in RRULE for event {event_dict.get("id")}: {rrule_str}')
        return [event_dict]

    range_start_dt = datetime.fromtimestamp(range_start_ns / 1_000_000_000)
    range_end_dt = datetime.fromtimestamp(range_end_ns / 1_000_000_000)
    scan_start = range_start_dt - timedelta(days=1)

    original_start_ns = event_dict['start_at']
    original_start_dt = datetime.fromtimestamp(original_start_ns / 1_000_000_000)

    try:
        # Keep the event's real start as the phase reference, moved forward per _anchor_near.
        dtstart = _anchor_near(rrule_str, original_start_dt, scan_start)
        rule = rrulestr(rrule_str, dtstart=dtstart, ignoretz=True)
    except Exception:
        log.warning(f'Failed to parse RRULE for event {event_dict.get("id")}: {rrule_str}')
        return [event_dict]

    original_end_ns = event_dict.get('end_at')
    duration_ns = (original_end_ns - original_start_ns) if original_end_ns else None

    instances = []
    scanned = 0

    # Walk the rule once. Repeated rule.after() calls would re-enumerate from dtstart each time.
    for dt in rule:
        scanned += 1
        if scanned > _MAX_SCAN:
            log.warning(f'RRULE scan limit reached for event {event_dict.get("id")}: {rrule_str}')
            break
        if dt < scan_start:
            continue
        if dt >= range_end_dt or len(instances) >= max_instances:
            break

        if tz:
            try:
                dt_tz = dt.replace(tzinfo=ZoneInfo(tz))
                instance_start_ns = int(dt_tz.timestamp() * 1_000_000_000)
            except Exception:
                instance_start_ns = int(dt.timestamp() * 1_000_000_000)
        else:
            instance_start_ns = int(dt.timestamp() * 1_000_000_000)

        if instance_start_ns >= range_start_ns:
            instance = {
                **event_dict,
                'start_at': instance_start_ns,
                'end_at': (instance_start_ns + duration_ns) if duration_ns else None,
                'instance_id': f'{event_dict["id"]}_{instance_start_ns}',
            }
            instances.append(instance)

    return instances


def ns_from_date(year: int, month: int, day: int, tz: Optional[str] = None) -> int:
    """Create epoch nanoseconds from a date."""
    if tz:
        dt = datetime(year, month, day, tzinfo=ZoneInfo(tz))
    else:
        dt = datetime(year, month, day)
    return int(dt.timestamp() * 1_000_000_000)
