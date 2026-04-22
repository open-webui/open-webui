import time
import logging
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import (
    Column,
    Text,
    JSON,
    Boolean,
    BigInteger,
    Index,
    UniqueConstraint,
    select,
    or_,
    exists,
    func,
    delete,
    update,
)
from sqlalchemy.ext.asyncio import AsyncSession

from open_webui.internal.db import Base, get_async_db_context
from open_webui.models.access_grants import AccessGrantModel, AccessGrants
from open_webui.models.groups import Groups
from open_webui.models.users import User, UserModel, UserResponse

log = logging.getLogger(__name__)


####################
# Calendar DB Schema
####################


class Calendar(Base):
    __tablename__ = 'calendar'

    id = Column(Text, primary_key=True)
    user_id = Column(Text, nullable=False)
    name = Column(Text, nullable=False)
    color = Column(Text, nullable=True)
    is_default = Column(Boolean, nullable=False, default=False)
    data = Column(JSON, nullable=True)
    meta = Column(JSON, nullable=True)

    created_at = Column(BigInteger, nullable=False)
    updated_at = Column(BigInteger, nullable=False)

    __table_args__ = (Index('ix_calendar_user', 'user_id'),)


class CalendarEvent(Base):
    __tablename__ = 'calendar_event'

    id = Column(Text, primary_key=True)
    calendar_id = Column(Text, nullable=False)
    user_id = Column(Text, nullable=False)
    title = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    start_at = Column(BigInteger, nullable=False)
    end_at = Column(BigInteger, nullable=True)
    all_day = Column(Boolean, nullable=False, default=False)
    rrule = Column(Text, nullable=True)
    color = Column(Text, nullable=True)
    location = Column(Text, nullable=True)
    data = Column(JSON, nullable=True)
    meta = Column(JSON, nullable=True)
    is_cancelled = Column(Boolean, nullable=False, default=False)

    created_at = Column(BigInteger, nullable=False)
    updated_at = Column(BigInteger, nullable=False)

    __table_args__ = (
        Index('ix_calendar_event_calendar', 'calendar_id', 'start_at'),
        Index('ix_calendar_event_user_date', 'user_id', 'start_at'),
    )


class CalendarEventAttendee(Base):
    __tablename__ = 'calendar_event_attendee'

    id = Column(Text, primary_key=True)
    event_id = Column(Text, nullable=False)
    user_id = Column(Text, nullable=False)
    status = Column(Text, nullable=False, default='pending')
    meta = Column(JSON, nullable=True)

    created_at = Column(BigInteger, nullable=False)
    updated_at = Column(BigInteger, nullable=False)

    __table_args__ = (
        UniqueConstraint('event_id', 'user_id', name='uq_event_attendee'),
        Index('ix_calendar_event_attendee_user', 'user_id', 'status'),
    )


####################
# Pydantic Models
####################


class CalendarModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    name: str
    color: Optional[str] = None
    is_default: bool = False
    is_system: bool = False

    data: Optional[dict] = None
    meta: Optional[dict] = None

    access_grants: list[AccessGrantModel] = Field(default_factory=list)

    created_at: int
    updated_at: int


class CalendarEventModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra='allow')

    id: str
    calendar_id: str
    user_id: str
    title: str
    description: Optional[str] = None
    start_at: int
    end_at: Optional[int] = None
    all_day: bool = False
    rrule: Optional[str] = None
    color: Optional[str] = None
    location: Optional[str] = None
    data: Optional[dict] = None
    meta: Optional[dict] = None
    is_cancelled: bool = False

    attendees: list['CalendarEventAttendeeModel'] = Field(default_factory=list)

    created_at: int
    updated_at: int


class CalendarEventAttendeeModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    event_id: str
    user_id: str
    status: str = 'pending'
    meta: Optional[dict] = None

    created_at: int
    updated_at: int


####################
# Forms
####################


class CalendarForm(BaseModel):
    name: str
    color: Optional[str] = None
    data: Optional[dict] = None
    meta: Optional[dict] = None
    access_grants: Optional[list[dict]] = None


class CalendarUpdateForm(BaseModel):
    name: Optional[str] = None
    color: Optional[str] = None
    data: Optional[dict] = None
    meta: Optional[dict] = None
    access_grants: Optional[list[dict]] = None


