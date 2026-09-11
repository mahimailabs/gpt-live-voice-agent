<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/cover-dark.png">
    <source media="(prefers-color-scheme: light)" srcset="docs/cover-light.png">
    <img src="docs/cover-light.png" alt="GPT-Live voice agent on LiveKit — the talker and the thinker" width="100%">
  </picture>
</p>

<p align="center">
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.11%2B-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python 3.11+"></a>
  <a href="https://github.com/livekit/agents"><img src="https://img.shields.io/badge/livekit--agents-~%3D1.8-00B37E?style=flat-square&logo=livekit&logoColor=white" alt="livekit-agents ~=1.8"></a>
  <a href="https://docs.astral.sh/uv/"><img src="https://img.shields.io/badge/uv-managed-DE5FE9?style=flat-square&logo=uv&logoColor=white" alt="Managed with uv"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue?style=flat-square" alt="MIT License"></a>
  <a href="https://discord.gg/9nrTM3E4v9"><img src="https://img.shields.io/badge/Discord-join-5865F2?style=flat-square&logo=discord&logoColor=white" alt="Join the Discord"></a>
</p>

# GPT-Live Voice Agent on LiveKit

**A minimal, runnable clinic phone agent built on OpenAI's GPT-Live full-duplex voice model, side by side with the same agent as a classic STT → LLM → TTS cascade.**

Run both. Interrupt both. Ask both for an exact reference number. You will have an opinion in ten minutes.

This repo is the code behind the article *[GPT-Live on LiveKit: Five Voice Agent Rules That Just Broke](https://medium.com/voice-ai-mastery/gpt-live-on-livekit-i-was-not-ready-for-this-5eab64d95988?sk=38988d5eff08b9773f9848a7133967a7)* and the starting point for the clinic agent in the [Voice Agents Mastery](https://medium.com/voice-ai-mastery) series.

---

## What GPT-Live changes

GPT-Live listens and speaks at the same time. It does not take turns. That one difference breaks five things you may have learned building voice agents:

| # | Rule that breaks | What this repo shows |
|---|---|---|
| 1 | You tune turn detection | The model owns the turn. `turn_detection` and endpointing options are discarded. A VAD is not required and cannot interrupt it: the model ends its own turn. |
| 2 | You can interrupt the agent | Playback stops. The model keeps talking and cannot be truncated. |
| 3 | One prompt, one model | Two models: a **voice model** with a persona, a **backend model** with the tools. The voice model never sees your tools. |
| 4 | `say()` reads a script | `say()` raises. No text-only mode, no half-cascade. Exact read-backs are not guaranteed. |
| 5 | You edit the chat context | Append-only after start. Three channels instead: `thinking`, `commentary`, `instructions`. |

The part that is new: **delegation is non-blocking.** The voice model keeps the conversation going while the backend model reasons and calls your tools. The talker is never busy. The thinker is never on the line.

---

## Quick start

```bash
git clone https://github.com/mahimailabs/gpt-live-voice-agent
cd gpt-live-voice-agent
uv sync
cp .env.example .env   # add LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET, OPENAI_API_KEY
```

Talk to the GPT-Live agent in your terminal:

```bash
make gptlive
```

Talk to the same agent as a cascade:

```bash
make cascade
```

Interrupt each one three times. That is the whole demo.

---

## The one sentence that matters

The voice model cannot see your tools. So the persona has to say **what to delegate**, not what the tools do. From `src/personas.py`:

> Delegate any question about appointments, availability, or a patient's record, and say what you are checking while you wait. Answer greetings, hours, and directions yourself.

Without that line, the voice model delegates small talk and answers availability questions it has no data for. With it, routing works.

---

## Verify each rule

| Rule | Command | What to look for |
|---|---|---|
| 1 · No turn detector | `make gptlive`, say "I'd like to book for, um…" and pause | It waits. Nothing configured that. |
| 2 · Cannot stop it | `make gptlive`, interrupt mid-sentence | Audio cuts. Next turn may reference what you did not hear. |
| 3 · Two prompts | `make test` | `test_delegation_routing.py` shows "hi" stays local, "is Thursday free" calls a tool. |
| 4 · No script | `make say-raises` then `make readback` | `say()` raises on GPT-Live. The read-back script prints five outputs for the same reference number. |
| 5 · Append-only | read `src/agent_gptlive.py` `on_enter` | Context arrives via `append_thinking`, not by editing history. |

Run the three simulated callers (rushed parent, delegated booking, mid-call reschedule):

```bash
make simulate
```

Enable agent observability on the LiveKit project first. Without it the scenarios
still run, but `agent_expectations` are never evaluated and the run ends with
`can't summarize: user data recording (observability) is disabled`, which reads
like a pass.

---

## Project layout

```
src/
  personas.py         voice persona + backend instructions, side by side
  tools.py            check_availability, book_appointment (fake clinic, deterministic)
  agent_gptlive.py    Reception agent on GPTLiveModel
  agent_cascade.py    same agent on STT-LLM-TTS
  demo_readback.py    ask for the reference number five times, print all five
  demo_say_raises.py  show that say() raises on GPT-Live
tests/
  test_delegation_routing.py
  test_readback_gate.py
scenarios.yaml        three simulated callers for `lk agent simulate`
```

Under 400 lines of Python. No frontend. No deploy config. One job.

---

## Cost

GPT-Live is priced per minute of session for the voice model, plus tokens for the backend model. LiveKit reports the two separately in `session.usage`. Both agents log usage at shutdown so you can compare a five-minute call on each.

---

## Requirements

- Python 3.11+ and [uv](https://docs.astral.sh/uv/)
- A [LiveKit Cloud](https://cloud.livekit.io) project (free tier works)
- An OpenAI API key with GPT-Live access
- [LiveKit CLI](https://docs.livekit.io/intro/basics/cli/) for `make simulate`

---

## Read more

- [LiveKit GPT-Live plugin guide](https://docs.livekit.io/agents/models/realtime/plugins/gpt-live)
- [LiveKit pipeline types: cascade vs realtime vs half-cascade](https://docs.livekit.io/agents/models/pipelines)
- [Voice Agents Handbook](https://handbook.mahimai.ca) — complete handbook for production voice agents with LiveKit

---

Built by [Mahimai Raja J](https://mahimai.ca) · [@voicexprt](https://x.com/voicexprt)

If this saved you an afternoon, a star helps the next person find it.
