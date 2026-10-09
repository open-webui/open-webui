"""Immutable snapshots of model configuration; the model row remains Production."""

import time
import uuid

from open_webui.internal.db import Base, get_async_db_context
from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import JSON, BigInteger, Column, Text, select, update


def model_snapshot(model) -> dict:
    data = (
        model
        if isinstance(model, dict)
        else {key: getattr(model, key) for key in ('name', 'base_model_id', 'params', 'meta')}
    )
    snapshot = {key: data.get(key) for key in ('name', 'base_model_id', 'params', 'meta')}
    for key in ('params', 'meta'):
        value = snapshot[key]
        snapshot[key] = value.model_dump() if isinstance(value, BaseModel) else dict(value or {})
    meta = snapshot['meta']
    meta.pop('hidden', None)
    meta.pop('chat_variables_schema', None)
    return snapshot


class ModelHistory(Base):
    __tablename__ = 'model_history'
    id = Column(Text, primary_key=True)
    model_id = Column(Text, nullable=False, index=True)
    parent_id = Column(Text, nullable=True)
    snapshot = Column(JSON, nullable=False)
    user_id = Column(Text, nullable=False)
    commit_message = Column(Text, nullable=True)
    created_at = Column(BigInteger, nullable=False)


class ModelHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    model_id: str
    parent_id: str | None = None
    user_id: str
    commit_message: str | None = None
    created_at: int
    user: dict | None = None


class ModelHistoryModel(ModelHistoryResponse):
    snapshot: dict


class ModelHistoryTable:
    async def delete_history_entry(self, model_id, history_id, db=None):
        from open_webui.models.models import Model

        async with get_async_db_context(db) as session:
            try:
                # Serialize with production switches on both SQLite and PostgreSQL.
                await session.execute(update(Model).where(Model.id == model_id).values(version_id=Model.version_id))
                model = await session.get(Model, model_id, populate_existing=True)
                if not model:
                    return False
                if model.version_id == history_id:
                    raise HTTPException(400, 'Cannot delete the current version')
                entry = (
                    await session.execute(select(ModelHistory).filter_by(id=history_id, model_id=model_id))
                ).scalar_one_or_none()
                if not entry:
                    return False
                await session.execute(
                    update(ModelHistory)
                    .where(ModelHistory.model_id == model_id, ModelHistory.parent_id == history_id)
                    .values(parent_id=entry.parent_id)
                )
                await session.delete(entry)
                await session.commit()
                return True
            except Exception:
                await session.rollback()
                raise

    def new_entry(self, model_id, snapshot, user_id, parent_id=None, commit_message=None):
        return ModelHistory(
            id=str(uuid.uuid4()),
            model_id=model_id,
            snapshot=snapshot,
            user_id=user_id,
            parent_id=parent_id,
            commit_message=commit_message,
            created_at=int(time.time()),
        )

    async def get_history_by_id(self, model_id, history_id, db=None):
        from open_webui.models.users import User

        async with get_async_db_context(db) as session:
            entry = (
                await session.execute(select(ModelHistory).filter_by(model_id=model_id, id=history_id))
            ).scalar_one_or_none()
            if not entry:
                return None
            result = ModelHistoryModel.model_validate(entry)
            author = (await session.execute(select(User.name).where(User.id == entry.user_id))).scalar_one_or_none()
            result.user = {'name': author} if author else None
            return result

    async def get_history_by_model_id(self, model_id, page=1, db=None):
        from open_webui.models.users import User

        async with get_async_db_context(db) as session:
            columns = [getattr(ModelHistory, key) for key in ModelHistoryResponse.model_fields if key != 'user']
            rows = (
                (
                    await session.execute(
                        select(*columns, User.name.label('author_name'))
                        .outerjoin(User, User.id == ModelHistory.user_id)
                        .where(ModelHistory.model_id == model_id)
                        .order_by(ModelHistory.created_at.desc(), ModelHistory.id.desc())
                        .offset((max(1, page) - 1) * 20)
                        .limit(20)
                    )
                )
                .mappings()
                .all()
            )
            return [
                ModelHistoryResponse(
                    **{key: value for key, value in row.items() if key != 'author_name'},
                    user={'name': row['author_name']} if row['author_name'] else None,
                )
                for row in rows
            ]


ModelHistories = ModelHistoryTable()
