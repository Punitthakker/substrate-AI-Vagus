"""Embedded Substrate: publishable keys, end-user mapping and order context for platforms.

A platform (a wealth app, a prediction market, a broker, a sportsbook) embeds Substrate in its own front end:

  publishable key   pk_live_... is safe in a browser. It is locked to the platform's origins, can only touch
                    genomes it created, and every call is rate-limited per IP. The secret tenant key never leaves
                    the platform's server.
  end users         the platform passes its own user id. Substrate hashes it with the tenant id into a private
                    genome id (ext-...); the raw id is never stored.
  order context     the widget sends what is on the screen (stake, price, side, leverage, instrument, market) and
                    Substrate turns it into a sentence the tissue can reason about. The user's own note, if any, is
                    what the limbic layer reads.

pk_demo works on the open demo (no admin key set) with any origin, mapped to sandboxed guest genomes.
"""
from __future__ import annotations

import hashlib
import json
import secrets
from urllib.parse import urlparse

from .ledger import Store, _lock, now

DEMO_PK = "pk_demo"


def init(store: Store) -> None:
    store.db.execute("""create table if not exists pkeys (pk text primary key, tenant_id text not null, label text not null,
                        origins text not null, tissue text not null, created text not null, revoked integer default 0)""")
    store.db.commit()


def create(store: Store, tenant_id: str, origins: list[str], tissue: str, label: str) -> str:
    init(store)
    pk = f"pk_live_{secrets.token_urlsafe(18)}"
    with _lock:
        store.db.execute("insert into pkeys (pk,tenant_id,label,origins,tissue,created) values (?,?,?,?,?,?)",
                         (pk, tenant_id, label, json.dumps(origins), tissue, now()))
        store.db.commit()
    return pk


def lookup(store: Store, pk: str) -> dict | None:
    init(store)
    r = store.db.execute("select pk,tenant_id,label,origins,tissue,created,revoked from pkeys where pk=?", (pk,)).fetchone()
    if not r or r[6]:
        return None
    return {"pk": r[0], "tenant_id": r[1], "label": r[2], "origins": json.loads(r[3]), "tissue": r[4], "created": r[5]}


def list_for(store: Store, tenant_id: str) -> list[dict]:
    init(store)
    return [{"pk": r[0][:12] + "...", "label": r[1], "origins": json.loads(r[2]), "tissue": r[3], "created": r[4],
             "revoked": bool(r[5])} for r in store.db.execute(
        "select pk,label,origins,tissue,created,revoked from pkeys where tenant_id=?", (tenant_id,)).fetchall()]


def origin_ok(allowed: list[str], origin: str | None) -> bool:
    if "*" in allowed:
        return True
    if not origin:
        return False
    host = urlparse(origin).netloc.lower()
    for a in allowed:
        a = a.lower().replace("https://", "").replace("http://", "").rstrip("/")
        if host == a or (a.startswith("*.") and host.endswith(a[1:])):
            return True
    return False


def user_id(tenant_id: str, external_user: str, tissue: str = "wealth") -> str:
    """One private genome per platform user per tissue (a person can trade gold and invest on one platform)."""
    h = hashlib.sha256(f"{tenant_id}:{external_user}:{tissue}".encode()).hexdigest()[:16]
    return ("guest-e" if tenant_id == "demo" else "ext-") + h


def _money(v) -> str:
    try:
        v = float(v)
    except (TypeError, ValueError):
        return str(v)
    return f"${v:,.0f}"


def context_message(tissue: str, ctx: dict, note: str = "") -> str:
    """Turn what's on the platform's screen into words the tissue reads. The user's note carries the feeling."""
    c = {k: v for k, v in (ctx or {}).items() if v not in (None, "")}
    parts = []
    if tissue == "markets":
        price = c.get("price")
        if price is not None:
            try:
                p = float(price)
                price = f"{p * 100:.0f}c" if p < 1 else f"{p:.0f}c"
            except ValueError:
                pass
        legs = c.get("legs")
        bet = f"{_money(c['stake'])} on {c.get('side', 'YES')}" if c.get("stake") else f"A bet on {c.get('side', 'YES')}"
        if price:
            bet += f" at {price}"
        if c.get("market"):
            bet += f" ({c['market']})"
        parts.append(bet + ".")
        if legs:
            leg_p = c.get("leg_prob")
            parts.append(f"{legs}-leg parlay" + (f", each leg {float(leg_p) * 100:.0f}%" if leg_p else "") + ".")
        if c.get("belief") is not None:
            parts.append(f"I think it's {float(c['belief']) * 100:.0f}%.")
    elif tissue == "trading":
        side = c.get("side", "long")
        inst = c.get("instrument", "XAUUSD")
        lev = c.get("leverage")
        parts.append(f"Going {side} {inst}" + (f" {float(lev):g}:1" if lev else "") +
                     (f", {_money(c['amount'])}" if c.get("amount") else "") +
                     (f", for {c['horizon']}" if c.get("horizon") else "") +
                     (f", stop at {c['stop_pct']}%" if c.get("stop_pct") else "") + ".")
    elif tissue == "wealth":
        parts.append(f"Putting {_money(c['amount'])} into {c.get('asset', 'this')}." if c.get("amount")
                     else f"Thinking about {c.get('asset', 'this investment')}.")
        if c.get("borrowed"):
            parts.append("I'd borrow to fund it.")
    elif tissue == "venture":
        parts.append(f"{_money(c.get('check'))} check" + (f" at a {_money(c['valuation'])} post" if c.get("valuation") else "") +
                     (f" on {_money(c['arr'])} ARR" if c.get("arr") else "") + (f" into {c['company']}" if c.get("company") else "") + ".")
    elif tissue == "founder":
        parts.append(f"Spending {_money(c.get('amount'))}" + (" a month" if c.get("monthly") else "") +
                     (f" on {c['item']}" if c.get("item") else "") + ".")
    else:
        parts.append(c.get("action", ""))
    if note:
        parts.append(note.strip())
    return " ".join(p for p in parts if p).strip() or (note or "Checking this decision.")


def compact(r) -> dict:
    """What a widget needs, nothing more."""
    return {"ledger_id": r.ledger_id, "label": r.label, "polarity": r.verdict.polarity.value,
            "headline": r.verdict.headline, "reasons": r.verdict.reasons, "message": r.message, "safety": r.safety,
            "temperament": r.temperament, "firmness": r.firmness,
            "forecasts": [f.model_dump() for f in (r.prediction.forecasts if r.prediction else [])],
            "p_follow": r.prediction.p_follow if r.prediction else None,
            "pact_offer": r.pact_offer, "pact_active": r.pact_active,
            "letter": {"from": r.letter["from_name"], "title": r.letter["title"]} if r.letter else None}
