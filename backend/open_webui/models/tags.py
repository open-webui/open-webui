"""Tag models and database operations."""

from __future__ import annotations

import logging
import time
import uuid

# local imports
from open_webui.internal.db import Base, JSONField, get_async_db_context
from open_webui.utils.misc import sanitize_text_for_db
from pydantic import BaseModel, ConfigDict
from sqlalchemy import (
    JSON,
    BigInteger,
    Column,
    Index,
    PrimaryKeyConstraint,
    String,
    Text,
    UniqueConstraint,
    and_,
    delete,
    func,
    or_,
    select,
    update,
)
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


class ResourceTag(Base):
    __tablename__ = 'resource_tag'

    id = Column(Text, primary_key=True)
    resource_type = Column(Text, nullable=False)  # "chat" or "note"
    resource_id = Column(Text, nullable=False)
    tag_id = Column(Text, nullable=False)
    user_id = Column(Text, nullable=False)  # the resource's owner, whose tag this is
    created_at = Column(BigInteger, nullable=False)

    __table_args__ = (
        UniqueConstraint('resource_type', 'resource_id', 'tag_id', name='uq_resource_tag'),
        Index('ix_resource_tag_user_id_tag_id', 'user_id', 'tag_id'),
    )


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


def get_tag_id(name: str) -> str:
    return sanitize_text_for_db(name).replace(' ', '_').lower()


def resource_tag_filter(resource_type: str, resource_id, tag_ids):
    """Condition for resources with any of *tag_ids*; 'none' means untagged."""
    links = select(ResourceTag.resource_id).where(ResourceTag.resource_type == resource_type)
    named = sorted(set(tag_ids) - {'none'})
    conditions = [~links.where(ResourceTag.resource_id == resource_id).exists()] if 'none' in tag_ids else []
    if named:
        conditions.append(resource_id.in_(links.where(ResourceTag.tag_id.in_(named))))
    return or_(*conditions)


async def delete_resource_tags(resource_type: str, resource_ids, db: AsyncSession) -> None:
    """Remove these resources' links, and the tags nothing else uses. The caller commits.

    Call it before deleting the resources: *resource_ids* may be a select over them.
    """
    links = (ResourceTag.resource_type == resource_type, ResourceTag.resource_id.in_(resource_ids))
    used = (await db.execute(select(ResourceTag.user_id, ResourceTag.tag_id).where(*links).distinct())).all()
    await db.execute(delete(ResourceTag).where(*links))
    for user_id in {row.user_id for row in used}:
        await delete_unused_tags([row.tag_id for row in used if row.user_id == user_id], user_id, db)


