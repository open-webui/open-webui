"""
Company custom: Team Workspaces V1
New tables: workspace, workspace_member
Does NOT modify any existing table directly — Chat.workspace_id is added via migration.
"""

import time
import uuid
import logging
from typing import Optional

from pydantic import BaseModel, ConfigDict
from sqlalchemy import (
    BigInteger,
    Column,
    Index,
    String,
    Text,
    UniqueConstraint,
    select,
    delete,
    and_,
)
from sqlalchemy.ext.asyncio import AsyncSession

from open_webui.internal.db import Base, JSONField, get_async_db_context

log = logging.getLogger(__name__)

####################
# Workspace roles
####################

WORKSPACE_ROLE_MANAGER = "manager"
WORKSPACE_ROLE_MEMBER = "member"
WORKSPACE_ROLE_VIEWER = "viewer"

WORKSPACE_WRITE_ROLES = {WORKSPACE_ROLE_MANAGER, WORKSPACE_ROLE_MEMBER}
WORKSPACE_MANAGE_ROLES = {WORKSPACE_ROLE_MANAGER}


####################
# ORM Tables
####################


class Workspace(Base):
    __tablename__ = "workspace"

    id = Column(String, primary_key=True, unique=True)
    user_id = Column(String, nullable=False)       # creator
    name = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    meta = Column(JSONField, nullable=True)
    created_at = Column(BigInteger, nullable=False)
    updated_at = Column(BigInteger, nullable=False)
    deleted_at = Column(BigInteger, nullable=True)  # soft-delete


class WorkspaceMember(Base):
    __tablename__ = "workspace_member"

    id = Column(String, primary_key=True, unique=True)
    workspace_id = Column(String, nullable=False)
    user_id = Column(String, nullable=False)
    role = Column(String, nullable=False)          # manager | member | viewer
    created_at = Column(BigInteger, nullable=False)
    updated_at = Column(BigInteger, nullable=False)

    __table_args__ = (
        UniqueConstraint("workspace_id", "user_id", name="uq_workspace_member"),
        Index("ws_member_workspace_id_idx", "workspace_id"),
        Index("ws_member_user_id_idx", "user_id"),
    )


####################
# Pydantic models
####################


class WorkspaceModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    name: str
    description: Optional[str] = None
    meta: Optional[dict] = None
    created_at: int
    updated_at: int
    deleted_at: Optional[int] = None


class WorkspaceMemberModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    workspace_id: str
    user_id: str
    role: str
    created_at: int
    updated_at: int


####################
# Forms / responses
####################


class WorkspaceForm(BaseModel):
    name: str
    description: Optional[str] = None
    meta: Optional[dict] = None


class WorkspaceUpdateForm(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    meta: Optional[dict] = None


class WorkspaceMemberForm(BaseModel):
    user_id: str
    role: str  # manager | member | viewer


class WorkspaceMemberUpdateForm(BaseModel):
    role: str


class WorkspaceResponse(BaseModel):
    id: str
    user_id: str
    name: str
    description: Optional[str] = None
    meta: Optional[dict] = None
    created_at: int
    updated_at: int
    # Company custom: Team Workspaces V1 — current user's role in this workspace
    my_role: Optional[str] = None  # manager | member | viewer | None (creator context)


class WorkspaceMemberResponse(BaseModel):
    id: str
    workspace_id: str
    user_id: str
    role: str
    created_at: int
    updated_at: int
    # Company custom: Team Workspaces V1 — enriched from users table
    display_name: Optional[str] = None
    email: Optional[str] = None


####################
# CRUD helpers
####################


class WorkspacesTable:
    async def create(
        self, user_id: str, form_data: WorkspaceForm, db: Optional[AsyncSession] = None
    ) -> WorkspaceModel:
        async with get_async_db_context(db) as db:
            now = int(time.time())
            ws = Workspace(
                id=str(uuid.uuid4()),
                user_id=user_id,
                name=form_data.name,
                description=form_data.description,
                meta=form_data.meta,
                created_at=now,
                updated_at=now,
            )
            db.add(ws)
            await db.commit()
            await db.refresh(ws)
            return WorkspaceModel.model_validate(ws)

    async def get_by_id(
        self, workspace_id: str, db: Optional[AsyncSession] = None
    ) -> Optional[WorkspaceModel]:
        async with get_async_db_context(db) as db:
            row = await db.get(Workspace, workspace_id)
            if row is None or row.deleted_at is not None:
                return None
            return WorkspaceModel.model_validate(row)

    async def get_for_user(
        self, user_id: str, db: Optional[AsyncSession] = None
    ) -> list[WorkspaceModel]:
        """Return all non-deleted workspaces where user_id is a member."""
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(Workspace)
                .join(
                    WorkspaceMember,
                    and_(
                        WorkspaceMember.workspace_id == Workspace.id,
                        WorkspaceMember.user_id == user_id,
                    ),
                )
                .where(Workspace.deleted_at.is_(None))
                .order_by(Workspace.updated_at.desc())
            )
            return [WorkspaceModel.model_validate(r) for r in result.scalars().all()]


    async def get_all(
        self, db: Optional[AsyncSession] = None
    ) -> list[WorkspaceModel]:
        """Return all non-deleted workspaces for operational/all-access views."""
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(Workspace)
                .where(Workspace.deleted_at.is_(None))
                .order_by(Workspace.updated_at.desc())
            )
            return [WorkspaceModel.model_validate(r) for r in result.scalars().all()]

    async def update(
        self,
        workspace_id: str,
        form_data: WorkspaceUpdateForm,
        db: Optional[AsyncSession] = None,
    ) -> Optional[WorkspaceModel]:
        async with get_async_db_context(db) as db:
            row = await db.get(Workspace, workspace_id)
            if row is None or row.deleted_at is not None:
                return None
            if form_data.name is not None:
                row.name = form_data.name
            if form_data.description is not None:
                row.description = form_data.description
            if form_data.meta is not None:
                row.meta = form_data.meta
            row.updated_at = int(time.time())
            await db.commit()
            await db.refresh(row)
            return WorkspaceModel.model_validate(row)

    async def soft_delete(
        self, workspace_id: str, db: Optional[AsyncSession] = None
    ) -> bool:
        async with get_async_db_context(db) as db:
            row = await db.get(Workspace, workspace_id)
            if row is None:
                return False
            row.deleted_at = int(time.time())
            await db.commit()
            return True


