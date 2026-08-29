"""
Calendar utilities.

RRULE expansion reusing the automation infra.
"""

import datetime as dt
import logging
from zoneinfo import ZoneInfo

from dateutil.rrule import rrulestr
from open_webui.utils.automations import _resolve_tz

log = logging.getLogger(__name__)


def expand_recurring_event(
    event_dict: dict,
    range_start_ns: int,
    range_end_ns: int,
    tz: str | None = None,
    max_instances: int = 5000,
) -> list[dict]:
    """Expand a recurring event into individual instances within a date range.

    Takes an event dict (from CalendarEventModel.model_dump()) and produces
    one dict per occurrence, with adjusted start_at / end_at.
    """
    rrule_str = event_dict.get('rrule')
    if not rrule_str:
        return [event_dict]
    if 'EXRULE' in rrule_str.upper():
        log.warning(f'EXRULE is not supported for event {event_dict.get("id")}: {rrule_str}')
        return [event_dict]

    user_timezone = _resolve_tz(tz)

    def to_local_datetime(timestamp_ns: int) -> dt.datetime:
        return dt.datetime.fromtimestamp(timestamp_ns / 1_000_000_000, tz=user_timezone).replace(tzinfo=None)

    range_start = to_local_datetime(range_start_ns)
    range_end = to_local_datetime(range_end_ns)
    scan_start = range_start - dt.timedelta(days=1)

    original_start_ns = event_dict['start_at']
    original_start = to_local_datetime(original_start_ns)
    rule_str = '\n'.join(line for line in rrule_str.splitlines() if not line.upper().startswith('DTSTART')) or rrule_str

    try:
        # Anchor to the event's real start so day-of-week / day-of-month are correct
        rule = rrulestr(rule_str, dtstart=original_start, ignoretz=True)
    except Exception:
        log.warning(f'Failed to parse RRULE for event {event_dict.get("id")}: {rrule_str}')
        return [event_dict]

    original_end_ns = event_dict.get('end_at')
    duration_ns = (original_end_ns - original_start_ns) if original_end_ns else None

    instances = []
    previous_start = None
    for occurrence_start in rule.xafter(scan_start, count=max_instances, inc=True):
        if occurrence_start >= range_end or occurrence_start == previous_start:
            break
        previous_start = occurrence_start

        instance_start_ns = int(occurrence_start.replace(tzinfo=user_timezone).timestamp() * 1_000_000_000)

        if instance_start_ns >= range_start_ns:
            instance = {
                **event_dict,
                'start_at': instance_start_ns,
                'end_at': (instance_start_ns + duration_ns) if duration_ns else None,
                'instance_id': f'{event_dict["id"]}_{instance_start_ns}',
            }
            instances.append(instance)

    return instances


def ns_from_date(year: int, month: int, day: int, tz: str | None = None) -> int:
    """Create epoch nanoseconds from a date."""
    if tz:
        date_time = dt.datetime(year, month, day, tzinfo=ZoneInfo(tz))
    else:
        date_time = dt.datetime(year, month, day)
    return int(date_time.timestamp() * 1_000_000_000)
