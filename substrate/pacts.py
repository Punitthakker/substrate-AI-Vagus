"""Pacts: precommitment, the oldest tool in behavioural science (Ulysses and the mast).

When Substrate says NO BET, NOT TONIGHT or STOP, it offers a pact: "hold me to it until 9am". The human chooses.
If they come back before the pact ends, Substrate reminds them of their own words, firmly, and even a fair bet
waits: the promise was theirs. Keeping it is recorded and celebrated; breaking it is recorded without shame.
A pact is always voluntary and can be released, and the release is on the ledger too.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from pydantic import BaseModel, Field

from .ledger import Store
from .schemas import Person

TEXT = {"markets": "No bets", "wellbeing": "No sending, no big decisions", "wealth": "No trade on this",
        "founder": "No signing or hiring on this", "venture": "No wire on this"}


class Pact(BaseModel):
    id: str = Field(default_factory=lambda: f"P-{uuid.uuid4().hex[:8]}")
    ledger_id: str = ""
    domain: str
    text: str
    created: str
    until: str
    status: str = "active"          # active | kept | broken | released


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(d: datetime) -> str:
    return d.strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def _offset(person: Person) -> timedelta:
    return timedelta(hours=float((person.profile or {}).get("utc_offset", 4)))


def local_hhmm(person: Person, iso: str) -> str:
    return (_parse(iso) + _offset(person)).strftime("%H:%M")


def suggest(person: Person, domain: str, now: datetime | None = None) -> dict:
    """Until 9am local tomorrow if it's evening or night; otherwise a 24-hour sleep-on-it."""
    now = now or _now()
    local = now + _offset(person)
    if local.hour >= 18 or local.hour < 6 or domain in ("wellbeing", "markets"):
        nine = local.replace(hour=9, minute=0, second=0, microsecond=0)
        if nine <= local:
            nine += timedelta(days=1)
        until = nine - _offset(person)
    else:
        until = now + timedelta(hours=24)
    hours = max(1, round((until - now).total_seconds() / 3600))
    label = f"{TEXT.get(domain, 'No action on this')} until {(until + _offset(person)).strftime('%H:%M')}" + \
        (" tomorrow" if (until + _offset(person)).date() > local.date() else "")
    return {"hours": hours, "until": _iso(until), "text": label}


def pacts(person: Person) -> list[Pact]:
    return [Pact(**p) for p in person.pacts]


def _save(person: Person, ps: list[Pact]) -> None:
    person.pacts = [p.model_dump() for p in ps[-20:]]


def sweep(store: Store, person: Person, record: bool = True) -> list[Pact]:
    """Mark expired active pacts as kept. Returns the newly kept ones."""
    ps, kept, now = pacts(person), [], _now()
    for p in ps:
        if p.status == "active" and _parse(p.until) <= now:
            p.status = "kept"
            kept.append(p)
    if kept:
        _save(person, ps)
        if record:
            store.put_person(person)
            for p in kept:
                store.append(person.user_id, "pact-kept", {"pact_id": p.id, "domain": p.domain, "text": p.text})
    return kept


def active(person: Person, domain: str) -> Pact | None:
    now = _now()
    return next((p for p in reversed(pacts(person)) if p.status == "active" and p.domain == domain
                 and _parse(p.until) > now), None)


def make(store: Store, person: Person, ledger_id: str, domain: str, hours: float | None = None) -> Pact:
    s = suggest(person, domain)
    until = s["until"] if hours is None else _iso(_now() + timedelta(hours=hours))
    text = s["text"] if hours is None else f"{TEXT.get(domain, 'No action on this')} for {hours:g} hours"
    p = Pact(ledger_id=ledger_id, domain=domain, text=text, created=_iso(_now()), until=until)
    # one active pact per tissue: a new one supersedes the old (which counts as released, on the record)
    ps = pacts(person)
    for old in ps:
        if old.status == "active" and old.domain == domain:
            old.status = "released"
    _save(person, ps + [p])
    store.put_person(person)
    store.append(person.user_id, "pact", {"pact_id": p.id, "ledger_id": ledger_id, "domain": domain, "text": text,
                                          "until": until})
    return p


def close(store: Store, person: Person, pact_id: str, status: str) -> Pact | None:
    ps = pacts(person)
    hit = next((p for p in ps if p.id == pact_id and p.status == "active"), None)
    if not hit:
        return None
    hit.status = status
    _save(person, ps)
    store.put_person(person)
    store.append(person.user_id, f"pact-{status}", {"pact_id": hit.id, "domain": hit.domain, "text": hit.text})
    return hit


def hours_left(p: Pact) -> float:
    return max(0.0, (_parse(p.until) - _now()).total_seconds() / 3600)
