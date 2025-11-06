import time
import uuid

from open_webui.internal.db import Base, get_db
from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Column, Text, Index


class AssignmentSessionActivity(Base):
    __tablename__ = "assignment_session_activity"

    id = Column(Text, primary_key=True)
    user_id = Column(Text, nullable=False)
    session_number = Column(BigInteger, nullable=False, default=1)
    active_ms_delta = Column(BigInteger, nullable=False, default=0)
    cumulative_ms = Column(BigInteger, nullable=False, default=0)
    created_at = Column(BigInteger, nullable=False)

    __table_args__ = (
        Index("idx_assignment_activity_user_session", "user_id", "session_number"),
        Index("idx_assignment_activity_created_at", "created_at"),
    )


class AssignmentSessionActivityForm(BaseModel):
    user_id: str
    session_number: int
    active_ms_cumulative: int


class AssignmentSessionActivityModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    session_number: int
    active_ms_delta: int
    cumulative_ms: int
    created_at: int


class AssignmentSessionActivityTable:
    def add_activity(self, form: AssignmentSessionActivityForm) -> AssignmentSessionActivityModel:
        with get_db() as db:
            ts = int(time.time() * 1000)
            # Fetch last cumulative for this user/session
            last = (
                db.query(AssignmentSessionActivity)
                .filter(
                    AssignmentSessionActivity.user_id == form.user_id,
                    AssignmentSessionActivity.session_number == form.session_number,
                )
                .order_by(AssignmentSessionActivity.created_at.desc())
                .first()
            )
            last_cum = int(getattr(last, "cumulative_ms", 0) or 0)
            incoming = max(0, int(form.active_ms_cumulative))
            delta = max(0, incoming - last_cum)
            obj = AssignmentSessionActivity(
                id=str(uuid.uuid4()),
                user_id=form.user_id,
                session_number=int(form.session_number),
                active_ms_delta=delta,
                cumulative_ms=incoming,
                created_at=ts,
            )
            db.add(obj)
            db.commit()
            db.refresh(obj)
            return AssignmentSessionActivityModel.model_validate(obj)


AssignmentSessionActivities = AssignmentSessionActivityTable()



