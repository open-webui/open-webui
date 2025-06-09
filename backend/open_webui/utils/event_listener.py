from open_webui.models.users import User, UserHistoricalEvents
from sqlalchemy import event
from sqlalchemy.dialects.postgresql import insert


def log_user_event(mapper, connection, target):
    """
    Logs the event (INSERT, UPDATE) for a User object into historical_user_events.
    """
    # Rounding of seconds to hr to keep the user last active at hr.
    last_active_at_hr = target.last_active_at - (target.last_active_at % 3600)
    historical_event = {
        "user_id": target.id,
        "user_email": target.email,
        "user_name": target.name,
        "active_at_hr": last_active_at_hr,
    }

    stmt = (
        insert(UserHistoricalEvents).values(**historical_event).on_conflict_do_nothing()
    )
    connection.execute(stmt)


def register_user_event_listener():
    event.listen(User, "after_update", log_user_event)
