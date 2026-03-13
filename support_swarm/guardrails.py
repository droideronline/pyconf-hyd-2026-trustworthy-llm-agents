"""Custom guardrail middleware for the support swarm agents."""

from __future__ import annotations

import json
from typing import Any

from langchain.agents.middleware import AgentMiddleware
from langchain_core.messages import ToolMessage


class RefundCapMiddleware(AgentMiddleware):
    """Blocks refund tool calls that exceed a configurable dollar cap."""

    def __init__(self, max_amount: float = 150.0):
        self.max_amount = max_amount

    def wrap_tool_call(self, request, handler):
        tool_call = request.tool_call
        if tool_call["name"] == "process_refund":
            amount = tool_call["args"].get("amount", 0)
            if amount > self.max_amount:
                return ToolMessage(
                    content=json.dumps(
                        {
                            "success": False,
                            "error": (
                                f"Refund ${amount:.2f} exceeds the "
                                f"${self.max_amount:.2f} policy cap. "
                                "Please escalate to a supervisor for approval."
                            ),
                        }
                    ),
                    tool_call_id=tool_call["id"],
                )
        return handler(request)

    async def awrap_tool_call(self, request, handler):
        tool_call = request.tool_call
        if tool_call["name"] == "process_refund":
            amount = tool_call["args"].get("amount", 0)
            if amount > self.max_amount:
                return ToolMessage(
                    content=json.dumps(
                        {
                            "success": False,
                            "error": (
                                f"Refund ${amount:.2f} exceeds the "
                                f"${self.max_amount:.2f} policy cap. "
                                "Please escalate to a supervisor for approval."
                            ),
                        }
                    ),
                    tool_call_id=tool_call["id"],
                )
        return await handler(request)
