"""
Tool registry for managing agent tools.

Provides a decorator that wraps langchain's @tool and auto-registers
each function in a global registry.  Declarative agents use their
``whitelisted_tools`` list to pull only the tools they're allowed to call.
"""

from collections.abc import Callable
from typing import Any

from langchain_core.tools import BaseTool, tool

# Global registry: function name → BaseTool instance
registry: dict[str, BaseTool] = {}


def register_tool(func: Callable | None = None, **kwargs: Any) -> Callable:
    """Decorator that wraps a function with langchain's ``@tool`` and
    registers it in the global registry keyed by function name.

    Supports both ``@register_tool`` and ``@register_tool()`` usage.
    """

    def decorator(f: Callable) -> BaseTool:
        wrapped = tool(f, **kwargs)
        registry[wrapped.name] = wrapped
        return wrapped

    return decorator(func) if func else decorator


def get_tools(tool_names: list[str]) -> list[BaseTool]:
    """Return registered tools matching the given names.

    Unknown names are silently skipped so a stale YAML won't crash the app.
    """
    return [registry[name] for name in tool_names if name in registry]
