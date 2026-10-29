"""Progress: the game layer. Honesty you can feel improving.

Everything is computed from the Vagus Ledger, so it can't be faked by tapping buttons:

  XP          +10 per advice, +25 per closed loop, +50 for following a STOP/CAUTION, bonus for money protected
  streak      consecutive decided calls where the human chose the honest path
  discipline  0-100, recency-weighted follow rate on the hard calls
  levels      Spark -> Pulse -> Rhythm -> Vagal Tone -> Steady Heart -> Lionheart
  badges      earned moments, each tied to a real behaviour, never to engagement for its own sake

Design rule: the game rewards closing the loop and choosing well, never using the product more.
There is no daily-login reward and no badge for volume. In the Markets and Wellbeing tissues, a session that
ends early is rewarded, not penalised.
"""
from __future__ import annotations

from .ledger import Store

LEVELS = [(0, "Spark"), (100, "Pulse"), (250, "Rhythm"), (500, "Vagal Tone"), (1000, "Steady Heart"), (2000, "Lionheart")]

BADGES = {
    "first-truth": ("First truth", "Heard your first honest answer"),
    "loop-closer": ("Loop closer", "Told Substrate what you actually did"),
    "cooled-off": ("Cooled off", "Followed a STOP when you wanted a yes"),
    "sized-right": ("Sized right", "Cut a bet or position to a size you can live with"),
    "never-twice": ("Never twice", "Followed the advice after once ignoring it"),
    "calm-under-fire": ("Calm under fire", "Chose well while stressed or euphoric"),
    "protected-1k": ("Protector", "Honesty protected $1,000 or more"),
    "protected-100k": ("Guardian", "Honesty protected $100,000 or more"),
    "walked-away": ("Walked away", "Ended a betting session instead of chasing"),
    "heir": ("Heir", "Carries an elder's lessons"),
    "streak-3": ("Steady rhythm", "Three honest choices in a row"),
    "streak-7": ("Heartbeat", "Seven honest choices in a row"),
}


def _level(xp: int) -> dict:
    cur = max(i for i, (t, _) in enumerate(LEVELS) if xp >= t)
    floor, name = LEVELS[cur]
    nxt = LEVELS[cur + 1] if cur + 1 < len(LEVELS) else None
    return {"level": cur + 1, "name": name, "floor": floor, "next": nxt[0] if nxt else None,
            "next_name": nxt[1] if nxt else None,
            "progress": 1.0 if not nxt else round((xp - floor) / (nxt[0] - floor), 3)}


def progress(store: Store, user_id: str) -> dict:
    person = store.get_person(user_id)
    if not person:
        raise KeyError(user_id)
    events = store.events(user_id)
    advice = {e["id"]: e["payload"] for e in events if e["kind"] == "advice" and not e["payload"].get("safety")}
    xp, earned, protected = 0, set(), 0.0
    decided: list[tuple[str, bool, dict]] = []   # (ledger id, honest choice?, advice payload)
    ignored_before = False
    for e in events:
        p = e["payload"]
        if e["kind"] == "advice" and e["id"] in advice:
            xp += 10
            earned.add("first-truth")
        elif e["kind"] == "action" and p.get("ledger_id") in advice:
            a = advice[p["ledger_id"]]
            hard = a.get("polarity") in ("stop", "caution")
            honest = p.get("taken") == "followed" or (not hard and p.get("taken") != "ignored")
            decided.append((p["ledger_id"], honest, a))
            xp += 25
            earned.add("loop-closer")
            if hard and p.get("taken") == "followed":
                xp += 50
                earned.add("cooled-off" if a.get("polarity") == "stop" else "sized-right")
                if a.get("domain") == "markets":
                    earned.add("walked-away" if a.get("polarity") == "stop" else "sized-right")
                if ignored_before:
                    earned.add("never-twice")
                if a.get("state") in ("stressed", "euphoric", "defensive"):
                    earned.add("calm-under-fire")
            if hard and p.get("taken") == "ignored":
                ignored_before = True
        elif e["kind"] == "outcome" and p.get("ledger_id") in advice:
            a = advice[p["ledger_id"]]
            d = p.get("value_delta") or 0
            followed = any(x[0] == p["ledger_id"] and x[1] for x in decided)
            if followed and (d >= 0 or p.get("type") == "avoided-loss"):
                protected += abs(d)
                xp += min(200, int(abs(d) / 1000) * 5)
            elif followed and a.get("polarity") in ("stop", "caution"):
                protected += abs(d) * 9   # sized down: lost a tenth of what the original size would have
    if person.ancestry:
        earned.add("heir")
    if protected >= 1000:
        earned.add("protected-1k")
    if protected >= 100_000:
        earned.add("protected-100k")
    streak = 0
    for _, honest, _ in reversed(decided):
        if not honest:
            break
        streak += 1
    best, run = 0, 0
    for _, honest, _ in decided:
        run = run + 1 if honest else 0
        best = max(best, run)
    if best >= 3:
        earned.add("streak-3")
    if best >= 7:
        earned.add("streak-7")
    hard = [(h, i) for i, (_, h, a) in enumerate(decided) if a.get("polarity") in ("stop", "caution")]
    if hard:
        w = [0.6 ** (len(hard) - 1 - k) for k in range(len(hard))]
        discipline = round(100 * sum(wi for wi, (h, _) in zip(w, hard) if h) / sum(w))
    else:
        discipline = None
    lv = _level(xp)
    badges = [{"key": k, "name": BADGES[k][0], "why": BADGES[k][1], "earned": k in earned} for k in BADGES]
    nxt = next((b for b in badges if not b["earned"] and b["key"] not in ("heir", "protected-100k")), None)
    return {"user_id": user_id, "xp": xp, **lv, "streak": streak, "best_streak": best, "discipline": discipline,
            "protected": round(protected, 2), "badges": badges, "earned": sorted(earned),
            "next_badge": nxt, "rule": "Rewards choosing well and closing the loop. Never rewards using it more."}
