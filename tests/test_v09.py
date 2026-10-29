"""v0.9: impact analytics, audit report, Arabic."""
from fastapi.testclient import TestClient

from app.main import app
from substrate import i18n
from substrate.analytics import impact
from substrate.audit import report
from substrate.engine import VagusEngine
from substrate.ledger import Store
from substrate.schemas import AdviseRequest, OutcomeRequest
from substrate.seed import seed

c = TestClient(app)


def eng():
    e = VagusEngine(Store(":memory:"))
    seed(e.store)
    return e


def test_impact_counts_honest_choices_and_money():
    e = eng()
    a0 = impact(e.store, e.store.users(public=True))
    r = e.advise(AdviseRequest(user_id="demo-kapoor", message="Another $200k into MOONX, good idea right?"))
    e.record_outcome(OutcomeRequest(ledger_id=r.ledger_id, action="followed", outcome_type="avoided-loss", value_delta=20000))
    a1 = impact(e.store, e.store.users(public=True))
    assert a1["hard_calls"] == a0["hard_calls"] + 1 and a1["honest_choices"] == a0["honest_choices"] + 1
    assert a1["money_protected"] == a0["money_protected"] + 20000
    assert len(a1["heatmap"]["weekday_hour"]) == 7 and len(a1["trend"]) == 30
    assert any(p["pattern"] == "concentration" for p in a1["top_patterns"])


def test_audit_report_verifies_chain_and_withholds_crisis():
    e = eng()
    e.advise(AdviseRequest(user_id="demo-kapoor", message="I want to end my life if this fails."))
    h = report(e.store, "demo-kapoor")
    assert "VERIFIED" in h and "Message withheld by design" in h and "end my life" not in h
    events = e.store.events("demo-kapoor")
    e.store.db.execute("update events set body=? where id=?", ('{"tampered": true}', events[0]["id"]))
    assert "BROKEN" in report(e.store, "demo-kapoor")


def test_arabic_understood_and_answered():
    assert i18n.detect("هل سيرتفع الذهب؟") == "ar" and i18n.detect("Will gold go up?") == "en"
    assert "$200k" in i18n.english_view("٢٠٠ ألف دولار")
    r = eng().advise(AdviseRequest(user_id="demo-farah", message="هل سيرتفع الذهب الأسبوع القادم؟"), record=False)
    assert r.language == "ar" and r.label == "NO CALL" and "لا أحد يستطيع" in r.message


def test_analytics_and_audit_endpoints():
    assert c.get("/v1/analytics").status_code in (200, 401)
    assert c.get("/v1/audit/demo-farah").headers["content-type"].startswith("text/html")
