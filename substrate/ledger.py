"""Organ 06 + the Vagus Ledger: append-only, hash-chained, per human.

Every event (advice, action, outcome) carries the hash of the event before it, so the record of
honest advice is tamper-evident and verifiable on its own - including inside an exported .sub file.
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import threading
import uuid
from datetime import datetime, timezone

from .schemas import Person

GENESIS = "0" * 16
_lock = threading.Lock()


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def canonical(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def event_hash(event: dict) -> str:
    body = {k: v for k, v in event.items() if k != "hash"}
    return hashlib.sha256(canonical(body).encode()).hexdigest()[:16]


def verify_chain(events: list[dict]) -> bool:
    prev = GENESIS
    for e in events:
        if e.get("prev_hash") != prev or event_hash(e) != e.get("hash"):
            return False
        prev = e["hash"]
    return True


class Store:
    """SQLite: zero cost, zero ops. Swap for Postgres behind the same methods when a bank signs."""

    def __init__(self, path: str | None = None):
        self.path = path or os.environ.get("SUBSTRATE_DB", "substrate.db")
        self.db = sqlite3.connect(self.path, check_same_thread=False)
        self.db.execute("pragma journal_mode=wal")
        self.db.executescript("""
            create table if not exists persons (user_id text primary key, body text not null);
            create table if not exists events (
                seq integer primary key autoincrement,
                id text unique not null, user_id text not null, kind text not null,
                ts text not null, body text not null, prev_hash text not null, hash text not null);
            create index if not exists ix_events_user on events(user_id, seq);
        """)
        self.db.commit()

    # ---------------- genome
    def put_person(self, p: Person) -> Person:
        if not p.vintage:
            p.vintage = now()[:10]
        with _lock:
            self.db.execute("insert or replace into persons values (?, ?)", (p.user_id, p.model_dump_json()))
            self.db.commit()
        return p

    def get_person(self, user_id: str) -> Person | None:
        row = self.db.execute("select body from persons where user_id=?", (user_id,)).fetchone()
        return Person.model_validate_json(row[0]) if row else None

    def delete_person(self, user_id: str) -> None:
        with _lock:
            self.db.execute("delete from persons where user_id=?", (user_id,))
            self.db.execute("delete from events where user_id=?", (user_id,))
            self.db.commit()

    # ---------------- ledger
    def head(self, user_id: str) -> str:
        row = self.db.execute("select hash from events where user_id=? order by seq desc limit 1", (user_id,)).fetchone()
        return row[0] if row else GENESIS

    def append(self, user_id: str, kind: str, payload: dict, event_id: str | None = None, ts: str | None = None) -> dict:
        with _lock:
            ev = {"id": event_id or f"{'L' if kind == 'advice' else kind[0].upper()}-{uuid.uuid4().hex[:8]}",
                  "user_id": user_id, "kind": kind, "ts": ts or now(), "payload": payload,
                  "prev_hash": self.head(user_id)}
            ev["hash"] = event_hash(ev)
            self.db.execute("insert into events (id,user_id,kind,ts,body,prev_hash,hash) values (?,?,?,?,?,?,?)",
                            (ev["id"], user_id, kind, ev["ts"], canonical(payload), ev["prev_hash"], ev["hash"]))
            self.db.commit()
            return ev

    def events(self, user_id: str, limit: int | None = None) -> list[dict]:
        q = "select id,user_id,kind,ts,body,prev_hash,hash from events where user_id=? order by seq"
        rows = self.db.execute(q, (user_id,)).fetchall()
        out = [{"id": r[0], "user_id": r[1], "kind": r[2], "ts": r[3], "payload": json.loads(r[4]),
                "prev_hash": r[5], "hash": r[6]} for r in rows]
        return out[-limit:] if limit else out

    def get_event(self, event_id: str) -> dict | None:
        r = self.db.execute("select id,user_id,kind,ts,body,prev_hash,hash from events where id=?", (event_id,)).fetchone()
        if not r:
            return None
        return {"id": r[0], "user_id": r[1], "kind": r[2], "ts": r[3], "payload": json.loads(r[4]), "prev_hash": r[5], "hash": r[6]}

    def history(self, user_id: str) -> list[dict]:
        """Fold advice + action + outcome events into base pairs for the reasoning core."""
        pairs: dict[str, dict] = {}
        for e in self.events(user_id):
            p = e["payload"]
            if e["kind"] == "advice":
                pairs[e["id"]] = {"id": e["id"], "ts": e["ts"], "polarity": p.get("polarity"),
                                  "headline": p.get("headline"), "message": p.get("user_message")}
            elif p.get("ledger_id") in pairs:
                tgt = pairs[p["ledger_id"]]
                if e["kind"] == "action":
                    tgt["action"] = p.get("taken")
                elif e["kind"] == "outcome":
                    tgt["value_delta"] = p.get("value_delta")
                    tgt["outcome_type"] = p.get("type")
        return list(pairs.values())