async def delete_unused_tags(tag_ids: list[str], user_id: str, db: AsyncSession) -> None:
    """Delete the user's *tag_ids* that no resource carries any more. The caller commits."""
    linked = select(ResourceTag.id).where(ResourceTag.user_id == Tag.user_id, ResourceTag.tag_id == Tag.id).exists()
    await db.execute(
        delete(Tag)
        .where(Tag.user_id == user_id, Tag.id.in_(tag_ids), ~linked)
        .execution_options(synchronize_session=False)
    )


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

    async def get_tags_by_user_id(self, user_id: str, db: AsyncSession | None = None) -> list[TagModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(select(Tag).filter_by(user_id=user_id))
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

    async def ensure_tags_exist(self, names: list[str], user_id: str, db: AsyncSession | None = None) -> None:
        """Create tag rows for any *names* that don't already exist for *user_id*."""
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        from sqlalchemy.dialects.sqlite import insert as sqlite_insert

        names = [name for name in map(sanitize_text_for_db, names) if name]
        if not names:
            return
        ids = [get_tag_id(name) for name in names]
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

    async def get_tags_by_resource(
        self, resource_type: str, resource_id: str, db: AsyncSession | None = None
    ) -> list[TagModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(Tag)
                .join(ResourceTag, and_(ResourceTag.tag_id == Tag.id, ResourceTag.user_id == Tag.user_id))
                .where(ResourceTag.resource_type == resource_type, ResourceTag.resource_id == resource_id)
                .order_by(ResourceTag.created_at, Tag.id)
            )
            return [TagModel.model_validate(tag) for tag in result.scalars().all()]

    async def get_tags_by_resources(
        self, resource_type: str, resource_ids: list[str], db: AsyncSession | None = None
    ) -> dict[str, list[dict]]:
        """Each resource's tags as list rows show them: id, name and color."""
        tags: dict[str, list[dict]] = {}
        async with get_async_db_context(db) as db:
            # Databases limit how many values one query may bind.
            for start in range(0, len(resource_ids), 500):
                result = await db.execute(
                    select(ResourceTag.resource_id, ResourceTag.tag_id, Tag.name, Tag.meta)
                    .outerjoin(Tag, and_(Tag.id == ResourceTag.tag_id, Tag.user_id == ResourceTag.user_id))
                    .where(
                        ResourceTag.resource_type == resource_type,
                        ResourceTag.resource_id.in_(resource_ids[start : start + 500]),
                    )
                    .order_by(ResourceTag.created_at, ResourceTag.tag_id)
                )
                for resource_id, tag_id, name, meta in result.all():
                    tags.setdefault(resource_id, []).append(
                        {
                            'id': tag_id,
                            'name': name or tag_id.replace('_', ' '),
                            # The palette and default color live in the frontend.
                            'color': (meta or {}).get('color'),
                        }
                    )
        return tags

    async def get_tag_counts(self, resource_type: str, resource_ids, db: AsyncSession | None = None) -> list[dict]:
        """Tags on the resources in the *resource_ids* select, with how many carry each."""
        async with get_async_db_context(db) as db:
            name = func.min(func.coalesce(Tag.name, func.replace(ResourceTag.tag_id, '_', ' ')))
            result = await db.execute(
                select(
                    ResourceTag.tag_id.label('id'),
                    name.label('name'),
                    func.min(Tag.meta['color'].as_string()).label('color'),
                    func.count(ResourceTag.id).label('count'),
                )
                .outerjoin(Tag, and_(Tag.id == ResourceTag.tag_id, Tag.user_id == ResourceTag.user_id))
                .where(ResourceTag.resource_type == resource_type, ResourceTag.resource_id.in_(resource_ids))
                .group_by(ResourceTag.tag_id)
                .order_by(func.lower(name))
            )
            return [dict(row) for row in result.mappings()]

    async def add_tags_to_resources(
        self, resource_type: str, tag_ids: dict[str, list[str]], user_id: str, db: AsyncSession | None = None
    ) -> None:
        """Add tags to the user's resources in one transaction, as {resource id: tag ids}."""
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        from sqlalchemy.dialects.sqlite import insert as sqlite_insert

        links = [
            dict(
                id=str(uuid.uuid4()),
                resource_type=resource_type,
                resource_id=resource_id,
                tag_id=tag_id,
                user_id=user_id,
                created_at=time.time_ns(),
            )
            for resource_id, ids in tag_ids.items()
            for tag_id in dict.fromkeys(ids)
            if tag_id and tag_id != 'none'
        ]
        if not links:
            return
        async with get_async_db_context(db) as db:
            insert = sqlite_insert if db.bind.dialect.name == 'sqlite' else pg_insert
            await db.execute(
                insert(ResourceTag).on_conflict_do_nothing(index_elements=['resource_type', 'resource_id', 'tag_id']),
                links,
            )
            await db.commit()

    async def add_tag_to_resource(
        self, resource_type: str, resource_id: str, name: str, user_id: str, db: AsyncSession | None = None
    ) -> None:
        await self.ensure_tags_exist([name], user_id, db=db)
        await self.add_tags_to_resources(resource_type, {resource_id: [get_tag_id(name)]}, user_id, db=db)

    async def remove_tag_from_resource(
        self, resource_type: str, resource_id: str, name: str, user_id: str, db: AsyncSession | None = None
    ) -> None:
        async with get_async_db_context(db) as db:
            tag_id = get_tag_id(name)
            await db.execute(
                delete(ResourceTag).where(
                    ResourceTag.resource_type == resource_type,
                    ResourceTag.resource_id == resource_id,
                    ResourceTag.tag_id == tag_id,
                )
            )
            await delete_unused_tags([tag_id], user_id, db)
            await db.commit()

    async def set_resource_tags(
        self, resource_type: str, resource_id: str, names: list[str], user_id: str, db: AsyncSession | None = None
    ) -> None:
        """Replace a resource's tags."""
        names = [name for name in names if get_tag_id(name) != 'none']
        tag_ids = [get_tag_id(name) for name in names]
        await self.ensure_tags_exist(names, user_id, db=db)
        async with get_async_db_context(db) as db:
            links = (ResourceTag.resource_type == resource_type, ResourceTag.resource_id == resource_id)
            removed = ResourceTag.tag_id.not_in(tag_ids)
            old = (await db.execute(select(ResourceTag.tag_id).where(*links, removed))).scalars().all()
            await db.execute(delete(ResourceTag).where(*links, removed))
            await delete_unused_tags(list(old), user_id, db)
            await db.commit()
        await self.add_tags_to_resources(resource_type, {resource_id: tag_ids}, user_id, db=db)


Tags = TagTable()  # singleton tag repository
