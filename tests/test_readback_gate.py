"""Rule 4's guardrail at the tool level: no reference number without a read-back.

Like test_delegation_routing.py, nothing here touches GPT-Live: it is audio-only
and answers over a live socket, so behavioural tests run against the cascade in
text. This file goes lower still and calls the tool directly, no model at all.

This is the half of rule 4 you can enforce. GPT-Live will not repeat a string
exactly, so the tool refuses to issue a reference until the caller has heard the
date and time read back.
"""

from tools import BOOKINGS, ClinicTools

REMINDER = "Read the date and time back to the caller first, then call again."


async def test_read_back_false_returns_the_reminder_and_writes_nothing() -> None:
    before = {day: dict(slots) for day, slots in BOOKINGS.items()}

    result = await ClinicTools().book_appointment("2026-09-18", "1:00 PM", read_back=False)

    assert result == REMINDER
    assert BOOKINGS == before


async def test_read_back_true_writes_and_returns_a_reference() -> None:
    result = await ClinicTools().book_appointment("2026-09-18", "4:00 PM", read_back=True)

    reference = BOOKINGS["2026-09-18"]["4:00 PM"]
    assert result == f"Booked for 2026-09-18 at 4:00 PM. Reference {reference}."
    assert 1000 <= reference <= 9999
