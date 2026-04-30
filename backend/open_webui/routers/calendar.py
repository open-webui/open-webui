import logging
import time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status

from open_webui.models.calendar import (
    Calendars,
    CalendarEvents,
    CalendarEventAttendees,
    CalendarForm,
    CalendarUpdateForm,
    CalendarEventForm,
    CalendarEventUpdateForm,
    CalendarModel,
    CalendarEventModel,
    CalendarEventUserResponse,
    CalendarEventListResponse,
    RSVPForm,
)
from open_webui.models.access_grants import AccessGrants
from open_webui.models.groups import Groups
from open_webui.models.users import UserModel
from open_webui.utils.auth import get_verified_user
from open_webui.utils.access_control import has_permission
from open_webui.utils.calendar import expand_recurring_event
from open_webui.constants import ERROR_MESSAGES

log = logging.getLogger(__name__)

router = APIRouter()

SCHEDULED_TASKS_CALENDAR_ID = '__scheduled_tasks__'


async def check_calendar_permission(request: Request, user):
    """Check global feature flag AND per-user permission for calendar access."""
    if not request.app.state.config.ENABLE_CALENDAR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )
    if user.role != 'admin' and not await has_permission(
        user.id, 'features.calendar', request.app.state.config.USER_PERMISSIONS
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )


async def _user_has_automations(request: Request, user) -> bool:
    """Check if automations feature is available to this user."""
    if not getattr(request.app.state.config, 'ENABLE_AUTOMATIONS', False):
        return False
    if user.role == 'admin':
        return True
    return await has_permission(user.id, 'features.automations', request.app.state.config.USER_PERMISSIONS)


async def _check_calendar_access(calendar_id: str, user: UserModel, permission: str = 'write') -> CalendarModel:
    """Verify user has access to a calendar. Returns the calendar or raises 403/404."""
    cal = await Calendars.get_calendar_by_id(calendar_id)
    if not cal:
        raise HTTPException(status_code=404, detail='Calendar not found')
    if cal.user_id == user.id or user.role == 'admin':
        return cal
    user_groups = await Groups.get_groups_by_member_id(user.id)
    user_group_ids = [g.id for g in user_groups]
    if await AccessGrants.has_access(
        user_id=user.id,
        resource_type='calendar',
        resource_id=cal.id,
        permission=permission,
        user_group_ids=user_group_ids,
    ):
        return cal
    raise HTTPException(status_code=403, detail='Access denied')


####################
# Calendar CRUD (static paths first)
####################


@router.get('/', response_model=list[CalendarModel])
async def get_calendars(request: Request, user: UserModel = Depends(get_verified_user)):
    """List user's calendars (owned + shared), plus a virtual Scheduled Tasks calendar
    when automations are available."""
    await check_calendar_permission(request, user)
    calendars = await Calendars.get_calendars_by_user(user.id)

    if await _user_has_automations(request, user):
        now = int(time.time_ns())
        calendars.append(
            CalendarModel(
                id=SCHEDULED_TASKS_CALENDAR_ID,
                user_id=user.id,
                name='Scheduled Tasks',
                color='#8b5cf6',
                is_default=False,
                is_system=True,
                created_at=now,
                updated_at=now,
            )
        )

    return calendars


@router.post('/create', response_model=CalendarModel)
async def create_calendar(request: Request, form_data: CalendarForm, user: UserModel = Depends(get_verified_user)):
    """Create a new user calendar."""
    await check_calendar_permission(request, user)
    return await Calendars.insert_new_calendar(user.id, form_data)


####################
# Event CRUD (before /{calendar_id} to avoid route conflicts)
####################


