"""Immutable snapshots of function configuration; the live row remains Production."""

import difflib
import time
import uuid
from copy import deepcopy

from fastapi import HTTPException
from open_webui.internal.db import Base, get_async_db_context
from pydantic import BaseModel, ConfigDict
from sqlalchemy import JSON, BigInteger, Column, Text, select, update


class FunctionHistory(Base):
    __tablename__ = 'function_history'
    id = Column(Text, primary_key=True)
    function_id = Column(Text, nullable=False, index=True)
    parent_id = Column(Text, nullable=True)
    snapshot = Column(JSON, nullable=False)
    user_id = Column(Text, nullable=False)
    commit_message = Column(Text, nullable=True)
    created_at = Column(BigInteger, nullable=False)


class FunctionHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    function_id: str
    parent_id: str | None = None
    user_id: str
    commit_message: str | None = None
    created_at: int
    user: dict | None = None


class FunctionHistoryModel(FunctionHistoryResponse):
    snapshot: dict


class FunctionHistoryTable:
    async def delete_history_entry(self, function_id, history_id, db=None):
        from open_webui.models.functions import Function

        async with get_async_db_context(db) as session:
            try:
                # Serialize with production switches on both SQLite and PostgreSQL.
                await session.execute(
                    update(Function).where(Function.id == function_id).values(version_id=Function.version_id)
                )
                model = await session.get(Function, function_id, populate_existing=True)
                if not model:
                    return False
                if model.version_id == history_id:
                    raise HTTPException(400, 'Cannot delete the current version')
                entry = (
                    await session.execute(select(FunctionHistory).filter_by(id=history_id, function_id=function_id))
                ).scalar_one_or_none()
                if not entry:
                    return False
                await session.execute(
                    update(FunctionHistory)
                    .where(FunctionHistory.function_id == function_id, FunctionHistory.parent_id == history_id)
                    .values(parent_id=entry.parent_id)
                )
                await session.delete(entry)
                await session.commit()
                return True
            except Exception:
                await session.rollback()
                raise

    def new_entry(self, function_id, snapshot, user_id, parent_id=None, commit_message=None):
        return FunctionHistory(
            id=str(uuid.uuid4()),
            function_id=function_id,
            snapshot=snapshot,
            user_id=user_id,
            parent_id=parent_id,
            commit_message=commit_message,
            created_at=int(time.time()),
        )

    async def get_history_by_id(self, function_id, history_id, db=None):
        from open_webui.models.users import User

        async with get_async_db_context(db) as session:
            entry = (
                await session.execute(select(FunctionHistory).filter_by(function_id=function_id, id=history_id))
            ).scalar_one_or_none()
            if not entry:
                return None
            result = FunctionHistoryModel.model_validate(entry)
            author = (await session.execute(select(User.name).where(User.id == entry.user_id))).scalar_one_or_none()
            result.user = {'name': author} if author else None
            return result

    async def get_history_by_function_id(self, function_id, page=1, db=None):
        from open_webui.models.users import User

        async with get_async_db_context(db) as session:
            columns = [getattr(FunctionHistory, key) for key in FunctionHistoryResponse.model_fields if key != 'user']
            rows = (
                (
                    await session.execute(
                        select(*columns, User.name.label('author_name'))
                        .outerjoin(User, User.id == FunctionHistory.user_id)
                        .where(FunctionHistory.function_id == function_id)
                        .order_by(FunctionHistory.created_at.desc(), FunctionHistory.id.desc())
                        .offset((max(1, page) - 1) * 20)
                        .limit(20)
                    )
                )
                .mappings()
                .all()
            )
            return [
                FunctionHistoryResponse(
                    **{key: value for key, value in row.items() if key != 'author_name'},
                    user={'name': row['author_name']} if row['author_name'] else None,
                )
                for row in rows
            ]


FunctionHistories = FunctionHistoryTable()


def function_snapshot(resource):
    data = (
        resource if isinstance(resource, dict) else {key: getattr(resource, key) for key in ('name', 'content', 'meta')}
    )
    meta = data.get('meta') or {}
    meta = meta.model_dump() if isinstance(meta, BaseModel) else deepcopy(meta)
    meta.setdefault('description', None)
    if not meta.get('i18n'):
        meta.pop('i18n', None)
    for key in ('manifest', 'has_user_valves', 'toggle'):
        meta.pop(key, None)
    return {'name': data.get('name'), 'content': data.get('content') or '', 'meta': meta}


def function_diff(before, after):
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
