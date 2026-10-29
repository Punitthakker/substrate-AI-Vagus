"""Demo genomes for the console: one fictional human per tissue, each with a real pattern on record."""
from __future__ import annotations

from .ledger import Store
from .schemas import Bias, Consent, Goal, Inheritance, Person, Position, RiskProfile

DEMO_USER = "demo-kapoor"
DEMO_HEIRS = {"demo-kapoor": ("demo-maya", "father")}
DEMO_USERS = {"wealth": "demo-kapoor", "venture": "demo-haddad", "founder": "demo-mehra", "wellbeing": "demo-sara", "markets": "demo-rahman"}


def _people() -> dict[str, Person]:
    return {
        "demo-kapoor": Person(
            user_id="demo-kapoor", name="Aarav Kapoor", domain="wealth", vintage="2026-10-29",
            consent=Consent(candor_level=4, allow_training=True, inheritance=Inheritance(heirs=["demo-maya"], scope="values+ledger")),
            temperament="mentor", values=["family security", "children's education", "long-horizon compounding"],
            risk_profile=RiskProfile(stated="moderate", observed="aggressive"), liquid_net_worth=1_200_000,
            positions=[Position(asset="Global Equity Index Fund", value=480_000, kind="fund"),
                       Position(asset="MOONX", value=340_000, kind="token"),
                       Position(asset="Dubai Property Fund", value=250_000, kind="fund"),
                       Position(asset="Cash", value=130_000, kind="cash")],
            biases=[Bias(type="loss-chasing", evidence=["L-seed-0314"], last_seen="2026-03-14"),
                    Bias(type="concentration", evidence=["L-seed-0314"], last_seen="2026-03-14")],
            goals=[Goal(name="Children's education fund by 2032", priority=1),
                   Goal(name="Financial independence by 2040", priority=2)],
            decision_style="Fast. Reverses under stress. Most decisions made after 10pm.",
            adherence={"5": {"followed": 0, "ignored": 1}, "4": {"followed": 1, "ignored": 0}},
            lessons=["2026-04-14: ignored a STOP (No. Do not put $150k into MOONX.) and lost $46k.",
                     "2026-10-01: followed a PROCEED into the index fund. +$4.8k and compounding."]),
        "demo-haddad": Person(
            user_id="demo-haddad", name="Layla Haddad", domain="venture", vintage="2026-10-29",
            consent=Consent(candor_level=4, allow_training=True), temperament="surgeon",
            values=["thesis discipline", "founder quality", "LP trust"],
            risk_profile=RiskProfile(stated="moderate", observed="aggressive"),
            profile={"fund_name": "Falcon Seed Fund I", "fund_size": 80_000_000, "deployed": 31_000_000,
                     "typical_check": 1_500_000, "reserves_ratio": 0.5, "thesis": ["fintech", "b2b", "saas", "mena"]},
            biases=[Bias(type="fomo", evidence=["L-seed-vc01"], last_seen="2026-02-20"),
                    Bias(type="valuation", evidence=["L-seed-vc01"], last_seen="2026-02-20")],
            goals=[Goal(name="3x net DPI on Fund I", priority=1), Goal(name="Raise Fund II in 2027", priority=2)],
            decision_style="Conviction-led. Moves fastest when a tier-1 lead is in.",
            adherence={"5": {"followed": 0, "ignored": 1}},
            lessons=["2026-08-30: ignored a PASS (Pass on the hot AI round at 90x ARR) and marked down $1.2M."]),
        "demo-mehra": Person(
            user_id="demo-mehra", name="Rohan Mehra", domain="founder", vintage="2026-10-29",
            consent=Consent(candor_level=4, allow_training=True), temperament="father",
            values=["customer obsession", "default alive", "team first"],
            profile={"company": "Ledgerly (B2B SaaS)", "cash_in_bank": 2_400_000, "monthly_burn": 210_000,
                     "mrr": 85_000, "mrr_growth": 0.06},
            biases=[Bias(type="over-hiring", evidence=["L-seed-fd01"], last_seen="2026-05-02")],
            goals=[Goal(name="Series A by Q3 2027", priority=1), Goal(name="Default alive by end of 2027", priority=2)],
            decision_style="Optimistic. Hires ahead of revenue.",
            adherence={"4": {"followed": 1, "ignored": 1}},
            lessons=["2026-05-02: ignored a NOT YET on 6 sales hires. Runway fell from 15 to 11 months."]),
        "demo-sara": Person(
            user_id="demo-sara", name="Sara Nasser", domain="wellbeing", vintage="2026-10-29",
            consent=Consent(candor_level=2, allow_training=True), temperament="comfort",
            values=["family", "health", "being kind to herself"],
            profile={"support_contacts": ["your sister Mira"], "region": "AE"},
            biases=[Bias(type="late-night rumination", evidence=[], last_seen="2026-10-20"),
                    Bias(type="people-pleasing", evidence=[], last_seen="2026-10-12")],
            goals=[Goal(name="Sleep before midnight", priority=1), Goal(name="Set boundaries at work", priority=2)],
            decision_style="Spirals at night, clearer in the morning.",
            lessons=["2026-10-12: waited until morning before replying to her manager. Glad she did."]),
        "demo-rahman": Person(
            user_id="demo-rahman", name="Zayd Rahman", domain="markets", vintage="2026-10-29",
            consent=Consent(candor_level=4, allow_training=True), temperament="surgeon",
            values=["discipline", "data over gut", "never bet the rent"],
            risk_profile=RiskProfile(stated="moderate", observed="aggressive"),
            profile={"bankroll": 25_000, "max_bet_fraction": 0.02, "fee": 0.02,
                     "venues": ["Polymarket", "Kalshi", "sportsbook"]},
            biases=[Bias(type="chasing", evidence=["L-seed-mk01"], last_seen="2026-09-14"),
                    Bias(type="parlay-math", evidence=["L-seed-mk01"], last_seen="2026-09-14")],
            goals=[Goal(name="Keep betting a hobby, under 2% a position", priority=1),
                   Goal(name="Positive closing-line value over 2026", priority=2)],
            decision_style="Sharp when calm. Chases after a losing weekend, mostly after midnight.",
            adherence={"5": {"followed": 0, "ignored": 1}, "3": {"followed": 1, "ignored": 0}},
            lessons=["2026-09-15: ignored a NO BET (Don't chase it.) on a 7-leg parlay and lost $6k.",
                     "2026-10-06: followed a SIZE DOWN on a Polymarket position. Lost $150 instead of $1.5k."]),
        "demo-maya": Person(
            user_id="demo-maya", name="Maya Kapoor", domain="wealth", vintage="2050-01-01",
            consent=Consent(candor_level=4, allow_training=True), temperament="mentor",
            values=["curiosity", "independence"], risk_profile=RiskProfile(stated="moderate"),
            liquid_net_worth=300_000,
            positions=[Position(asset="Global Equity Index Fund", value=220_000, kind="fund"),
                       Position(asset="Cash", value=80_000, kind="cash")],
            goals=[Goal(name="Buy a first home by 2055", priority=1)],
            decision_style="Inherited her father's instinct for big swings."),
    }


