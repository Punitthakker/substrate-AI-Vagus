"""Organ 04: VAGAL TONE - the firmness dial, named for the nerve that joins heart to brain.

Deterministic and auditable. Firmness shapes delivery, never the verdict.
v1.1 adds the learned component: the Vagus Ledger tells the dial which firmness this particular
human actually acts on, so a client who keeps ignoring gentle advice gets firmer advice.
"""
from __future__ import annotations

from .schemas import Facts, Person, State


def infer_stakes(facts: Facts, person: Person) -> str:
    if facts.leverage or facts.floor.severity == 2:
        return "high"
    if facts.amount and person.liquid_net_worth:
        share = facts.amount / person.liquid_net_worth
        if share >= 0.10:
            return "high"
        if share >= 0.02:
            return "medium"
        return "low"
    return "medium" if facts.amount else "low"


def learned_shift(person: Person, f: int) -> tuple[int, str | None]:
    """If this human ignores advice at this firmness more often than they follow it, go one firmer."""
    if f >= 5:
        return 0, None
    stats = person.adherence.get(str(f), {})
    ignored, followed = stats.get("ignored", 0), stats.get("followed", 0)
    if ignored >= 1 and ignored > followed:
        return 1, f"Learned: {person.name.split()[0]} ignored advice at tone {f} {ignored}x, so tone rises to {f + 1}."
    return 0, None


def vagal_tone_explained(person: Person, state: State, stakes: str, temperament_bias: int = 0) -> tuple[int, list[str]]:
    """firmness = f(consented candor, stakes, inferred state, temperament, learned adherence). Clamped 1..5."""
    notes: list[str] = []
    f = person.consent.candor_level
    notes.append(f"Consented candor {f}.")
    if stakes == "high":
        f += 1
        notes.append("High stakes: +1.")
    if state == State.euphoric:
        f += 1
        notes.append("Euphoric state: +1.")
    if state == State.stressed:
        f -= 1
        notes.append("Stressed state: -1, same truth, gentler landing.")
    if state == State.defensive and f < 3:
        f = 3
        notes.append("Pushback never weakens the floor.")
    if temperament_bias:
        f += temperament_bias
        notes.append(f"Temperament {temperament_bias:+d}.")
    f = max(1, min(5, f))
    shift, why = learned_shift(person, f)
    if shift:
        f = min(5, f + shift)
        notes.append(why)
    return f, notes


def vagal_tone(person: Person, state: State, stakes: str, temperament_bias: int = 0) -> int:
    return vagal_tone_explained(person, state, stakes, temperament_bias)[0]
