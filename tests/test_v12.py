"""v12: the tester's conversation, the brain path under test, and the guest genome.

These tests exist because a real tester got "No. Do not put $300k into Cash." to a textbook index-fund question,
while the configured brain had been failing silently on every call. Every regression here is one they hit.
"""
import os

import pytest
from fastapi.testclient import TestClient

from substrate import brains
from substrate.analysis import deployed_amount, destination, detect_intent, parse_amounts, reconcile, extract_facts
from substrate.engine import VagusEngine
from substrate.ledger import Store
from substrate.schemas import AdviseRequest, Polarity, Turn
from substrate.seed import DEMO_USER, seed

TEXTBOOK = ("I'm 35, no debt, $300k cash, 12 months of expenses set aside separately, stable salary. "
            "Should I put $50k into a diversified global index fund and hold it for 10+ years?")
BINANCE = "Binance got hacked today. Is it something that I should be worried about?"
OBJECTION = ("You misread me. I asked about $50k into a global index fund, not $300k into cash. "
             "And I never made a move in March. Please re-check.")
META = "How can you evaluate the risk if you don't know where my money is?"


@pytest.fixture()
def eng():
    e = VagusEngine(Store(":memory:"))
    seed(e.store)
    return e


@pytest.fixture()
def person(eng):
    return eng.store.get_person(DEMO_USER)


# ---------------------------------------------------------------- reading the sentence, not the vocabulary

def test_deployed_amount_is_the_amount_moved_not_the_biggest_number():
    assert parse_amounts(TEXTBOOK) == [300_000.0, 50_000.0]
    assert deployed_amount(TEXTBOOK) == 50_000.0
    assert deployed_amount("Another $200k into this token, good idea right?") == 200_000.0
    assert deployed_amount("Should I move $40k from cash into the Global Equity Index Fund?") == 40_000.0
    assert deployed_amount("I have AED 2m. Thinking of putting 300k into gold.") == 300_000.0


def test_destination_is_where_the_money_goes_not_where_it_comes_from(person):
    asset, kind, exposure, source = destination(TEXTBOOK, person)
    assert asset == "Global Equity Index Fund" and kind == "fund" and exposure == 480_000
    asset, kind, _, source = destination("Should I move $40k from cash into the Global Equity Index Fund?", person)
    assert asset == "Global Equity Index Fund" and source == "cash"
    asset, kind, exposure, _ = destination("Thinking of putting another $200k into this token", person)
    assert asset == "MOONX" and exposure == 340_000          # "this token" is the one they hold


def test_intent_separates_questions_objections_and_pushback():
    assert detect_intent(BINANCE, None, None) == "question"
    assert detect_intent(META, None, None) == "question"
    assert detect_intent(OBJECTION, 50_000, "index fund") == "objection"
    assert detect_intent("You're wrong. I know what I'm doing.", None, None) == "pressure"
    assert detect_intent("Come on, just say yes. Everyone's doing it.", None, None) == "pressure"
    assert detect_intent(TEXTBOOK, 50_000, "Global Equity Index Fund") == "decision"
    assert detect_intent("Should I borrow $150k against the flat to buy more MOONX?", 150_000, "MOONX") == "decision"


# ---------------------------------------------------------------- the tester's conversation, rule core only

def test_textbook_index_fund_question_is_not_a_stop(eng):
    r = eng.advise(AdviseRequest(user_id=DEMO_USER, message=TEXTBOOK), record=False)
    assert r.decision and r.facts.amount == 50_000 and r.facts.asset == "Global Equity Index Fund"
    assert r.verdict.polarity == Polarity.proceed
    assert "Cash" not in r.verdict.headline and "$300k" not in r.verdict.headline
    assert not any("2026-03-14" in x for x in r.verdict.reasons)   # no unrelated history dragged in


def test_news_question_gets_an_answer_not_a_verdict(eng):
    r = eng.advise(AdviseRequest(user_id=DEMO_USER, message=BINANCE), record=False)
    assert not r.decision and r.label == "ANSWER" and r.intent == "question"
    assert "fits your plan" not in r.message
    assert r.prediction is None