@router.get('/events')
async def get_events(
    request: Request,
    start: str,
    end: str,
    calendar_ids: Optional[str] = None,
    user: UserModel = Depends(get_verified_user),
):
    """Get events in date range.

    Args:
        start: ISO 8601 datetime string (e.g. 2026-04-01T00:00:00)
        end:   ISO 8601 datetime string (e.g. 2026-05-01T00:00:00)
        calendar_ids: optional comma-separated list to filter

    Includes:
    - Stored events from the database
    - Virtual events computed from active automation RRULEs (Scheduled Tasks calendar)
    """
    await check_calendar_permission(request, user)
    from datetime import datetime

    try:
        start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(end.replace('Z', '+00:00'))
    except ValueError:
        raise HTTPException(status_code=400, detail='Invalid date format. Use ISO 8601 (e.g. 2026-04-01T00:00:00)')

    NS = 1_000_000
    start_ns = int(start_dt.timestamp() * 1000) * NS
    end_ns = int(end_dt.timestamp() * 1000) * NS
    cal_id_list = calendar_ids.split(',') if calendar_ids else None

    # 1. Stored events
    events = await CalendarEvents.get_events_by_range(
        user_id=user.id,
        start=start_ns,
        end=end_ns,
        calendar_ids=cal_id_list,
    )

    # Expand recurring stored events
    expanded = []
    for event in events:
        event_dict = event.model_dump()
        if event_dict.get('rrule'):
            instances = expand_recurring_event(event_dict, start_ns, end_ns, tz=user.timezone)
            for inst in instances:
                expanded.append(CalendarEventUserResponse(**{**inst, 'user': event.user}))
        else:
            expanded.append(event)

    # 2. Virtual automation events (Scheduled Tasks calendar)
    if await _user_has_automations(request, user) and (
        cal_id_list is None or SCHEDULED_TASKS_CALENDAR_ID in cal_id_list
    ):
        try:
            from open_webui.models.automations import Automations, AutomationRuns

            # Future runs: expand RRULEs for active automations only
            active_automations = await Automations.get_active_by_user(user.id)
            for auto in active_automations:
                rrule_str = auto.data.get('rrule', '') if auto.data else ''
                if not rrule_str:
                    continue

                virtual = {
                    'id': f'auto_{auto.id}',
                    'calendar_id': SCHEDULED_TASKS_CALENDAR_ID,
                    'user_id': user.id,
                    'title': auto.name,
                    'description': auto.data.get('prompt', '') if auto.data else '',
                    'start_at': auto.next_run_at or 0,
                    'end_at': None,
                    'all_day': False,
                    'rrule': rrule_str,
                    'color': None,
                    'location': None,
                    'data': None,
                    'meta': {'automation_id': auto.id},
                    'is_cancelled': False,
                    'attendees': [],
                    'created_at': auto.created_at,
                    'updated_at': auto.updated_at,
                    'user': None,
                }

                # Only expand into the future — past runs are handled below
                now_ns = int(time.time_ns())
                rrule_start = max(start_ns, now_ns)
                instances = expand_recurring_event(virtual, rrule_start, end_ns, tz=user.timezone)
                for inst in instances:
                    expanded.append(CalendarEventUserResponse(**inst))

            # Past runs: single range query joined with automation
            runs_with_auto = await AutomationRuns.get_runs_by_user_range(user.id, start_ns, end_ns)
            for run, auto in runs_with_auto:
                expanded.append(
                    CalendarEventUserResponse(
                        id=f'run_{run.id}',
                        calendar_id=SCHEDULED_TASKS_CALENDAR_ID,
                        user_id=user.id,
                        title=auto.name,
                        description=run.error if run.status == 'error' else '',
                        start_at=run.created_at,
                        end_at=None,
                        all_day=False,
                        color=None,
                        location=None,
                        data=None,
                        meta={
                            'automation_id': auto.id,
                            'run_id': run.id,
                            'chat_id': run.chat_id,
                            'status': run.status,
                        },
                        is_cancelled=False,
                        attendees=[],
                        created_at=run.created_at,
                        updated_at=run.created_at,
                        user=None,
                    )
                )
        except Exception as e:
            log.warning(f'Failed to compute automation events: {e}', exc_info=True)

    return [e.model_dump() if hasattr(e, 'model_dump') else e for e in expanded]


@router.post('/events/create', response_model=CalendarEventModel)
async def create_event(request: Request, form_data: CalendarEventForm, user: UserModel = Depends(get_verified_user)):
    await check_calendar_permission(request, user)
    await _check_calendar_access(form_data.calendar_id, user, 'write')
    return await CalendarEvents.insert_new_event(user.id, form_data)


@router.get('/events/search', response_model=CalendarEventListResponse)
async def search_events(
    request: Request,
    query: Optional[str] = None,
    skip: int = 0,
    limit: int = 30,
    user: UserModel = Depends(get_verified_user),
):
    await check_calendar_permission(request, user)
    return await CalendarEvents.search_events(user_id=user.id, query=query, skip=skip, limit=limit)


@router.get('/events/{event_id}', response_model=CalendarEventModel)
async def get_event(request: Request, event_id: str, user: UserModel = Depends(get_verified_user)):
    await check_calendar_permission(request, user)
    event = await CalendarEvents.get_event_by_id(event_id)
    if not event:
        raise HTTPException(status_code=404, detail='Event not found')

    await _check_calendar_access(event.calendar_id, user, 'read')

    return event


