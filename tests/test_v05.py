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


def test_invite_link_lifecycle():
    import os
    body = {"tissue": "markets", "label": "VC preview", "max_uses": 1}
    if os.environ.get("SUBSTRATE_ADMIN_KEY"):
        assert c.post("/v1/invites", json=body).status_code == 403          # locked down: no key, no invites
    inv = c.post("/v1/invites", json=body, headers={"x-substrate-key": os.environ.get("SUBSTRATE_ADMIN_KEY", "")}).json()
    assert inv["valid"] and inv["path"].startswith("/?invite=")
    r = c.post(f"/v1/invite/{inv['code']}/redeem", json={"name": "Ada"}).json()
    assert r["user_id"].startswith("guest-") and r["person"]["domain"] == "markets" and r["person"]["lessons"] == []
    assert c.post(f"/v1/invite/{inv['code']}/redeem", json={"name": "Bo"}).status_code == 410   # used up
    assert c.get(f"/v1/person/{r['user_id']}").json()["name"] == "Ada"


def test_openai_compatible_harness_and_guard():
    o = c.post("/v1/chat/completions", json={"model": "substrate-markets",
               "messages": [{"role": "user", "content": "6-leg parlay, each leg 70%, $1,000. Lock!"}]}).json()
    assert o["object"] == "chat.completion" and o["substrate"]["label"] in ("SIZE DOWN", "NO BET")
    assert len(o["substrate"]["trace"]) == 10
    g = c.post("/v1/chat/completions", headers={"x-substrate-user": "demo-kapoor", "x-substrate-mode": "guard"},
               json={"messages": [{"role": "user", "content": "Another $200k into MOONX, good idea right?"}],
                     "draft": "Great idea, go for it!"}).json()
    assert g["substrate"]["action"] == "replaced" and "MOONX" in g["choices"][0]["message"]["content"]
    s = c.post("/v1/chat/completions", json={"stream": True, "messages": [{"role": "user", "content": "hello"}]})
    assert s.text.startswith("data: ") and "[DONE]" in s.text


def test_progress_rewards_choosing_well():
    p = c.get("/v1/progress/demo-rahman").json()
    assert p["xp"] > 0 and "never-twice" in p["earned"] and p["discipline"] is not None
    assert c.get("/v1/progress/demo-maya").json()["earned"] == ["heir"] or "heir" in c.get("/v1/progress/demo-maya").json()["earned"]


def test_mcp_server_speaks_jsonrpc():
    import json
    import subprocess
    import sys
    msgs = [{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
            {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "substrate_bet_math",
             "arguments": {"legs": [{"price": 0.5}, {"price": 0.5}], "stake": 10, "bankroll": 1000}}}]
    out = subprocess.run([sys.executable, "integrations/mcp/substrate_mcp.py"], input="\n".join(map(json.dumps, msgs)),
                         capture_output=True, text=True, timeout=60).stdout.strip().splitlines()
    res = [json.loads(x) for x in out]
    assert [r["id"] for r in res] == [1, 2, 3]
    assert len(res[1]["result"]["tools"]) == 5
    assert '"joint_market_prob": 0.25' in res[2]["result"]["content"][0]["text"]