class CalendarEventForm(BaseModel):
    calendar_id: str
    title: str
    description: Optional[str] = None
    start_at: int
    end_at: Optional[int] = None
    all_day: bool = False
    rrule: Optional[str] = None
    color: Optional[str] = None
    location: Optional[str] = None
    data: Optional[dict] = None
    meta: Optional[dict] = None
    attendees: Optional[list[dict]] = None


class CalendarEventUpdateForm(BaseModel):
    calendar_id: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    start_at: Optional[int] = None
    end_at: Optional[int] = None
    all_day: Optional[bool] = None
    rrule: Optional[str] = None
    color: Optional[str] = None
    location: Optional[str] = None
    data: Optional[dict] = None
    meta: Optional[dict] = None
    is_cancelled: Optional[bool] = None
    attendees: Optional[list[dict]] = None


class RSVPForm(BaseModel):
    status: str  # 'accepted' | 'declined' | 'tentative' | 'pending'


####################
# Response Models
####################


class CalendarEventUserResponse(CalendarEventModel):
    user: Optional[UserResponse] = None


class CalendarEventListResponse(BaseModel):
    items: list[CalendarEventUserResponse]
    total: int


####################
# Table Operations
####################


class CalendarTable:
    async def _get_access_grants(self, calendar_id: str, db: Optional[AsyncSession] = None) -> list[AccessGrantModel]:
        return await AccessGrants.get_grants_by_resource('calendar', calendar_id, db=db)

    async def _to_calendar_model(
        self,
        cal: Calendar,
        access_grants: Optional[list[AccessGrantModel]] = None,
        db: Optional[AsyncSession] = None,
    ) -> CalendarModel:
        cal_data = CalendarModel.model_validate(cal).model_dump(exclude={'access_grants'})
        cal_data['access_grants'] = (
            access_grants if access_grants is not None else await self._get_access_grants(cal_data['id'], db=db)
        )
        return CalendarModel.model_validate(cal_data)

    async def get_or_create_defaults(self, user_id: str, db: Optional[AsyncSession] = None) -> list[CalendarModel]:
        """Return user's calendars, creating 'Personal' default if none exist."""
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(Calendar).filter(Calendar.user_id == user_id).order_by(Calendar.created_at.asc())
            )
            calendars = result.scalars().all()

            if calendars:
                return [CalendarModel.model_validate(c) for c in calendars]

            now = int(time.time_ns())
            cal = Calendar(
                id=str(uuid4()),
                user_id=user_id,
                name='Personal',
                color='#3b82f6',
                is_default=True,
                created_at=now,
                updated_at=now,
            )
            db.add(cal)
            await db.commit()
            return [CalendarModel.model_validate(cal)]

    async def get_calendars_by_user(self, user_id: str, db: Optional[AsyncSession] = None) -> list[CalendarModel]:
        """Owned + shared calendars."""
        async with get_async_db_context(db) as db:
            user_groups = await Groups.get_groups_by_member_id(user_id, db=db)
            user_group_ids = [g.id for g in user_groups]

            stmt = select(Calendar)
            stmt = AccessGrants.has_permission_filter(
                db=db,
                query=stmt,
                DocumentModel=Calendar,
                filter={'user_id': user_id, 'group_ids': user_group_ids},
                resource_type='calendar',
                permission='read',
            )
            stmt = stmt.order_by(Calendar.created_at.asc())

            result = await db.execute(stmt)
            calendars = result.scalars().all()

            if not calendars:
                return await self.get_or_create_defaults(user_id, db=db)

            cal_ids = [c.id for c in calendars]
            grants_map = await AccessGrants.get_grants_by_resources('calendar', cal_ids, db=db)

            return [await self._to_calendar_model(c, access_grants=grants_map.get(c.id, []), db=db) for c in calendars]

    async def get_calendar_by_id(self, id: str, db: Optional[AsyncSession] = None) -> Optional[CalendarModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(select(Calendar).filter(Calendar.id == id))
            cal = result.scalars().first()
            return await self._to_calendar_model(cal, db=db) if cal else None

    async def insert_new_calendar(
        self, user_id: str, form_data: CalendarForm, db: Optional[AsyncSession] = None
    ) -> Optional[CalendarModel]:
        async with get_async_db_context(db) as db:
            now = int(time.time_ns())
            cal = Calendar(
                id=str(uuid4()),
                user_id=user_id,
                name=form_data.name,
                color=form_data.color,
                is_default=False,
                data=form_data.data,
                meta=form_data.meta,
                created_at=now,
                updated_at=now,
            )
            db.add(cal)
            await db.commit()
            if form_data.access_grants is not None:
                await AccessGrants.set_access_grants('calendar', cal.id, form_data.access_grants, db=db)
            return await self._to_calendar_model(cal, db=db)

    async def update_calendar_by_id(
        self, id: str, form_data: CalendarUpdateForm, db: Optional[AsyncSession] = None
    ) -> Optional[CalendarModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(select(Calendar).filter(Calendar.id == id))
            cal = result.scalars().first()
            if not cal:
                return None

            update_data = form_data.model_dump(exclude_unset=True)
            if 'name' in update_data:
                cal.name = update_data['name']
            if 'color' in update_data:
                cal.color = update_data['color']
            if 'data' in update_data:
                cal.data = {**(cal.data or {}), **update_data['data']}
            if 'meta' in update_data:
                cal.meta = {**(cal.meta or {}), **update_data['meta']}
            if 'access_grants' in update_data:
                await AccessGrants.set_access_grants('calendar', id, update_data['access_grants'], db=db)

            cal.updated_at = int(time.time_ns())
            await db.commit()
            return await self._to_calendar_model(cal, db=db)

    async def set_default_calendar(
        self, user_id: str, calendar_id: str, db: Optional[AsyncSession] = None
    ) -> Optional[CalendarModel]:
        """Set a calendar as the user's default, clearing all others."""
        async with get_async_db_context(db) as db:
            # Clear all defaults for this user
            await db.execute(
                update(Calendar)
                .where(Calendar.user_id == user_id, Calendar.is_default == True)
                .values(is_default=False)
            )
            # Set the new default
            result = await db.execute(select(Calendar).filter(Calendar.id == calendar_id, Calendar.user_id == user_id))
            cal = result.scalars().first()
            if not cal:
                return None
            cal.is_default = True
            cal.updated_at = int(time.time_ns())
            await db.commit()
            return await self._to_calendar_model(cal, db=db)

    async def delete_calendar_by_id(self, id: str, db: Optional[AsyncSession] = None) -> bool:
        """Delete a non-default calendar. Cascades to events, attendees, and grants."""
        try:
            async with get_async_db_context(db) as db:
                result = await db.execute(select(Calendar).filter(Calendar.id == id))
                cal = result.scalars().first()
                if not cal or cal.is_default:
                    return False

                # Delete attendees for all events in this calendar
                event_ids_result = await db.execute(select(CalendarEvent.id).filter(CalendarEvent.calendar_id == id))
                event_ids = [r[0] for r in event_ids_result.all()]
                if event_ids:
                    await db.execute(
                        delete(CalendarEventAttendee).filter(CalendarEventAttendee.event_id.in_(event_ids))
                    )

                # Delete events
                await db.execute(delete(CalendarEvent).filter(CalendarEvent.calendar_id == id))

                # Delete access grants
                await AccessGrants.revoke_all_access('calendar', id, db=db)

                # Delete calendar
                await db.execute(delete(Calendar).filter(Calendar.id == id))
                await db.commit()
                return True
        except Exception:
            return False


class CalendarEventTable:
    async def _get_attendees(
        self, event_id: str, db: Optional[AsyncSession] = None
    ) -> list[CalendarEventAttendeeModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(select(CalendarEventAttendee).filter(CalendarEventAttendee.event_id == event_id))
            rows = result.scalars().all()
            return [CalendarEventAttendeeModel.model_validate(r) for r in rows]

    async def _to_event_model(
        self,
        event: CalendarEvent,
        attendees: Optional[list[CalendarEventAttendeeModel]] = None,
        db: Optional[AsyncSession] = None,
    ) -> CalendarEventModel:
        event_data = CalendarEventModel.model_validate(event).model_dump(exclude={'attendees'})
        event_data['attendees'] = (
            attendees if attendees is not None else await self._get_attendees(event_data['id'], db=db)
        )
        return CalendarEventModel.model_validate(event_data)

    async def insert_new_event(
        self, user_id: str, form_data: CalendarEventForm, db: Optional[AsyncSession] = None
    ) -> Optional[CalendarEventModel]:
        async with get_async_db_context(db) as db:
            now = int(time.time_ns())
            event = CalendarEvent(
                id=str(uuid4()),
                calendar_id=form_data.calendar_id,
                user_id=user_id,
                title=form_data.title,
                description=form_data.description,
                start_at=form_data.start_at,
                end_at=form_data.end_at,
                all_day=form_data.all_day,
                rrule=form_data.rrule,
                color=form_data.color,
                location=form_data.location,
                data=form_data.data,
                meta=form_data.meta,
                is_cancelled=False,
                created_at=now,
                updated_at=now,
            )
            db.add(event)
            await db.commit()

            # Add attendees
            if form_data.attendees:
                await CalendarEventAttendees.set_attendees(event.id, form_data.attendees, db=db)

            return await self._to_event_model(event, db=db)

    async def get_event_by_id(self, id: str, db: Optional[AsyncSession] = None) -> Optional[CalendarEventModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(select(CalendarEvent).filter(CalendarEvent.id == id))
            event = result.scalars().first()
            return await self._to_event_model(event, db=db) if event else None

    async def get_events_by_range(
        self,
        user_id: str,
        start: int,
        end: int,
        calendar_ids: Optional[list[str]] = None,
        db: Optional[AsyncSession] = None,
    ) -> list[CalendarEventUserResponse]:
        """Fetch events visible to user within a date range.

        Visible events = events in owned/shared calendars + events user attends.
        Recurring events are fetched if they have any rrule (expansion in Python).
        """
        async with get_async_db_context(db) as db:
            user_groups = await Groups.get_groups_by_member_id(user_id, db=db)
            user_group_ids = [g.id for g in user_groups]

            # Get calendar IDs accessible to user
            cal_stmt = select(Calendar.id)
            cal_stmt = AccessGrants.has_permission_filter(
                db=db,
                query=cal_stmt,
                DocumentModel=Calendar,
                filter={'user_id': user_id, 'group_ids': user_group_ids},
                resource_type='calendar',
                permission='read',
            )
            cal_result = await db.execute(cal_stmt)
            accessible_cal_ids = [r[0] for r in cal_result.all()]

            if calendar_ids:
                # Filter to requested calendars only
                accessible_cal_ids = [c for c in accessible_cal_ids if c in calendar_ids]

            # Also get event IDs where user is an attendee
            attendee_event_ids_result = await db.execute(
                select(CalendarEventAttendee.event_id).filter(CalendarEventAttendee.user_id == user_id)
            )
            attendee_event_ids = [r[0] for r in attendee_event_ids_result.all()]

            # Build conditions for accessible events
            conditions = []
            if accessible_cal_ids:
                conditions.append(CalendarEvent.calendar_id.in_(accessible_cal_ids))
            if attendee_event_ids:
                conditions.append(CalendarEvent.id.in_(attendee_event_ids))

            if not conditions:
                return []

            # Build event query
            stmt = (
                select(CalendarEvent, User)
                .outerjoin(User, User.id == CalendarEvent.user_id)
                .filter(
                    CalendarEvent.is_cancelled == False,
                    or_(*conditions),
                    or_(
                        # Non-recurring: overlaps the range
                        (
                            CalendarEvent.rrule.is_(None)
                            & (CalendarEvent.start_at < end)
                            & or_(
                                CalendarEvent.end_at.is_(None) & (CalendarEvent.start_at >= start),
                                CalendarEvent.end_at.isnot(None) & (CalendarEvent.end_at > start),
                            )
                        ),
                        # Recurring: fetch all (expansion in Python)
                        CalendarEvent.rrule.isnot(None),
                    ),
                )
                .order_by(CalendarEvent.start_at.asc())
            )

            result = await db.execute(stmt)
            items = result.all()

            if not items:
                return []

            # Batch-load attendees for all events in one query (avoid N+1)
            event_ids = [event.id for event, _user in items]
            att_result = await db.execute(
                select(CalendarEventAttendee).filter(CalendarEventAttendee.event_id.in_(event_ids))
            )
            att_rows = att_result.scalars().all()
            att_map: dict[str, list[CalendarEventAttendeeModel]] = {}
            for a in att_rows:
                att_map.setdefault(a.event_id, []).append(CalendarEventAttendeeModel.model_validate(a))

            events = []
            for event, user in items:
                event_data = CalendarEventModel.model_validate(event).model_dump(exclude={'attendees'})
                event_data['attendees'] = att_map.get(event.id, [])
                events.append(
                    CalendarEventUserResponse(
                        **event_data,
                        user=(UserResponse(**UserModel.model_validate(user).model_dump()) if user else None),
                    )
                )

            return events

    async def search_events(
        self,
        user_id: str,
        query: Optional[str] = None,
        skip: int = 0,
        limit: int = 30,
        db: Optional[AsyncSession] = None,
    ) -> CalendarEventListResponse:
        async with get_async_db_context(db) as db:
            user_groups = await Groups.get_groups_by_member_id(user_id, db=db)
            user_group_ids = [g.id for g in user_groups]

            # Get accessible calendar IDs
            cal_stmt = select(Calendar.id)
            cal_stmt = AccessGrants.has_permission_filter(
                db=db,
                query=cal_stmt,
                DocumentModel=Calendar,
                filter={'user_id': user_id, 'group_ids': user_group_ids},
                resource_type='calendar',
                permission='read',
            )
            cal_result = await db.execute(cal_stmt)
            accessible_cal_ids = [r[0] for r in cal_result.all()]
            if not accessible_cal_ids:
                return CalendarEventListResponse(items=[], total=0)

            stmt = (
                select(CalendarEvent, User)
                .outerjoin(User, User.id == CalendarEvent.user_id)
                .filter(
                    CalendarEvent.is_cancelled == False,
                    CalendarEvent.calendar_id.in_(accessible_cal_ids),
                )
            )

            if query:
                search = f'%{query}%'
                stmt = stmt.filter(
                    or_(
                        CalendarEvent.title.ilike(search),
                        CalendarEvent.description.ilike(search),
                        CalendarEvent.location.ilike(search),
                    )
                )

            stmt = stmt.order_by(CalendarEvent.start_at.desc())

            count_result = await db.execute(select(func.count()).select_from(stmt.subquery()))
            total = count_result.scalar()

            if skip:
                stmt = stmt.offset(skip)
            if limit:
                stmt = stmt.limit(limit)

            result = await db.execute(stmt)
            items = result.all()

            if not items:
                return CalendarEventListResponse(items=[], total=total)

            # Batch-load attendees
            event_ids = [event.id for event, _user in items]
            att_result = await db.execute(
                select(CalendarEventAttendee).filter(CalendarEventAttendee.event_id.in_(event_ids))
            )
            att_rows = att_result.scalars().all()
            att_map: dict[str, list[CalendarEventAttendeeModel]] = {}
            for a in att_rows:
                att_map.setdefault(a.event_id, []).append(CalendarEventAttendeeModel.model_validate(a))

            events = []
            for event, user in items:
                event_data = CalendarEventModel.model_validate(event).model_dump(exclude={'attendees'})
                event_data['attendees'] = att_map.get(event.id, [])
                events.append(
                    CalendarEventUserResponse(
                        **event_data,
                        user=(UserResponse(**UserModel.model_validate(user).model_dump()) if user else None),
                    )
                )

            return CalendarEventListResponse(items=events, total=total)

    async def update_event_by_id(
        self, id: str, form_data: CalendarEventUpdateForm, db: Optional[AsyncSession] = None
    ) -> Optional[CalendarEventModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(select(CalendarEvent).filter(CalendarEvent.id == id))
            event = result.scalars().first()
            if not event:
                return None

            update_data = form_data.model_dump(exclude_unset=True)
            for field in [
                'calendar_id',
                'title',
                'description',
                'start_at',
                'end_at',
                'all_day',
                'rrule',
                'color',
                'location',
                'is_cancelled',
            ]:
                if field in update_data:
                    setattr(event, field, update_data[field])

            if 'data' in update_data and update_data['data'] is not None:
                event.data = {**(event.data or {}), **update_data['data']}
            if 'meta' in update_data and update_data['meta'] is not None:
                event.meta = {**(event.meta or {}), **update_data['meta']}

            if 'attendees' in update_data and update_data['attendees'] is not None:
                await CalendarEventAttendees.set_attendees(id, update_data['attendees'], db=db)

            event.updated_at = int(time.time_ns())
            await db.commit()
            return await self._to_event_model(event, db=db)

    async def get_upcoming_events(
        self,
        now_ns: int,
        default_lookahead_ns: int,
        db: Optional[AsyncSession] = None,
    ) -> list[tuple[CalendarEventModel, Optional[str]]]:
        """Events starting between now and now + lookahead, for alert processing.

        Per-event lookahead is read from meta.alert_minutes (falls back to
        default_lookahead_ns).  Returns (event, user_timezone) pairs.
        """
        from open_webui.models.users import User as UserRow

        # Use the maximum possible lookahead (60 min) to cast a wide net;
        # per-event filtering happens in Python after fetching.
        max_lookahead_ns = max(default_lookahead_ns, 60 * 60 * 1_000_000_000)
        upper = now_ns + max_lookahead_ns

        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(CalendarEvent, UserRow.timezone)
                .outerjoin(UserRow, UserRow.id == CalendarEvent.user_id)
                .filter(
                    CalendarEvent.is_cancelled == False,
                    CalendarEvent.start_at >= now_ns,
                    CalendarEvent.start_at <= upper,
                )
            )
            rows = result.all()

        events = []
        for event, tz in rows:
            model = CalendarEventModel.model_validate(event)
            # Determine per-event alert window
            alert_minutes = None
            if model.meta and 'alert_minutes' in model.meta:
                alert_minutes = model.meta['alert_minutes']

            if alert_minutes is not None:
                if alert_minutes < 0:
                    # alert_minutes < 0 means "no alert"
                    continue
                event_lookahead_ns = alert_minutes * 60 * 1_000_000_000
            else:
                event_lookahead_ns = default_lookahead_ns

            if model.start_at <= now_ns + event_lookahead_ns:
                events.append((model, tz))

        return events

    async def delete_event_by_id(self, id: str, db: Optional[AsyncSession] = None) -> bool:
        try:
            async with get_async_db_context(db) as db:
                await db.execute(delete(CalendarEventAttendee).filter(CalendarEventAttendee.event_id == id))
                await db.execute(delete(CalendarEvent).filter(CalendarEvent.id == id))
                await db.commit()
                return True
        except Exception:
            return False


class CalendarEventAttendeeTable:
    async def set_attendees(
        self, event_id: str, attendees: list[dict], db: Optional[AsyncSession] = None
    ) -> list[CalendarEventAttendeeModel]:
        """Replace all attendees for an event.

        Each dict in attendees: {user_id: str, status?: str, meta?: dict}
        """
        async with get_async_db_context(db) as db:
            # Remove existing
            await db.execute(delete(CalendarEventAttendee).filter(CalendarEventAttendee.event_id == event_id))

            now = int(time.time_ns())
            models = []
            for att in attendees:
                row = CalendarEventAttendee(
                    id=str(uuid4()),
                    event_id=event_id,
                    user_id=att['user_id'],
                    status=att.get('status', 'pending'),
                    meta=att.get('meta'),
                    created_at=now,
                    updated_at=now,
                )
                db.add(row)
                models.append(CalendarEventAttendeeModel.model_validate(row))

            await db.commit()
            return models

    async def update_rsvp(
        self, event_id: str, user_id: str, status: str, db: Optional[AsyncSession] = None
    ) -> Optional[CalendarEventAttendeeModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(CalendarEventAttendee).filter(
                    CalendarEventAttendee.event_id == event_id,
                    CalendarEventAttendee.user_id == user_id,
                )
            )
            att = result.scalars().first()
            if not att:
                return None

            att.status = status
            att.updated_at = int(time.time_ns())
            await db.commit()
            return CalendarEventAttendeeModel.model_validate(att)

    async def get_attendees_by_event(
        self, event_id: str, db: Optional[AsyncSession] = None
    ) -> list[CalendarEventAttendeeModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(select(CalendarEventAttendee).filter(CalendarEventAttendee.event_id == event_id))
            return [CalendarEventAttendeeModel.model_validate(r) for r in result.scalars().all()]

    async def get_events_by_attendee(self, user_id: str, db: Optional[AsyncSession] = None) -> list[str]:
        """Return event IDs where user is an attendee."""
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(CalendarEventAttendee.event_id).filter(CalendarEventAttendee.user_id == user_id)
            )
            return [r[0] for r in result.all()]


Calendars = CalendarTable()
CalendarEvents = CalendarEventTable()
CalendarEventAttendees = CalendarEventAttendeeTable()
