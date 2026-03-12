from pydantic import BaseModel


class OpenAIConfig(BaseModel):
    model: str = "gpt-4o"
    temperature: float = 0
    api_key: str = ""
