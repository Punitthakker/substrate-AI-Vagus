"""Organ 06 + the Vagus Ledger: append-only, hash-chained, per human.

Every event (advice, action, outcome) carries the hash of the event before it, so the record of
honest advice is tamper-evident and verifiable on its own - including inside an exported .sub file.
"""
from __future__ import annotations

import hashlib
import secrets
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
            create table if not exists tenants (id text primary key, name text not null, key_hash text unique not null,
                                                policy text not null, created text not null);
            create table if not exists owners (user_id text primary key, tenant_id text not null);
        """)
        self.db.commit()

    # ---------------- enterprise tenancy
    @staticmethod
    def _h(raw: str) -> str:
        return hashlib.sha256(raw.encode()).hexdigest()

    def create_tenant(self, name: str, policy: dict) -> tuple[str, str]:
        tid = f"tn_{uuid.uuid4().hex[:10]}"
        raw = f"sk_sub_{secrets.token_urlsafe(24)}"   # shown once, stored hashed
        with _lock:
            self.db.execute("insert into tenants values (?,?,?,?,?)", (tid, name, self._h(raw), canonical(policy), now()))
            self.db.commit()
        return tid, raw

    def tenant_by_key(self, raw: str | None) -> dict | None:
        if not raw:
            return None
        r = self.db.execute("select id,name,policy,created from tenants where key_hash=?", (self._h(raw),)).fetchone()
        return {"id": r[0], "name": r[1], "policy": json.loads(r[2]), "created": r[3]} if r else None

    def tenants(self) -> list[dict]:
        return [{"id": r[0], "name": r[1], "policy": json.loads(r[2]), "created": r[3]}
                for r in self.db.execute("select id,name,policy,created from tenants order by created")]

    def set_policy(self, tenant_id: str, policy: dict) -> None:
        with _lock:
            self.db.execute("update tenants set policy=? where id=?", (canonical(policy), tenant_id))
            self.db.commit()

    def owner(self, user_id: str) -> str | None:
        r = self.db.execute("select tenant_id from owners where user_id=?", (user_id,)).fetchone()
        return r[0] if r else None

    def set_owner(self, user_id: str, tenant_id: str) -> None:
        with _lock:
            self.db.execute("insert or replace into owners values (?,?)", (user_id, tenant_id))
            self.db.commit()

    def users(self, tenant_id: str | None = None, public: bool = False) -> list[str]:
        if tenant_id:
            return [r[0] for r in self.db.execute("select user_id from owners where tenant_id=?", (tenant_id,))]
        rows = [r[0] for r in self.db.execute("select user_id from persons")]
        return [u for u in rows if u.startswith(("demo-", "guest-"))] if public else rows

    def metrics(self, user_ids: list[str]) -> dict:
        """Operational truth for a tenant: what Substrate said, what humans did, what it cost them."""
        if not user_ids:
            return {"advice": 0}
        q = ",".join("?" * len(user_ids))
        rows = self.db.execute(f"select id,kind,body from events where user_id in ({q})", user_ids).fetchall()
        adv, actions, outcomes = {}, {}, {}
        for eid, kind, body in rows:
            p = json.loads(body)
            if kind == "advice":
                adv[eid] = p
            elif kind == "action":
                actions[p.get("ledger_id")] = p.get("taken")
            elif kind == "outcome":
                outcomes[p.get("ledger_id")] = p.get("value_delta")
        by_pol, by_dom, firm, pf = {}, {}, [], []
        for p in adv.values():
            by_pol[p.get("polarity", "?")] = by_pol.get(p.get("polarity", "?"), 0) + 1
            by_dom[p.get("domain", "wealth")] = by_dom.get(p.get("domain", "wealth"), 0) + 1
            if p.get("firmness"):
                firm.append(p["firmness"])
            if p.get("p_follow") is not None:
                pf.append(p["p_follow"])
        followed = sum(1 for a in actions.values() if a == "followed")
        ignored = sum(1 for a in actions.values() if a == "ignored")
        cost = sum(-(outcomes.get(k) or 0) for k, a in actions.items() if a == "ignored" and (outcomes.get(k) or 0) < 0)
        return {"advice": len(adv), "by_polarity": by_pol, "by_domain": by_dom,
                "floor_engagements": sum(1 for p in adv.values() if p.get("floor_applied")),
                "safety_events": sum(1 for p in adv.values() if p.get("safety")),
                "avg_firmness": round(sum(firm) / len(firm), 2) if firm else None,
                "avg_p_follow": round(sum(pf) / len(pf), 2) if pf else None,
                "followed": followed, "ignored": ignored,
                "follow_rate": round(followed / (followed + ignored), 2) if followed + ignored else None,
                "cost_of_ignoring": cost, "humans": len(user_ids)}

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
