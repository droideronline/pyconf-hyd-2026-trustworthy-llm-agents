import asyncio
import json
import os
from pathlib import Path

import pytest
from langgraph_sdk import get_client

LANGGRAPH_URL = os.getenv("LANGGRAPH_URL", "http://localhost:2024")
ASSISTANT_ID = "shop_assist"


@pytest.fixture(scope="session")
def golden_dataset():
    path = Path(__file__).parent / "golden_dataset.json"
    with open(path) as f:
        data = json.load(f)
    return {tc["id"]: tc for tc in data["test_cases"]}


@pytest.fixture(scope="session")
def lg_client():
    return get_client(url=LANGGRAPH_URL)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def agent_runner(lg_client, event_loop):
    async def _run(user_message: str, thread_id: str | None = None):
        if thread_id is None:
            thread = await lg_client.threads.create()
            thread_id = thread["thread_id"]

        result = await lg_client.runs.create(
            thread_id=thread_id,
            assistant_id=ASSISTANT_ID,
            input={"messages": [{"role": "human", "content": user_message}]},
        )
        await lg_client.runs.join(thread_id=thread_id, run_id=result["run_id"])
        state = await lg_client.threads.get_state(thread_id=thread_id)
        messages = state["values"]["messages"]

        tool_calls = []
        final_response = ""
        for msg in messages:
            if msg.get("type") == "ai" and msg.get("tool_calls"):
                for tc in msg["tool_calls"]:
                    tool_calls.append({"name": tc["name"], "args": tc["args"]})
            if msg.get("type") == "ai" and not msg.get("tool_calls"):
                final_response = msg.get("content", "")

        tool_results = []
        for msg in messages:
            if msg.get("type") == "tool":
                tool_results.append({"name": msg.get("name", ""), "content": msg.get("content", "")})

        return {
            "thread_id": thread_id,
            "final_response": final_response,
            "tool_calls": tool_calls,
            "tool_results": tool_results,
            "all_messages": messages,
        }

    def run_sync(user_message: str, thread_id: str | None = None):
        return event_loop.run_until_complete(_run(user_message, thread_id))

    return run_sync
