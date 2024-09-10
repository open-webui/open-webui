from pydantic import BaseModel
from typing import Optional, List, Any


class VectorItem(BaseModel):
    id: str
    text: str
    vector: List[float | int]
    metadata: Any


class QueryResult(BaseModel):
    ids: Optional[List[List[str]]]
    distances: Optional[List[List[float | int]]]
    documents: Optional[List[List[str]]]
    metadatas: Optional[List[List[Any]]]
