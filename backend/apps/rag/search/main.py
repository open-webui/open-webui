from typing import Optional

from pydantic import BaseModel


class SearchResult(BaseModel):
    link: str
    title: Optional[str]
    snippet: Optional[str]
