from __future__ import annotations

from pydantic import BaseModel


class OpenAIConfig(BaseModel):
    model: str = "gpt-4o"
    api_key: str = ""
    base_url: str | None = None
