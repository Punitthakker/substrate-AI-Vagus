"""Inheritance: a genome passed down.

An heir receives a verified .sub. What crosses depends on the elder's consented scope:

  values         the elder's values
  values+ledger  + the lessons they paid for and the patterns they were prone to
  full           + their decision style, as context

Money, positions, raw messages and safety events never cross. The elder (or their estate) can revoke at any
time: inheritance is a revocable will, which is why Inheritance.revocable is fixed to True.

At advice time, when the heir's decision shows a pattern the elder was prone to, Substrate cites the elder's
lesson. That is the product: the next generation doesn't have to pay for the same lesson twice.
"""
from __future__ import annotations

from .export import verify_sub
from .ledger import Store, now
from .schemas import Ancestor, Person

# patterns that mean the same mistake across tissues
KIN = {"concentration": {"concentration", "bankroll", "check-concentration", "all-in", "oversized"},
       "loss-chasing": {"loss-chasing", "chasing", "repeat-pattern"},
       "chasing": {"chasing", "loss-chasing"},
       "fomo": {"fomo", "certainty"},
       "leverage": {"leverage", "harm"},
       "valuation": {"valuation"},
       "over-hiring": {"runway", "runway-drop"},
       "parlay-math": {"parlay-math", "combo-multiplier"}}


class InheritanceError(Exception):
    pass


def inherit(store: Store, doc: dict, heir_id: str, relation: str = "family") -> Ancestor:
    v = verify_sub(doc)
    if not v["valid"]:
        raise InheritanceError("The .sub file failed verification (checksum or ledger chain).")
    g = doc["genome"]
    consent = doc.get("consent") or g.get("consent") or {}
    inh = consent.get("inheritance") or {}
    if heir_id not in (inh.get("heirs") or []):
        raise InheritanceError(f"'{heir_id}' is not a named heir of this genome.")
    elder = store.get_person(g["user_id"])
    if elder and heir_id not in elder.consent.inheritance.heirs:
        raise InheritanceError("The elder has revoked this inheritance.")
    heir = store.get_person(heir_id)
    if not heir:
        raise InheritanceError(f"No genome '{heir_id}'. Create the heir first.")
    scope = inh.get("scope", "values")
    first = (g.get("name") or "Your elder").split()[0]
    a = Ancestor(from_user=g["user_id"], name=first, relation=relation, vintage=g.get("vintage", ""), scope=scope,
                 values=list(g.get("values") or []), checksum=doc.get("checksum", ""), received=now())
    if scope in ("values+ledger", "full"):
        a.lessons = list(g.get("lessons") or [])[-8:]
        a.patterns = [b["type"] for b in g.get("biases") or []]
    same = next((x for x in heir.ancestry if x.from_user == a.from_user and x.scope == a.scope
                 and x.values == a.values and x.lessons == a.lessons and x.patterns == a.patterns), None)
    if same:
        return same   # already received this exact genome
    heir.ancestry = [x for x in heir.ancestry if x.from_user != a.from_user] + [a]
    for val in a.values:
        if val not in heir.values:
            heir.values.append(val)
    store.put_person(heir)
    from .legacy import import_from_sub
    import_from_sub(store, doc, heir_id)
    store.append(heir_id, "inheritance", {"from_user": a.from_user, "relation": relation, "scope": scope,
                                          "checksum": a.checksum, "lessons": len(a.lessons)})
    return a


def revoke(store: Store, heir_id: str, from_user: str) -> bool:
    heir = store.get_person(heir_id)
    if not heir:
        return False
    before = len(heir.ancestry)
    heir.ancestry = [x for x in heir.ancestry if x.from_user != from_user]
    store.put_person(heir)
    if len(heir.ancestry) != before:
        store.append(heir_id, "inheritance-revoked", {"from_user": from_user})
        return True
    return False


def ancestral_lesson(person: Person, flags: list[str]) -> tuple[Ancestor, str] | None:
    """The elder's lesson that matches the pattern in front of us right now, if there is one."""
    live = set(flags)
    for a in reversed(person.ancestry):
        hit = [p for p in a.patterns if KIN.get(p, {p}) & live]
        if not hit:
            continue
        for l in reversed(a.lessons):
            if "ignored" in l and ("lost" in l or "marked down" in l or "fell" in l):
                return a, l
        if a.lessons:
            return a, a.lessons[-1]
    return None


def phrase(a: Ancestor, lesson: str) -> str:
    when, _, what = lesson.partition(": ")
    year = when[:4] if when[:4].isdigit() else "years ago"
    who = {"father": "Your father", "mother": "Your mother", "grandfather": "Your grandfather",
           "grandmother": "Your grandmother"}.get(a.relation.lower(), f"{a.name}, your {a.relation},")
    pron = {"father": "he", "grandfather": "he", "mother": "she", "grandmother": "she"}.get(a.relation.lower(), "they")
    return f"{who} learned this in {year}: {pron} {what}"