@router.post('/events/{event_id}/update', response_model=CalendarEventModel)
async def update_event(
    request: Request, event_id: str, form_data: CalendarEventUpdateForm, user: UserModel = Depends(get_verified_user)
):
    await check_calendar_permission(request, user)
    event = await CalendarEvents.get_event_by_id(event_id)
    if not event:
        raise HTTPException(status_code=404, detail='Event not found')

    await _check_calendar_access(event.calendar_id, user, 'write')

    updated = await CalendarEvents.update_event_by_id(event_id, form_data)
    if not updated:
        raise HTTPException(status_code=500, detail='Failed to update')
    return updated


@router.delete('/events/{event_id}/delete')
async def delete_event(request: Request, event_id: str, user: UserModel = Depends(get_verified_user)):
    await check_calendar_permission(request, user)
    event = await CalendarEvents.get_event_by_id(event_id)
    if not event:
        raise HTTPException(status_code=404, detail='Event not found')

    await _check_calendar_access(event.calendar_id, user, 'write')

    result = await CalendarEvents.delete_event_by_id(event_id)
    if not result:
        raise HTTPException(status_code=500, detail='Failed to delete')
    return {'status': True}


@router.post('/events/{event_id}/rsvp', response_model=dict)
async def rsvp_event(
    request: Request, event_id: str, form_data: RSVPForm, user: UserModel = Depends(get_verified_user)
):
    """Update own RSVP status for an event."""
    await check_calendar_permission(request, user)
    if form_data.status not in ('accepted', 'declined', 'tentative', 'pending'):
        raise HTTPException(status_code=400, detail='Invalid status')

    result = await CalendarEventAttendees.update_rsvp(event_id, user.id, form_data.status)
    if not result:
        raise HTTPException(status_code=404, detail='Not an attendee of this event')
    return {'status': True, 'rsvp': result.status}


####################
# Calendar by ID (dynamic path — MUST come after /events* routes)
####################


@router.get('/{calendar_id}', response_model=CalendarModel)
async def get_calendar_by_id(request: Request, calendar_id: str, user: UserModel = Depends(get_verified_user)):
    await check_calendar_permission(request, user)
    cal = await _check_calendar_access(calendar_id, user, 'read')
    return cal


@router.post('/{calendar_id}/update', response_model=CalendarModel)
async def update_calendar(
    request: Request, calendar_id: str, form_data: CalendarUpdateForm, user: UserModel = Depends(get_verified_user)
):
    await check_calendar_permission(request, user)
    cal = await _check_calendar_access(calendar_id, user, 'write')

    # Only owner/admin can change access grants
    if form_data.access_grants is not None and cal.user_id != user.id and user.role != 'admin':
        raise HTTPException(status_code=403, detail='Only owner can manage sharing')

    updated = await Calendars.update_calendar_by_id(calendar_id, form_data)
    if not updated:
        raise HTTPException(status_code=500, detail='Failed to update')
    return updated


@router.delete('/{calendar_id}/delete')
async def delete_calendar(request: Request, calendar_id: str, user: UserModel = Depends(get_verified_user)):
    await check_calendar_permission(request, user)

    # Block deletion of the virtual Scheduled Tasks calendar
    if calendar_id == SCHEDULED_TASKS_CALENDAR_ID:
        raise HTTPException(status_code=400, detail='System calendars cannot be deleted')

    cal = await _check_calendar_access(calendar_id, user, 'write')

    # Only owner/admin can delete
    if cal.user_id != user.id and user.role != 'admin':
        raise HTTPException(status_code=403, detail='Only owner can delete calendar')

    # Block deletion of default calendar
    if cal.is_default:
        raise HTTPException(status_code=400, detail='Default calendar cannot be deleted')

    result = await Calendars.delete_calendar_by_id(calendar_id)
    if not result:
        raise HTTPException(status_code=500, detail='Failed to delete')
    return {'status': True}


@router.post('/{calendar_id}/default')
async def set_default_calendar(request: Request, calendar_id: str, user: UserModel = Depends(get_verified_user)):
    await check_calendar_permission(request, user)
    cal = await Calendars.set_default_calendar(user.id, calendar_id)
    if not cal:
        raise HTTPException(status_code=404, detail='Calendar not found')
    return cal
