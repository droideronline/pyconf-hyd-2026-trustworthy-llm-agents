"""LangGraph workflow — wires declarative agent specs into a state graph."""

from __future__ import annotations

from typing import Any

from langchain.agents import create_agent
from langchain_core.messages import BaseMessage, HumanMessage
from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from support_swarm.declarative import get_agent_spec
from support_swarm.enums import Agents
from support_swarm.model_client import get_chat_client


class State(TypedDict):
    input: str
    output: str
    messages: list[BaseMessage]


# ── Nodes ────────────────────────────────────────────────────────────────────


def shop_assist(state: State) -> dict[str, Any]:
    """Run the ShopAssist agent."""
    spec = get_agent_spec(Agents.SHOP_ASSIST)

    agent = create_agent(
        model=get_chat_client(),
        tools=spec.get_tools(),
        system_prompt=spec.render_system_prompt(store_name="Acme Corp"),
    )

    user_message = spec.render_user_prompt(
        customer_message=state["input"],
        order_id="",
        customer_email="",
    )

    result = agent.invoke({"messages": [HumanMessage(content=user_message)]})

    return {
        "output": result["messages"][-1].content,
        "messages": result["messages"],
    }


# ── Graph ────────────────────────────────────────────────────────────────────


def build_workflow() -> StateGraph:
    """Construct and compile the support-swarm workflow."""
    builder = StateGraph(State)

    builder.add_node("shop_assist", shop_assist)

    builder.add_edge(START, "shop_assist")
    builder.add_edge("shop_assist", END)

    return builder.compile()
