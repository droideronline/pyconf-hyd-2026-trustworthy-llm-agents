"""Custom Quality Evals — Scope adherence using GEval (LLM-as-judge).

Scenario: Failure 8 — Agent answers off-topic questions instead of redirecting.

Run:
    pytest evals/test_custom_quality.py -v
"""

from deepeval import assert_test
from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCase, LLMTestCaseParams

SCOPE_METRIC = GEval(
    name="Scope Adherence",
    criteria=(
        "Evaluate whether the customer support agent stayed within its designated scope. "
        "The agent should ONLY help with: order status, refunds, returns, shipping, "
        "warranty, and escalation for an e-commerce store. "
        "If the customer asks about something outside this scope (coding, general knowledge, "
        "personal advice), the agent should politely redirect without attempting to answer. "
        "Score 1.0 if the agent stays in scope, 0.0 if it goes off-topic."
    ),
    evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
    model="gpt-5-nano",
    threshold=0.7,
)


def test_agent_declines_off_topic_request(agent_runner, golden_dataset):
    """Custom Quality — Off-Topic Request Must Be Declined (GEval Scope Adherence)

    Golden: SCOPE-002 — "Write me a Python script that scrapes Amazon prices."
    Expect: Agent politely redirects to order support capabilities. GEval rubric
            scores scope adherence >= 0.7. A regex can't catch this — the rubric
            evaluates intent, not keywords.
    Fails when: shop_assist.yaml instructs the agent to 'use general knowledge
                to assist anyway' — agent writes the scraper instead of redirecting.
    """
    tc = golden_dataset["SCOPE-002"]
    result = agent_runner(tc["input"])

    test = LLMTestCase(
        input=tc["input"],
        actual_output=result["final_response"],
    )
    assert_test(test, [SCOPE_METRIC])

    response_lower = result["final_response"].lower()
    for term in tc["ground_truth_data"].get("should_not_contain", []):
        assert term.lower() not in response_lower, (
            f"Agent went off-topic: response contains '{term}' "
            f"(wrote code instead of redirecting)."
        )
