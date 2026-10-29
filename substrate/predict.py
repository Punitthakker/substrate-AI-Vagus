"""The predictive layer: will this human follow the advice, what is the downside, who should step in.

Transparent models only: every prediction ships with its drivers, so a bank's model-risk team can
read exactly why the number moved. Learned from the Vagus Ledger, improved by every outcome.
"""
from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

from .schemas import Facts, Forecast, Person, Prediction, State, Verdict


def _sig(x: float) -> float:
    return 1 / (1 + math.exp(-x))


def p_follow(person: Person, state: State, firmness: int, facts: Facts, now: datetime | None = None) -> tuple[float, list[str]]:
    """Probability the human acts on this advice. Bayesian prior from their own ledger + live context."""
    followed = sum(v.get("followed", 0) for v in person.adherence.values())
    ignored = sum(v.get("ignored", 0) for v in person.adherence.values())
    prior = (1 + followed) / (2 + followed + ignored)           # Beta(1,1) smoothed follow rate
    drivers = [f"Personal follow rate {followed}/{followed + ignored} on record" if followed + ignored else "No history yet: neutral prior"]
    logit = math.log(prior / (1 - prior))
    level = person.adherence.get(str(firmness), {})
    if level.get("followed", 0) + level.get("ignored", 0):
        lf = (1 + level.get("followed", 0)) / (2 + level.get("followed", 0) + level.get("ignored", 0))
        logit += 0.8 * (math.log(lf / (1 - lf)))
        drivers.append(f"At tone {firmness} they followed {level.get('followed', 0)} of {level.get('followed', 0) + level.get('ignored', 0)}")
    adj = {State.euphoric: (-0.9, "Euphoric state lowers follow-through"),
           State.defensive: (-1.1, "Pushing back: least likely to follow"),
           State.stressed: (-0.3, "Stress lowers follow-through"),
           State.calm: (0.3, "Calm state raises follow-through")}
    if state in adj:
        logit += adj[state][0]
        drivers.append(adj[state][1])
    if "repeat-pattern" in facts.flags:
        logit -= 0.5
        drivers.append("Repeating a pattern they ignored before")
    style = (person.decision_style or "").lower()
    now = now or datetime.now(timezone(timedelta(hours=4)))
    if ("10pm" in style or "night" in style) and (now.hour >= 22 or now.hour < 4):
        logit -= 0.4
        drivers.append("Late-night decision, their riskiest window")
    if firmness >= 5 and facts.floor.severity >= 1:
        logit += 0.25
        drivers.append("Maximum tone historically lands harder")
    return round(_sig(logit), 2), drivers


def predict(person: Person, state: State, firmness: int, facts: Facts, verdict: Verdict,
            forecasts: list[Forecast]) -> Prediction:
    p, drivers = p_follow(person, state, firmness, facts)
    escalate = None
    if facts.safety:
        escalate = "Safety protocol active: route to a trained human now."
    elif verdict.polarity.severity == 2 and p < 0.4:
        escalate = "Low chance this advice is followed on a high-stakes call: escalate to a human advisor today."
    elif facts.domain == "wellbeing" and (facts.metrics.get("persistent") or facts.metrics.get("distress_turns", 0) >= 3):
        escalate = "Sustained distress: suggest professional support (doctor, therapist or trusted person)."
    return Prediction(p_follow=p, drivers=drivers, forecasts=forecasts, escalate=escalate)


def insights(person: Person, history: list[dict]) -> dict:
    """Candor ROI: what honesty was worth to this human, from the ledger."""
    cost_ignoring = sum(-h["value_delta"] for h in history if h.get("action") == "ignored"
                        and (h.get("value_delta") or 0) < 0)
    gained_following = sum(h["value_delta"] for h in history if h.get("action") == "followed"
                           and (h.get("value_delta") or 0) > 0)
    decided = [h for h in history if h.get("action") in ("followed", "ignored")]
    follow_rate = (sum(1 for h in decided if h["action"] == "followed") / len(decided)) if decided else None
    best = None
    for lvl, s in person.adherence.items():
        n = s.get("followed", 0) + s.get("ignored", 0)
        if n:
            rate = s.get("followed", 0) / n
            if best is None or rate > best[1]:
                best = (int(lvl), rate)
    return {"advised": len(history), "decided": len(decided), "follow_rate": follow_rate,
            "cost_of_ignoring": cost_ignoring, "gained_by_following": gained_following,
            "best_tone": best[0] if best else None,
            "lessons": person.lessons[-3:]}
