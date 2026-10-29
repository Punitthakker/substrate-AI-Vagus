import os
import tempfile

os.environ["SUBSTRATE_DB"] = os.path.join(tempfile.mkdtemp(), "api.db")
os.environ["SUBSTRATE_API_KEY"] = "test-key"
os.environ["SUBSTRATE_ADMIN_KEY"] = "admin-key"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

c = TestClient(app)


def test_health_and_console():
    assert c.get("/v1/health").json()["ok"]
    assert c.get("/").status_code == 200 and c.get("/embed.js").status_code == 200


def test_guest_genome_try_it_yourself():
    g = c.post("/v1/guest", json={"name": "Omar", "liquid_net_worth": 400000, "risk": "conservative", "candor": 4,
                                 "temperament": "boss", "holdings": [{"asset": "Bitcoin", "value": 100000, "kind": "token"}]}).json()
    uid = g["user_id"]
    assert uid.startswith("guest-")
    r = c.post("/v1/advise", json={"user_id": uid, "message": "Put another $150k into bitcoin, right?"}).json()
    assert r["verdict"]["polarity"] == "stop" and r["temperament"] == "boss"


def test_private_genomes_need_the_key():
    body = {"name": "Private", "liquid_net_worth": 1000}
    assert c.put("/v1/person/bank-client-1", json=body).status_code == 401
    assert c.put("/v1/person/bank-client-1", json=body, headers={"x-substrate-key": "test-key"}).status_code == 200


def test_outcome_endpoint_updates_genome():
    r = c.post("/v1/advise", json={"user_id": "demo-kapoor", "message": "Another $200k into this token?"}).json()
    c.post("/v1/outcome", json={"ledger_id": r["ledger_id"], "action": "ignored", "outcome_type": "pnl", "value_delta": -10000})
    p = c.get("/v1/person/demo-kapoor").json()
    assert any("$10k" in l for l in p["lessons"])


def test_multi_tenant_isolation_and_policy():
    A = {"x-substrate-key": "admin-key"}
    bank = c.post("/v1/admin/tenants", json={"name": "Gulf Private Bank",
                  "policy": {"allowed_temperaments": ["mentor", "surgeon"], "concentration_stop_pct": 15}}, headers=A).json()
    fund = c.post("/v1/admin/tenants", json={"name": "Falcon Ventures"}, headers=A).json()
    B, F = {"x-substrate-key": bank["api_key"]}, {"x-substrate-key": fund["api_key"]}
    body = {"name": "HNW Client", "liquid_net_worth": 1000000, "risk_profile": {"stated": "moderate"},
            "positions": [{"asset": "Apple", "value": 50000, "kind": "stock"}]}
    assert c.put("/v1/person/bank-001", json=body, headers=B).status_code == 200
    assert c.get("/v1/person/bank-001", headers=F).status_code == 403          # other tenant cannot see it
    assert c.get("/v1/person/bank-001").status_code == 401                     # nor can the public
    r = c.post("/v1/advise", json={"user_id": "bank-001", "message": "Put another $120k into Apple", "temperament": "boss"},
               headers=B).json()
    assert r["temperament"] in ("mentor", "surgeon")                            # bank policy bans the Boss
    assert r["verdict"]["polarity"] == "stop"                                   # 17% breaches the bank's 15% limit
    m = c.get("/v1/metrics", headers=B).json()
    assert m["scope"] == "Gulf Private Bank" and m["advice"] == 1


def test_models_and_tissues_catalogue():
    ms = c.get("/v1/models").json()["models"]
    assert {"anthropic", "nvidia", "gemini", "ollama", "vllm"} <= {m["key"] for m in ms}
    assert {t["key"] for t in c.get("/v1/tissues").json()} == {"wealth", "venture", "founder", "wellbeing", "markets"}


def test_graph_and_learning_endpoints():
    g = c.get("/v1/graph/demo-kapoor").json()
    assert g["nodes"] and g["edges"]
    L = c.get("/v1/learn/stats").json()
    assert L["sft_examples"] > 0 and "nvidia" in " ".join(L["base_models"]).lower()
    assert c.post("/v1/learn/export").status_code == 403          # dataset export is admin-only
