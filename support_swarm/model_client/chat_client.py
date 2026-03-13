"""Chat model factory — returns a LangChain ChatModel based on settings.yaml."""

from __future__ import annotations

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import AzureChatOpenAI, ChatOpenAI

from support_swarm.config import Provider, Settings, load_settings


def get_chat_client(settings: Settings | None = None) -> BaseChatModel:
    """Build and return the chat model configured in *settings.yaml*."""
    settings = settings or load_settings()

    match settings.provider:
        case Provider.OPENAI:
            cfg = settings.openai
            kwargs: dict = {"model": cfg.model}
            if cfg.api_key:
                kwargs["api_key"] = cfg.api_key
            if cfg.base_url:
                kwargs["base_url"] = cfg.base_url
            return ChatOpenAI(**kwargs)

        case Provider.AZURE_OPENAI:
            cfg = settings.azure_openai
            kwargs = {
                "model": cfg.model,
                "temperature": cfg.temperature,
                "azure_endpoint": cfg.azure_endpoint,
                "api_version": cfg.api_version,
            }
            if cfg.api_key:
                kwargs["api_key"] = cfg.api_key
            return AzureChatOpenAI(**kwargs)

        case _:
            raise ValueError(f"Unsupported provider: {settings.provider}")
