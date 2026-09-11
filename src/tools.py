"""A fake clinic, deterministic so the demo reads the same every run.

These are the BACKEND model's tools; the voice model never sees them. Mixing
ClinicTools into the Agent puts them in the agent process, and the call is
non-blocking, so the voice model keeps talking while this runs.

Docstrings are the schema: when to call, when not to, and every argument format.
"""

import hashlib
from datetime import date as _date

from livekit.agents import function_tool

# Open slots keyed on weekday (0 = Monday). Deterministic on purpose, so a blog
# reader gets the same transcript.
_SLOTS_BY_WEEKDAY = {
    0: ["9:00 AM", "10:30 AM", "1:00 PM", "3:30 PM"],
    1: ["8:30 AM", "11:00 AM", "2:00 PM"],
    2: ["9:30 AM", "1:30 PM", "4:30 PM"],
    3: ["11:00 AM", "3:15 PM", "4:45 PM"],
    4: ["1:00 PM", "2:30 PM", "4:00 PM"],
}

# New patients get a double-length first visit, which the clinic only runs in
# the afternoon. This is why `party` is a parameter and not a constant.
_AFTERNOON_START = 13

# date -> {time -> reference}. In-memory, so it resets with the process.
BOOKINGS: dict[str, dict[str, int]] = {}


def _reference(day: str, time: str) -> int:
    """Stable 4-digit reference. Not random, not process-salted."""
    return 1000 + int(hashlib.sha256(f"{day} {time}".encode()).hexdigest(), 16) % 9000


def _hour24(time: str) -> int:
    """13 for "1:00 PM". Every time here is "H:MM AM" or "H:MM PM"."""
    clock, meridiem = time.split(" ")
    hour = int(clock.split(":")[0]) % 12
    return hour + 12 if meridiem == "PM" else hour


class ClinicTools:
    """Mixed into the Agent in both agent_gptlive.py and agent_cascade.py."""

    @function_tool
    async def check_availability(self, date: str, party: str) -> str:
        """Look up the open appointment slots for one specific day.

        Call this whenever the caller asks what is free, whether a day works, or
        what times are left, and before you offer any time out loud. The calendar
        changes during the day, so never answer from what you were told earlier
        in the call.

        Do not call this to book anything; it only reads. Do not call it for a
        range of days: it takes one day, so if the caller says "sometime next
        week", ask which day first.

        Args:
            date: The single day to check, as YYYY-MM-DD, for example 2026-09-18.
                Resolve words like "Thursday" to a real date before calling.
            party: Either "new" for a caller not seen at this clinic before, or
                "returning" for an existing patient. New patients get a longer
                first visit and so see fewer slots.

        Returns:
            One sentence naming the open times, ready to read out loud.
        """
        try:
            weekday = _date.fromisoformat(date).weekday()
        except ValueError:
            return f"{date} is not a valid date. Ask the caller for the day again."

        slots = _SLOTS_BY_WEEKDAY.get(weekday)
        if not slots:
            return f"The clinic is closed on {date}. It is open weekdays only."

        if party == "new":
            slots = [s for s in slots if _hour24(s) >= _AFTERNOON_START]
        slots = [s for s in slots if s not in BOOKINGS.get(date, {})]

        if not slots:
            return f"Nothing open on {date}. Offer the caller another day."
        count = "1 slot" if len(slots) == 1 else f"{len(slots)} slots"
        return f"{count} open on {date}: {', '.join(slots)}."

    @function_tool
    async def book_appointment(self, date: str, time: str, read_back: bool) -> str:
        """Hold an appointment slot for the caller.

        Call this only once the caller has named both a day and a time and has
        agreed to it. Call it twice: first with read_back false, which returns
        the instruction to confirm out loud, then again with read_back true once
        the caller has heard the date and time and said yes.

        Do not call this to check what is free. Do not pass read_back true unless
        the caller actually confirmed, and do not invent a reference number: only
        this tool issues one.

        Args:
            date: The agreed day, as YYYY-MM-DD, for example 2026-09-18.
            time: The agreed time exactly as it was offered, 12-hour with the
                meridiem, for example "2:30 PM".
            read_back: False on the first call, true on the second, after the
                caller confirmed. True without a confirmation books the wrong
                slot and there is no undo.

        Returns:
            Either the instruction to read the details back, or a confirmation
            sentence containing the reference number.
        """
        if not read_back:
            return "Read the date and time back to the caller first, then call again."

        reference = _reference(date, time)
        BOOKINGS.setdefault(date, {})[time] = reference
        return f"Booked for {date} at {time}. Reference {reference}."
