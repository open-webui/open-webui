"""OBS-02 proof of concept: state change and audit outbox row share one transaction.

Self-contained on purpose: importing ``open_webui.internal.db`` runs migrations
against ``DATABASE_URL``. The helpers below are the ones proposed for
``internal/db.py`` in docs/observability/Canchat-v2-OBS-02-Unit-of-Work.md; the table class
mirrors ``UsersTable`` after the refactor.
"""

import time
import uuid
from contextlib import contextmanager
from typing import Iterator, Optional

import pytest
from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Column, String, Text, create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

Base = declarative_base()

# Bound per test to a file-backed DB so sessions use separate connections.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False)


def get_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


get_db = contextmanager(get_session)


# --- Proposed helpers for internal/db.py ------------------------------------

_UOW_KEY = "canchat.unit_of_work"


@contextmanager
def unit_of_work(db: Optional[Session] = None) -> Iterator[Session]:
    if db is not None:
        # Join the caller's unit of work; the outermost block commits.
        if not db.info.get(_UOW_KEY):
            raise RuntimeError("unit_of_work(db) requires a unit-of-work session")
        yield db
        return
    with get_db() as session:
        session.info[_UOW_KEY] = True
        try:
            yield session
            session.commit()
        except BaseException:
            session.rollback()
            raise


@contextmanager
def get_db_context(db: Optional[Session] = None) -> Iterator[Session]:
    if db is None:
        with get_db() as session:
            yield session
        return
    if not db.info.get(_UOW_KEY):
        raise RuntimeError("Pass only sessions created by unit_of_work()")
    yield db


def commit_or_flush(db: Session) -> None:
    if db.info.get(_UOW_KEY):
        db.flush()
    else:
        db.commit()


# --- Tables -----------------------------------------------------------------


class User(Base):
    __tablename__ = "user"
    id = Column(String, primary_key=True)
    role = Column(String, nullable=False)


class GroupMember(Base):
    __tablename__ = "group_member"
    group_id = Column(String, primary_key=True)
    user_id = Column(String, primary_key=True)


class AuditOutbox(Base):
    __tablename__ = "audit_outbox"
    event_id = Column(String, primary_key=True)
    action = Column(String, nullable=False)
    target_id = Column(Text, nullable=True)
    created_at = Column(BigInteger, nullable=False)


class UserModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    role: str


class GroupsTable:
    def remove_user_from_all_groups(
        self, user_id: str, *, db: Optional[Session] = None
    ) -> bool:
        try:
            with get_db_context(db) as session:
                session.query(GroupMember).filter_by(user_id=user_id).delete()
                commit_or_flush(session)
                return True
        except Exception:
            if db is not None:
                raise
            return False


Groups = GroupsTable()


class UsersTable:
    def insert_new_user(
        self, id: str, role: str, *, db: Optional[Session] = None
    ) -> Optional[UserModel]:
        with get_db_context(db) as session:
            result = User(id=id, role=role)
            session.add(result)
            commit_or_flush(session)
            session.refresh(result)
            return UserModel.model_validate(result)

    def get_user_by_id(
        self, id: str, *, db: Optional[Session] = None
    ) -> Optional[UserModel]:
        try:
            with get_db_context(db) as session:
                user = session.query(User).filter_by(id=id).first()
                return UserModel.model_validate(user)
        except Exception:
            return None

    def update_user_role_by_id(
        self, id: str, role: str, *, db: Optional[Session] = None
    ) -> Optional[UserModel]:
        try:
            with get_db_context(db) as session:
                session.query(User).filter_by(id=id).update({"role": role})
                commit_or_flush(session)
                user = session.query(User).filter_by(id=id).first()
                return UserModel.model_validate(user)
        except Exception:
            if db is not None:
                raise
            return None

    def delete_user_by_id(self, id: str, *, db: Optional[Session] = None) -> bool:
        try:
            with get_db_context(db) as session:
                Groups.remove_user_from_all_groups(id, db=db)
                session.query(User).filter_by(id=id).delete()
                commit_or_flush(session)
                return True
        except Exception:
            if db is not None:
                raise
            return False


Users = UsersTable()

ALLOWED_ACTIONS = {"user.role_change", "user.delete"}


