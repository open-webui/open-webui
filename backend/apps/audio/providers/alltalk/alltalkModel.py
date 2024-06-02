from pydantic import BaseModel

class AllTalkConfigForm(BaseModel):
    url: str
    model: str
    speaker: str
    deepspeed: bool
    low_vram: bool