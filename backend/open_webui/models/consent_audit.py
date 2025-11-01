import time
from typing import Optional
from sqlalchemy import Column, String, Text, BigInteger, Boolean
from sqlalchemy import Index
from open_webui.internal.db import Base, get_db
from pydantic import BaseModel, ConfigDict


class ConsentAudit(Base):
    __tablename__ = "consent_audit"

    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False)
    timestamp_utc = Column(BigInteger, nullable=False)
    consent_version = Column(String, nullable=True)
    prolific_pid = Column(String, nullable=True)
    study_id = Column(String, nullable=True)
    session_id = Column(String, nullable=True)
    ui_version = Column(String, nullable=True)
    user_agent = Column(Text, nullable=True)
    consent_given = Column(Boolean, nullable=False, default=False)

    __table_args__ = (
        Index("idx_consent_audit_user", "user_id"),
        Index("idx_consent_audit_timestamp", "timestamp_utc"),
        Index("idx_consent_audit_prolific", "prolific_pid"),
    )


class ConsentAuditModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    timestamp_utc: int
    consent_version: Optional[str] = None
    prolific_pid: Optional[str] = None
    study_id: Optional[str] = None
    session_id: Optional[str] = None
    ui_version: Optional[str] = None
    user_agent: Optional[str] = None
    consent_given: bool


class ConsentAuditForm(BaseModel):
    user_id: str
    consent_version: Optional[str] = None
    prolific_pid: Optional[str] = None
    study_id: Optional[str] = None
    session_id: Optional[str] = None
    ui_version: Optional[str] = None
    user_agent: Optional[str] = None
    consent_given: bool


class ConsentAuditTable:
    def create_consent_record(
        self, form: ConsentAuditForm
    ) -> Optional[ConsentAuditModel]:
        """
        Create a consent audit record with idempotency check.
        Returns existing record if one already exists for this user/session combination.
        """
        import uuid
        
        with get_db() as db:
            # Idempotency check: if user has already given consent for this session, return existing record
            if form.consent_given and form.prolific_pid and form.session_id:
                existing = (
                    db.query(ConsentAudit)
                    .filter_by(
                        user_id=form.user_id,
                        prolific_pid=form.prolific_pid,
                        session_id=form.session_id,
                        consent_given=True,
                    )
                    .first()
                )
                if existing:
                    return ConsentAuditModel.model_validate(existing)

            record_id = str(uuid.uuid4())
            timestamp = int(time.time())

            obj = ConsentAudit(
                id=record_id,
                user_id=form.user_id,
                timestamp_utc=timestamp,
                consent_version=form.consent_version,
                prolific_pid=form.prolific_pid,
                study_id=form.study_id,
                session_id=form.session_id,
                ui_version=form.ui_version,
                user_agent=form.user_agent,
                consent_given=form.consent_given,
            )

            db.add(obj)
            db.commit()
            db.refresh(obj)

            return ConsentAuditModel.model_validate(obj)

    def get_consent_records_by_user_id(
        self, user_id: str
    ) -> list[ConsentAuditModel]:
        with get_db() as db:
            records = (
                db.query(ConsentAudit)
                .filter_by(user_id=user_id)
                .order_by(ConsentAudit.timestamp_utc.desc())
                .all()
            )
            return [ConsentAuditModel.model_validate(record) for record in records]


ConsentAudits = ConsentAuditTable()

