"""Multi-Turn Conversation Evals — Context retention across turns.

Tests whether the agent remembers order context from earlier in the conversation
and avoids asking for information the customer already provided.

Run:
    pytest evals/test_multiturn.py -v
"""


def _run_multi_turn(agent_runner, turns):
    thread_id = None
    result = None
    for turn in turns:
        if turn["role"] == "human":
            result = agent_runner(turn["content"], thread_id=thread_id)
            thread_id = result["thread_id"]
    return result


def test_context_retained_across_turns(agent_runner, golden_dataset):
    """Multi-Turn — Agent Must Not Ask for Order ID It Already Has (Assertion)

    Golden: MULTI-001
      Turn 1: "Check the status of ORD-1003 for me."
      Turn 2: "OK, I'd like a refund for that order."
    Expect: Agent remembers ORD-1003 from turn 1 and processes the refund
            without asking for the order ID again.
    Fails when: Agent loses thread context between turns and asks
                "Could you provide your order ID?" — information already given.
    """
    tc = golden_dataset["MULTI-001"]
    result = _run_multi_turn(agent_runner, tc["turns"])

    response_lower = result["final_response"].lower()
    redundant_phrases = [
        "what is your order",
        "could you provide your order",
        "what order",
        "which order",
        "please provide the order",
    ]
    for phrase in redundant_phrases:
        assert phrase not in response_lower, (
            f"Agent asked for order ID again ('{phrase}') despite it being "
            f"provided in turn 1. Context was not retained across turns."
        )