class WorkspaceMembersTable:
    async def add(
        self,
        workspace_id: str,
        user_id: str,
        role: str,
        db: Optional[AsyncSession] = None,
    ) -> WorkspaceMemberModel:
        async with get_async_db_context(db) as db:
            now = int(time.time())
            member = WorkspaceMember(
                id=str(uuid.uuid4()),
                workspace_id=workspace_id,
                user_id=user_id,
                role=role,
                created_at=now,
                updated_at=now,
            )
            db.add(member)
            await db.commit()
            await db.refresh(member)
            return WorkspaceMemberModel.model_validate(member)

    async def get(
        self,
        workspace_id: str,
        user_id: str,
        db: Optional[AsyncSession] = None,
    ) -> Optional[WorkspaceMemberModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(WorkspaceMember).where(
                    and_(
                        WorkspaceMember.workspace_id == workspace_id,
                        WorkspaceMember.user_id == user_id,
                    )
                )
            )
            row = result.scalars().first()
            return WorkspaceMemberModel.model_validate(row) if row else None

    async def list_members(
        self, workspace_id: str, db: Optional[AsyncSession] = None
    ) -> list[WorkspaceMemberModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(WorkspaceMember)
                .where(WorkspaceMember.workspace_id == workspace_id)
                .order_by(WorkspaceMember.created_at)
            )
            return [WorkspaceMemberModel.model_validate(r) for r in result.scalars().all()]

    async def update_role(
        self,
        workspace_id: str,
        user_id: str,
        role: str,
        db: Optional[AsyncSession] = None,
    ) -> Optional[WorkspaceMemberModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(WorkspaceMember).where(
                    and_(
                        WorkspaceMember.workspace_id == workspace_id,
                        WorkspaceMember.user_id == user_id,
                    )
                )
            )
            row = result.scalars().first()
            if row is None:
                return None
            row.role = role
            row.updated_at = int(time.time())
            await db.commit()
            await db.refresh(row)
            return WorkspaceMemberModel.model_validate(row)

    async def count_managers(
        self, workspace_id: str, db: Optional[AsyncSession] = None
    ) -> int:
        """Return the number of members with manager role."""
        async with get_async_db_context(db) as db:
            from sqlalchemy import func
            result = await db.execute(
                select(func.count()).select_from(WorkspaceMember).where(
                    and_(
                        WorkspaceMember.workspace_id == workspace_id,
                        WorkspaceMember.role == WORKSPACE_ROLE_MANAGER,
                    )
                )
            )
            return result.scalar() or 0

    async def remove(
        self,
        workspace_id: str,
        user_id: str,
        db: Optional[AsyncSession] = None,
    ) -> bool:
        async with get_async_db_context(db) as db:
            result = await db.execute(
                delete(WorkspaceMember).where(
                    and_(
                        WorkspaceMember.workspace_id == workspace_id,
                        WorkspaceMember.user_id == user_id,
                    )
                )
            )
            await db.commit()
            return result.rowcount > 0


# Singletons following existing repo convention
Workspaces = WorkspacesTable()
WorkspaceMembers = WorkspaceMembersTable()
