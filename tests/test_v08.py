"""v0.8: embedded SDK backend - publishable keys, origin lock, hashed users, loop closing."""
import os

from fastapi.testclient import TestClient

from app.main import app, store
from substrate import embed

c = TestClient(app)
ADMIN = os.environ.get("SUBSTRATE_ADMIN_KEY")


def test_context_becomes_words_the_tissue_reads():
    m = embed.context_message("markets", {"stake": 5000, "price": 0.62, "side": "YES", "belief": 0.8}, "need a win")
    assert m == "$5,000 on YES at 62c. I think it's 80%. need a win"
    t = embed.context_message("trading", {"side": "long", "instrument": "XAUUSD", "leverage": 50, "amount": 100000})
    assert "XAUUSD 50:1" in t and "$100,000" in t
    assert embed.origin_ok(["*.mybank.com"], "https://app.mybank.com") and not embed.origin_ok(["mybank.com"], "https://evil.com")


def test_publishable_key_locked_to_origin_and_isolated():
    if not ADMIN:
        return
    t = c.post("/v1/admin/tenants", headers={"x-substrate-key": ADMIN}, json={"name": "PolyBank"}).json()
    sk, tid = t["api_key"], t["tenant_id"]
    pk = c.post("/v1/embed/keys", headers={"x-substrate-key": sk},
                json={"origins": ["app.polybank.com"], "tissue": "markets"}).json()["pk"]
    body = {"user": "u-777", "context": {"stake": 5000, "price": 0.62, "side": "YES", "belief": 0.8}, "message": "need a win"}
    assert c.post("/v1/embed/advise", headers={"x-substrate-pk": pk, "origin": "https://evil.com"}, json=body).status_code == 403
    r = c.post("/v1/embed/advise", headers={"x-substrate-pk": pk, "origin": "https://app.polybank.com"}, json=body).json()
    assert r["label"] in ("NO BET", "SIZE DOWN") and r["read_as"].startswith("$5,000 on YES")
    uid = embed.user_id(tid, "u-777", "markets")
    assert uid.startswith("ext-") and "u-777" not in uid and store.owner(uid) == tid
    assert c.get(f"/v1/person/{uid}").status_code == 401                       # not readable without the tenant key
    # the widget closes the loop, but only for its own user
    assert c.post("/v1/embed/outcome", headers={"x-substrate-pk": pk, "origin": "https://app.polybank.com"},
                  json={"user": "someone-else", "ledger_id": r["ledger_id"], "action": "ignored"}).status_code == 404
    assert c.post("/v1/embed/outcome", headers={"x-substrate-pk": pk, "origin": "https://app.polybank.com"},
                  json={"user": "u-777", "ledger_id": r["ledger_id"], "action": "followed"}).json()["ok"]


def test_demo_key_respects_lockdown():
    r = c.post("/v1/embed/advise", headers={"x-substrate-pk": "pk_demo"},
               json={"user": "x", "tissue": "trading", "message": "Will gold go up next week?"})
    if os.environ.get("SUBSTRATE_ADMIN_KEY") or os.environ.get("SUBSTRATE_API_KEY"):
        assert r.status_code == 403
    else:
        assert r.json()["label"] == "NO CALL"


def test_sdk_and_developer_page_served():
    assert "data-substrate-check" in c.get("/sdk.js").text
    assert "No-code builder" in c.get("/developers").text
    assert "/v1/embed/advise" in c.get("/openapi.json").text
