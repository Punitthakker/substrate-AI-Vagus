"""v1.0: check-ins, advisor desk, WhatsApp channel."""
import hashlib
import hmac
import os

from substrate import checkins, desk
from substrate.channels import whatsapp
from substrate.engine import VagusEngine
from substrate.ledger import Store
from substrate.schemas import AdviseRequest
from substrate.seed import seed


def eng():
    e = VagusEngine(Store(":memory:"))
    seed(e.store)
    return e


def test_checkins_due_and_answer_closes_the_loop():
    e = eng()
    items = {c["kind"]: c for c in checkins.due(e.store, "demo-rahman")}
    assert "morning-after" in items
    checkins.answer(e.store, e, "demo-rahman", items["morning-after"]["id"], "followed")
    assert all(c["id"] != items["morning-after"]["id"] for c in checkins.due(e.store, "demo-rahman"))
    assert any(ev["kind"] == "action" and ev["payload"]["ledger_id"] == "L-seed-mk03" for ev in e.store.events("demo-rahman"))
    assert [c["kind"] for c in checkins.due(e.store, "demo-haddad")] == ["close-the-loop"]


def test_desk_opens_urgent_for_safety_without_words():
    e = eng()
    e.advise(AdviseRequest(user_id="demo-sara", message="I want to end my life"))
    e.advise(AdviseRequest(user_id="demo-sara", message="Everyone would be better off without me"))
    ts = [t for t in desk.tickets(e.store) if t["user_id"] == "demo-sara"]
    assert len(ts) == 1 and ts[0]["priority"] == "urgent" and ts[0]["signals"] == 2
    assert "life" not in str(ts[0])
    desk.update(e.store, ts[0]["id"], "resolved", "Aisha (advisor)", "Called, she is safe with her sister.")
    assert desk.tickets(e.store, status="resolved")[0]["notes"][0]["by"] == "Aisha (advisor)"


def test_whatsapp_roundtrip_buttons_bound_to_sender():
    e = eng()
    whatsapp.handle(e.store, e, "+971500000009", "tissue markets")
    r = whatsapp.handle(e.store, e, "+971500000009", "Down $3k, need a win. 6-leg parlay, each leg 70%, $1,000 tonight")
    assert r[0]["type"] == "text" and r[1]["type"] == "interactive"
    bid = r[1]["interactive"]["action"]["buttons"][0]["reply"]["id"]
    assert "Pact made" not in str(whatsapp.handle(e.store, e, "+971500000777", button_id=bid))   # not another number's
    assert "Pact made" in whatsapp.handle(e.store, e, "+971500000009", button_id=bid)[0]["text"]["body"]
    crisis = whatsapp.handle(e.store, e, "+971500000009", "I want to end my life")
    assert "999" in crisis[0]["text"]["body"] and len(crisis) == 1


def test_whatsapp_signature_and_parse():
    os.environ["WHATSAPP_APP_SECRET"] = "s3cret"
    try:
        body = b'{"entry":[]}'
        good = "sha256=" + hmac.new(b"s3cret", body, hashlib.sha256).hexdigest()
        assert whatsapp.verify_signature(body, good) and not whatsapp.verify_signature(body, "sha256=00")
    finally:
        del os.environ["WHATSAPP_APP_SECRET"]
    p = {"entry": [{"changes": [{"value": {"messages": [{"from": "1", "type": "text", "text": {"body": "hi"}},
          {"from": "1", "type": "interactive", "interactive": {"button_reply": {"id": "pact:L-1"}}}]}}]}]}
    assert whatsapp.parse(p) == [("1", "hi", None), ("1", None, "pact:L-1")]
