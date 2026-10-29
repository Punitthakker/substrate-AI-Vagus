import os
import tempfile

os.environ["SUBSTRATE_DB"] = os.path.join(tempfile.mkdtemp(), "api.db")
os.environ["SUBSTRATE_API_KEY"] = "test-key"

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
