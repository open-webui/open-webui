from pydantic import BaseModel

class OpenAIConfigUpdateForm(BaseModel):
    url: str
    key: str
    model: str
    speaker: str