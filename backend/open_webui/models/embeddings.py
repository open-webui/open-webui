# backend/open_webui/models/embeddings.py
from typing import Union, List, Optional
from pydantic import BaseModel, Field

class OpenAIEmbeddingRequest(BaseModel):
    input: Union[str, List[str]]
    model: str
    encoding_format: Optional[str] = Field("float", pattern="^(float|base64)$")
    dimensions: Optional[int] = None
    user: Optional[str] = None

class EmbeddingObject(BaseModel):
    object: str = "embedding"
    embedding: Union[List[float], str] # List of floats or base64 string
    index: int

class UsageObject(BaseModel):
    prompt_tokens: int
    total_tokens: int

class OpenAIEmbeddingResponse(BaseModel):
    object: str = "list"
    data: List[EmbeddingObject]
    model: str # The model ID used for the embedding
    usage: UsageObject