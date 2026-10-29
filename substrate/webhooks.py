"""Webhooks: Substrate tells the bank's own systems when a human needs a human.

Events
  escalation   high-stakes advice predicted unlikely to be followed, gambling harm, chasing, sustained distress
  safety       the Safety Protocol fired. The payload NEVER contains the message, only that it happened.
  pact-broken  the human acted against a pact they made
  stop         every STOP / NO BET / PASS verdict (opt-in, noisy)

Each tenant registers one URL and gets a secret once. Every delivery is signed:
  x-substrate-signature: sha256=HMAC_SHA256(secret, raw_body)
  x-substrate-event: <event>
Delivery is fire-and-forget on a background thread with one retry; the last 50 attempts are kept for debugging.
A single-tenant deployment can set SUBSTRATE_WEBHOOK_URL and SUBSTRATE_WEBHOOK_SECRET instead.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import threading
import time
from collections import deque

import httpx

from .ledger import Store, _lock, now

EVENTS = {"escalation", "safety", "pact-broken", "stop"}
LOG: deque = deque(maxlen=50)


def init(store: Store) -> None:
    store.db.execute("""create table if not exists webhooks (tenant_id text primary key, url text not null,
                        secret text not null, events text not null, created text not null)""")
    store.db.commit()


def register(store: Store, tenant_id: str, url: str, events: list[str]) -> str:
    init(store)
    secret = f"whsec_{secrets.token_urlsafe(24)}"
    with _lock:
        store.db.execute("insert or replace into webhooks values (?,?,?,?,?)",
                         (tenant_id, url, secret, json.dumps(sorted(set(events) & EVENTS)), now()))
        store.db.commit()
    return secret


def target(store: Store, user_id: str) -> tuple[str, str, set[str]] | None:
    init(store)
    tid = store.owner(user_id)
    if tid:
        r = store.db.execute("select url, secret, events from webhooks where tenant_id=?", (tid,)).fetchone()
        if r:
            return r[0], r[1], set(json.loads(r[2]))
    url = os.environ.get("SUBSTRATE_WEBHOOK_URL")
    if url:
        return url, os.environ.get("SUBSTRATE_WEBHOOK_SECRET", ""), set(
            os.environ.get("SUBSTRATE_WEBHOOK_EVENTS", "escalation,safety,pact-broken").split(","))
    return None


def sign(secret: str, body: bytes) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def _send(url: str, secret: str, event: str, body: bytes) -> None:
    for attempt in (1, 2):
        try:
            r = httpx.post(url, content=body, timeout=5, headers={
                "content-type": "application/json", "x-substrate-event": event, "x-substrate-signature": sign(secret, body)})
            LOG.append({"ts": now(), "event": event, "url": url, "status": r.status_code, "attempt": attempt})
            if r.status_code < 500:
                return
        except Exception as e:  # never let a webhook break advice
            LOG.append({"ts": now(), "event": event, "url": url, "error": type(e).__name__, "attempt": attempt})
        time.sleep(1.5)


def emit(store: Store, user_id: str, event: str, data: dict, sync: bool = False) -> bool:
    t = target(store, user_id)
    if not t or event not in t[2]:
        return False
    url, secret, _ = t
    body = json.dumps({"event": event, "user_id": user_id, "ts": now(), "data": data}, separators=(",", ":")).encode()
    if sync:
        _send(url, secret, event, body)
    else:
        threading.Thread(target=_send, args=(url, secret, event, body), daemon=True).start()
    return True


def from_advice(store: Store, r) -> list[str]:
    """Decide which events an advice response raises. Crisis content is never included."""
    sent, uid = [], _uid(store, r)
    if not uid:
        return sent
    if r.safety:
        if emit(store, uid, "safety", {"ledger_id": r.ledger_id, "domain": r.domain,
                                       "note": "Safety Protocol engaged. Reach out now."}):
            sent.append("safety")
        return sent
    if r.prediction and r.prediction.escalate and emit(store, uid, "escalation", {
            "ledger_id": r.ledger_id, "domain": r.domain, "label": r.label, "verdict": r.verdict.headline,
            "p_follow": r.prediction.p_follow, "reason": r.prediction.escalate}):
        sent.append("escalation")
    if r.verdict.polarity.value == "stop" and emit(store, uid, "stop", {
            "ledger_id": r.ledger_id, "domain": r.domain, "label": r.label, "verdict": r.verdict.headline}):
        sent.append("stop")
    return sent


def _uid(store: Store, r) -> str:
    ev = store.get_event(r.ledger_id) if r.ledger_id and r.ledger_id != "preview" else None
    return ev["user_id"] if ev else ""
