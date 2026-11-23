"""Tag models and database operations."""

from __future__ import annotations

import logging
import time
import uuid

# local imports
from open_webui.internal.db import Base, JSONField, get_async_db_context
from pydantic import BaseModel, ConfigDict
from sqlalchemy import JSON, BigInteger, Column, Index, PrimaryKeyConstraint, String, delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)


class Tag(Base):  # database table mapping for tag entity
    __tablename__ = 'tag'
    id = Column(String)
    name = Column(String, index=True)  # tag label
    user_id = Column(String, index=True)  # user identifier
    meta = Column(JSON, nullable=True)

    __table_args__ = (
        PrimaryKeyConstraint('id', 'user_id', name='pk_id_user_id'),
        Index('user_id_idx', 'user_id'),
    )

    # Unique constraint ensuring (id, user_id) is unique, not just the `id` column
    __table_args__ = (PrimaryKeyConstraint('id', 'user_id', name='pk_id_user_id'),)


class TagModel(BaseModel):
    id: str
    name: str
    user_id: str
    meta: dict | None = None
    model_config = ConfigDict(from_attributes=True)  # allows ORM model binding


# Tag schema forms
# Forms


class TagChatIdForm(BaseModel):
    name: str
    chat_id: str


class TagTable:
    async def insert_new_tag(
        self,
        name: str,
        user_id: str,
        db: AsyncSession | None = None,
    ) -> TagModel | None:
        """Create a new tag, deriving the id from the name."""
        async with get_async_db_context(db) as db:
            tag_id = name.replace(' ', '_').lower()
            try:
                record = Tag(id=tag_id, user_id=user_id, name=name)
                db.add(record)
                await db.commit()
                return TagModel.model_validate(record) if record else None
            except Exception as e:
                log.exception('Error inserting tag %r: %s', name, e)
                return None  # insertion failed

    async def get_tag_by_name_and_user_id(
        self, name: str, user_id: str, db: AsyncSession | None = None
    ) -> TagModel | None:
        try:
            id = name.replace(' ', '_').lower()
            async with get_async_db_context(db) as db:
                result = await db.execute(select(Tag).filter_by(id=id, user_id=user_id))
                tag = result.scalars().first()
                return TagModel.model_validate(tag) if tag else None
        except Exception:
            return None

    async def get_tags_by_user_id(self, user_id: str, db: AsyncSession | None = None) -> list[TagModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(select(Tag).filter_by(user_id=user_id))
            return [TagModel.model_validate(tag) for tag in result.scalars().all()]

    async def get_tags_by_ids_and_user_id(
        self, ids: list[str], user_id: str, db: AsyncSession | None = None
    ) -> list[TagModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(select(Tag).filter(Tag.id.in_(ids), Tag.user_id == user_id))
            return [TagModel.model_validate(tag) for tag in result.scalars().all()]

    async def update_tag_color_by_name_and_user_id(
        self, name: str, user_id: str, color: str, db: AsyncSession | None = None
    ) -> bool:
        async with get_async_db_context(db) as db:
            id = name.replace(' ', '_').lower()
            meta = (await db.execute(select(Tag.meta).filter_by(id=id, user_id=user_id))).one_or_none()
            if meta is None:
                return False
            await db.execute(
                update(Tag).filter_by(id=id, user_id=user_id).values(meta={**(meta[0] or {}), 'color': color})
            )
            await db.commit()
            return True

    async def get_tag_ids_used_by_notes(self, ids: list[str], user_id: str, db: AsyncSession) -> set[str]:
        """The *ids* one of this user's notes still carries.

        Chats drop a tag's row once no chat uses it; notes share those rows, so they
        are checked here, where every deletion ends up.
        """
        # Imported here: notes pull in far more models than tags should.
        from open_webui.models.notes import Note

        if not ids:
            return set()
        metas = (await db.execute(select(Note.meta).filter_by(user_id=user_id))).scalars().all()
        return {tag_id for meta in metas for tag_id in (meta or {}).get('tags') or []} & set(ids)

    async def delete_tag_by_name_and_user_id(self, name: str, user_id: str, db: AsyncSession | None = None) -> bool:
        try:
            async with get_async_db_context(db) as db:
                id = name.replace(' ', '_').lower()
                if await self.get_tag_ids_used_by_notes([id], user_id, db):
                    return False
                result = await db.execute(delete(Tag).filter_by(id=id, user_id=user_id))
                log.debug('res: %s', result.rowcount)
                await db.commit()
                return True
        except Exception as e:
            log.error(f'delete_tag: {e}')
            return False

    async def delete_tags_by_ids_and_user_id(
        self, ids: list[str], user_id: str, db: AsyncSession | None = None
    ) -> bool:
        """Delete all tags whose id is in *ids* for the given user, in one query."""
        if not ids:
            return True
        try:
            async with get_async_db_context(db) as db:
                kept = await self.get_tag_ids_used_by_notes(ids, user_id, db)
                ids = [tag_id for tag_id in ids if tag_id not in kept]
                if not ids:
                    return True
                await db.execute(delete(Tag).filter(Tag.id.in_(ids), Tag.user_id == user_id))
                await db.commit()
                return True
        except Exception as e:
            log.error(f'delete_tags_by_ids: {e}')
            return False

    async def ensure_tags_exist(self, names: list[str], user_id: str, db: AsyncSession | None = None) -> None:
        """Create tag rows for any *names* that don't already exist for *user_id*."""
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        from sqlalchemy.dialects.sqlite import insert as sqlite_insert

        if not names:
            return
        ids = [n.replace(' ', '_').lower() for n in names]
        async with get_async_db_context(db) as db:
            result = await db.execute(select(Tag.id).filter(Tag.id.in_(ids), Tag.user_id == user_id))
            existing = {row[0] for row in result.all()}
            new_tags = [
                dict(id=tag_id, name=name, user_id=user_id)
                for tag_id, name in zip(ids, names)
                if tag_id not in existing
            ]
            if new_tags:
                insert = sqlite_insert if db.bind.dialect.name == 'sqlite' else pg_insert
                # A concurrent request may have created the same tag since the read above
                await db.execute(insert(Tag).on_conflict_do_nothing(index_elements=['id', 'user_id']), new_tags)
                await db.commit()


Tags = TagTable()  # singleton tag repository
