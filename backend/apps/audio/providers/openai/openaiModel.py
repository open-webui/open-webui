from pydantic import BaseModel

class OpenAIConfigUpdateForm(BaseModel):
    OPENAI_API_BASE_URL: str
    OPENAI_API_KEY: str