"""Demo genome for the investor console: a fictional Dubai private-banking client with a real pattern."""
from __future__ import annotations

from .ledger import Store
from .schemas import Bias, Consent, Goal, Inheritance, Person, Position, RiskProfile

DEMO_USER = "demo-kapoor"


def demo_person() -> Person:
    return Person(
        user_id=DEMO_USER,
        name="Aarav Kapoor",
        vintage="2026-10-29",
        consent=Consent(candor_level=4, inheritance=Inheritance(heirs=["kapoor-heir-01"], scope="values+ledger")),
        temperament="mentor",
        values=["family security", "children's education", "long-horizon compounding"],
        risk_profile=RiskProfile(stated="moderate", observed="aggressive"),
        liquid_net_worth=1_200_000,
        currency="USD",
        positions=[
            Position(asset="Global Equity Index Fund", value=480_000, kind="fund"),
            Position(asset="MOONX", value=340_000, kind="token"),
            Position(asset="Dubai Property Fund", value=250_000, kind="fund"),
            Position(asset="Cash", value=130_000, kind="cash"),
        ],
        biases=[Bias(type="loss-chasing", evidence=["L-seed-0314"], last_seen="2026-03-14"),
                Bias(type="concentration", evidence=["L-seed-0314"], last_seen="2026-03-14")],
        goals=[Goal(name="Children's education fund by 2032", priority=1), Goal(name="Financial independence by 2040", priority=2)],
        decision_style="Fast. Reverses under stress. Most decisions made after 10pm.",
        adherence={"5": {"followed": 0, "ignored": 1}, "4": {"followed": 1, "ignored": 0}},
        lessons=["2026-04-14: ignored a STOP (No. Do not put $150k into MOONX.) and lost $46k.",
                 "2026-10-01: followed a PROCEED into the index fund. +$4.8k and compounding."],
    )


def seed(store: Store, reset: bool = False) -> None:
    if reset:
        store.delete_person(DEMO_USER)
    if store.get_person(DEMO_USER):
        return
    store.put_person(demo_person())
    # the pattern: told no in March, went ahead, lost money
    adv = store.append(DEMO_USER, "advice", {
        "user_message": "Thinking of adding $150k to MOONX before the listing. Can't miss this.",
        "polarity": "stop", "headline": "No. Do not put $150k into MOONX.",
        "reasons": ["This would put 25% of your liquid net worth in one token."],
        "model": "rule-core", "floor_applied": False, "state": "euphoric", "firmness": 5,
        "temperament": "mentor", "stakes": "high", "flags": ["concentration", "fomo"]},
        event_id="L-seed-0314", ts="2026-03-14T22:41:07Z")
    store.append(DEMO_USER, "action", {"ledger_id": adv["id"], "taken": "ignored"}, ts="2026-03-15T09:02:00Z")
    store.append(DEMO_USER, "outcome", {"ledger_id": adv["id"], "type": "pnl", "value_delta": -46_000,
                                        "horizon": "30d", "note": "Token fell 31% after listing."},
                 ts="2026-04-14T09:00:00Z")
    # and one he followed
    adv2 = store.append(DEMO_USER, "advice", {
        "user_message": "Should I move $60k from cash into the index fund?",
        "polarity": "proceed", "headline": "Yes, this fits your plan.",
        "reasons": ["At 5% of liquid net worth, the size is within your limits."],
        "model": "rule-core", "floor_applied": False, "state": "calm", "firmness": 4,
        "temperament": "mentor", "stakes": "medium", "flags": []},
        event_id="L-seed-0702", ts="2026-07-02T10:15:00Z")
    store.append(DEMO_USER, "action", {"ledger_id": adv2["id"], "taken": "followed"}, ts="2026-07-02T11:00:00Z")
    store.append(DEMO_USER, "outcome", {"ledger_id": adv2["id"], "type": "pnl", "value_delta": 4_800,
                                        "horizon": "90d", "note": "Steady compounding."},
                 ts="2026-10-01T09:00:00Z")
