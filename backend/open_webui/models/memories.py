"""Long-term memory storage for per-user context recall."""

from __future__ import annotations

import time
import uuid
from typing import Literal

from open_webui.internal.db import Base, get_async_db_context
from pydantic import BaseModel, ConfigDict
from sqlalchemy import JSON, BigInteger, Column, String, Text, delete, select
from sqlalchemy.ext.asyncio import AsyncSession


class Memory(Base):  # user memory store
    """Stores user-created memory entries linked to a vector collection."""

    __tablename__ = 'memory'

    id = Column(String, primary_key=True, unique=True)
    user_id = Column(String, index=True)
    type = Column(String, default='context', server_default='context', index=True)
    path = Column(Text, nullable=True)
    content = Column(Text)  # free-form text learned from conversation
    meta = Column(JSON, nullable=True)
    updated_at = Column(BigInteger)  # epoch seconds
    created_at = Column(BigInteger)  # epoch seconds


class MemoryModel(BaseModel):
    """Pydantic mirror of the Memory table row."""

    id: str
    user_id: str
    type: Literal['user', 'context'] = 'context'
    path: str | None = None
    content: str
    meta: dict | None = None
    updated_at: int  # timestamp in epoch
    created_at: int  # timestamp in epoch
    model_config = ConfigDict(from_attributes=True)  # allows ORM mapping


