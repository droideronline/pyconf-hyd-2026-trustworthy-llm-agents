from __future__ import annotations

from typing import TYPE_CHECKING, TypeAlias

from jinja2 import Template
from pydantic import BaseModel, model_validator

if TYPE_CHECKING:
    from langchain_core.tools import BaseTool


class AgentSpec(BaseModel):
    """Parsed and validated declarative agent specification."""

    name: str
    system_prompt: str | list[str] = ""
    user_prompt: str | list[str]
    whitelisted_tools: list[str] = []

    @model_validator(mode="after")
    def _coerce_prompts_to_str(self) -> AgentSpec:
        """Flatten list-style prompts into a single string for Jinja rendering."""
        if isinstance(self.system_prompt, list):
            self.system_prompt = "\n".join(self.system_prompt)
        if isinstance(self.user_prompt, list):
            self.user_prompt = "\n".join(self.user_prompt)
        return self

    def render_system_prompt(self, **variables: object) -> str:
        """Render the system prompt as a Jinja2 template.

        Args:
            **variables: Template variables referenced in the prompt.

        Returns:
            Fully rendered system prompt string.
        """
        return Template(self.system_prompt).render(**variables)

    def render_user_prompt(self, **variables: object) -> str:
        """Render the user prompt as a Jinja2 template.

        Args:
            **variables: Template variables referenced in the prompt.

        Returns:
            Fully rendered user prompt string.
        """
        return Template(self.user_prompt).render(**variables)

    def get_tools(self) -> list[BaseTool]:
        """Return registered tool instances matching ``whitelisted_tools``."""
        from support_swarm.tools.registry import get_tools

        return get_tools(self.whitelisted_tools)


# Flat name → AgentSpec mapping used by the registry
SpecRegistry: TypeAlias = dict[str, AgentSpec]
