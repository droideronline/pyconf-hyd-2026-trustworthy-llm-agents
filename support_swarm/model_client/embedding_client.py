"""Embedding model factory — returns a LangChain Embeddings based on settings.yaml."""

from __future__ import annotations

from langchain_core.embeddings import Embeddings
from langchain_openai import AzureOpenAIEmbeddings, OpenAIEmbeddings

from support_swarm.config import Provider, Settings, load_settings


def get_embedding_client(settings: Settings | None = None) -> Embeddings:
    """Build and return the embedding model configured in *settings.yaml*."""
    settings = settings or load_settings()

    match settings.provider:
        case Provider.OPENAI:
            cfg = settings.openai
            kwargs: dict = {"model": settings.embedding_model}
            if cfg.api_key:
                kwargs["api_key"] = cfg.api_key
            return OpenAIEmbeddings(**kwargs)

        case Provider.AZURE_OPENAI:
            cfg = settings.azure_openai
            kwargs = {
                "model": settings.embedding_model,
                "azure_endpoint": cfg.azure_endpoint,
                "api_version": cfg.api_version,
            }
            if cfg.api_key:
                kwargs["api_key"] = cfg.api_key
            return AzureOpenAIEmbeddings(**kwargs)

        case _:
            raise ValueError(f"Unsupported provider: {settings.provider}")
