"""v0.5: markets tissue, bet math, inheritance, PII redaction, GoEmotions mapping, LiteLLM brain."""
from fastapi.testclient import TestClient

from app.main import app
from substrate import brains, limbic
from substrate.engine import VagusEngine
from substrate.export import export_sub
from substrate.inherit import InheritanceError, inherit, revoke
from substrate.ledger import Store
from substrate.markets_api import BetMath, Leg, analyze
from substrate.redact import redact
from substrate.schemas import AdviseRequest
from substrate.seed import seed

c = TestClient(app)


def eng():
    e = VagusEngine(Store(":memory:"))
    seed(e.store)
    return e


def test_parlay_math_and_chase():
    r = eng().advise(AdviseRequest(user_id="demo-rahman",
                                   message="Down $3k, need a win. 6-leg parlay, each leg 70%, $1,000 tonight."), record=False)
    assert r.label == "NO BET" and "11.8%" in r.message and "chasing" in r.facts.flags


def test_no_edge_sizes_down_without_old_history():
    r = eng().advise(AdviseRequest(user_id="demo-rahman", message="Kalshi YES at 70c, I'm 65% sure. $300 on it."), record=False)
    assert r.label == "SIZE DOWN" and r.facts.metrics["edge"] < 0 and "repeat-pattern" not in r.facts.flags


def test_harm_switches_to_care():
    r = eng().advise(AdviseRequest(user_id="demo-rahman", message="Borrowed $2k from my brother to bet tonight.",
                                   temperament="boss"), record=False)
    assert r.label == "NO BET" and r.temperament == "comfort" and r.firmness <= 3 and "gamblingtherapy.org" in r.message


def test_bet_math_api():
    out = analyze(BetMath(legs=[Leg(price=0.7)] * 6, stake=1000, bankroll=25000))
    assert abs(out["parlay"]["joint_market_prob"] - 0.7 ** 6) < 1e-4 and out["verdict"] == "SIZE DOWN"
    out = analyze(BetMath(price=0.5, round_robin=(5, 2), stake=200, bankroll=25000))
    assert out["round_robin"]["bets"] == 10 and out["round_robin"]["total_stake"] == 2000
    assert c.post("/v1/markets/analyze", json={"american_odds": 150, "belief": 0.45, "stake": 200,
                                                "bankroll": 25000}).json()["verdict"] == "SIZED RIGHT"


def test_inheritance_cites_elder_and_respects_consent():
    e = eng()
    maya = e.store.get_person("demo-maya")
    assert maya.ancestry and maya.ancestry[0].relation == "father"
    r = e.advise(AdviseRequest(user_id="demo-maya", message="Putting $120k into a new token before it lists!"), record=False)
    assert r.ancestry and "Your father" in r.message and r.verdict.polarity.value == "stop"
    try:
        inherit(e.store, export_sub(e.store, "demo-kapoor"), "demo-sara")
        assert False, "non-heir must be refused"
    except InheritanceError:
        pass
    assert revoke(e.store, "demo-maya", "demo-kapoor")
    r = e.advise(AdviseRequest(user_id="demo-maya", message="Putting $120k into a new token before it lists!"), record=False)
    assert r.ancestry is None


def test_redaction_keeps_money_drops_identity():
    out = redact("Aarav Kapoor, aarav@x.ae, +971 50 123 4567, card 4111 1111 1111 1111. $150k on 2026-04-14.",
                 ["Aarav Kapoor", "Aarav", "Kapoor"])
    assert "Aarav" not in out and "@" not in out and "4111" not in out and "$150k" in out and "2026-04-14" in out


def test_goemotions_mapping_and_litellm_registered():
    limbic.set_classifier(lambda t: [{"label": "nervousness", "score": 0.9}, {"label": "neutral", "score": 0.1}])
    try:
        assert limbic.read("I'm not sure about this").dominant == "fear"
    finally:
        limbic.set_classifier(None)
    assert "litellm" in brains.REGISTRY and c.get("/v1/models").status_code == 200
