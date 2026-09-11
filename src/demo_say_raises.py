"""Rule 4: session.say() on GPT-Live raises. There is no half-cascade.

The guard is agent_activity.py:1554-1565 and it is four conditions: no rendered
audio= was handed in, there is no TTS, the realtime model does not itself support
say(), and the session has an audio sink that is enabled. DuplexRealtimeAdapter
hardcodes supports_say=False (duplex_adapter.py:268), so the third condition
always holds and the raise is unavoidable without a TTS.

Attaching a TTS, or passing say() pre-rendered audio=, silences it. Both are the
half-cascade this repo will not build: they put a second voice on the line.

This runs offline. OPENAI_API_KEY only has to be non-empty
(gpt_live_model.py:198-203); GPT-Live account access is not needed, because the
guard is a local check and session.start() does not wait on the websocket. A
connection error on stderr is expected when you have no access, and harmless.
"""

import asyncio

from dotenv import load_dotenv
from livekit import rtc
from livekit.agents import AgentSession
from livekit.agents.voice.io import AudioOutput, AudioOutputCapabilities
from livekit.plugins.openai.realtime import GPTLiveModel

from agent_gptlive import Reception
from personas import BACKEND_INSTRUCTIONS

load_dotenv()


class NullAudioOutput(AudioOutput):
    """A console or room session always has an audio sink. This script has no
    room, so it attaches one: the guard only fires when audio output is present
    and enabled, and otherwise say() falls through to the text path."""

    def __init__(self) -> None:
        super().__init__(label="null", capabilities=AudioOutputCapabilities(pause=False))

    async def capture_frame(self, frame: rtc.AudioFrame) -> None: ...

    def flush(self) -> None: ...

    def clear_buffer(self) -> None: ...


async def main() -> None:
    # Held separately: AgentSession.aclose() closes the activity but never the
    # model, and GPTLiveModel owns an aiohttp session outside a job context.
    model = GPTLiveModel(
        responses_options={"model": "gpt-5.6-luna", "instructions": BACKEND_INSTRUCTIONS}
    )
    session = AgentSession(llm=model)
    session.output.audio = NullAudioOutput()
    await session.start(Reception())
    try:
        session.say("Your appointment is confirmed for Friday the eighteenth at 2:30 PM.")
    except RuntimeError as exc:
        print(f"session.say() raised {type(exc).__name__}:\n  {exc}")
    else:
        print("say() did not raise. Audio output is missing or disabled on this session.")
    finally:
        await session.aclose()
        await model.aclose()


if __name__ == "__main__":
    asyncio.run(main())
