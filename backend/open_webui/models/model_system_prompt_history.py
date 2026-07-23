import difflib
import time
import uuid
from typing import Optional

from open_webui.internal.db import Base, get_async_db_context
from open_webui.models.users import User, UserModel, UserResponse, Users
from pydantic import BaseModel, ConfigDict
from sqlalchemy import JSON, BigInteger, Column, Text, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession


# ── Version history table ────────────────────────────────────────────

class ModelSystemPromptHistory(Base):
    __tablename__ = 'model_system_prompt_history'

    id = Column(Text, primary_key=True)
    model_id = Column(Text, nullable=False, index=True)
    parent_id = Column(Text, nullable=True)
    system_prompt = Column(Text, nullable=False, default='')
    user_id = Column(Text, nullable=False)
    commit_message = Column(Text, nullable=True)
    snapshot = Column(JSON, nullable=True)
    created_at = Column(BigInteger, nullable=False)


class ModelSystemPromptHistoryModel(BaseModel):
    id: str
    model_id: str
    parent_id: Optional[str] = None
    system_prompt: str = ''
    user_id: str
    commit_message: Optional[str] = None
    snapshot: Optional[dict] = None
    created_at: int

    model_config = ConfigDict(from_attributes=True)


class ModelSystemPromptHistoryResponse(ModelSystemPromptHistoryModel):
    user: Optional[UserResponse] = None


# ── Comment table ────────────────────────────────────────────────────

class ModelSystemPromptComment(Base):
    __tablename__ = 'model_system_prompt_comment'

    id = Column(Text, primary_key=True)
    history_id = Column(Text, nullable=False, index=True)
    user_id = Column(Text, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(BigInteger, nullable=False)


class ModelSystemPromptCommentModel(BaseModel):
    id: str
    history_id: str
    user_id: str
    content: str
    created_at: int

    model_config = ConfigDict(from_attributes=True)


class ModelSystemPromptCommentResponse(ModelSystemPromptCommentModel):
    user: Optional[UserResponse] = None


# ── Diff response ────────────────────────────────────────────────────

class ModelSystemPromptDiffResponse(BaseModel):
    from_id: str
    to_id: str
    content_diff: list[str]


class ModelSystemPromptHistoryTable:
    async def create_history_entry(
        self,
        model_id: str,
        system_prompt: str,
        user_id: str,
        parent_id: Optional[str] = None,
        commit_message: Optional[str] = None,
        snapshot: Optional[dict] = None,
        db: Optional[AsyncSession] = None,
    ) -> Optional[ModelSystemPromptHistoryModel]:
        async with get_async_db_context(db) as db:
            history = ModelSystemPromptHistory(
                id=str(uuid.uuid4()),
                model_id=model_id,
                parent_id=parent_id,
                system_prompt=system_prompt,
                user_id=user_id,
                commit_message=commit_message,
                snapshot=snapshot,
                created_at=int(time.time()),
            )
            db.add(history)
            await db.commit()
            await db.refresh(history)
            return ModelSystemPromptHistoryModel.model_validate(history)

    async def get_history_by_model_id(
        self,
        model_id: str,
        limit: int = 50,
        offset: int = 0,
        db: Optional[AsyncSession] = None,
    ) -> list[ModelSystemPromptHistoryResponse]:
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(ModelSystemPromptHistory)
                .filter(ModelSystemPromptHistory.model_id == model_id)
                .order_by(ModelSystemPromptHistory.created_at.desc())
                .offset(offset)
                .limit(limit)
            )
            entries = result.scalars().all()

            user_ids = list(set(e.user_id for e in entries))
            users = await Users.get_users_by_user_ids(user_ids, db=db) if user_ids else []
            users_dict = {user.id: user for user in users}

            return [
                ModelSystemPromptHistoryResponse(
                    **ModelSystemPromptHistoryModel.model_validate(entry).model_dump(),
                    user=(users_dict.get(entry.user_id).model_dump() if users_dict.get(entry.user_id) else None),
                )
                for entry in entries
            ]

    async def get_history_entry_by_id(
        self,
        history_id: str,
        db: Optional[AsyncSession] = None,
    ) -> Optional[ModelSystemPromptHistoryModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(select(ModelSystemPromptHistory).filter(ModelSystemPromptHistory.id == history_id))
            entry = result.scalars().first()
            if entry:
                return ModelSystemPromptHistoryModel.model_validate(entry)
            return None

    async def get_latest_history_entry(
        self,
        model_id: str,
        db: Optional[AsyncSession] = None,
    ) -> Optional[ModelSystemPromptHistoryModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(ModelSystemPromptHistory)
                .filter(ModelSystemPromptHistory.model_id == model_id)
                .order_by(ModelSystemPromptHistory.created_at.desc())
                .limit(1)
            )
            entry = result.scalars().first()
            if entry:
                return ModelSystemPromptHistoryModel.model_validate(entry)
            return None

    async def get_history_count(
        self,
        model_id: str,
        db: Optional[AsyncSession] = None,
    ) -> int:
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(func.count()).select_from(ModelSystemPromptHistory).filter(ModelSystemPromptHistory.model_id == model_id)
            )
            return result.scalar()

    async def get_detail(
        self,
        history_id: str,
        db: Optional[AsyncSession] = None,
    ) -> Optional[ModelSystemPromptHistoryResponse]:
        async with get_async_db_context(db) as db:
            result = await db.execute(select(ModelSystemPromptHistory).filter(ModelSystemPromptHistory.id == history_id))
            entry = result.scalars().first()
            if not entry:
                return None

            user = None
            u_result = await db.execute(select(User).filter(User.id == entry.user_id))
            u_row = u_result.scalars().first()
            if u_row:
                user = UserResponse(**UserModel.model_validate(u_row).model_dump())

            return ModelSystemPromptHistoryResponse(
                **ModelSystemPromptHistoryModel.model_validate(entry).model_dump(),
                user=user,
            )

    async def compute_diff(
        self,
        from_id: str,
        to_id: str,
        model_id: str,
        db: Optional[AsyncSession] = None,
    ) -> Optional[ModelSystemPromptDiffResponse]:
        async with get_async_db_context(db) as db:
            result_from = await db.execute(
                select(ModelSystemPromptHistory).filter(ModelSystemPromptHistory.id == from_id, ModelSystemPromptHistory.model_id == model_id)
            )
            from_entry = result_from.scalars().first()
            result_to = await db.execute(
                select(ModelSystemPromptHistory).filter(ModelSystemPromptHistory.id == to_id, ModelSystemPromptHistory.model_id == model_id)
            )
            to_entry = result_to.scalars().first()

            if not from_entry or not to_entry:
                return None

            from_content = from_entry.system_prompt or ''
            to_content = to_entry.system_prompt or ''

            diff_lines = list(
                difflib.unified_diff(
                    from_content.splitlines(keepends=True),
                    to_content.splitlines(keepends=True),
                    fromfile=f'v{from_id[:8]}',
                    tofile=f'v{to_id[:8]}',
                    lineterm='',
                )
            )

            return ModelSystemPromptDiffResponse(
                from_id=from_id,
                to_id=to_id,
                content_diff=diff_lines,
            )

    async def delete_history_by_model_id(
        self,
        model_id: str,
        db: Optional[AsyncSession] = None,
    ) -> bool:
        async with get_async_db_context(db) as db:
            await db.execute(delete(ModelSystemPromptHistory).filter(ModelSystemPromptHistory.model_id == model_id))
            await db.commit()
            return True

    async def delete_history_entry(
        self,
        history_id: str,
        model_id: str,
        db: Optional[AsyncSession] = None,
    ) -> bool:
        async with get_async_db_context(db) as db:
            result = await db.execute(select(ModelSystemPromptHistory).filter_by(id=history_id, model_id=model_id))
            entry = result.scalars().first()
            if not entry:
                return False

            children_result = await db.execute(select(ModelSystemPromptHistory).filter_by(parent_id=history_id))
            children = children_result.scalars().all()

            for child in children:
                child.parent_id = entry.parent_id

            await db.delete(entry)
            await db.commit()
            return True


