"""RAGAS Evaluation — Faithfulness scored with the RAGAS framework.

Scenario: Act 4 positive — same faithfulness case as test_faithfulness.py,
          evaluated by a completely independent framework.
          When two frameworks agree on a pass, you have high confidence.

Run:
    pytest evals/test_ragas.py -v
"""

import asyncio
import os

from openai import OpenAI
from ragas.dataset_schema import SingleTurnSample
from ragas.llms import llm_factory
from ragas.metrics import Faithfulness


def test_policy_response_grounded_in_kb_ragas(agent_runner, golden_dataset):
    """Faithfulness — Policy Answer Grounded in KB (RAGAS Faithfulness)

    Golden: FAITH-003 — "What's the maximum refund I can get automatically?"
    Expect: RAGAS Faithfulness score >= 0.7. RAGAS decomposes the response into
            individual claims and checks each against the retrieved KB context.
            The correct answer ($150) is in the KB — the response must not invent
            figures or options that contradict the retrieved article.

    This is a positive verification test (Act 4). After fixing policy_advisor.yaml,
    both DeepEval and RAGAS should agree the response is faithful.
    """
    tc = golden_dataset["FAITH-003"]
    result = agent_runner(tc["input"])

    retrieved = [tr["content"] for tr in result["tool_results"]]
    if not retrieved:
        retrieved = ["No context retrieved from tools."]

    sample = SingleTurnSample(
        user_input=tc["input"],
        response=result["final_response"],
        retrieved_contexts=retrieved,
    )

    model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    llm = llm_factory(model_name, client=OpenAI(), max_completion_tokens=4096)
    # gpt-5-nano requires max_completion_tokens, not max_tokens
    llm.model_args.pop("max_tokens", None)
    scorer = Faithfulness(llm=llm)

    loop = asyncio.new_event_loop()
    try:
        score = loop.run_until_complete(scorer.single_turn_ascore(sample))
    finally:
        loop.close()

    assert score >= 0.7, (
        f"RAGAS faithfulness for FAITH-003: {score:.2f} < 0.7 threshold. "
        f"Response contains claims not supported by the retrieved KB article."
    )
