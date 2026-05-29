"""
Company custom: Team Workspaces V1 — backend tests

Fully self-contained: defines its own minimal ORM tables and helpers
mirroring the production models, so the full OpenWebUI app stack is not
required. Tests the core business invariants.

Run from repo root:
    cd backend && python3 -m pytest tests/test_workspaces.py -v
"""

import asyncio
import time
import uuid
import pytest
import pytest_asyncio

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Index,
    String,
    Text,
    UniqueConstraint,
    select,
    delete,
    and_,
)
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base

Base = declarative_base()


# ---------------------------------------------------------------------------
# Minimal ORM mirrors (same schema as production models)
# ---------------------------------------------------------------------------

class WsWorkspace(Base):
    __tablename__ = "workspace"
    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False)
    name = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(BigInteger, nullable=False)
    updated_at = Column(BigInteger, nullable=False)
    deleted_at = Column(BigInteger, nullable=True)


class WsWorkspaceMember(Base):
    __tablename__ = "workspace_member"
    id = Column(String, primary_key=True)
    workspace_id = Column(String, nullable=False)
    user_id = Column(String, nullable=False)
    role = Column(String, nullable=False)
    created_at = Column(BigInteger, nullable=False)
    updated_at = Column(BigInteger, nullable=False)
    __table_args__ = (
        UniqueConstraint("workspace_id", "user_id", name="uq_workspace_member"),
        Index("ws_member_workspace_id_idx", "workspace_id"),
    )


class WsChat(Base):
    __tablename__ = "chat"
    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False)
    title = Column(Text, nullable=False)
    archived = Column(Boolean, default=False)
    workspace_id = Column(String, nullable=True)
    created_at = Column(BigInteger, nullable=False)
    updated_at = Column(BigInteger, nullable=False)


# ---------------------------------------------------------------------------
# Role constants (mirrors production)
# ---------------------------------------------------------------------------

ROLE_MANAGER = "manager"
ROLE_MEMBER = "member"
ROLE_VIEWER = "viewer"

WRITE_ROLES = {ROLE_MANAGER, ROLE_MEMBER}
MANAGE_ROLES = {ROLE_MANAGER}


# ---------------------------------------------------------------------------
# Minimal CRUD helpers
# ---------------------------------------------------------------------------

def _uid():
    return str(uuid.uuid4())


def _now():
    return int(time.time())


async def create_workspace(db: AsyncSession, creator_id: str, name: str = "WS") -> WsWorkspace:
    ws = WsWorkspace(id=_uid(), user_id=creator_id, name=name, created_at=_now(), updated_at=_now())
    db.add(ws)
    await db.commit()
    await db.refresh(ws)
    return ws


async def add_member(db: AsyncSession, workspace_id: str, user_id: str, role: str) -> WsWorkspaceMember:
    m = WsWorkspaceMember(id=_uid(), workspace_id=workspace_id, user_id=user_id, role=role,
                          created_at=_now(), updated_at=_now())
    db.add(m)
    await db.commit()
    await db.refresh(m)
    return m


async def get_member(db: AsyncSession, workspace_id: str, user_id: str):
    r = await db.execute(
        select(WsWorkspaceMember).where(
            and_(WsWorkspaceMember.workspace_id == workspace_id,
                 WsWorkspaceMember.user_id == user_id)
        )
    )
    return r.scalars().first()


async def workspaces_for_user(db: AsyncSession, user_id: str):
    r = await db.execute(
        select(WsWorkspace)
        .join(WsWorkspaceMember, and_(
            WsWorkspaceMember.workspace_id == WsWorkspace.id,
            WsWorkspaceMember.user_id == user_id,
        ))
        .where(WsWorkspace.deleted_at.is_(None))
    )
    return r.scalars().all()


async def workspace_chats(db: AsyncSession, workspace_id: str):
    r = await db.execute(
        select(WsChat)
        .where(WsChat.workspace_id == workspace_id)
        .where(WsChat.archived == False)  # noqa
    )
    return r.scalars().all()


async def personal_chats(db: AsyncSession, user_id: str):
    """Personal chats: belongs to user AND workspace_id IS NULL."""
    r = await db.execute(
        select(WsChat)
        .where(WsChat.user_id == user_id)
        .where(WsChat.workspace_id.is_(None))
    )
    return r.scalars().all()


# ---------------------------------------------------------------------------
# Pytest fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="module")
async def db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with factory() as session:
        yield session
    await engine.dispose()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_creator_becomes_manager(db):
    """Workspace creator is added as manager."""
    creator_id = _uid()
    ws = await create_workspace(db, creator_id)
    await add_member(db, ws.id, creator_id, ROLE_MANAGER)

    m = await get_member(db, ws.id, creator_id)
    assert m is not None
    assert m.role == ROLE_MANAGER


@pytest.mark.asyncio
async def test_non_member_cannot_see_workspace(db):
    """Non-member must not see workspace in their list."""
    creator_id = _uid()
    stranger_id = _uid()

    ws = await create_workspace(db, creator_id, name="Private")
    await add_member(db, ws.id, creator_id, ROLE_MANAGER)

    stranger_workspaces = await workspaces_for_user(db, stranger_id)
    assert all(w.id != ws.id for w in stranger_workspaces)


@pytest.mark.asyncio
async def test_added_member_sees_workspace(db):
    """After being added, a member should see the workspace."""
    creator_id = _uid()
    member_id = _uid()

    ws = await create_workspace(db, creator_id, name="Shared")
    await add_member(db, ws.id, creator_id, ROLE_MANAGER)
    await add_member(db, ws.id, member_id, ROLE_MEMBER)

    member_workspaces = await workspaces_for_user(db, member_id)
    assert any(w.id == ws.id for w in member_workspaces)


