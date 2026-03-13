"""LangGraph workflow — multi-agent swarm with intent-based routing."""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware, PIIMiddleware
from langchain.agents.structured_output import ProviderStrategy
from langchain_core.messages import AIMessage
from langgraph.graph import END, START, MessagesState, StateGraph
from pydantic import BaseModel, Field

from support_swarm.declarative import get_agent_spec
from support_swarm.enums import Agents
from support_swarm.guardrails import RefundCapMiddleware
from support_swarm.model_client import get_chat_client


# ── Router Schema ────────────────────────────────────────────────────────────


class Intent(StrEnum):
    GENERAL = "general"
    ORDER_SUPPORT = "order_support"
    POLICY_INQUIRY = "policy_inquiry"
    ESCALATION = "escalation"


class RouterIntent(BaseModel):
    """Structured output from the intent-detection router."""

    intent: Intent = Field(
        description="The classified intent of the customer's message."
    )
    reasoning: str = Field(
        description="One-sentence justification for the chosen intent."
    )


# ── Intent → Node mapping ───────────────────────────────────────────────────

_INTENT_TO_NODE: dict[Intent, str] = {
    Intent.GENERAL: "shop_assist",
    Intent.ORDER_SUPPORT: "shop_assist",
    Intent.POLICY_INQUIRY: "policy_advisor",
    Intent.ESCALATION: "escalation_agent",
}


# ── Nodes ────────────────────────────────────────────────────────────────────


async def router(state: MessagesState) -> dict[str, Any]:
    """Classify user intent using structured output (ProviderStrategy)."""
    spec = get_agent_spec(Agents.ROUTER)
    agent = create_agent(
        model=get_chat_client(),
        tools=[],
        system_prompt=spec.render_system_prompt(store_name="Acme Corp"),
        response_format=ProviderStrategy(RouterIntent),
    )
    result = await agent.ainvoke({"messages": state["messages"]})
    intent: RouterIntent = result["structured_response"]
    return {
        "messages": [
            AIMessage(
                content=intent.intent.value,
                additional_kwargs={"routing": intent.model_dump()},
            )
        ]
    }


def route_by_intent(
    state: MessagesState,
) -> Literal["shop_assist", "policy_advisor", "escalation_agent"]:
    """Read the router's structured classification and pick the next node."""
    last_msg = state["messages"][-1]
    routing = last_msg.additional_kwargs.get("routing", {})
    intent_value = routing.get("intent", last_msg.content.strip().lower())

    try:
        intent = Intent(intent_value)
    except ValueError:
        intent = Intent.GENERAL  # safe fallback

    return _INTENT_TO_NODE[intent]


async def shop_assist(state: MessagesState) -> dict[str, Any]:
    """Run the ShopAssist agent with guardrails middleware.

    Middleware stack:
    - HumanInTheLoopMiddleware: pauses for human approval before process_refund
      and send_email calls (uses LangGraph interrupt).
    - RefundCapMiddleware: hard-blocks refunds exceeding $150 policy cap.
    - PIIMiddleware: redacts credit-card numbers in model output.
    """
    spec = get_agent_spec(Agents.SHOP_ASSIST)
    agent = create_agent(
        model=get_chat_client(),
        tools=spec.get_tools(),
        system_prompt=spec.render_system_prompt(store_name="Acme Corp"),
        middleware=[
            HumanInTheLoopMiddleware(
                interrupt_on={
                    "process_refund": {
                        "description": "Review this refund before processing",
                        "allowed_decisions": ["approve", "edit", "reject"],
                    },
                    "send_email": {
                        "description": "Review this email before sending",
                        "allowed_decisions": ["approve", "edit", "reject"],
                    },
                }
            ),
            RefundCapMiddleware(max_amount=150.0),
            PIIMiddleware("credit_card", strategy="redact", apply_to_output=True),
        ],
    )
    result = await agent.ainvoke({"messages": state["messages"]})
    return {"messages": result["messages"]}


async def policy_advisor(state: MessagesState) -> dict[str, Any]:
    """Run the PolicyAdvisor agent."""
    spec = get_agent_spec(Agents.POLICY_ADVISOR)
    agent = create_agent(
        model=get_chat_client(),
        tools=spec.get_tools(),
        system_prompt=spec.render_system_prompt(store_name="Acme Corp"),
    )
    result = await agent.ainvoke({"messages": state["messages"]})
    return {"messages": result["messages"]}


async def escalation_agent(state: MessagesState) -> dict[str, Any]:
    """Run the EscalationAgent with HITL guardrail on send_email."""
    spec = get_agent_spec(Agents.ESCALATION_AGENT)
    agent = create_agent(
        model=get_chat_client(),
        tools=spec.get_tools(),
        system_prompt=spec.render_system_prompt(store_name="Acme Corp"),
        middleware=[
            HumanInTheLoopMiddleware(
                interrupt_on={
                    "send_email": {
                        "description": "Review escalation email before sending",
                        "allowed_decisions": ["approve", "edit", "reject"],
                    },
                }
            ),
        ],
    )
    result = await agent.ainvoke({"messages": state["messages"]})
    return {"messages": result["messages"]}


# ── Graph ────────────────────────────────────────────────────────────────────


def build_workflow() -> StateGraph:
    """Construct and compile the multi-agent support-swarm workflow.

    Flow:
        START → router → (conditional) → shop_assist | policy_advisor | escalation_agent → END

    Guardrails:
        - shop_assist: HITL interrupt on process_refund & send_email,
          refund-cap enforcement ($150), credit-card PII redaction.
        - escalation_agent: HITL interrupt on send_email.

    Persistence:
        The LangGraph API runtime automatically provides a PostgreSQL
        checkpointer — no manual checkpointer is needed.
    """
    builder = StateGraph(MessagesState)

    # Nodes
    builder.add_node("router", router)
    builder.add_node("shop_assist", shop_assist)
    builder.add_node("policy_advisor", policy_advisor)
    builder.add_node("escalation_agent", escalation_agent)

    # Edges
    builder.add_edge(START, "router")
    builder.add_conditional_edges("router", route_by_intent)
    builder.add_edge("shop_assist", END)
    builder.add_edge("policy_advisor", END)
    builder.add_edge("escalation_agent", END)

    return builder.compile()


# Module-level compiled graph for langgraph.json
graph = build_workflow()
