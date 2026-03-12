from enum import StrEnum

from pydantic import BaseModel

from support_swarm.config.azure_openai import AzureOpenAIConfig
from support_swarm.config.openai import OpenAIConfig


class Provider(StrEnum):
    OPENAI = "openai"
    AZURE_OPENAI = "azure_openai"


class Settings(BaseModel):
    # Database
    database_url: str = (
        "postgresql+psycopg2://support:support@localhost:5432/support_swarm"
    )

    # Embeddings
    embedding_model: str = "text-embedding-3-small"

    # LLM provider
    provider: Provider = Provider.OPENAI
    openai: OpenAIConfig = OpenAIConfig()
    azure_openai: AzureOpenAIConfig = AzureOpenAIConfig()