def emit_audit_event(db: Session, action: str, target_id: str) -> str:
    # Validate before touching the session so a schema error never leaves partial writes.
    if action not in ALLOWED_ACTIONS:
        raise ValueError(f"unknown audit action: {action}")
    event_id = str(uuid.uuid4())
    db.add(
        AuditOutbox(
            event_id=event_id,
            action=action,
            target_id=target_id,
            created_at=int(time.time()),
        )
    )
    db.flush()
    return event_id


# --- Tests ------------------------------------------------------------------


@pytest.fixture(autouse=True)
def fresh_schema(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'uow.db'}",
        connect_args={"check_same_thread": False},
    )
    SessionLocal.configure(bind=engine)
    Base.metadata.create_all(engine)
    Users.insert_new_user("u1", "user")
    with get_db() as db:
        db.add(GroupMember(group_id="g1", user_id="u1"))
        db.commit()
    yield
    engine.dispose()


def _outbox_rows() -> list[AuditOutbox]:
    with get_db() as db:
        return db.query(AuditOutbox).all()


def _group_member_count(user_id: str) -> int:
    with get_db() as db:
        return db.query(GroupMember).filter_by(user_id=user_id).count()


def test_legacy_call_without_session_still_commits_immediately():
    updated = Users.update_user_role_by_id("u1", "admin")

    assert updated.role == "admin"
    assert Users.get_user_by_id("u1").role == "admin"
    assert _outbox_rows() == []


def test_legacy_call_keeps_swallowing_errors():
    # role is NOT NULL; the pre-refactor contract returns None instead of raising.
    assert Users.update_user_role_by_id("u1", None) is None
    assert Users.get_user_by_id("u1").role == "user"


def test_state_change_and_outbox_row_commit_together():
    with unit_of_work() as db:
        Users.update_user_role_by_id("u1", "admin", db=db)
        event_id = emit_audit_event(db, "user.role_change", "u1")

        # Nothing is visible to other sessions until the unit of work commits.
        assert Users.get_user_by_id("u1").role == "user"
        assert _outbox_rows() == []

    assert Users.get_user_by_id("u1").role == "admin"
    assert [r.event_id for r in _outbox_rows()] == [event_id]


def test_audit_failure_rolls_back_state_change():
    with pytest.raises(ValueError):
        with unit_of_work() as db:
            Users.update_user_role_by_id("u1", "admin", db=db)
            emit_audit_event(db, "not.an.action", "u1")

    assert Users.get_user_by_id("u1").role == "user"
    assert _outbox_rows() == []


def test_failure_after_audit_write_rolls_back_both():
    with pytest.raises(RuntimeError):
        with unit_of_work() as db:
            Users.update_user_role_by_id("u1", "admin", db=db)
            emit_audit_event(db, "user.role_change", "u1")
            raise RuntimeError("request failed after both writes")

    assert Users.get_user_by_id("u1").role == "user"
    assert _outbox_rows() == []


def test_model_error_inside_unit_of_work_propagates_and_rolls_back():
    with pytest.raises(Exception):
        with unit_of_work() as db:
            emit_audit_event(db, "user.role_change", "u1")
            Users.update_user_role_by_id("u1", None, db=db)

    assert Users.get_user_by_id("u1").role == "user"
    assert _outbox_rows() == []


def test_nested_model_calls_share_the_transaction():
    with pytest.raises(RuntimeError):
        with unit_of_work() as db:
            Users.delete_user_by_id("u1", db=db)
            emit_audit_event(db, "user.delete", "u1")
            raise RuntimeError("abort")

    assert Users.get_user_by_id("u1") is not None
    assert _group_member_count("u1") == 1
    assert _outbox_rows() == []

    with unit_of_work() as db:
        assert Users.delete_user_by_id("u1", db=db) is True
        emit_audit_event(db, "user.delete", "u1")

    assert Users.get_user_by_id("u1") is None
    assert _group_member_count("u1") == 0
    assert len(_outbox_rows()) == 1


def test_nested_unit_of_work_joins_outer_transaction():
    with pytest.raises(RuntimeError):
        with unit_of_work() as outer:
            with unit_of_work(outer) as inner:
                assert inner is outer
                Users.update_user_role_by_id("u1", "admin", db=inner)
                emit_audit_event(inner, "user.role_change", "u1")
            raise RuntimeError("outer fails after inner block exits")

    assert Users.get_user_by_id("u1").role == "user"
    assert _outbox_rows() == []


def test_plain_session_is_rejected():
    with get_db() as db:
        with pytest.raises(RuntimeError):
            Users.insert_new_user("u2", "user", db=db)