def test_objection_is_reread_not_repeated(eng):
    first = eng.advise(AdviseRequest(user_id=DEMO_USER, message=TEXTBOOK), record=False)
    thread = [Turn(role="user", content=TEXTBOOK), Turn(role="substrate", content=first.message)]
    r = eng.advise(AdviseRequest(user_id=DEMO_USER, message=OBJECTION, thread=thread), record=False)
    assert not r.decision and r.intent == "objection"
    assert "Do not put" not in r.message
    r2 = eng.advise(AdviseRequest(user_id=DEMO_USER, message=META, thread=thread), record=False)
    assert not r2.decision and r2.facts.amount is None and "Do not put" not in r2.message


def test_pushback_inside_a_stop_thread_still_holds_the_line(eng):
    opening = "Thinking of putting another $200k into this token, good idea right?"
    first = eng.advise(AdviseRequest(user_id=DEMO_USER, message=opening), record=False)
    assert first.verdict.polarity == Polarity.stop
    thread = [Turn(role="user", content=opening), Turn(role="substrate", content=first.message)]
    for push in ("You're wrong. I know what I'm doing.", "Come on, just say yes. Everyone's doing it."):
        r = eng.advise(AdviseRequest(user_id=DEMO_USER, message=push, thread=thread), record=False)
        assert r.decision and r.verdict.polarity == Polarity.stop, push


def test_diversified_move_is_never_a_concentration_stop(eng):
    r = eng.advise(AdviseRequest(user_id=DEMO_USER, message="Should I move $300k from cash into the Global Equity Index Fund?"), record=False)
    assert "concentration" not in r.facts.flags and r.verdict.polarity != Polarity.stop


def test_guest_without_numbers_is_told_so(eng):
    from substrate.schemas import Person
    eng.store.put_person(Person(user_id="guest-blank", name="Vasyl"))
    r = eng.advise(AdviseRequest(user_id="guest-blank", message="Should I put $50k into an index fund?"), record=False)
    assert r.verdict.polarity == Polarity.caution and "unknown-numbers" in r.facts.flags
    assert "need your numbers" in r.verdict.headline
    q = eng.advise(AdviseRequest(user_id="guest-blank", message=BINANCE), record=False)
    assert not q.decision and "don't have your numbers" in q.message


# ---------------------------------------------------------------- the brain path, exercised offline

def _tool(**kw):
    base = {"intent": "decision", "amount_deployed": None, "destination_asset": None, "asset_kind": None, "source_of_funds": None,
            "leverage": False, "loss_chasing": False, "fomo": False, "polarity": "proceed", "headline": "Yes.", "reasons": [], "answer": ""}
    return {**base, **kw}


