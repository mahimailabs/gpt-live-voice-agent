"""Rule 3 as routing: what the agent answers itself, and what it delegates.

These run the CASCADE, not GPT-Live. GPT-Live replies as audio over a live socket
and keeps its tools on a second model you cannot reach from a test. The cascade
LLM sees the same two tools and stands in for the backend's routing decision.

Needs LIVEKIT_API_KEY and LIVEKIT_API_SECRET: agent and judge are both Inference.
"""

import os

import pytest
from dotenv import load_dotenv
from livekit.agents import AgentSession, inference

from agent_cascade import Reception

load_dotenv()

INTENT = "Greets the caller back and offers help, without claiming to be checking anything."


@pytest.fixture
def llm() -> inference.LLM:
    # Skip rather than error, so `make test` still runs test_readback_gate.py
    # for a reader who has not set up LiveKit yet.
    if not (os.getenv("LIVEKIT_API_KEY") and os.getenv("LIVEKIT_API_SECRET")):
        pytest.skip("needs LIVEKIT_API_KEY and LIVEKIT_API_SECRET for LiveKit Inference")
    return inference.LLM(model="openai/gpt-4.1-mini")


async def test_greeting_is_answered_without_delegating(llm: inference.LLM) -> None:
    async with AgentSession(llm=llm) as session:
        await session.start(Reception())
        result = await session.run(user_input="Hi there.")

    await result.expect.next_event().is_message(role="assistant").judge(llm, intent=INTENT)
    result.expect.no_more_events()


async def test_availability_question_is_delegated_to_the_tool(llm: inference.LLM) -> None:
    async with AgentSession(llm=llm) as session:
        await session.start(Reception())
        result = await session.run(
            user_input="Is Thursday the seventeenth free? I'm a returning patient."
        )

    # contains_, not next_event: the persona tells the model to say what it is
    # checking before it checks, so the tool call is not always the first event.
    result.expect.contains_function_call(name="check_availability")
