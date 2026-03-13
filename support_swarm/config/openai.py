from pydantic import BaseModel


class OpenAIConfig(BaseModel):
    model: str = "gpt-5-nano"
    temperature: float = 0
    api_key: str = ""
