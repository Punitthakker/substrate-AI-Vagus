"""Organ 05: the Delivery Layer.

The verdict headline is inserted verbatim. Temperament and firmness shape everything around it:
the opener, the order, the warmth, the closer. Architecturally, delivery cannot rewrite the truth.
"""
from __future__ import annotations

from .schemas import State, Verdict
from .temperaments import Temperament


def deliver(v: Verdict, t: Temperament, firmness: int, state: State) -> str:
    pol = v.polarity.value
    parts: list[str] = []

    if state == State.stressed and t.empathy:
        parts.append(t.empathy)
    if state == State.defensive and t.pushback:
        parts.append(t.pushback)

    opener = t.open.get(pol, "")
    if firmness <= 2 and state != State.defensive:
        # gentle landing: warmth first, then the truth
        if opener:
            parts.append(opener)
        parts.append(f"**{v.headline}**")
    else:
        # firm landing: the truth first, then the voice
        parts.append(f"**{v.headline}**")
        if opener:
            parts.append(opener)

    if v.reasons:
        bullets = "\n".join(f"- {r}" for r in v.reasons)
        parts.append(f"{t.reasons_lead}\n{bullets}")

    closer = t.close.get(pol, "")
    if closer:
        parts.append(closer)
    if firmness >= 5 and pol != "proceed":
        parts.append("_This advice is recorded in your Vagus Ledger._")
    return "\n\n".join(p for p in parts if p)
