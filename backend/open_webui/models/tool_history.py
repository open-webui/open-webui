"""Immutable snapshots of tool configuration; the live row remains Production."""

import difflib
import time
import uuid
from copy import deepcopy

from fastapi import HTTPException
from open_webui.internal.db import Base, get_async_db_context
from pydantic import BaseModel, ConfigDict
from sqlalchemy import JSON, BigInteger, Column, Text, select, update


class ToolHistory(Base):
    __tablename__ = 'tool_history'
    id = Column(Text, primary_key=True)
    tool_id = Column(Text, nullable=False, index=True)
    parent_id = Column(Text, nullable=True)
    snapshot = Column(JSON, nullable=False)
    user_id = Column(Text, nullable=False)
    commit_message = Column(Text, nullable=True)
    created_at = Column(BigInteger, nullable=False)


class ToolHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    tool_id: str
    parent_id: str | None = None
    user_id: str
    commit_message: str | None = None
    created_at: int
    user: dict | None = None


class ToolHistoryModel(ToolHistoryResponse):
    snapshot: dict


class ToolHistoryTable:
    async def delete_history_entry(self, tool_id, history_id, db=None):
        from open_webui.models.tools import Tool

        async with get_async_db_context(db) as session:
            try:
                # Serialize with production switches on both SQLite and PostgreSQL.
                await session.execute(update(Tool).where(Tool.id == tool_id).values(version_id=Tool.version_id))
                model = await session.get(Tool, tool_id, populate_existing=True)
                if not model:
                    return False
                if model.version_id == history_id:
                    raise HTTPException(400, 'Cannot delete the current version')
                entry = (
                    await session.execute(select(ToolHistory).filter_by(id=history_id, tool_id=tool_id))
                ).scalar_one_or_none()
                if not entry:
                    return False
                await session.execute(
                    update(ToolHistory)
                    .where(ToolHistory.tool_id == tool_id, ToolHistory.parent_id == history_id)
                    .values(parent_id=entry.parent_id)
                )
                await session.delete(entry)
                await session.commit()
                return True
            except Exception:
                await session.rollback()
                raise

    def new_entry(self, tool_id, snapshot, user_id, parent_id=None, commit_message=None):
        return ToolHistory(
            id=str(uuid.uuid4()),
            tool_id=tool_id,
            snapshot=snapshot,
            user_id=user_id,
            parent_id=parent_id,
            commit_message=commit_message,
            created_at=int(time.time()),
        )

    async def get_history_by_id(self, tool_id, history_id, db=None):
        from open_webui.models.users import User

        async with get_async_db_context(db) as session:
            entry = (
                await session.execute(select(ToolHistory).filter_by(tool_id=tool_id, id=history_id))
            ).scalar_one_or_none()
            if not entry:
                return None
            result = ToolHistoryModel.model_validate(entry)
            author = (await session.execute(select(User.name).where(User.id == entry.user_id))).scalar_one_or_none()
            result.user = {'name': author} if author else None
            return result

    async def get_history_by_tool_id(self, tool_id, page=1, db=None):
        from open_webui.models.users import User

        async with get_async_db_context(db) as session:
            columns = [getattr(ToolHistory, key) for key in ToolHistoryResponse.model_fields if key != 'user']
            rows = (
                (
                    await session.execute(
                        select(*columns, User.name.label('author_name'))
                        .outerjoin(User, User.id == ToolHistory.user_id)
                        .where(ToolHistory.tool_id == tool_id)
                        .order_by(ToolHistory.created_at.desc(), ToolHistory.id.desc())
                        .offset((max(1, page) - 1) * 20)
                        .limit(20)
                    )
                )
                .mappings()
                .all()
            )
            return [
                ToolHistoryResponse(
                    **{key: value for key, value in row.items() if key != 'author_name'},
                    user={'name': row['author_name']} if row['author_name'] else None,
                )
                for row in rows
            ]


ToolHistories = ToolHistoryTable()


def tool_snapshot(resource):
    data = (
        resource if isinstance(resource, dict) else {key: getattr(resource, key) for key in ('name', 'content', 'meta')}
    )
    meta = data.get('meta') or {}
    meta = meta.model_dump() if isinstance(meta, BaseModel) else deepcopy(meta)
    meta.setdefault('description', None)
    if not meta.get('i18n'):
        meta.pop('i18n', None)
    for key in ('manifest', 'has_user_valves'):
        meta.pop(key, None)
    return {'name': data.get('name'), 'content': data.get('content') or '', 'meta': meta}


def tool_diff(before, after):
    left, right = before.snapshot, after.snapshot
    metadata = {
        key: {'before': left.get(key), 'after': right.get(key)}
        for key in ('name', 'meta')
        if left.get(key) != right.get(key)
    }
    old, new = left.get('content') or '', right.get('content') or ''
    # splitlines handles a missing final newline and CRLF without breaking the renderer.
    patch = '\n'.join(
        difflib.unified_diff(
            old.splitlines(), new.splitlines(), fromfile='selected.py', tofile='production.py', lineterm=''
        )
    )
    return {
        'from_id': before.id,
        'to_id': after.id,
        'metadata': metadata,
        'content_diff': patch,
        'line_endings_only': old != new and not patch,
    }
