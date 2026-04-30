"""
Calendar utilities.

RRULE expansion reusing the automation infra.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

from open_webui.utils.automations import _parse_rule

log = logging.getLogger(__name__)


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

    range_start_dt = datetime.fromtimestamp(range_start_ns / 1_000_000_000)
    range_end_dt = datetime.fromtimestamp(range_end_ns / 1_000_000_000)
    scan_start = range_start_dt - timedelta(days=1)

    try:
        # Parse with dtstart near the range so we never iterate from epoch
        rule = rrulestr(rrule_str, dtstart=scan_start, ignoretz=True)
    except Exception:
        log.warning(f'Failed to parse RRULE for event {event_dict.get("id")}: {rrule_str}')
        return [event_dict]

    original_start_ns = event_dict['start_at']
    original_end_ns = event_dict.get('end_at')
    duration_ns = (original_end_ns - original_start_ns) if original_end_ns else None

    instances = []
    dt = rule.after(scan_start, inc=True)

    while dt and dt < range_end_dt and len(instances) < max_instances:
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

        dt = rule.after(dt)

    return instances


def ns_from_date(year: int, month: int, day: int, tz: Optional[str] = None) -> int:
    """Create epoch nanoseconds from a date."""
    if tz:
        dt = datetime(year, month, day, tzinfo=ZoneInfo(tz))
    else:
        dt = datetime(year, month, day)
    return int(dt.timestamp() * 1_000_000_000)
