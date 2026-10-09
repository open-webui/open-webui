import time
import uuid

from open_webui.internal.db import Base, get_async_db_context
from pydantic import BaseModel, ConfigDict
from sqlalchemy import JSON, BigInteger, Column, Text, select


class SkillHistory(Base):
    __tablename__ = 'skill_history'
    id = Column(Text, primary_key=True)
    skill_id = Column(Text, nullable=False, index=True)
    parent_id = Column(Text, nullable=True)
    snapshot = Column(JSON, nullable=False)
    user_id = Column(Text, nullable=False)
    commit_message = Column(Text, nullable=True)
    created_at = Column(BigInteger, nullable=False)


class SkillHistoryModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    skill_id: str
    parent_id: str | None = None
    snapshot: dict
    user_id: str
    commit_message: str | None = None
    created_at: int


class SkillHistoryResponse(BaseModel):
    id: str
    skill_id: str
    parent_id: str | None = None
    user_id: str
    commit_message: str | None = None
    created_at: int
    user: dict | None = None


class SkillHistoryTable:
    def new_entry(self, skill_id, snapshot, user_id, parent_id=None, commit_message=None):
        return SkillHistory(
            id=str(uuid.uuid4()),
            skill_id=skill_id,
            snapshot=snapshot,
            user_id=user_id,
            parent_id=parent_id,
            commit_message=commit_message,
            created_at=int(time.time()),
        )

    async def get_history_by_id(self, skill_id, history_id, db=None):
        async with get_async_db_context(db) as session:
            entry = (
                await session.execute(select(SkillHistory).filter_by(id=history_id, skill_id=skill_id))
            ).scalar_one_or_none()
            return SkillHistoryModel.model_validate(entry) if entry else None

    async def get_history_by_skill_id(self, skill_id, page=1, db=None):
        from open_webui.models.users import User

        async with get_async_db_context(db) as session:
            columns = [getattr(SkillHistory, key) for key in SkillHistoryResponse.model_fields if key != 'user']
            rows = (
                (
                    await session.execute(
                        select(*columns, User.name.label('author_name'))
                        .outerjoin(User, User.id == SkillHistory.user_id)
                        .where(SkillHistory.skill_id == skill_id)
                        .order_by(SkillHistory.created_at.desc(), SkillHistory.id.desc())
                        .offset((max(1, page) - 1) * 20)
                        .limit(20)
                    )
                )
                .mappings()
                .all()
            )
            return [
                SkillHistoryResponse(
                    **{k: v for k, v in row.items() if k != 'author_name'},
                    user={'name': row['author_name']} if row['author_name'] else None,
                )
                for row in rows
            ]


SkillHistories = SkillHistoryTable()
