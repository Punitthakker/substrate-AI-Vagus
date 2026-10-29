"""Go-live: accounts and sessions, private genomes, profile editing, heirs by email."""
from fastapi.testclient import TestClient

from app.main import app

c = TestClient(app)


def test_signup_login_session_and_privacy():
    r = c.post("/v1/auth/signup", json={"email": "Lina@Example.com", "password": "correct horse battery", "name": "Lina",
                                       "tissue": "trading"})
    assert r.status_code == 200, r.text
    tok, uid = r.json()["token"], r.json()["user_id"]
    H = {"authorization": f"Bearer {tok}"}
    assert c.get("/v1/auth/me", headers=H).json()["email"] == "lina@example.com"
    assert c.get(f"/v1/person/{uid}").status_code == 401                         # private without a session
    assert c.get("/v1/person/demo-farah", headers=H).status_code == 200          # demos stay public
    a = c.post("/v1/advise", headers=H, json={"user_id": uid, "message": "Will gold go up next week?"}).json()
    assert a["label"] == "NO CALL"
    assert c.post("/v1/auth/signup", json={"email": "lina@example.com", "password": "another long one"}).status_code == 400
    # a second account cannot read the first
    t2 = c.post("/v1/auth/signup", json={"email": "omar@example.com", "password": "omar password 1"}).json()["token"]
    assert c.get(f"/v1/person/{uid}", headers={"authorization": f"Bearer {t2}"}).status_code == 403
    # sign out everywhere kills the token
    assert c.post("/v1/auth/logout", headers=H).json()["ok"]
    assert c.get("/v1/auth/me", headers=H).status_code == 401


def test_lockout_after_failed_attempts():
    c.post("/v1/auth/signup", json={"email": "lock@example.com", "password": "the right password"})
    for _ in range(5):
        assert c.post("/v1/auth/login", json={"email": "lock@example.com", "password": "wrong"}).status_code == 401
    r = c.post("/v1/auth/login", json={"email": "lock@example.com", "password": "the right password"})
    assert r.status_code == 401 and "Too many attempts" in r.json()["detail"]


def test_profile_patch_and_heir_by_email():
    pa = c.post("/v1/auth/signup", json={"email": "father@example.com", "password": "father password 1", "name": "Karim"}).json()
    ch = c.post("/v1/auth/signup", json={"email": "daughter@example.com", "password": "daughter password 1", "name": "Noor"}).json()
    HP = {"authorization": f"Bearer {pa['token']}"}
    p = c.patch(f"/v1/person/{pa['user_id']}", headers=HP, json={
        "values": ["family", "patience"], "liquid_net_worth": 500000, "risk": "moderate",
        "holdings": [{"asset": "MOONX", "value": 200000, "kind": "token"}, {"asset": "Cash", "value": 300000, "kind": "cash"}],
        "heirs": ["email:daughter@example.com"], "inheritance_scope": "values+ledger", "profile": {"evil": 1, "region": "AE"}}).json()
    assert p["values"] == ["family", "patience"] and "evil" not in p["profile"] and p["profile"]["region"] == "AE"
    lt = c.post("/v1/legacy/letter", headers=HP, json={"from_user": pa["user_id"], "to_user": ch["user_id"],
                "title": "For the day you go all in", "body": "Noor, wait one night.", "release_type": "moment",
                "release_value": "concentration"})
    assert lt.status_code == 200, lt.text
    inh = c.post(f"/v1/inherit/{pa['user_id']}", headers=HP, json={"heir_id": ch["user_id"], "relation": "father"})
    assert inh.status_code == 200, inh.text
