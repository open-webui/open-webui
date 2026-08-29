"""
Calendar utilities.

RRULE expansion reusing the automation infra.
"""

import datetime as dt
import logging
from itertools import islice
from zoneinfo import ZoneInfo

from dateutil.rrule import HOURLY, MINUTELY, SECONDLY, rruleset, rrulestr
from open_webui.constants import ERROR_MESSAGES
from open_webui.utils.automations import _resolve_tz

log = logging.getLogger(__name__)

# The read path sees rules the validator never did: pre-existing rows and automation rrules
MAX_OCCURRENCES_SCANNED = 100_000


def validate_calendar_rrule(rrule_str: str) -> None:
    """Raise ValueError if the RRULE is unsupported, unparseable, or repeats more often than daily."""
    if 'EXRULE' in rrule_str.upper():
        raise ValueError(ERROR_MESSAGES.EXRULE_UNSUPPORTED)

    try:
        parsed = rrulestr(rrule_str, ignoretz=True)
    except Exception as e:
        raise ValueError(ERROR_MESSAGES.INVALID_RRULE(e))

    rules = parsed._rrule if isinstance(parsed, rruleset) else [parsed]
    for rule in rules:
        if rule._interval < 1:
            raise ValueError(ERROR_MESSAGES.INVALID_RRULE('INTERVAL must be a positive integer'))
        # BYHOUR/BYMINUTE/BYSECOND lists multiply a daily rule into a sub-daily one
        sub_daily = rule._freq in (HOURLY, MINUTELY, SECONDLY)
        if sub_daily or any(len(part or ()) > 1 for part in (rule._byhour, rule._byminute, rule._bysecond)):
            raise ValueError(ERROR_MESSAGES.CALENDAR_RRULE_TOO_FREQUENT)


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

    # An EXRULE can cancel every candidate, and a rule that yields nothing is never bounded by an occurrence ceiling
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

    # A DTSTART would re-anchor the rule anywhere the caller likes; drop it, tokenising on whitespace as dateutil does
    rule_without_dtstart = ' '.join(part for part in rrule_str.split() if not part.upper().startswith('DTSTART'))

    try:
        # Anchor to the event's real start so day-of-week / day-of-month are correct
        rule = rrulestr(rule_without_dtstart, dtstart=original_start, ignoretz=True)
    except Exception:
        log.warning(f'Failed to parse RRULE for event {event_dict.get("id")}: {rrule_str}')
        return [event_dict]

    original_end_ns = event_dict.get('end_at')
    duration_ns = (original_end_ns - original_start_ns) if original_end_ns else None

    instances = []
    scanned = 0
    previous_start = None  # INTERVAL=0 makes dateutil yield the same datetime forever

    # One forward pass; rule.after() would restart from dtstart on every call
    for occurrence_start in islice(rule, MAX_OCCURRENCES_SCANNED):
        scanned += 1
        if occurrence_start >= range_end or occurrence_start == previous_start or len(instances) >= max_instances:
            return instances

        previous_start = occurrence_start
        if occurrence_start < scan_start:
            continue

        instance_start_ns = int(occurrence_start.replace(tzinfo=user_timezone).timestamp() * 1_000_000_000)

        if instance_start_ns >= range_start_ns:
            instance = {
                **event_dict,
                'start_at': instance_start_ns,
                'end_at': (instance_start_ns + duration_ns) if duration_ns else None,
                'instance_id': f'{event_dict["id"]}_{instance_start_ns}',
            }
            instances.append(instance)

    if scanned >= MAX_OCCURRENCES_SCANNED:
        log.warning(f'Recurrence scan limit reached for event {event_dict.get("id")}: {rrule_str}')

    return instances


def ns_from_date(year: int, month: int, day: int, tz: str | None = None) -> int:
    """Create epoch nanoseconds from a date."""
    if tz:
        date_time = dt.datetime(year, month, day, tzinfo=ZoneInfo(tz))
    else:
        date_time = dt.datetime(year, month, day)
    return int(date_time.timestamp() * 1_000_000_000)
