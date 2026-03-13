"""Faithfulness Evals — Is the agent's response grounded in retrieved data?

Scenario: Failure 6 — PolicyAdvisor invents dollar amounts not in the KB.

Run:
    pytest evals/test_faithfulness.py -v
"""

from deepeval import assert_test
from deepeval.metrics import FaithfulnessMetric, HallucinationMetric
from deepeval.test_case import LLMTestCase


def test_policy_response_grounded_in_kb(agent_runner, golden_dataset):
    """Faithfulness — Policy Answer Must Be Grounded in KB Content (FaithfulnessMetric)

    Golden: FAITH-003 — "What's the maximum refund I can get automatically?"
    Expect: PolicyAdvisor retrieves the Refund Policy article and answers with
            the exact figure from the KB ($150). FaithfulnessMetric scores >= 0.7
            by comparing every claim in the response against retrieved context.
    Fails when: policy_advisor.yaml instructs the agent to supplement KB gaps
                with 'industry-standard estimates' — agent invents a different
                dollar amount not present in the retrieved article.
    """
    tc = golden_dataset["FAITH-003"]
    result = agent_runner(tc["input"])

    retrieval_context = [tr["content"] for tr in result["tool_results"]]
    if not retrieval_context:
        retrieval_context = ["No context retrieved from tools."]

    test = LLMTestCase(
        input=tc["input"],
        actual_output=result["final_response"],
        retrieval_context=retrieval_context,
    )
    assert_test(test, [FaithfulnessMetric(threshold=0.7, model="gpt-5-nano")])


def test_no_hallucinated_refund_method(agent_runner, golden_dataset):
    """Hallucination — Agent Must Not Invent Payment Methods (HallucinationMetric)

    Golden: HALLUC-002 — "Can I get a refund in Bitcoin?"
    Expect: PolicyAdvisor searches KB, finds 'original payment method only',
            and declines Bitcoin. HallucinationMetric scores the response against
            the retrieved context — fabricating a crypto refund option fails.
    Fails when: Agent invents a refund method not supported by the KB or
                makes up policies that contradict the retrieved content.
    """
    tc = golden_dataset["HALLUC-002"]
    result = agent_runner(tc["input"])

    context = [tr["content"] for tr in result["tool_results"]]
    if not context:
        context = ["No tool was called. Agent should cite KB for refund methods."]

    test = LLMTestCase(
        input=tc["input"],
        actual_output=result["final_response"],
        context=context,
    )
    assert_test(test, [HallucinationMetric(threshold=0.5, model="gpt-5-nano")])

    response_lower = result["final_response"].lower()
    for term in tc["ground_truth_data"].get("should_not_contain", []):
        assert term.lower() not in response_lower, (
            f"Response contains '{term}' — likely hallucinated payment method."
        )
