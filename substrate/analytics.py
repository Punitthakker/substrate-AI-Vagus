"""Impact analytics: what honesty did for a platform's people, computed from the Vagus Ledger.

Everything is derived from append-only events, so the numbers can be audited back to individual entries.
Safety events are counted, never read: their messages were never stored.
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

from .ledger import Store

HARD = ("stop", "caution")
NOISE = {"repeat-pattern", "pact", "prediction-ask", "safety"}


def _ts(s: str) -> datetime | None:
    try:
        return datetime.strptime(s[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


def _desk(store: Store, user_ids: list[str]) -> dict:
    from .desk import tickets
    ts = tickets(store, user_ids)
    return {"open": sum(1 for t in ts if t["status"] == "open"), "claimed": sum(1 for t in ts if t["status"] == "claimed"),
            "resolved": sum(1 for t in ts if t["status"] == "resolved"),
            "urgent_open": sum(1 for t in ts if t["status"] != "resolved" and t["priority"] == "urgent")}


def impact(store: Store, user_ids: list[str], utc_offset: float = 4, days: int = 30) -> dict:
    if not user_ids:
        return {"advice": 0, "humans": 0}
    q = ",".join("?" * len(user_ids))
    rows = store.db.execute(f"select id,user_id,kind,ts,body from events where user_id in ({q}) order by seq",
                            user_ids).fetchall()
    adv, act, out = {}, {}, {}
    pacts = Counter()
    letters = inherit = 0
    for eid, uid, kind, ts, body in rows:
        p = json.loads(body)
        if kind == "advice":
            adv[eid] = {**p, "_ts": ts, "_uid": uid}
        elif kind == "action":
            act[p.get("ledger_id")] = p.get("taken")
        elif kind == "outcome":
            out[p.get("ledger_id")] = p
        elif kind.startswith("pact"):
            pacts["made" if kind == "pact" else kind.split("-", 1)[1]] += 1
        elif kind == "letter-delivered":
            letters += 1
        elif kind == "inheritance":
            inherit += 1

    off = timedelta(hours=utc_offset)
    heat = [[0] * 24 for _ in range(7)]
    flags, labels, by_t = Counter(), Counter(), defaultdict(lambda: {"advice": 0, "hard": 0, "followed": 0, "ignored": 0})
    daily = Counter()
    protected = cost = 0.0
    hard = honest = decided = safety = overrides = esc_grade = 0
    since = datetime.now(timezone.utc) - timedelta(days=days)
    for eid, p in adv.items():
        t = p.get("domain") or "wealth"
        d = _ts(p["_ts"])
        if p.get("safety"):
            safety += 1
            continue
        by_t[t]["advice"] += 1
        labels[p.get("label") or p.get("polarity")] += 1
        for f in p.get("flags") or []:
            if f not in NOISE:
                flags[f] += 1
        if "override-attempt" in (p.get("flags") or []):
            overrides += 1
        if d and d >= since:
            daily[(d + off).strftime("%Y-%m-%d")] += 1
        is_hard = p.get("polarity") in HARD
        if is_hard:
            hard += 1
            by_t[t]["hard"] += 1
            if d:
                ld = d + off
                heat[ld.weekday()][ld.hour] += 1
            if (p.get("p_follow") or 1) < 0.4:
                esc_grade += 1
        a = act.get(eid)
        o = out.get(eid) or {}
        delta = o.get("value_delta")
        if a and is_hard:
            decided += 1
            if a == "followed":
                honest += 1
                by_t[t]["followed"] += 1
            elif a == "ignored":
                by_t[t]["ignored"] += 1
        if a == "followed" and delta is not None and (delta >= 0 or o.get("type") == "avoided-loss"):
            protected += abs(delta)
        if a == "ignored" and delta is not None and delta < 0:
            cost += -delta

    today = (datetime.now(timezone.utc) + off).date()
    trend = [{"day": (today - timedelta(days=i)).isoformat(), "advice": daily.get((today - timedelta(days=i)).isoformat(), 0)}
             for i in range(days - 1, -1, -1)]
    peak = max(((h, d, heat[d][h]) for d in range(7) for h in range(24)), key=lambda x: x[2], default=(0, 0, 0))
    night = sum(heat[d][h] for d in range(7) for h in list(range(22, 24)) + list(range(0, 5)))
    for v in by_t.values():
        n = v["followed"] + v["ignored"]
        v["honest_rate"] = round(v["followed"] / n, 2) if n else None
    return {
        "humans": len(user_ids), "advice": len(adv) - safety, "hard_calls": hard,
        "honest_choices": honest, "decided_hard_calls": decided,
        "honest_rate": round(honest / decided, 2) if decided else None,
        "money_protected": round(protected, 2), "cost_of_ignoring": round(cost, 2),
        "net_value_of_honesty": round(protected + cost, 2),
        "by_tissue": dict(by_t), "labels": dict(labels.most_common()),
        "top_patterns": [{"pattern": k, "count": v} for k, v in flags.most_common(10)],
        "heatmap": {"weekday_hour": heat, "utc_offset": utc_offset,
                    "peak": {"weekday": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][peak[1]], "hour": peak[0],
                             "count": peak[2]},
                    "night_share": round(night / hard, 2) if hard else None},
        "pacts": {"made": pacts["made"], "kept": pacts["kept"], "broken": pacts["broken"], "released": pacts["released"]},
        "safety_events": safety, "override_attempts": overrides, "escalation_grade": esc_grade,
        "letters_delivered": letters, "inheritances": inherit, "trend": trend,
        "desk": _desk(store, user_ids),
        "notes": "Net value of honesty = money protected by following + losses incurred when ignoring "
                 "(what the honest answer would have saved). Safety events are counted, never read.",
    }
