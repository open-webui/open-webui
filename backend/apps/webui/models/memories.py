import os
from pydantic import BaseModel, ConfigDict
from typing import List, Optional

from mem0 import MemoryClient


memory = MemoryClient(api_key=os.getenv("MEM0_API_KEY"))

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
    ) -> Optional[MemoryModel]:

        try:
            memory.add(messages=content, user_id=user_id)
        except:
            return None
    
    def query_memory(
        self,
        user_id: str,
        content: str,
        k: int,
    ):
        try:
            chromadb_format = {
                'documents': [],
                'ids': [],
                'distances': [],
                'uris': None,
                'data': None,
                'metadatas': [],
                'embeddings': None,
            }

            memories = memory.search(query=content, user_id=user_id, limit=k)

            for item in memories:
                chromadb_format['documents'].append([item['memory']])
                chromadb_format['ids'].append([item['id']])
                chromadb_format['distances'].append([item['score']])
                chromadb_format['metadatas'].append([item['metadata']])

            return chromadb_format
        except:
            return None


    def update_memory_by_id(
        self,
        id: str,
        content: str,
    ) -> Optional[MemoryModel]:
        try:
            memory.update(memory_id=id, data=content)
            return self.get_memory_by_id(id)
        except:
            return None

    def get_memories_by_user_id(self, user_id: str) -> List[MemoryModel]:
        try:
            memories = memory.get_all(user_id=user_id)
            resulting_memories = []
            for memory in memories:
                resulting_memories.append(
                    MemoryModel(
                        id=memory["id"],
                        user_id=memory["user_id"],
                        content=memory["memory"],
                        updated_at=memory["updated_at"],
                        created_at=memory["created_at"],
                    )
                )
            return resulting_memories
        except:
            return None

    def get_memory_by_id(self, id: str) -> Optional[MemoryModel]:
            try:
                memory = memory.get(memory_id=id)
                return MemoryModel(
                    id=memory["id"],
                    user_id=memory["user_id"],
                    content=memory["memory"],
                    updated_at=memory["updated_at"],
                    created_at=memory["created_at"],
                )
            except:
                return None

    def delete_memory_by_id(self, id: str) -> bool:
            try:
                memory.delete(id=id)
                return True
            except:
                return False

    def delete_memories_by_user_id(self, user_id: str) -> bool:
            try:
                memory.delete_all(user_id=user_id)
                return True
            except:
                return False

    def reset_memory(self) -> bool:
        try:
            memory.delete_all()
            return True
        except:
            return False

Memories = MemoriesTable()