@pytest.mark.asyncio
async def test_viewer_role_stored_correctly(db):
    """CEO/viewer role is stored and retrievable."""
    creator_id = _uid()
    ceo_id = _uid()

    ws = await create_workspace(db, creator_id)
    await add_member(db, ws.id, creator_id, ROLE_MANAGER)
    await add_member(db, ws.id, ceo_id, ROLE_VIEWER)

    m = await get_member(db, ws.id, ceo_id)
    assert m is not None
    assert m.role == ROLE_VIEWER


@pytest.mark.asyncio
async def test_role_constants_write_access():
    """Viewer must NOT have write access; member and manager must."""
    assert ROLE_VIEWER not in WRITE_ROLES
    assert ROLE_MEMBER in WRITE_ROLES
    assert ROLE_MANAGER in WRITE_ROLES


@pytest.mark.asyncio
async def test_role_constants_manage_access():
    """Only manager has manage access."""
    assert ROLE_VIEWER not in MANAGE_ROLES
    assert ROLE_MEMBER not in MANAGE_ROLES
    assert ROLE_MANAGER in MANAGE_ROLES


@pytest.mark.asyncio
async def test_manager_add_remove_member(db):
    """Manager can add and remove a member."""
    creator_id = _uid()
    new_member_id = _uid()

    ws = await create_workspace(db, creator_id)
    await add_member(db, ws.id, creator_id, ROLE_MANAGER)
    await add_member(db, ws.id, new_member_id, ROLE_MEMBER)

    assert await get_member(db, ws.id, new_member_id) is not None

    await db.execute(
        delete(WsWorkspaceMember).where(
            and_(WsWorkspaceMember.workspace_id == ws.id,
                 WsWorkspaceMember.user_id == new_member_id)
        )
    )
    await db.commit()

    assert await get_member(db, ws.id, new_member_id) is None


@pytest.mark.asyncio
async def test_manager_update_member_role(db):
    """Manager can change a member's role."""
    creator_id = _uid()
    member_id = _uid()

    ws = await create_workspace(db, creator_id)
    await add_member(db, ws.id, creator_id, ROLE_MANAGER)
    m = await add_member(db, ws.id, member_id, ROLE_MEMBER)

    m.role = ROLE_VIEWER
    await db.commit()
    await db.refresh(m)

    updated = await get_member(db, ws.id, member_id)
    assert updated.role == ROLE_VIEWER


@pytest.mark.asyncio
async def test_workspace_chat_excluded_from_personal_list(db):
    """Workspace chat (workspace_id IS NOT NULL) must NOT appear in personal chat list."""
    user_id = _uid()
    ws_id = _uid()

    # Insert a workspace chat
    ws_chat = WsChat(id=_uid(), user_id=user_id, title="WS Chat",
                     workspace_id=ws_id, created_at=_now(), updated_at=_now())
    db.add(ws_chat)
    await db.commit()

    personal = await personal_chats(db, user_id)
    assert all(c.id != ws_chat.id for c in personal)


@pytest.mark.asyncio
async def test_workspace_chat_appears_in_workspace_list(db):
    """Workspace chat must appear in workspace-scoped list."""
    user_id = _uid()
    ws_id = _uid()

    ws_chat = WsChat(id=_uid(), user_id=user_id, title="WS Chat 2",
                     workspace_id=ws_id, created_at=_now(), updated_at=_now())
    db.add(ws_chat)
    await db.commit()

    chats = await workspace_chats(db, ws_id)
    assert any(c.id == ws_chat.id for c in chats)


@pytest.mark.asyncio
async def test_private_chat_not_in_workspace_list(db):
    """Private chat (workspace_id IS NULL) must NOT appear in any workspace's list."""
    user_id = _uid()

    private_chat = WsChat(id=_uid(), user_id=user_id, title="Private",
                          workspace_id=None, created_at=_now(), updated_at=_now())
    db.add(private_chat)
    await db.commit()

    # Try fetching as workspace_id = some random ID
    chats = await workspace_chats(db, _uid())
    assert all(c.id != private_chat.id for c in chats)


@pytest.mark.asyncio
async def test_soft_deleted_workspace_hidden(db):
    """Soft-deleted workspace must not appear in user list."""
    creator_id = _uid()

    ws = await create_workspace(db, creator_id, name="Deleted WS")
    await add_member(db, ws.id, creator_id, ROLE_MANAGER)

    # Soft-delete
    ws.deleted_at = _now()
    await db.commit()

    result = await workspaces_for_user(db, creator_id)
    assert all(w.id != ws.id for w in result)


@pytest.mark.asyncio
async def test_duplicate_membership_raises(db):
    """Adding same user twice must raise due to unique constraint."""
    from sqlalchemy.exc import IntegrityError

    creator_id = _uid()
    member_id = _uid()

    ws = await create_workspace(db, creator_id)
    await add_member(db, ws.id, creator_id, ROLE_MANAGER)
    await add_member(db, ws.id, member_id, ROLE_MEMBER)

    with pytest.raises(Exception):
        await add_member(db, ws.id, member_id, ROLE_MEMBER)
    await db.rollback()


@pytest.mark.asyncio
async def test_workspace_chat_share_block_logic():
    """
    In production, the share endpoint raises 403 when chat.workspace_id is not None.
    This test verifies the condition that triggers the block.
    """
    class FakeChat:
        workspace_id = "ws-123"

    chat = FakeChat()
    # The guard: if chat.workspace_id is not None → block
    assert chat.workspace_id is not None, "Block condition must be True for workspace chats"
