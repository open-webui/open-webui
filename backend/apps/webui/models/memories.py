from pydantic import BaseModel
from peewee import *
from playhouse.shortcuts import model_to_dict
from typing import List, Union, Optional

from apps.webui.internal.db import DB
from apps.webui.models.chats import Chats

import time
import uuid

####################
# Memory DB Schema
####################


class Memory(Model):
    id = CharField(unique=True)
    user_id = CharField()
    content = TextField()
    updated_at = BigIntegerField()
    created_at = BigIntegerField()

    class Meta:
        database = DB


class MemoryModel(BaseModel):
    id: str
    user_id: str
    content: str
    updated_at: int  # timestamp in epoch
    created_at: int  # timestamp in epoch


####################
# Forms
####################


class MemoriesTable:
    def __init__(self, db):
        self.db = db
        self.db.create_tables([Memory])

    def insert_new_memory(
        self,
        user_id: str,
        content: str,
    ) -> Optional[MemoryModel]:
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
        result = Memory.create(**memory.model_dump())
        if result:
            return memory
        else:
            return None

    def get_memories(self) -> List[MemoryModel]:
        try:
            memories = Memory.select()
            return [MemoryModel(**model_to_dict(memory)) for memory in memories]
        except:
            return None

    def get_memories_by_user_id(self, user_id: str) -> List[MemoryModel]:
        try:
            memories = Memory.select().where(Memory.user_id == user_id)
            return [MemoryModel(**model_to_dict(memory)) for memory in memories]
        except:
            return None

    def get_memory_by_id(self, id) -> Optional[MemoryModel]:
        try:
            memory = Memory.get(Memory.id == id)
            return MemoryModel(**model_to_dict(memory))
        except:
            return None

    def delete_memory_by_id(self, id: str) -> bool:
        try:
            query = Memory.delete().where(Memory.id == id)
            query.execute()  # Remove the rows, return number of rows removed.

            return True

        except:
            return False

    def delete_memories_by_user_id(self, user_id: str) -> bool:
        try:
            query = Memory.delete().where(Memory.user_id == user_id)
            query.execute()

            return True
        except:
            return False

    def delete_memory_by_id_and_user_id(self, id: str, user_id: str) -> bool:
        try:
            query = Memory.delete().where(Memory.id == id, Memory.user_id == user_id)
            query.execute()

            return True
        except:
            return False


Memories = MemoriesTable(DB)
