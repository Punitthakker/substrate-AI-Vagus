"""Check-ins: the follow-up a good advisor makes, computed from the ledger (no scheduler needed).

  morning-after   8-72h after a hard stop made in a heated or late moment, with no decision recorded
  close-the-loop  7-120 days after any STOP/CAUTION with no decision recorded
  pact-kept       a pact that ran its full course, not yet celebrated

Every answer is written back to the ledger, so a check-in is how the genome keeps learning from people who
never press a button. Items are computed on read and acknowledged by id, so nothing is ever sent twice.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from .ledger import Store

HEATED = {"stressed", "euphoric", "defensive"}
LATE_FLAGS = {"late-night", "impulse", "chasing"}


def _ts(s: str) -> datetime:
    return datetime.strptime(s[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)


def _short(headline: str) -> str:
    h = (headline or "").strip().rstrip(".")
    return h if len(h) <= 90 else h[:87] + "..."


def due(store: Store, user_id: str, now: datetime | None = None) -> list[dict]:
    now = now or datetime.now(timezone.utc)
    events = store.events(user_id)
    acked = {e["payload"].get("checkin_id") for e in events if e["kind"] == "checkin"}
    decided = {e["payload"].get("ledger_id") for e in events if e["kind"] == "action"}
    out = []
    for e in events:
        p = e["payload"]
        if e["kind"] == "advice" and not p.get("safety") and p.get("polarity") in ("stop", "caution") \
                and e["id"] not in decided:
            age = now - _ts(e["ts"])
            heated = p.get("state") in HEATED or LATE_FLAGS & set(p.get("flags") or [])
            if heated and p.get("polarity") == "stop" and timedelta(hours=8) <= age <= timedelta(hours=72):
                cid = f"morning-after:{e['id']}"
                if cid not in acked:
                    out.append({"id": cid, "kind": "morning-after", "ledger_id": e["id"], "ts": e["ts"],
                                "title": "The morning after",
                                "text": f"Last time we spoke, I said: “{_short(p.get('headline'))}”. "
                                        f"How does it look now, with some distance?",
                                "options": [{"key": "followed", "label": "Glad I waited"},
                                            {"key": "ignored", "label": "I did it anyway"},
                                            {"key": "later", "label": "Still thinking"}]})
            elif timedelta(days=7) <= age <= timedelta(days=120):
                cid = f"close-loop:{e['id']}"
                if cid not in acked:
                    out.append({"id": cid, "kind": "close-the-loop", "ledger_id": e["id"], "ts": e["ts"],
                                "title": "What did you decide?",
                                "text": f"On {e['ts'][:10]} I said: “{_short(p.get('headline'))}”. "
                                        f"What happened? Telling me is how I get better for you.",
                                "options": [{"key": "followed", "label": "I followed it"},
                                            {"key": "ignored", "label": "I went ahead"},
                                            {"key": "later", "label": "Ask me later"}]})
        elif e["kind"] == "pact-kept":
            cid = f"pact-kept:{p.get('pact_id')}"
            if cid not in acked:
                out.append({"id": cid, "kind": "pact-kept", "ts": e["ts"], "title": "You kept your word",
                            "text": f"“{p.get('text', '')}”. You made a promise to your future self and kept it. "
                                    "That is the whole skill.",
                            "options": [{"key": "ack", "label": "Thank you"}]})
    return sorted(out, key=lambda x: x["ts"], reverse=True)[:10]


def answer(store: Store, engine, user_id: str, checkin_id: str, key: str) -> dict:
    item = next((x for x in due(store, user_id) if x["id"] == checkin_id), None)
    if not item:
        raise KeyError(checkin_id)
    if key == "later":
        return {"ok": True, "deferred": True}
    from .schemas import OutcomeRequest
    if key in ("followed", "ignored") and item.get("ledger_id"):
        engine.record_outcome(OutcomeRequest(ledger_id=item["ledger_id"], action=key))
    store.append(user_id, "checkin", {"checkin_id": checkin_id, "kind": item["kind"], "answer": key})
    return {"ok": True, "recorded": key}
