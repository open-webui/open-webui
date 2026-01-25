import time
import uuid
from typing import Optional

from sqlalchemy.orm import Session
from open_webui.internal.db import Base, get_db, get_db_context
from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Column, String, Text

####################
# Memory DB Schema
####################


class Memory(Base):
    __tablename__ = "memory"

    id = Column(String, primary_key=True, unique=True)
    user_id = Column(String)
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
    def insert_new_memory(
        self,
        user_id: str,
        content: str,
        db: Optional[Session] = None,
    ) -> Optional[MemoryModel]:
        with get_db_context(db) as db:
            id = str(uuid.uuid4())

            memory = MemoryModel(
                **{
                    "id": id,
                    "user_id": user_id,
                    "content": content,
                    "created_at": int(time.time()),
                    "updated_at": int(time.time()),
                }
            )
            result = Memory(**memory.model_dump())
            db.add(result)
            db.commit()
            db.refresh(result)
            if result:
                return MemoryModel.model_validate(result)
            else:
                return None

    def update_memory_by_id_and_user_id(
        self,
        id: str,
        user_id: str,
        content: str,
        db: Optional[Session] = None,
    ) -> Optional[MemoryModel]:
        with get_db_context(db) as db:
            try:
                memory = db.get(Memory, id)
                if not memory or memory.user_id != user_id:
                    return None

                memory.content = content
                memory.updated_at = int(time.time())

                db.commit()
                return self.get_memory_by_id(id)
            except Exception:
                return None

    def get_memories(self, db: Optional[Session] = None) -> list[MemoryModel]:
        with get_db_context(db) as db:
            try:
                memories = db.query(Memory).all()
                return [MemoryModel.model_validate(memory) for memory in memories]
            except Exception:
                return None

    def get_memories_by_user_id(
        self, user_id: str, db: Optional[Session] = None
    ) -> list[MemoryModel]:
        with get_db_context(db) as db:
            try:
                memories = db.query(Memory).filter_by(user_id=user_id).all()
                return [MemoryModel.model_validate(memory) for memory in memories]
            except Exception:
                return None

    def get_memory_by_id(
        self, id: str, db: Optional[Session] = None
    ) -> Optional[MemoryModel]:
        with get_db_context(db) as db:
            try:
                memory = db.get(Memory, id)
                return MemoryModel.model_validate(memory)
            except Exception:
                return None

    def delete_memory_by_id(self, id: str, db: Optional[Session] = None) -> bool:
        with get_db_context(db) as db:
            try:
                db.query(Memory).filter_by(id=id).delete()
                db.commit()

                return True

            except Exception:
                return False

    def delete_memories_by_user_id(
        self, user_id: str, db: Optional[Session] = None
    ) -> bool:
        with get_db_context(db) as db:
            try:
                db.query(Memory).filter_by(user_id=user_id).delete()
                db.commit()

                return True
            except Exception:
                return False

    def delete_memory_by_id_and_user_id(
        self, id: str, user_id: str, db: Optional[Session] = None
    ) -> bool:
        with get_db_context(db) as db:
            try:
                memory = db.get(Memory, id)
                if not memory or memory.user_id != user_id:
                    return None

                # Delete the memory
                db.delete(memory)
                db.commit()

                return True
            except Exception:
                return False


Memories = MemoriesTable()
