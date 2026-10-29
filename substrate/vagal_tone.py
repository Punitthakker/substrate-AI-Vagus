"""Organ 04: VAGAL TONE - the firmness dial, named for the nerve that joins heart to brain.

Deterministic and auditable. Firmness shapes delivery, never the verdict.
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


def vagal_tone(person: Person, state: State, stakes: str, temperament_bias: int = 0) -> int:
    """firmness = f(consented candor, stakes, inferred state, temperament). Clamped to 1..5."""
    f = person.consent.candor_level
    if stakes == "high":
        f += 1                      # money moving: lean firmer
    if state == State.euphoric:
        f += 1                      # the moment it is most needed
    if state == State.stressed:
        f -= 1                      # same truth, gentler landing
    if state == State.defensive:
        f = max(f, 3)               # pushback never weakens the floor
    f += temperament_bias
    return max(1, min(5, f))