def seed(store: Store, reset: bool = False, only: str | None = None) -> None:
    for uid, person in _people().items():
        if only and uid != only:
            continue
        if reset:
            store.delete_person(uid)
        if store.get_person(uid):
            continue
        store.put_person(person)
        _history(store, uid)
    # the inheritance demo: Aarav's genome passed to his daughter Maya (2050)
    from .export import export_sub
    from .inherit import inherit
    for elder, (heir, relation) in DEMO_HEIRS.items():
        e, h = store.get_person(elder), store.get_person(heir)
        if e and h and not h.ancestry:
            if heir not in e.consent.inheritance.heirs:   # older stored genome: name the heir, as the demo intends
                e.consent.inheritance.heirs.append(heir)
                store.put_person(e)
            try:
                inherit(store, export_sub(store, elder), heir, relation)
            except Exception:   # a demo nicety must never stop the engine from starting
                pass


def _history(store: Store, uid: str) -> None:
    A = store.append
    if uid == "demo-kapoor":
        adv = A(uid, "advice", {"user_message": "Thinking of adding $150k to MOONX before the listing. Can't miss this.",
                                "domain": "wealth", "polarity": "stop", "label": "STOP", "headline": "No. Do not put $150k into MOONX.",
                                "reasons": ["This would put 25% of your liquid net worth in one token."], "model": "rule-core",
                                "floor_applied": False, "state": "euphoric", "firmness": 5, "temperament": "mentor",
                                "stakes": "high", "flags": ["concentration", "fomo"]}, event_id="L-seed-0314", ts="2026-03-14T22:41:07Z")
        A(uid, "action", {"ledger_id": adv["id"], "taken": "ignored"}, ts="2026-03-15T09:02:00Z")
        A(uid, "outcome", {"ledger_id": adv["id"], "type": "pnl", "value_delta": -46_000, "horizon": "30d",
                           "note": "Token fell 31% after listing."}, ts="2026-04-14T09:00:00Z")
        adv2 = A(uid, "advice", {"user_message": "Should I move $60k from cash into the index fund?", "domain": "wealth",
                                 "polarity": "proceed", "label": "PROCEED", "headline": "Yes, this fits your plan.",
                                 "reasons": ["At 5% of liquid net worth, the size is within your limits."], "model": "rule-core",
                                 "floor_applied": False, "state": "calm", "firmness": 4, "temperament": "mentor",
                                 "stakes": "medium", "flags": []}, event_id="L-seed-0702", ts="2026-07-02T10:15:00Z")
        A(uid, "action", {"ledger_id": adv2["id"], "taken": "followed"}, ts="2026-07-02T11:00:00Z")
        A(uid, "outcome", {"ledger_id": adv2["id"], "type": "pnl", "value_delta": 4_800, "horizon": "90d",
                           "note": "Steady compounding."}, ts="2026-10-01T09:00:00Z")
    elif uid == "demo-haddad":
        adv = A(uid, "advice", {"user_message": "Hot AI round, $3M at 90x ARR, closing Friday. We're in.", "domain": "venture",
                                "polarity": "stop", "label": "PASS", "headline": "Pass on the hot AI round at 90x ARR.",
                                "reasons": ["90x ARR requires a top-decile outcome just to return the check."], "model": "rule-core",
                                "floor_applied": False, "state": "euphoric", "firmness": 5, "temperament": "surgeon",
                                "stakes": "high", "flags": ["valuation", "fomo"]}, event_id="L-seed-vc01", ts="2026-02-20T18:05:00Z")
        A(uid, "action", {"ledger_id": adv["id"], "taken": "ignored"}, ts="2026-02-21T08:30:00Z")
        A(uid, "outcome", {"ledger_id": adv["id"], "type": "pnl", "value_delta": -1_200_000, "horizon": "6m",
                           "note": "Down round, 40% markdown."}, ts="2026-08-30T09:00:00Z")
    elif uid == "demo-mehra":
        adv = A(uid, "advice", {"user_message": "Hiring 6 sales reps at $9k a month each.", "domain": "founder",
                                "polarity": "caution", "label": "NOT YET", "headline": "Not yet. Find a version of this the runway can carry.",
                                "reasons": ["Runway goes from 15 to 11 months."], "model": "rule-core", "floor_applied": False,
                                "state": "decision-ready", "firmness": 4, "temperament": "father", "stakes": "high",
                                "flags": ["runway-drop"]}, event_id="L-seed-fd01", ts="2026-05-02T11:20:00Z")
        A(uid, "action", {"ledger_id": adv["id"], "taken": "ignored"}, ts="2026-05-03T09:00:00Z")
    elif uid == "demo-sara":
        adv = A(uid, "advice", {"user_message": "I'm going to reply to my manager right now and tell her exactly what I think.",
                                "domain": "wellbeing", "polarity": "stop", "label": "NOT TONIGHT",
                                "headline": "Not tonight. Please give yourself until the morning.",
                                "reasons": ["Write it out tonight. If you still want to send it in the morning, send it then."],
                                "model": "rule-core", "floor_applied": False, "state": "stressed", "firmness": 2,
                                "temperament": "comfort", "stakes": "medium", "flags": ["impulse"]},
                event_id="L-seed-wb01", ts="2026-10-11T23:48:00Z")
        A(uid, "action", {"ledger_id": adv["id"], "taken": "followed"}, ts="2026-10-12T08:10:00Z")
    elif uid == "demo-rahman":
        adv = A(uid, "advice", {"user_message": "Down $4k this weekend. 7-leg parlay, $6k, need to win it back tonight.",
                                "domain": "markets", "polarity": "stop", "label": "NO BET", "headline": "No bet. Don't chase it.",
                                "reasons": ["7 legs at 70% each hit together 8.2% of the time, not 70%."], "model": "rule-core",
                                "floor_applied": False, "state": "stressed", "firmness": 5, "temperament": "surgeon",
                                "stakes": "high", "flags": ["chasing", "parlay-math", "bankroll"]},
                event_id="L-seed-mk01", ts="2026-09-14T01:12:00Z")
        A(uid, "action", {"ledger_id": adv["id"], "taken": "ignored"}, ts="2026-09-14T01:20:00Z")
        A(uid, "outcome", {"ledger_id": adv["id"], "type": "pnl", "value_delta": -6_000, "horizon": "1d",
                           "note": "Parlay lost on leg 5."}, ts="2026-09-15T09:00:00Z")
        adv2 = A(uid, "advice", {"user_message": "Polymarket YES at 55c, I think 60%. $1,500 on it.", "domain": "markets",
                                 "polarity": "caution", "label": "SIZE DOWN", "headline": "Size down. The idea may be fine, the size isn't.",
                                 "reasons": ["A quarter-Kelly stake on your own numbers is about $150."], "model": "rule-core",
                                 "floor_applied": False, "state": "calm", "firmness": 3, "temperament": "surgeon",
                                 "stakes": "medium", "flags": ["oversized"]}, event_id="L-seed-mk02", ts="2026-10-05T19:00:00Z")
        A(uid, "action", {"ledger_id": adv2["id"], "taken": "followed"}, ts="2026-10-05T19:05:00Z")
        A(uid, "outcome", {"ledger_id": adv2["id"], "type": "pnl", "value_delta": -150, "horizon": "1d",
                           "note": "Resolved NO. Small loss, as sized."}, ts="2026-10-06T09:00:00Z")
