from __future__ import annotations

import time
import uuid
from typing import Optional

from open_webui.internal.db import Base, get_async_db_context
from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Column, String, Text, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

####################
# Memory DB Schema
# What was learned at cost should not need to be paid
# for again. Let the memory hold.
####################


class Memory(Base):
    __tablename__ = 'memory'

    id = Column(String, primary_key=True, unique=True)
    user_id = Column(String, index=True)
    content = Column(Text)
    updated_at = Column(BigInteger)
    created_at = Column(BigInteger)


class MemoryModel(BaseModel):
    id: str
    user_id: str
    content: str
    updated_at: int  # timestamp in epoch
    created_at: int  # timestamp in epoch

    model_config = ConfigDict(from_attributes=True)


####################
# Forms
####################


class MemoriesTable:
    async def insert_new_memory(
        self,
        user_id: str,
        content: str,
        db: AsyncSession | None = None,
    ) -> MemoryModel | None:
        async with get_async_db_context(db) as db:
            id = str(uuid.uuid4())

            memory = MemoryModel(
                **{
                    'id': id,
                    'user_id': user_id,
                    'content': content,
                    'created_at': int(time.time()),
                    'updated_at': int(time.time()),
                }
            )
            result = Memory(**memory.model_dump())
            db.add(result)
            await db.commit()
            await db.refresh(result)
            if result:
                return MemoryModel.model_validate(result)
            else:
                return None

    async def update_memory_by_id_and_user_id(
        self,
        id: str,
        user_id: str,
        content: str,
        db: AsyncSession | None = None,
    ) -> MemoryModel | None:
        async with get_async_db_context(db) as db:
            try:
                memory = await db.get(Memory, id)
                if not memory or memory.user_id != user_id:
                    return None

                memory.content = content
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
                    return None

                # Delete the memory
                await db.delete(memory)
                await db.commit()

                return True
            except Exception:
                return False


Memories = MemoriesTable()
