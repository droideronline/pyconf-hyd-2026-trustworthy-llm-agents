"""LangGraph workflow — wires declarative agent specs into a state graph."""

from __future__ import annotations

from typing import Any

from langchain.agents import create_agent
from langgraph.graph import END, START, MessagesState, StateGraph

from support_swarm.declarative import get_agent_spec
from support_swarm.enums import Agents
from support_swarm.model_client import get_chat_client


# ── Nodes ────────────────────────────────────────────────────────────────────


async def shop_assist(state: MessagesState) -> dict[str, Any]:
    """Run the ShopAssist agent."""
    spec = get_agent_spec(Agents.SHOP_ASSIST)

    agent = create_agent(
        model=get_chat_client(),
        tools=spec.get_tools(),
        system_prompt=spec.render_system_prompt(store_name="Acme Corp"),
    )

    result = await agent.ainvoke({"messages": state["messages"]})

    return {"messages": result["messages"]}


# ── Graph ────────────────────────────────────────────────────────────────────


def build_workflow() -> StateGraph:
    """Construct and compile the support-swarm workflow."""
    builder = StateGraph(MessagesState)

    builder.add_node("shop_assist", shop_assist)

    builder.add_edge(START, "shop_assist")
    builder.add_edge("shop_assist", END)

    return builder.compile()


# Module-level compiled graph for langgraph.json
graph = build_workflow()
