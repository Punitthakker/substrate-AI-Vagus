"""Advisor Desk: when a human needs a human, the platform's people get a ticket.

Opened automatically when Substrate predicts a high-stakes call is unlikely to be followed, when gambling-harm,
chasing or sustained distress is detected, and (as urgent) whenever the Safety Protocol fires. One open ticket per
person: new signals update it rather than piling up. A ticket carries the verdict and the reason, never the words
of a crisis message.
"""
from __future__ import annotations

import json
import uuid

from .ledger import Store, _lock, now


def init(store: Store) -> None:
    store.db.execute("""create table if not exists desk (id text primary key, user_id text not null, tenant_id text,
        priority text not null, status text not null, body text not null, created text not null, updated text not null)""")
    store.db.commit()


def open_or_update(store: Store, user_id: str, priority: str, summary: dict) -> str:
    init(store)
    r = store.db.execute("select id, priority, body from desk where user_id=? and status!='resolved'", (user_id,)).fetchone()
    with _lock:
        if r:
            body = json.loads(r[2])
            body["signals"] = (body.get("signals") or [])[-9:] + [summary]
            pri = "urgent" if "urgent" in (priority, r[1]) else priority
            store.db.execute("update desk set priority=?, body=?, updated=? where id=?", (pri, json.dumps(body), now(), r[0]))
            store.db.commit()
            return r[0]
        tid = f"D-{uuid.uuid4().hex[:8]}"
        store.db.execute("insert into desk values (?,?,?,?,?,?,?,?)",
                         (tid, user_id, store.owner(user_id), priority, "open",
                          json.dumps({"signals": [summary], "notes": []}), now(), now()))
        store.db.commit()
    return tid


def tickets(store: Store, user_ids: list[str] | None = None, status: str | None = None) -> list[dict]:
    init(store)
    rows = store.db.execute("select id,user_id,tenant_id,priority,status,body,created,updated from desk order by updated desc").fetchall()
    out = []
    for r in rows:
        if user_ids is not None and r[1] not in user_ids:
            continue
        if status and r[4] != status:
            continue
        b = json.loads(r[5])
        p = store.get_person(r[1])
        out.append({"id": r[0], "user_id": r[1], "name": p.name if p else r[1], "domain": p.domain if p else None,
                    "priority": r[3], "status": r[4], "created": r[6], "updated": r[7],
                    "latest": (b.get("signals") or [{}])[-1], "signals": len(b.get("signals") or []),
                    "notes": b.get("notes") or [], "claimed_by": b.get("claimed_by")})
    order = {"urgent": 0, "high": 1, "normal": 2}
    return sorted(out, key=lambda t: (t["status"] == "resolved", order.get(t["priority"], 3)))


def update(store: Store, ticket_id: str, status: str, advisor: str = "", note: str = "") -> dict | None:
    init(store)
    r = store.db.execute("select body, user_id from desk where id=?", (ticket_id,)).fetchone()
    if not r:
        return None
    b = json.loads(r[0])
    if advisor:
        b["claimed_by"] = advisor
    if note:
        b.setdefault("notes", []).append({"ts": now(), "by": advisor or "advisor", "note": note[:1000]})
    with _lock:
        store.db.execute("update desk set status=?, body=?, updated=? where id=?", (status, json.dumps(b), now(), ticket_id))
        store.db.commit()
    store.append(r[1], "desk", {"ticket_id": ticket_id, "status": status, "by": advisor or "advisor"})
    return {"id": ticket_id, "status": status}


def from_response(store: Store, user_id: str, r) -> str | None:
    """Engine hook: open or update a ticket when the response calls for a human."""
    if r.ledger_id == "preview":
        return None
    if r.safety:
        return open_or_update(store, user_id, "urgent", {"ts": now(), "ledger_id": r.ledger_id, "domain": r.domain,
                                                         "label": "SAFETY", "reason": "Safety Protocol engaged. Reach out now.",
                                                         "verdict": "Message withheld by design."})
    esc = r.prediction.escalate if r.prediction else None
    if not esc:
        return None
    return open_or_update(store, user_id, "high" if r.verdict.polarity.value == "stop" else "normal", {
        "ts": now(), "ledger_id": r.ledger_id, "domain": r.domain, "label": r.label, "verdict": r.verdict.headline,
        "reason": esc, "p_follow": r.prediction.p_follow, "flags": r.facts.flags[:6]})
