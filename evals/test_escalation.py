"""Escalation Agent Evals — Priority classification and acknowledgment email.

Scenario: Failure 4 — Safety/legal incident classified as P1 instead of P0.

Golden dataset case:
  ESCL-001: fire + legal threat → P0, trust-and-safety, 15 min SLA

Run:
    pytest evals/test_escalation.py -v
"""


def test_escalation_safety_incident_is_p0(agent_runner, golden_dataset):
    """Escalation — Safety Incident Must Be Classified P0 (Assertion)

    Golden: ESCL-001 — "Your product caused a fire... contacting my lawyer
            and the consumer protection board."
    Expect: Escalation agent assigns P0 (Critical) — safety incident with
            legal threat requires a 15-minute response, not 1 hour.
    Fails when: escalation_agent.yaml or the KB defines P0 as 'system outage
                only', demoting safety incidents to P1. The response will say
                P1 and the audience won't notice — but this eval will.
    """
    tc = golden_dataset["ESCL-001"]
    result = agent_runner(tc["input"])

    response_lower = result["final_response"].lower()
    assert "p0" in response_lower, (
        "Escalation response must mention P0 for ESCL-001. "
        "A fire + legal threat is a safety incident — P0, 15-minute SLA. "
        f"Response was: {result['final_response'][:300]}"
    )


def test_escalation_sends_acknowledgment_email(agent_runner, golden_dataset):
    """Escalation — Acknowledgment Email Must Be Sent (Assertion)

    Golden: ESCL-001.
    Expect: Escalation agent calls send_email to confirm the issue was received,
            the priority level, and when the customer can expect a response.
    Fails when: Agent responds conversationally but never triggers send_email —
                the customer has no confirmation their complaint was logged.
    """
    tc = golden_dataset["ESCL-001"]
    result = agent_runner(tc["input"])

    email_calls = [c for c in result["tool_calls"] if c["name"] == "send_email"]
    assert len(email_calls) >= 1, (
        "Escalation agent must call send_email to acknowledge ESCL-001. "
        "Customer must receive confirmation that their case was escalated."
    )
