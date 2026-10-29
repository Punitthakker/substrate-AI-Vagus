"""Memory bridge: the genome, readable by the open-source memory ecosystem.

Agents built on Mem0 (mem0ai/mem0, Apache-2.0) or Letta (letta-ai/letta, formerly MemGPT, Apache-2.0) keep their
own long-term memory. This bridge lets them carry the parts of a Substrate genome that make them kinder and more
honest: values, goals, known patterns, lessons paid for, active pacts, and what was inherited.

  memories(person)   plain-language facts, one per line (any memory system can ingest these)
  core_block(person) a compact block for Letta-style core memory ("human" block), under 2,000 characters
  push_mem0(person)  writes memories into Mem0 when the mem0ai package is installed (MEM0_API_KEY for the
                     hosted platform, otherwise a local Mem0 instance)

Money balances, positions and raw messages are never exported: memory should hold who someone is, not their
account details.
"""
from __future__ import annotations

import os

from .schemas import Person


def memories(person: Person) -> list[str]:
    first = (person.name or "The user").split()[0]
    out = []
    if person.values:
        out.append(f"{first} values {', '.join(person.values)}.")
    for g in person.goals:
        out.append(f"{first}'s goal (priority {g.priority}): {g.name}.")
    if person.risk_profile.observed and person.risk_profile.observed != person.risk_profile.stated:
        out.append(f"{first} says their risk appetite is {person.risk_profile.stated}, but behaves "
                   f"{person.risk_profile.observed}.")
    for b in person.biases:
        out.append(f"{first} is prone to {b.type}" + (f" (seen {len(b.evidence)}x)." if b.evidence else "."))
    if person.decision_style:
        out.append(f"Decision style: {person.decision_style}")
    for l in person.lessons[-5:]:
        out.append(f"Lesson {first} paid for: {l}")
    for p in person.pacts:
        if p.get("status") == "active":
            out.append(f"{first} made a pact: {p.get('text')}. Hold them to it, kindly.")
    for a in person.ancestry:
        out.append(f"{first} inherited {a.name}'s ({a.relation}) values: {', '.join(a.values[:4])}.")
        if a.patterns:
            out.append(f"{a.name} was prone to {', '.join(a.patterns)}. Watch for the same pattern in {first}.")
    out.append(f"{first} consented to candor level {person.consent.candor_level}/5: tell the truth, "
               f"{'gently' if person.consent.candor_level <= 2 else 'directly'}.")
    return out


def core_block(person: Person) -> str:
    text = "\n".join(memories(person))
    return text[:1990]


def push_mem0(person: Person) -> int:
    try:
        if os.environ.get("MEM0_API_KEY"):
            from mem0 import MemoryClient  # type: ignore
            client = MemoryClient(api_key=os.environ["MEM0_API_KEY"])
            for m in memories(person):
                client.add([{"role": "user", "content": m}], user_id=person.user_id, metadata={"source": "substrate"})
        else:
            from mem0 import Memory  # type: ignore
            mem = Memory()
            for m in memories(person):
                mem.add(m, user_id=person.user_id, metadata={"source": "substrate"})
    except ImportError as e:
        raise RuntimeError("Install mem0ai to push memories (pip install mem0ai).") from e
    return len(memories(person))
