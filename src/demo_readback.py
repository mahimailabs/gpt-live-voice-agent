"""Rule 4: GPT-Live cannot speak a script, so an exact read-back is not a thing.

Same question five times, five answers. Watch the reference number survive and
the sentence around it change. This reuses the cascade agent's persona
and tools in a text harness. On a real cascade you also have a TTS, so you could
hand over the exact string with session.say(). GPT-Live has no TTS and say()
raises (demo_say_raises.py).

Not run on GPT-Live because there is no text-only mode. You can type at it,
since session.run routes duplex models through a typed-input branch
(gpt_live_model.py:1048-1060), but the reply is generated as speech over a socket
and arrives as a transcript. By hand: `make gptlive`, book something, then ask
"what was that reference number again?" five times.

Needs LIVEKIT_API_KEY and LIVEKIT_API_SECRET: the cascade LLM is LiveKit Inference.
"""

import asyncio

from dotenv import load_dotenv
from livekit.agents import AgentSession, inference, mock_tools

from agent_cascade import Reception
from tools import _reference

load_dotenv()

RUNS = 5
# A mock may declare any subset of the real tool's parameters, so a no-arg lambda
# is enough. The reference is the real one for this slot, so what the demo prints
# matches what book_appointment would actually issue.
_DATE, _TIME = "2026-09-18", "2:30 PM"
BOOKED = f"Booked for {_DATE} at {_TIME}. Reference {_reference(_DATE, _TIME)}."


async def ask_for_the_reference(llm: inference.LLM) -> str:
    async with AgentSession(llm=llm) as session:
        await session.start(Reception())
        with mock_tools(Reception, {"book_appointment": lambda: BOOKED}):
            await session.run(user_input="Book me Friday the eighteenth at two thirty, go ahead.")
            result = await session.run(user_input="Sorry, what was that reference number?")

    for event in reversed(result.events):
        if event.type == "message" and event.item.role == "assistant":
            return event.item.text_content or "(empty message)"
    return "(no assistant message)"


async def main() -> None:
    llm = inference.LLM(model="openai/gpt-4.1-mini")
    print(f"Tool returned, every run: {BOOKED}\n")
    for run in range(1, RUNS + 1):
        print(f"{run}. {await ask_for_the_reference(llm)}")


if __name__ == "__main__":
    asyncio.run(main())