# ── Comments ─────────────────────────────────────────────────────

    async def create_comment(
        self,
        history_id: str,
        user_id: str,
        content: str,
        db: Optional[AsyncSession] = None,
    ) -> Optional[ModelSystemPromptCommentModel]:
        async with get_async_db_context(db) as db:
            comment = ModelSystemPromptComment(
                id=str(uuid.uuid4()),
                history_id=history_id,
                user_id=user_id,
                content=content,
                created_at=int(time.time()),
            )
            db.add(comment)
            await db.commit()
            await db.refresh(comment)
            return ModelSystemPromptCommentModel.model_validate(comment)

    async def get_comments_by_history_id(
        self,
        history_id: str,
        db: Optional[AsyncSession] = None,
    ) -> list[ModelSystemPromptCommentResponse]:
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(ModelSystemPromptComment)
                .filter(ModelSystemPromptComment.history_id == history_id)
                .order_by(ModelSystemPromptComment.created_at.asc())
            )
            comments = result.scalars().all()

            user_ids = list(set(c.user_id for c in comments))
            users = await Users.get_users_by_user_ids(user_ids, db=db) if user_ids else []
            users_dict = {u.id: u for u in users}

            return [
                ModelSystemPromptCommentResponse(
                    **ModelSystemPromptCommentModel.model_validate(c).model_dump(),
                    user=(users_dict.get(c.user_id).model_dump() if users_dict.get(c.user_id) else None),
                )
                for c in comments
            ]

    async def delete_comment(
        self,
        comment_id: str,
        user_id: str,
        db: Optional[AsyncSession] = None,
    ) -> bool:
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(ModelSystemPromptComment).filter_by(id=comment_id, user_id=user_id)
            )
            comment = result.scalars().first()
            if not comment:
                return False
            await db.delete(comment)
            await db.commit()
            return True


ModelSystemPromptHistories = ModelSystemPromptHistoryTable()