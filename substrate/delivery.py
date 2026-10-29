"""Organ 05: the Delivery Layer.

The verdict headline is inserted verbatim. Temperament, tissue and firmness shape everything around
it: the opener, the order, the warmth, the closer. Architecturally, delivery cannot rewrite the truth.
"""
from __future__ import annotations

from .schemas import State, Verdict
from .temperaments import Temperament


def deliver(v: Verdict, t: Temperament, firmness: int, state: State, overrides: dict | None = None,
            ack: list[str] | None = None) -> str:
    o = overrides or {}
    pol = v.polarity.value
    open_ = o.get("open", {}).get(pol, t.open.get(pol, ""))
    close = o.get("close", {}).get(pol, t.close.get(pol, ""))
    empathy = o.get("empathy", t.empathy)
    pushback = o.get("pushback", t.pushback)
    lead = o.get("reasons_lead", t.reasons_lead)

    parts: list[str] = []
    if state == State.stressed and empathy:
        parts.append(empathy)
    if state == State.defensive and pushback:
        parts.append(pushback)
    feel = list(ack or [])
    if parts and feel and len(feel) > 1:
        feel = feel[1:]            # the temperament already acknowledged the feeling; keep only the need
    elif parts and feel and not any(feel[0].startswith(x) for x in ("You're asking", "It's your call", "You're not wrong")):
        feel = []
    if firmness <= 2 and state != State.defensive:
        parts.extend(feel)
        # gentle landing: warmth first, then the truth
        if open_:
            parts.append(open_)
        parts.append(f"**{v.headline}**")
    else:
        # firm landing: the truth first, then the voice
        parts.append(f"**{v.headline}**")
        parts.extend(feel)
        if open_:
            parts.append(open_)
    if v.reasons:
        parts.append(lead + "\n" + "\n".join(f"- {r}" for r in v.reasons))
    if close:
        parts.append(close)
    if firmness >= 5 and pol != "proceed":
        parts.append("_This advice is recorded in your Vagus Ledger._")
    return "\n\n".join(p for p in parts if p)
