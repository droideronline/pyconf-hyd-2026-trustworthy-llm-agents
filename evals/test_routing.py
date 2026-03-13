"""Routing Accuracy Evals — Does the router classify intent correctly?

Scenario: Failure 5 — Manager request routed to shop_assist instead of escalation_agent.

Run:
    pytest evals/test_routing.py -v
"""


def test_escalation_intent_routed_correctly(agent_runner, golden_dataset):
    """Routing — Upset Customer Must Be Classified as Escalation (Assertion)

    Golden: ROUTE-003 — "I've been waiting for weeks... I want to speak to a manager."
    Expect: Router classifies intent as 'escalation', not 'order_support'.
            Wrong routing means an angry customer lands in the wrong agent —
            shop_assist tries to look up an order instead of escalating the complaint.
    Fails when: The escalation definition in router.yaml is narrowed to only
                cover formal legal/regulatory filings, excluding manager requests.
    """
    tc = golden_dataset["ROUTE-003"]
    result = agent_runner(tc["input"])

    routed_intent = None
    for msg in result["all_messages"]:
        if msg.get("type") == "ai":
            routing_info = msg.get("additional_kwargs", {}).get("routing", {})
            if routing_info:
                routed_intent = routing_info.get("intent")
                break

    assert routed_intent == "escalation", (
        f"Routing mismatch for ROUTE-003: "
        f"expected 'escalation', got '{routed_intent}'. "
        f"Manager requests must trigger the escalation agent."
    )
