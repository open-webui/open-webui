from pydantic import BaseModel

class AllTalkConfigForm(BaseModel):
    url: str
    model: str
    speaker: str