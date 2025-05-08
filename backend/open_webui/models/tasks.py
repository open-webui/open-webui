
from pydantic import BaseModel


class AsyncTaskResponse(BaseModel):
    task_id: str
    status: str
    message: str
