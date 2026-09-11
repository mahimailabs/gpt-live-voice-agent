"""The same receptionist as an STT-LLM-TTS cascade, for comparison.

Two differences, and they are the whole comparison. This LLM sees the tools, so
its instructions must describe them, where the GPT-Live voice persona must not.
And everything GPT-Live discards works here: turn_detection= and vad= below are
real, and the session waits for the endpointer before it answers.

No duplex_session on a cascade, so no append_thinking: mid-call context goes into
chat_ctx, which GPT-Live refuses to let you edit after start.
"""

import logging

from dotenv import load_dotenv
from livekit.agents import Agent, AgentServer, AgentSession, JobContext, cli, inference
from livekit.plugins import silero

from personas import VOICE_PERSONA
from tools import ClinicTools

load_dotenv()
logger = logging.getLogger("clinic-cascade")
server = AgentServer()

# The half of BACKEND_INSTRUCTIONS that has to move onto the voice model once
# there is only one model. On GPT-Live this text would be actively harmful.
TOOL_GUIDANCE = """You call your own tools. There is no backend model here.

Call check_availability before you offer any time out loud, and never guess a slot.
Call book_appointment twice: once with read_back false, then read the date and time
back to the caller, then again with read_back true once they confirm. Only that
second call issues a reference number, and you must not invent one."""

CASCADE_INSTRUCTIONS = f"{VOICE_PERSONA}\n\n{TOOL_GUIDANCE}"


class Reception(ClinicTools, Agent):
    def __init__(self) -> None:
        super().__init__(instructions=CASCADE_INSTRUCTIONS)

    async def on_enter(self) -> None:
        # This one could equally be session.say("..."), which is exactly what
        # GPT-Live refuses: see demo_say_raises.py.
        self.session.generate_reply(instructions="Greet the caller and ask what they need.")


@server.rtc_session(agent_name="clinic-cascade")
async def entrypoint(ctx: JobContext) -> None:
    session = AgentSession(
        stt=inference.STT(model="deepgram/nova-3"),
        llm=inference.LLM(model="openai/gpt-4.1-mini"),
        tts=inference.TTS(model="inworld/inworld-tts-2"),
        # turn_detection= is deprecated in 1.8.1 for
        # turn_handling=TurnHandlingOptions(...) and logs one warning at startup.
        # Kept in this spelling because it is the line GPT-Live throws away.
        turn_detection=inference.TurnDetector(),
        vad=silero.VAD.load(),
    )

    async def log_usage() -> None:
        for usage in session.usage.model_usage:
            logger.info("usage %r", usage)

    ctx.add_shutdown_callback(log_usage)
    await session.start(room=ctx.room, agent=Reception())


if __name__ == "__main__":
    cli.run_app(server)
