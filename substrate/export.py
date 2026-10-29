"""The .sub file: a portable, ownable, bequeathable genome.

Person model + the full hash-chained ledger + consent, sealed with a checksum. Verifiable offline,
independent of Substrate the company. The artifact a family can hold for a hundred years.
"""
from __future__ import annotations

import hashlib

from .ledger import Store, canonical, now, verify_chain

FORMAT = "substrate.sub/1"


def export_sub(store: Store, user_id: str) -> dict:
    person = store.get_person(user_id)
    if not person:
        raise KeyError(user_id)
    events = store.events(user_id)
    body = {
        "format": FORMAT,
        "exported_at": now(),
        "genome": person.model_dump(),
        "consent": person.consent.model_dump(),
        "ledger": events,
        "letters": __import__("substrate.legacy", fromlist=["export_for"]).export_for(store, user_id),
        "chain": {"length": len(events), "head": events[-1]["hash"] if events else None,
                  "verified": verify_chain(events)},
    }
    body["checksum"] = hashlib.sha256(canonical(body).encode()).hexdigest()
    return body


def verify_sub(doc: dict) -> dict:
    body = {k: v for k, v in doc.items() if k != "checksum"}
    ok_sum = hashlib.sha256(canonical(body).encode()).hexdigest() == doc.get("checksum")
    ok_chain = verify_chain(doc.get("ledger", []))
    return {"checksum_valid": ok_sum, "chain_valid": ok_chain, "valid": ok_sum and ok_chain}
