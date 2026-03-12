from pydantic import BaseModel


class AzureOpenAIConfig(BaseModel):
    model: str = "gpt-4o"
    temperature: float = 0
    api_key: str = ""
    azure_endpoint: str = ""
    api_version: str = "2024-12-01-preview"
