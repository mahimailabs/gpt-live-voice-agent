"""The GPT-Live receptionist: rules 1, 2, 3 and 5. Rule 4 is in the demo_ scripts.

Run `make gptlive`, then interrupt it mid-sentence.

Rule 1 (the model owns the turn) and rule 2 (barge-in does not cut the model) are
both things this file does NOT do, so they are annotated where they would have
gone: see the AgentSession call below. Rule 3 is personas.py. Rule 5 is on_enter.
"""

import logging

from dotenv import load_dotenv
from livekit.agents import Agent, AgentServer, AgentSession, JobContext, cli
from livekit.plugins.openai.realtime import GPTLiveModel

from personas import BACKEND_INSTRUCTIONS, VOICE_PERSONA
from tools import ClinicTools

load_dotenv()
logger = logging.getLogger("clinic-gptlive")
server = AgentServer()


class Reception(ClinicTools, Agent):
    def __init__(self) -> None:
        # VOICE_PERSONA and nothing else. The tools arrive from ClinicTools and
        # belong to the backend model; this model is never shown them.
        super().__init__(instructions=VOICE_PERSONA)

    async def on_enter(self) -> None:
        # Rule 5: append-only after start. Three channels exist, each capped at
        # 500 tokens by the service, all sync and fire-and-forget. Only thinking
        # is used here: context the model holds but does not say out loud.
        # append_commentary is what generate_reply below goes through, and
        # append_instructions adds a standing rule.
        self.duplex_session.append_thinking("The caller just connected. Nothing has been said yet.")

        # This does not set instructions on this model: the plugin wraps the text
        # into a commentary append (gpt_live_model.py:1046). The model may
        # decline, and a decline is not a raise, it lands on the handle.
        handle = self.session.generate_reply(
            instructions="Greet the caller and ask what they need."
        )
        await handle
        if (refusal := handle.exception()) is not None:
            logger.warning("the model declined to greet: %s", refusal)


@server.rtc_session(agent_name="clinic-gptlive")
async def entrypoint(ctx: JobContext) -> None:
    session = AgentSession(
        llm=GPTLiveModel(
            voice="marin",
            responses_options={"model": "gpt-5.6-luna", "instructions": BACKEND_INSTRUCTIONS},
        ),
        # Rule 1: no stt=, no tts=, no turn_detection=. can_disable_turn_detection
        # is False, so a client turn detector or any mode other than "realtime_llm"
        # is warned about and discarded (agent_activity.py:360-364, 406-418,
        # 441-463). "realtime_llm" is the one spelling that survives, and it
        # silently switches off interruption by audio activity
        # (agent_activity.py:334-337). Endpointing options are dropped in silence.
        #
        # And deliberately no vad=. AgentSession builds a default VAD then unwires
        # it for this model (agent_activity.py:1174-1177). Passing one flips
        # _using_default_vad to False, moving user-turn state off the model's own
        # speech events back onto client VAD (agent_activity.py:2057, 2080).
        #
        # Rule 2: interrupt it and the framework does not treat that as an
        # interruption at all. supports_overlapping_speech makes
        # _on_input_speech_started return early, commented "the caller talking is
        # not an interruption here; the model ends its own turn"
        # (agent_activity.py:2065-2067). Playback stops because the model stops
        # sending audio, and nothing is trimmed: truncate() is a no-op
        # (duplex_adapter.py:616-624).
    )

    async def log_usage() -> None:
        # Voice seconds land as session_duration on the gpt-live-1 entry; the
        # backend Responses model reports its tokens on a separate entry.
        for usage in session.usage.model_usage:
            logger.info("usage %r", usage)

    ctx.add_shutdown_callback(log_usage)
    await session.start(room=ctx.room, agent=Reception())


if __name__ == "__main__":
    cli.run_app(server)