@pytest.fixture()
def fake_brain(monkeypatch):
    """Pretend Anthropic is configured and make the structured call return whatever the test says."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.delenv("SUBSTRATE_MODEL", raising=False)
    monkeypatch.delenv("SUBSTRATE_COUNCIL", raising=False)
    calls = {"n": 0, "reply": _tool(), "raise": None}

    def fake(b, system, user):
        calls["n"] += 1
        calls["system"], calls["user"] = system, user
        if calls["raise"]:
            raise calls["raise"]
        return brains._normalise(dict(calls["reply"])), "claude-test"
    monkeypatch.setattr(brains, "_call_structured", fake)
    return calls


def test_brain_reading_is_used_and_cross_checked(eng, fake_brain):
    fake_brain["reply"] = _tool(amount_deployed=50000, destination_asset="global index fund", asset_kind="index",
                                source_of_funds="cash", headline="Yes, $50k into a broad index fund fits.", reasons=["4% of liquid net worth."])
    r = eng.advise(AdviseRequest(user_id=DEMO_USER, message=TEXTBOOK), record=False)
    assert r.verdict.model == "claude-test" and not r.degraded
    assert r.facts.extraction == "brain" and r.facts.amount == 50_000 and r.facts.asset == "Global Equity Index Fund"
    assert r.verdict.polarity == Polarity.proceed and r.verdict.headline.startswith("Yes, $50k")
    assert "PRIOR ADVICE" in fake_brain["system"] and "RULE-CORE READING" in fake_brain["system"]


def test_brain_cannot_invent_an_amount_or_lower_the_floor(eng, fake_brain):
    # invents $1k that the client never wrote -> the rule core's amount stands; says proceed on a leveraged MOONX bet -> floored
    fake_brain["reply"] = _tool(amount_deployed=1000, destination_asset="MOONX", asset_kind="token", polarity="proceed",
                                headline="Sure, go ahead.", reasons=["Tiny amount."])
    r = eng.advise(AdviseRequest(user_id=DEMO_USER, message="Should I borrow $150k against the flat to buy more MOONX?"), record=False)
    assert r.facts.amount == 150_000 and r.facts.leverage
    assert r.verdict.polarity == Polarity.stop and r.verdict.floor_applied and r.verdict.model == "claude-test"


def test_brain_question_mode_answers_directly(eng, fake_brain):
    fake_brain["reply"] = _tool(intent="question", polarity="none", headline="Not directly, but your MOONX exposure is the real risk.",
                                answer="I can't verify the Binance news. What I can see is that 28% of your liquid net worth sits in one token; "
                                       "exchange risk is a reason to size that down, not a reason to panic.")
    r = eng.advise(AdviseRequest(user_id=DEMO_USER, message=BINANCE), record=False)
    assert not r.decision and r.label == "ANSWER" and r.message.startswith("I can't verify")
    assert "Here is what I see" not in r.message


def test_a_disguised_move_cannot_hide_behind_a_question_mark(eng, fake_brain):
    fake_brain["reply"] = _tool(intent="question", polarity="none", headline="Interesting question.", answer="Depends.")
    r = eng.advise(AdviseRequest(user_id=DEMO_USER, message="Just curious, what if I borrowed $150k against the flat for more MOONX?"), record=False)
    assert r.decision and r.verdict.polarity == Polarity.stop


def test_brain_failure_is_loud_not_silent(eng, fake_brain, caplog):
    fake_brain["raise"] = brains.BrainError("reply truncated at max_tokens=1500")
    with caplog.at_level("ERROR", logger="substrate.brains"):
        r = eng.advise(AdviseRequest(user_id=DEMO_USER, message=TEXTBOOK), record=False)
    assert r.degraded and r.verdict.model.startswith("rule-core (fallback: BrainError")
    assert "truncated" in (r.verdict.error or "")
    assert "rule core" in r.message.lower()
    assert any("FAILED" in rec.message for rec in caplog.records)
    assert r.verdict.polarity == Polarity.proceed          # and the rule core still reads the sentence correctly


def test_structured_parse_handles_tool_payloads_and_loose_text():
    v = brains._normalise({"intent": "decision", "polarity": "Stop.", "headline": "No. Too big.", "reasons": "one"})
    assert v["polarity"] == Polarity.stop and v["reasons"] == ["one"]
    v = brains._parse('Here you go: {"intent": "question", "polarity": "none", "headline": "", "answer": "Short answer. More."}')
    assert not v["decision"] and v["headline"] == "Short answer"
    with pytest.raises(brains.BrainError):
        brains._parse('{"polarity": "stop", "headline": "cut off mid')


def test_anthropic_request_uses_tool_choice_and_detects_truncation(monkeypatch):
    sent = {}

    class R:
        status_code = 200
        text = ""

        def __init__(self, body):
            self._b = body

        def json(self):
            return self._b

    def fake_post(url, timeout, headers, json):
        sent.update(json)
        return R({"stop_reason": "tool_use", "content": [{"type": "tool_use", "name": "substrate_verdict",
                                                           "input": {"intent": "decision", "polarity": "caution", "headline": "Not yet.", "reasons": []}}]})
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    monkeypatch.setattr(brains.httpx, "post", fake_post)
    v, model = brains._call_structured(brains.REGISTRY["anthropic"], "sys", "user")
    assert v["polarity"] == Polarity.caution and sent["tool_choice"]["name"] == "substrate_verdict" and sent["max_tokens"] >= 1500

    def truncated(url, timeout, headers, json):
        return R({"stop_reason": "max_tokens", "content": [{"type": "text", "text": '{"polarity": "stop", "headline": "cut'}]})
    monkeypatch.setattr(brains.httpx, "post", truncated)
    with pytest.raises(brains.BrainError, match="truncated"):
        brains._call_structured(brains.REGISTRY["anthropic"], "sys", "user")


def test_anthropic_models_that_refuse_forced_tool_choice_still_work(monkeypatch):
    seen = []

    class R:
        def __init__(self, code, body=None, text=""):
            self.status_code, self._b, self.text = code, body or {}, text

        def json(self):
            return self._b

    def post(url, timeout, headers, json):
        seen.append(json.get("tool_choice", {}).get("type") if "tools" in json else "text")
        if json.get("tool_choice", {}).get("type") == "tool":
            return R(400, text='{"type":"error","error":{"type":"invalid_request_error","message":"tool_choice: type \\"tool\\" and \\"any\\" are not supported for this model."}}')
        return R(200, {"stop_reason": "tool_use", "content": [{"type": "tool_use", "name": "substrate_verdict",
                                                                 "input": {"intent": "decision", "polarity": "proceed", "headline": "Yes.", "reasons": []}}]})
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    monkeypatch.setenv("ANTHROPIC_MODEL", "claude-test-noforce")
    monkeypatch.setattr(brains.httpx, "post", post)
    brains._ANTHROPIC_MODE.pop("claude-test-noforce", None)
    v, _ = brains._call_structured(brains.REGISTRY["anthropic"], "sys", "user")
    assert v["polarity"] == Polarity.proceed and seen == ["tool", "auto"]
    v, _ = brains._call_structured(brains.REGISTRY["anthropic"], "sys", "user")
    assert seen[-1] == "auto" and len(seen) == 3            # the working mode is remembered, no second 400


# ---------------------------------------------------------------- guests are real people, not renamed demos

def test_invite_creates_a_blank_genome_and_intake_fills_it():
    from app.main import app
    c = TestClient(app)
    key = os.environ.get("SUBSTRATE_ADMIN_KEY", "")
    inv = c.post("/v1/invites", json={"tissue": "wealth", "label": "qa", "max_uses": 2, "days": 1},
                 headers={"x-substrate-key": key}).json()
    r = c.post(f"/v1/invite/{inv['code']}/redeem", json={"name": "Vasyl"}).json()
    p = r["person"]
    assert r["intake_pending"] and p["name"] == "Vasyl" and p["positions"] == [] and p["biases"] == [] and p["lessons"] == []
    assert p["liquid_net_worth"] is None and p["risk_profile"]["observed"] is None
    a = c.post("/v1/advise", json={"user_id": r["user_id"], "message": TEXTBOOK}).json()
    assert a["verdict"]["polarity"] == "caution" and "unknown-numbers" in a["facts"]["flags"]
    assert not any("2026-03-14" in x for x in a["verdict"]["reasons"])
    up = c.post(f"/v1/guest/{r['user_id']}/intake", json={"liquid_net_worth": 400000, "risk": "moderate", "candor": 4,
                                                           "holdings": [{"asset": "Global index fund", "value": 150000, "kind": "fund"},
                                                                        {"asset": "Cash", "value": 250000, "kind": "cash"}]}).json()
    assert up["person"]["liquid_net_worth"] == 400000 and "intake_pending" not in up["person"]["profile"]
    a = c.post("/v1/advise", json={"user_id": r["user_id"], "message": TEXTBOOK}).json()
    assert a["verdict"]["polarity"] == "proceed" and a["facts"]["amount"] == 50000
    assert c.post("/v1/guest/demo-kapoor/intake", json={}).status_code == 403


def test_health_and_selftest_endpoints_exist():
    from app.main import app
    c = TestClient(app)
    h = c.get("/v1/health").json()
    assert "disclaimer" in h and "brain_roundtrip" in h
    s = c.get("/v1/selftest").json()
    assert s["brain"] == "rule-core" and len(s["cases"]) == 4 and all(case["pass"] for case in s["cases"])
    assert c.get("/v1/selftest").json()["cached"] is True