class MemoriesTable:
    @staticmethod
    def normalize_memory_type(memory_type: str | None = None) -> str:
        return 'user' if memory_type == 'user' else 'context'

    async def insert_new_memory(
        self,
        user_id: str,
        content: str,
        memory_type: str | None = None,
        path: str | None = None,
        meta: dict | None = None,
        db: AsyncSession | None = None,
    ) -> MemoryModel | None:
        """Persist a new memory entry and return the created model."""
        async with get_async_db_context(db) as db:
            now = int(time.time())
            record = Memory(
                id=str(uuid.uuid4()),
                user_id=user_id,
                type=self.normalize_memory_type(memory_type),
                path=path,
                content=content,
                meta=meta,
                created_at=now,
                updated_at=now,
            )
            db.add(record)
            await db.commit()
            await db.refresh(record)
            return MemoryModel.model_validate(record) if record else None

    async def update_memory_by_id_and_user_id(
        self,
        id: str,
        user_id: str,
        content: str | None,
        memory_type: str | None = None,
        path: str | None = None,
        update_path: bool = False,
        meta: dict | None = None,
        db: AsyncSession | None = None,
    ) -> MemoryModel | None:
        async with get_async_db_context(db) as db:
            try:
                memory = await db.get(Memory, id)
                if not memory or memory.user_id != user_id:
                    return None

                if content is not None:
                    memory.content = content
                if memory_type is not None:
                    memory.type = self.normalize_memory_type(memory_type)
                if update_path:
                    memory.path = path
                if meta is not None:
                    memory.meta = {**(memory.meta or {}), **meta}
                memory.updated_at = int(time.time())

                await db.commit()
                await db.refresh(memory)
                return MemoryModel.model_validate(memory)
            except Exception:
                return None

    async def get_memories(self, db: AsyncSession | None = None) -> list[MemoryModel]:
        async with get_async_db_context(db) as db:
            try:
                result = await db.execute(select(Memory))
                memories = result.scalars().all()
                return [MemoryModel.model_validate(memory) for memory in memories]
            except Exception:
                return None

    async def get_memories_by_user_id(self, user_id: str, db: AsyncSession | None = None) -> list[MemoryModel]:
        async with get_async_db_context(db) as db:
            try:
                result = await db.execute(select(Memory).filter_by(user_id=user_id))
                memories = result.scalars().all()
                return [MemoryModel.model_validate(memory) for memory in memories]
            except Exception:
                return None

    async def get_memory_by_id(self, id: str, db: AsyncSession | None = None) -> MemoryModel | None:
        async with get_async_db_context(db) as db:
            try:
                memory = await db.get(Memory, id)
                return MemoryModel.model_validate(memory) if memory else None
            except Exception:
                return None

    async def delete_memory_by_id(self, id: str, db: AsyncSession | None = None) -> bool:
        async with get_async_db_context(db) as db:
            try:
                await db.execute(delete(Memory).filter_by(id=id))
                await db.commit()

                return True

            except Exception:
                return False

    async def delete_memories_by_user_id(self, user_id: str, db: AsyncSession | None = None) -> bool:
        async with get_async_db_context(db) as db:
            try:
                await db.execute(delete(Memory).filter_by(user_id=user_id))
                await db.commit()

                return True
            except Exception:
                return False

    async def delete_memory_by_id_and_user_id(self, id: str, user_id: str, db: AsyncSession | None = None) -> bool:
        async with get_async_db_context(db) as db:
            try:
                memory = await db.get(Memory, id)
                if not memory or memory.user_id != user_id:
                    return False

                await db.delete(memory)
                await db.commit()
                return True
            except Exception:
                return False

    async def apply_memory_operations(
        self,
        user_id: str,
        operations: list[dict],
        db: AsyncSession | None = None,
    ) -> list[dict]:
        now = int(time.time())
        results: list[dict] = []

        async with get_async_db_context(db) as db:
            for operation in operations:
                action = operation.get('action')

                if action == 'add':
                    content = operation.get('content', '').strip()
                    memory_type = self.normalize_memory_type(operation.get('type'))
                    path = operation.get('path')
                    result = await db.execute(
                        select(Memory).filter_by(user_id=user_id, content=content, type=memory_type, path=path)
                    )
                    existing = result.scalars().first()
                    if existing:
                        results.append(
                            {
                                'action': action,
                                'status': 'skipped',
                                'memory': MemoryModel.model_validate(existing),
                                'reason': 'duplicate',
                            }
                        )
                        continue

                    memory = Memory(
                        id=str(uuid.uuid4()),
                        user_id=user_id,
                        type=memory_type,
                        path=path,
                        content=content,
                        meta=operation.get('meta'),
                        created_at=now,
                        updated_at=now,
                    )
                    db.add(memory)
                    await db.flush()
                    results.append(
                        {'action': action, 'status': 'created', 'memory': MemoryModel.model_validate(memory)}
                    )

                elif action == 'replace':
                    memory_id = operation.get('id')
                    content = operation.get('content', '').strip()
                    memory = await db.get(Memory, memory_id)
                    if not memory or memory.user_id != user_id:
                        raise ValueError(f'Memory not found: {memory_id}')

                    memory.content = content
                    if operation.get('type') is not None:
                        memory.type = self.normalize_memory_type(operation.get('type'))
                    if 'path' in operation:
                        memory.path = operation.get('path')
                    if operation.get('meta') is not None:
                        memory.meta = {**(memory.meta or {}), **operation.get('meta')}
                    memory.updated_at = now
                    await db.flush()
                    results.append(
                        {'action': action, 'status': 'updated', 'memory': MemoryModel.model_validate(memory)}
                    )

                elif action == 'move':
                    memory_id = operation.get('id')
                    memory = await db.get(Memory, memory_id)
                    if not memory or memory.user_id != user_id:
                        raise ValueError(f'Memory not found: {memory_id}')

                    memory.path = operation.get('path')
                    if operation.get('meta') is not None:
                        memory.meta = {**(memory.meta or {}), **operation.get('meta')}
                    memory.updated_at = now
                    await db.flush()
                    results.append(
                        {'action': action, 'status': 'updated', 'memory': MemoryModel.model_validate(memory)}
                    )

                elif action == 'remove':
                    memory_id = operation.get('id')
                    memory = await db.get(Memory, memory_id)
                    if not memory or memory.user_id != user_id:
                        raise ValueError(f'Memory not found: {memory_id}')

                    await db.delete(memory)
                    results.append({'action': action, 'status': 'deleted', 'id': memory_id})

                else:
                    raise ValueError(f'Unsupported memory operation: {action}')

            await db.commit()

        return results


Memories = MemoriesTable()  # user memory registry
