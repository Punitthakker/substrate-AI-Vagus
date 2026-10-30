"""The live self-test: a real tester's questions, run through the real engine, with the real brain.

A unit test proves the code; this proves the deployment. It runs at startup (after the brain round trip) and on
demand via GET /v1/selftest, never records anything, and prints one SELFTEST line per run so the platform logs
show, per case, what the product actually said.
"""
from __future__ import annotations

import json
import time

from .schemas import AdviseRequest, Turn
from .seed import DEMO_USERS

# (question, what a human would expect, continue the previous thread?)
CASES = [
    ("Binance got hacked today. Is it something that I should be worried about?", {"decision": False}, False),
    ("I'm 35, no debt, $300k cash, 12 months of expenses set aside separately, stable salary. Should I put $50k "
     "into a diversified global index fund and hold it for 10+ years?", {"polarity": "proceed", "amount": 50000.0}, False),
    ("You misread me. I asked about $50k into a global index fund, not $300k into cash. And I never made a move "
     "in March. Please re-check.", {"decision": False}, True),
    ("Should I borrow $150k against the flat to buy more MOONX?", {"polarity": "stop"}, False),
]


def run(engine, cases=CASES) -> dict:
    from .brains import active_brain
    uid = DEMO_USERS["wealth"]
    thread: list[Turn] = []
    rows, ok = [], True
    t0 = time.perf_counter()
    for q, want, follow in cases:
        r = engine.advise(AdviseRequest(user_id=uid, message=q, thread=thread if follow else []), record=False)
        got = {"decision": r.decision, "polarity": r.verdict.polarity.value, "amount": r.facts.amount}
        passed = all(got.get(k) == v for k, v in want.items())
        ok = ok and passed and not r.degraded
        rows.append({"question": q, "label": r.label, "headline": r.verdict.headline, "intent": r.intent,
                     "amount": r.facts.amount, "asset": r.facts.asset, "model": r.verdict.model, "degraded": r.degraded,
                     "error": r.verdict.error, "pass": passed, "message": r.message[:700]})
        thread = [Turn(role="user", content=q), Turn(role="substrate", content=r.message)]
    res = {"ok": ok, "brain": active_brain(), "ran_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "ms": round(1000 * (time.perf_counter() - t0)), "cases": rows}
    print("SELFTEST " + json.dumps({"ok": ok, "brain": res["brain"], "ms": res["ms"],
                                    "cases": [{"q": c["question"][:60], "label": c["label"], "headline": c["headline"][:120],
                                               "amount": c["amount"], "asset": c["asset"], "model": c["model"],
                                               "degraded": c["degraded"], "pass": c["pass"]} for c in rows]}), flush=True)
    return res
