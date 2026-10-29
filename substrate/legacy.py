"""The Legacy Vault: letters across generations, delivered at the moment they matter.

An elder writes to an heir. Each letter is sealed (sha256 over its content) and waits for its release:

  date     on or after a calendar date                      ("on 1 Jan 2040")
  age      when the heir reaches an age (needs birth_year)  ("when Maya turns 25")
  moment   when the heir is about to repeat a pattern       ("the first time she goes all in on one thing")
  first    at the heir's first conversation with Substrate

Moments are matched against the live tissue flags, so a letter about concentration arrives in the same breath
as the STOP on a concentrated bet. Letters never arrive during a Safety Protocol event. A sealed letter can be
revoked by its author until it is delivered; delivery is on the heir's ledger. Letters travel inside the .sub
file, so the family keeps them even if Substrate the company does not survive.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, Field

from .ledger import Store, _lock, canonical, now

MOMENTS = {
    "concentration": {"concentration", "bankroll", "check-concentration", "all-in", "oversized"},
    "trading-leverage": {"leverage", "chasing"},
    "chasing": {"chasing", "loss-chasing", "repeat-pattern"},
    "fomo": {"fomo", "certainty"},
    "leverage": {"leverage", "harm"},
    "runway": {"runway", "runway-drop", "vanity-spend"},
    "impulse": {"impulse"},
    "any-stop": set(),          # any STOP verdict
}


class Release(BaseModel):
    type: str = Field("moment", pattern="^(date|age|moment|first)$")
    value: str = ""                    # ISO date | age as text | moment key


class Letter(BaseModel):
    id: str = Field(default_factory=lambda: f"LT-{uuid.uuid4().hex[:8]}")
    from_user: str
    from_name: str
    to_user: str
    relation: str = "family"
    title: str
    body: str
    release: Release = Field(default_factory=Release)
    written: str = Field(default_factory=now)
    seal: str = ""
    delivered: str | None = None
    revoked: bool = False

    def sealed(self) -> "Letter":
        self.seal = hashlib.sha256(canonical({"from": self.from_user, "to": self.to_user, "title": self.title,
                                              "body": self.body, "release": self.release.model_dump(),
                                              "written": self.written}).encode()).hexdigest()
        return self

    def intact(self) -> bool:
        return self.seal == Letter(**self.model_dump()).sealed().seal

    def public(self) -> dict:
        """What the heir sees before delivery: that a letter exists and when it opens. Never the words."""
        d = self.model_dump()
        if not self.delivered:
            d["body"] = None
        return d


def init(store: Store) -> None:
    store.db.execute("create table if not exists letters (id text primary key, to_user text not null, "
                     "from_user text not null, body text not null)")
    store.db.commit()


def write(store: Store, letter: Letter) -> Letter:
    init(store)
    letter.sealed()
    with _lock:
        store.db.execute("insert or replace into letters values (?,?,?,?)",
                         (letter.id, letter.to_user, letter.from_user, letter.model_dump_json()))
        store.db.commit()
    store.append(letter.from_user, "letter-sealed", {"letter_id": letter.id, "to": letter.to_user,
                                                     "title": letter.title, "release": letter.release.model_dump(),
                                                     "seal": letter.seal})
    return letter


def _save(store: Store, letter: Letter) -> None:
    with _lock:
        store.db.execute("update letters set body=? where id=?", (letter.model_dump_json(), letter.id))
        store.db.commit()


def to(store: Store, user_id: str) -> list[Letter]:
    init(store)
    return [Letter(**json.loads(r[0])) for r in
            store.db.execute("select body from letters where to_user=? order by rowid", (user_id,)).fetchall()]


def by(store: Store, user_id: str) -> list[Letter]:
    init(store)
    return [Letter(**json.loads(r[0])) for r in
            store.db.execute("select body from letters where from_user=? order by rowid", (user_id,)).fetchall()]


def revoke(store: Store, letter_id: str, author: str) -> bool:
    for l in by(store, author):
        if l.id == letter_id and not l.delivered and not l.revoked:
            l.revoked = True
            _save(store, l)
            store.append(author, "letter-revoked", {"letter_id": l.id, "to": l.to_user})
            return True
    return False


def _due(l: Letter, heir_profile: dict, flags: set[str], severity: int, first: bool) -> bool:
    if l.delivered or l.revoked:
        return False
    r = l.release
    if r.type == "first":
        return first
    if r.type == "date":
        return bool(r.value) and r.value <= datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if r.type == "age":
        by_ = heir_profile.get("birth_year")
        try:
            return bool(by_) and datetime.now(timezone.utc).year - int(by_) >= int(r.value)
        except ValueError:
            return False
    if r.type == "moment":
        if r.value == "any-stop":
            return severity == 2
        return severity >= 1 and bool(MOMENTS.get(r.value, {r.value}) & flags)
    return False


def deliver_due(store: Store, user_id: str, heir_profile: dict, flags: list[str], severity: int,
                first: bool, record: bool = True) -> Letter | None:
    """At most one letter per answer: the one written for this moment."""
    for l in to(store, user_id):
        if _due(l, heir_profile or {}, set(flags), severity, first) and l.intact():
            if record:
                l.delivered = now()
                _save(store, l)
                store.append(user_id, "letter-delivered", {"letter_id": l.id, "from": l.from_user,
                                                          "title": l.title, "seal": l.seal})
            return l
    return None


def render(l: Letter) -> str:
    who = {"father": "your father", "mother": "your mother", "grandfather": "your grandfather",
           "grandmother": "your grandmother"}.get(l.relation.lower(), l.from_name)
    year = l.written[:4]
    body = "\n".join("> " + line if line else ">" for line in l.body.strip().splitlines())
    return f"**A letter from {who}, sealed in {year}, for this moment:** _{l.title}_\n\n{body}\n>\n> - {l.from_name}"


def export_for(store: Store, user_id: str) -> list[dict]:
    """Letters authored by this user, for the .sub file (sealed bodies included: the family owns them)."""
    return [l.model_dump() for l in by(store, user_id) if not l.revoked]


def import_from_sub(store: Store, doc: dict, heir_id: str) -> int:
    have = {l.id for l in to(store, heir_id)}
    n = 0
    for d in doc.get("letters") or []:
        l = Letter(**d)
        if l.to_user == heir_id and l.id not in have and l.intact():
            init(store)
            with _lock:
                store.db.execute("insert or replace into letters values (?,?,?,?)",
                                 (l.id, l.to_user, l.from_user, l.model_dump_json()))
                store.db.commit()
            n += 1
    return n
