# Everything runs through uv. `uv sync` once, then pick a target.
.PHONY: gptlive cascade test simulate readback say-raises

# Talk to the GPT-Live agent from your terminal mic. Interrupt it mid-sentence:
# playback stops, the model does not.
gptlive:
	uv run src/agent_gptlive.py console

# The same receptionist as an STT-LLM-TTS cascade, for comparison.
cascade:
	uv run src/agent_cascade.py console

# Behavioural tests. Run against the cascade LLM in text, not GPT-Live.
test:
	uv run pytest -q

# Simulated callers against the gptlive agent. lk spawns it locally; no need to
# have it running. Text-only by default, so --audio is what makes barge-in real.
# lk is a separate Go process and does not read .env, so export it first.
simulate:
	set -a; . ./.env; set +a; lk agent simulate --scenarios scenarios.yaml --audio src/agent_gptlive.py

# Rule 4 on the CASCADE, the generous case: the same question five times, five
# different sentences. GPT-Live has no text-only mode, so rule 4 there is by hand.
readback:
	uv run src/demo_readback.py

# Rule 4: session.say() on GPT-Live with no TTS attached.
say-raises:
	uv run src/demo_say_raises.py
