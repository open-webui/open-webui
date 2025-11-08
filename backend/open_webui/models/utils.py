from pydantic import BaseModel


class ReindexForm(BaseModel):
    process_from_disk: bool = False
    batch_size: int = 10