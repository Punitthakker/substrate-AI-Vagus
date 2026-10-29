"""Substrate API - the Vagus Engine over HTTP, multi-tenant, plus the investor console and embed widget.

Auth model (header x-substrate-key):
  admin key   SUBSTRATE_ADMIN_KEY  - create tenants, see everything
  master key  SUBSTRATE_API_KEY    - single-tenant deployments
  tenant key  sk_sub_...           - a bank / fund / platform; sees only its own genomes, uses its own policy
  no key                           - public demo genomes (demo-*) and sandboxed guests (guest-*) only
"""
from __future__ import annotations

import os
import secrets
import time
from collections import defaultdict, deque
from pathlib import Path
from typing import Literal, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from substrate import __version__, domains, temperaments
from substrate.brains import active_brain, catalogue as model_catalogue, council_members
from substrate.engine import VagusEngine
from substrate.evals import run as run_evals
from substrate.export import export_sub, verify_sub
from substrate import harness, webhooks
from substrate.progress import progress as progress_of
from substrate.inherit import InheritanceError, inherit, revoke
from substrate.markets_api import BetMath, analyze as bet_analyze, polymarket_price
from substrate.graph import build_graph, to_graphiti_episodes
from substrate.learn import build as build_dataset
from substrate.ledger import Store, verify_chain
from substrate.policy import DEFAULT, Policy
from substrate.predict import insights as person_insights
from substrate.schemas import AdviseRequest, Consent, Goal, OutcomeRequest, Person, Position, RiskProfile
from substrate.seed import DEMO_HEIRS, DEMO_USER, DEMO_USERS, seed

STATIC = Path(__file__).parent / "static"
store = Store()
seed(store)
engine = VagusEngine(store)

app = FastAPI(title="Substrate AI - Vagus Engine", version=__version__,
              description="The emotional chromosome of AI. Vagal tone changes how truth is delivered. Never whether.")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# ---------------------------------------------------------------- auth + tenancy

class Ctx(BaseModel):
    role: Literal["public", "tenant", "master", "admin"] = "public"
    tenant: Optional[dict] = None


def ctx(x_substrate_key: str | None = Header(default=None)) -> Ctx:
    if not x_substrate_key:
        return Ctx()
    admin, master = os.environ.get("SUBSTRATE_ADMIN_KEY"), os.environ.get("SUBSTRATE_API_KEY")
    if admin and secrets.compare_digest(x_substrate_key, admin):
        return Ctx(role="admin")
    if master and secrets.compare_digest(x_substrate_key, master):
        return Ctx(role="master")
    t = store.tenant_by_key(x_substrate_key)
    if t:
        return Ctx(role="tenant", tenant=t)
    raise HTTPException(401, "Invalid x-substrate-key.")


def is_public(user_id: str) -> bool:
    return user_id.startswith(("demo-", "guest-"))


def locked_down() -> bool:
    return bool(os.environ.get("SUBSTRATE_API_KEY") or os.environ.get("SUBSTRATE_ADMIN_KEY"))


def authorize(user_id: str, c: Ctx) -> Policy:
    """Returns the policy that governs this genome, or refuses access."""
    if is_public(user_id):
        return DEFAULT
    owner = store.owner(user_id)
    if c.role in ("admin", "master"):
        return _policy_of(owner)
    if c.role == "tenant":
        if owner and owner != c.tenant["id"]:
            raise HTTPException(403, "This genome belongs to another tenant.")
        return Policy(**c.tenant["policy"])
    if owner or locked_down():
        raise HTTPException(401, "Missing or invalid x-substrate-key header.")
    return DEFAULT


def _policy_of(tenant_id: str | None) -> Policy:
    if not tenant_id:
        return DEFAULT
    t = next((t for t in store.tenants() if t["id"] == tenant_id), None)
    return Policy(**t["policy"]) if t else DEFAULT


# ---------------------------------------------------------------- rate limit (public demo protection)

RATE = int(os.environ.get("SUBSTRATE_RATE_PER_MIN", "60"))
_hits: dict[str, deque] = defaultdict(deque)


@app.middleware("http")
async def rate_limit(request: Request, call_next):
    if request.method == "POST" and request.url.path.startswith("/v1/") and not request.headers.get("x-substrate-key"):
        ip = (request.headers.get("x-forwarded-for") or (request.client.host if request.client else "?")).split(",")[0].strip()
        q, t = _hits[ip], time.monotonic()
        while q and t - q[0] > 60:
            q.popleft()
        if len(q) >= RATE:
            return JSONResponse({"detail": "Slow down: rate limit reached. Try again in a minute."}, status_code=429)
        q.append(t)
    return await call_next(request)


# ---------------------------------------------------------------- system

@app.get("/v1/health")
def health():
    models = model_catalogue()
    return {"ok": True, "engine": "vagus", "version": __version__, "brain": active_brain(),
            "council": council_members(), "models_configured": sum(m["configured"] for m in models),
            "models_available": len(models), "tissues": list(domains.TISSUES), "temperaments": len(temperaments.TEMPERAMENTS),
            "demo_users": DEMO_USERS, "demo_heirs": {k: v[0] for k, v in DEMO_HEIRS.items()}}


@app.get("/v1/temperaments")
def list_temperaments():
    return temperaments.catalogue()


@app.get("/v1/tissues")
def list_tissues():
    return domains.catalogue()


@app.get("/v1/models")
def list_models():
    return {"active": active_brain(), "council": council_members(), "models": model_catalogue()}


@app.get("/v1/policy")
def get_policy(c: Ctx = Depends(ctx)):
    return c.tenant["policy"] if c.role == "tenant" else DEFAULT.model_dump()


# ---------------------------------------------------------------- genome

@app.put("/v1/person/{user_id}")
def put_person(user_id: str, person: Person, c: Ctx = Depends(ctx)):
    authorize(user_id, c)
    if c.role == "tenant" and not is_public(user_id):
        store.set_owner(user_id, c.tenant["id"])
    person.user_id = user_id
    return store.put_person(person)


@app.get("/v1/person/{user_id}")
def get_person(user_id: str, c: Ctx = Depends(ctx)):
    authorize(user_id, c)
    p = store.get_person(user_id)
    if not p:
        raise HTTPException(404, "person not found")
    return p


@app.delete("/v1/person/{user_id}")
def delete_person(user_id: str, c: Ctx = Depends(ctx)):
    authorize(user_id, c)
    if user_id.startswith("demo-"):
        raise HTTPException(400, "Use POST /v1/demo/reset for demo genomes.")
    store.delete_person(user_id)
    return {"ok": True, "deleted": user_id}


class Holding(BaseModel):
    asset: str = Field(min_length=1, max_length=60)
    value: float = Field(ge=0, le=1e12)
    kind: Literal["token", "stock", "fund", "property", "cash", "bond", "other"] = "other"


class GuestRequest(BaseModel):
    name: str = Field("Guest", max_length=60)
    domain: Literal["wealth", "venture", "founder", "wellbeing", "markets", "trading"] = "wealth"
    liquid_net_worth: Optional[float] = Field(None, gt=0, le=1e12)
    currency: Literal["USD", "AED", "INR"] = "USD"
    risk: Literal["conservative", "moderate", "aggressive"] = "moderate"
    candor: int = Field(3, ge=1, le=5)
    temperament: str = "mentor"
    holdings: list[Holding] = Field(default_factory=list, max_length=8)
    goals: list[str] = Field(default_factory=list, max_length=4)
    profile: dict = Field(default_factory=dict)


@app.post("/v1/guest")
def create_guest(g: GuestRequest):
    """Try it on yourself: a sandboxed genome in any tissue, open without a key, never mixed with client data."""
    uid = f"guest-{secrets.token_hex(4)}"
    allowed = {"fund_size", "thesis", "cash_in_bank", "monthly_burn", "mrr", "company", "support_contacts",
               "bankroll", "max_bet_fraction"}
    p = Person(user_id=uid, name=g.name.strip() or "Guest", domain=g.domain, consent=Consent(candor_level=g.candor),
               temperament=temperaments.get(g.temperament).key, risk_profile=RiskProfile(stated=g.risk),
               liquid_net_worth=g.liquid_net_worth, currency=g.currency,
               positions=[Position(**h.model_dump()) for h in g.holdings],
               goals=[Goal(name=x[:80], priority=i + 1) for i, x in enumerate(g.goals) if x.strip()],
               profile={k: v for k, v in g.profile.items() if k in allowed})
    store.put_person(p)
    return {"user_id": uid, "person": p}


# ---------------------------------------------------------------- the engine

@app.post("/v1/advise")
def advise(req: AdviseRequest, c: Ctx = Depends(ctx)):
    policy = authorize(req.user_id, c)
    try:
        r = engine.advise(req, policy=policy)
    except KeyError as e:
        raise HTTPException(404, str(e))
    webhooks.from_advice(store, r)
    return r


@app.post("/v1/advise/compare")
def compare(req: AdviseRequest, c: Ctx = Depends(ctx)):
    policy = authorize(req.user_id, c)
    try:
        return engine.compare(req, policy=policy)
    except KeyError as e:
        raise HTTPException(404, str(e))


@app.post("/v1/markets/analyze")
def markets_analyze(b: BetMath):
    """Stateless bet arithmetic: price to probability, parlay legs, round robins, fees, Kelly, bankroll share.
    No genome, no personal data. For platforms that want an honest pre-bet panel."""
    return bet_analyze(b)


class VolRequest(BaseModel):
    pair: str = Field("XAUUSD", max_length=7)
    price: Optional[float] = Field(None, gt=0)
    prices: list[float] = Field(default_factory=list, max_length=5000)
    horizon_days: float = Field(5, gt=0, le=252)
    leverage: float = Field(1, ge=1, le=1000)
    stop_pct: Optional[float] = Field(None, gt=0, le=50)
    notional: Optional[float] = Field(None, gt=0)
    events: Optional[list[dict]] = Field(None, max_length=8)
    event_week: bool = False
    live: bool = False
    text: str = Field("", max_length=4000, description="Optional trader message for the behavioural read")


@app.post("/v1/volatility/analyze")
def volatility_analyze(v: VolRequest):
    """Stateless FX and gold volatility: GARCH/EWMA, ranges, stop-out odds, event combinatorics, trader biases.
    Direction is never forecast."""
    from substrate import behavior, volatility
    for e in v.events or []:
        if not isinstance(e, dict) or not e.get("outcomes") or len(e["outcomes"]) > 6:
            raise HTTPException(422, "Each event needs 1-6 outcomes: {name, outcomes: [{label, p, vol_mult}]}")
    out = volatility.analyze(v.pair, v.price, v.prices, v.horizon_days, v.leverage, v.stop_pct, v.notional,
                             v.events, live=v.live, event_week=v.event_week)
    if v.text:
        out["behavior"] = behavior.read(v.text)
    return out


@app.get("/v1/markets/polymarket/{slug}")
def markets_polymarket(slug: str, outcome: str = "Yes"):
    """Live price for a Polymarket market slug via the public Gamma API (best effort)."""
    try:
        return polymarket_price(slug, outcome)
    except Exception as e:
        raise HTTPException(502, f"Polymarket price unavailable: {type(e).__name__}")


@app.post("/v1/outcome")
def outcome(req: OutcomeRequest, c: Ctx = Depends(ctx)):
    ev = store.get_event(req.ledger_id)
    if not ev:
        raise HTTPException(404, "ledger entry not found")
    authorize(ev["user_id"], c)
    try:
        written = engine.record_outcome(req)
    except KeyError as e:
        raise HTTPException(404, str(e))
    last = store.events(ev["user_id"])[-1]
    if last["kind"] == "pact-broken":
        webhooks.emit(store, ev["user_id"], "pact-broken", {"pact_id": last["payload"]["pact_id"],
                                                            "domain": last["payload"]["domain"]})
    return {"ok": True, "events": written}


# ---------------------------------------------------------------- ledger, insight, inheritance

@app.get("/v1/ledger/{user_id}")
def ledger(user_id: str, limit: int = 50, c: Ctx = Depends(ctx)):
    authorize(user_id, c)
    events = store.events(user_id)
    return {"user_id": user_id, "verified": verify_chain(events), "length": len(events),
            "head": events[-1]["hash"] if events else None, "events": events[-limit:]}


@app.get("/v1/insights/{user_id}")
def insights(user_id: str, c: Ctx = Depends(ctx)):
    authorize(user_id, c)
    p = store.get_person(user_id)
    if not p:
        raise HTTPException(404, "person not found")
    return person_insights(p, store.history(user_id))


@app.get("/v1/export/{user_id}")
def export(user_id: str, c: Ctx = Depends(ctx)):
    authorize(user_id, c)
    try:
        doc = export_sub(store, user_id)
    except KeyError:
        raise HTTPException(404, "person not found")
    return JSONResponse(doc, headers={"content-disposition": f'attachment; filename="{user_id}.sub"'})


@app.post("/v1/export/verify")
def verify(doc: dict):
    return verify_sub(doc)


# ---------------------------------------------------------------- invites, progress, harness

class InviteCreate(BaseModel):
    tissue: Literal["wealth", "venture", "founder", "wellbeing", "markets", "trading"] = "wealth"
    label: str = Field("Substrate private preview", max_length=80)
    max_uses: int = Field(25, ge=1, le=10_000)
    days: int = Field(14, ge=1, le=365)


def can_invite(c: Ctx) -> bool:
    return c.role in ("admin", "master") or not locked_down()


@app.post("/v1/invites")
def create_invite(req: InviteCreate, c: Ctx = Depends(ctx)):
    """Create a shareable test link. Admin/master key once the deployment is locked down."""
    if not can_invite(c):
        raise HTTPException(403, "Invites need the admin or master key.")
    from datetime import datetime, timedelta, timezone
    exp = (datetime.now(timezone.utc) + timedelta(days=req.days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    code = store.create_invite(req.tissue, req.label, req.max_uses, exp)
    return {**store.invite(code), "path": f"/?invite={code}"}


@app.get("/v1/invites")
def list_invites(c: Ctx = Depends(ctx)):
    if not can_invite(c):
        raise HTTPException(403, "Invites need the admin or master key.")
    return store.invites()


@app.get("/v1/invite/{code}")
def invite_info(code: str):
    inv = store.invite(code)
    if not inv:
        raise HTTPException(404, "Unknown invite.")
    return {k: inv[k] for k in ("code", "tissue", "label", "remaining", "valid", "expires")}


class Redeem(BaseModel):
    name: str = Field("Guest", max_length=40)


@app.post("/v1/invite/{code}/redeem")
def redeem_invite(code: str, r: Redeem):
    """Each invitee gets a private sandboxed genome in the invite's tissue, seeded from the demo profile."""
    inv = store.invite(code)
    if not inv or not inv["valid"] or not store.use_invite(code):
        raise HTTPException(410, "This invite has expired or is used up.")
    base = store.get_person(DEMO_USERS[inv["tissue"]])
    uid = f"guest-{secrets.token_hex(4)}"
    p = base.model_copy(deep=True) if base else Person(domain=inv["tissue"])
    p.user_id, p.name, p.lessons, p.adherence, p.ancestry = uid, (r.name.strip() or "Guest")[:40], [], {}, []
    p.biases = [b.model_copy(update={"evidence": []}) for b in p.biases]
    p.consent.allow_training, p.consent.inheritance.heirs = False, []
    if "support_contacts" in p.profile:
        p.profile["support_contacts"] = []
    store.put_person(p)
    return {"user_id": uid, "tissue": inv["tissue"], "label": inv["label"], "person": p}


# ---------------------------------------------------------------- legacy vault

class LetterRequest(BaseModel):
    from_user: str
    to_user: str
    relation: str = Field("family", max_length=30)
    title: str = Field(..., min_length=1, max_length=120)
    body: str = Field(..., min_length=1, max_length=8000)
    release_type: Literal["date", "age", "moment", "first"] = "moment"
    release_value: str = Field("any-stop", max_length=40)


@app.post("/v1/legacy/letter")
def write_letter(req: LetterRequest, c: Ctx = Depends(ctx)):
    """Seal a letter for an heir. It opens on a date, an age, or the moment they need it."""
    authorize(req.from_user, c)
    authorize(req.to_user, c)
    from substrate import legacy
    elder = store.get_person(req.from_user)
    if not elder or not store.get_person(req.to_user):
        raise HTTPException(404, "Both the author and the heir need a genome.")
    if req.to_user not in elder.consent.inheritance.heirs:
        raise HTTPException(403, f"'{req.to_user}' is not a named heir of {req.from_user}.")
    lt = legacy.write(store, legacy.Letter(from_user=req.from_user, from_name=(elder.name or "").split()[0] or "Family",
                                           to_user=req.to_user, relation=req.relation, title=req.title, body=req.body,
                                           release=legacy.Release(type=req.release_type, value=req.release_value)))
    return {"ok": True, "letter": lt.public(), "seal": lt.seal}


@app.get("/v1/legacy/{user_id}")
def legacy_vault(user_id: str, c: Ctx = Depends(ctx)):
    """Letters to this person (sealed ones show only title and release) and letters they have written."""
    authorize(user_id, c)
    from substrate import legacy
    return {"to": [l.public() for l in legacy.to(store, user_id) if not l.revoked],
            "by": [l.model_dump() for l in legacy.by(store, user_id)],
            "moments": sorted(legacy.MOMENTS)}


@app.delete("/v1/legacy/{author}/{letter_id}")
def revoke_letter(author: str, letter_id: str, c: Ctx = Depends(ctx)):
    authorize(author, c)
    from substrate import legacy
    if not legacy.revoke(store, letter_id, author):
        raise HTTPException(404, "No sealed, undelivered letter with that id.")
    return {"ok": True}


@app.get("/v1/memory/{user_id}")
def memory_view(user_id: str, c: Ctx = Depends(ctx)):
    """The genome as plain-language memories (Mem0, Letta, any agent memory) plus a Letta-style core block."""
    authorize(user_id, c)
    from substrate import memory_bridge
    p = store.get_person(user_id)
    if not p:
        raise HTTPException(404, user_id)
    return {"user_id": user_id, "memories": memory_bridge.memories(p), "core_block": memory_bridge.core_block(p)}


@app.post("/v1/memory/{user_id}/mem0")
def memory_push_mem0(user_id: str, c: Ctx = Depends(ctx)):
    authorize(user_id, c)
    from substrate import memory_bridge
    p = store.get_person(user_id)
    if not p:
        raise HTTPException(404, user_id)
    try:
        return {"ok": True, "pushed": memory_bridge.push_mem0(p)}
    except RuntimeError as e:
        raise HTTPException(501, str(e))


class PactRequest(BaseModel):
    user_id: str
    ledger_id: str = ""
    hours: Optional[float] = Field(None, gt=0, le=24 * 30)


@app.post("/v1/pact")
def make_pact(req: PactRequest, c: Ctx = Depends(ctx)):
    """The human makes a promise to their future self. Substrate holds them to it, kindly."""
    authorize(req.user_id, c)
    from substrate import pacts
    person = store.get_person(req.user_id)
    if not person:
        raise HTTPException(404, req.user_id)
    p = pacts.make(store, person, req.ledger_id, person.domain, req.hours)
    return {"ok": True, "pact": p, "local_until": pacts.local_hhmm(person, p.until)}


@app.get("/v1/pact/{user_id}")
def list_pacts(user_id: str, c: Ctx = Depends(ctx)):
    authorize(user_id, c)
    from substrate import pacts
    person = store.get_person(user_id)
    if not person:
        raise HTTPException(404, user_id)
    pacts.sweep(store, person)
    return [p.model_dump() | {"hours_left": round(pacts.hours_left(p), 1)} for p in pacts.pacts(person)]


@app.delete("/v1/pact/{user_id}/{pact_id}")
def release_pact(user_id: str, pact_id: str, c: Ctx = Depends(ctx)):
    """Release is always allowed, and always recorded."""
    authorize(user_id, c)
    from substrate import pacts
    person = store.get_person(user_id)
    p = person and pacts.close(store, person, pact_id, "released")
    if not p:
        raise HTTPException(404, "No active pact with that id.")
    return {"ok": True, "pact": p}


@app.get("/v1/progress/{user_id}")
def get_progress(user_id: str, c: Ctx = Depends(ctx)):
    authorize(user_id, c)
    try:
        return progress_of(store, user_id)
    except KeyError as e:
        raise HTTPException(404, str(e))


@app.get("/v1/harness/layers")
def harness_layers():
    return [{"layer": k, "what": v} for k, v in harness.LAYERS]


@app.post("/v1/chat/completions")
def chat_completions(body: dict, c: Ctx = Depends(ctx),
                     x_substrate_user: Optional[str] = Header(None), x_substrate_mode: Optional[str] = Header(None)):
    """OpenAI-compatible harness. Point any OpenAI SDK's base_url at Substrate."""
    uid = x_substrate_user or body.get("user")
    if not uid or not store.get_person(uid):
        if uid and not uid.startswith("guest-"):
            authorize(uid, c)   # named but unknown genome: refuse rather than invent
        uid = harness.ensure_user(store, uid, harness.tissue_from_model(body.get("model")))
    policy = authorize(uid, c)
    mode = (x_substrate_mode or body.get("substrate_mode") or "substrate").lower()
    try:
        out = harness.chat(engine, body, uid, mode, policy)
    except ValueError as e:
        raise HTTPException(400, str(e))
    if body.get("stream"):
        import json as _json
        from fastapi.responses import StreamingResponse
        chunk = {"id": out["id"], "object": "chat.completion.chunk", "created": out["created"], "model": out["model"],
                 "choices": [{"index": 0, "delta": {"role": "assistant", "content": out["choices"][0]["message"]["content"]},
                              "finish_reason": "stop"}], "substrate": out["substrate"]}
        return StreamingResponse(iter([f"data: {_json.dumps(chunk)}\n\n", "data: [DONE]\n\n"]),
                                 media_type="text/event-stream")
    return out


@app.get("/v1/models/openai")
def openai_models():
    """OpenAI-style model list so SDKs and tools can discover the harness."""
    return {"object": "list", "data": [{"id": m, "object": "model", "owned_by": "substrate"} for m in
                                      ["substrate", "substrate-wealth", "substrate-venture", "substrate-founder",
                                       "substrate-wellbeing", "substrate-markets"]]}


class InheritRequest(BaseModel):
    heir_id: str
    relation: str = Field("family", max_length=30)
    sub: Optional[dict] = Field(None, description="A .sub document. Omit to inherit from the elder's live genome.")


@app.post("/v1/inherit/{elder_id}")
def inherit_genome(elder_id: str, req: InheritRequest, c: Ctx = Depends(ctx)):
    """Pass a genome down: the heir receives the elder's values and the lessons they paid for (per consent)."""
    authorize(req.heir_id, c)
    try:
        if req.sub is None:
            authorize(elder_id, c)
            doc = export_sub(store, elder_id)
        else:
            doc = req.sub
        a = inherit(store, doc, req.heir_id, req.relation)
    except KeyError as e:
        raise HTTPException(404, str(e))
    except InheritanceError as e:
        raise HTTPException(403, str(e))
    return {"ok": True, "heir": req.heir_id, "ancestor": a}


@app.delete("/v1/inherit/{elder_id}/{heir_id}")
def revoke_inheritance(elder_id: str, heir_id: str, c: Ctx = Depends(ctx)):
    authorize(heir_id, c)
    return {"ok": revoke(store, heir_id, elder_id)}


@app.get("/v1/graph/{user_id}")
def genome_graph(user_id: str, c: Ctx = Depends(ctx)):
    authorize(user_id, c)
    try:
        return build_graph(store, user_id)
    except KeyError:
        raise HTTPException(404, "person not found")


@app.get("/v1/graph/{user_id}/graphiti")
def graphiti_episodes(user_id: str, c: Ctx = Depends(ctx)):
    authorize(user_id, c)
    return {"user_id": user_id, "episodes": to_graphiti_episodes(store, user_id)}


# ---------------------------------------------------------------- learning

@app.get("/v1/learn/stats")
def learn_stats():
    """What the next training round would learn from (consented public genomes + self-distillation)."""
    d = build_dataset(store, store.users(public=True))
    return {**d["stats"], "base_models": ["Qwen/Qwen2.5-7B-Instruct", "meta-llama/Llama-3.1-8B-Instruct",
                                         "mistralai/Mistral-Nemo-Instruct-2407", "nvidia/Llama-3.1-Nemotron-70B-Instruct-HF"],
            "pipeline": ["consented ledger", "outcome weighting", "SFT (LoRA)", "DPO: honest > sycophantic, calibrated > fearful",
                         "merge", "serve on vLLM / NVIDIA NIM", "evals: native honesty"],
            "sample": {"sft": d["sft"][0] if d["sft"] else None, "dpo": d["dpo"][0] if d["dpo"] else None}}


@app.post("/v1/learn/export")
def learn_export(c: Ctx = Depends(ctx)):
    if c.role not in ("admin", "master"):
        raise HTTPException(403, "Admin key required.")
    d = build_dataset(store)
    return {"stats": d["stats"], "sft": d["sft"], "dpo": d["dpo"]}


# ---------------------------------------------------------------- enterprise

@app.get("/v1/metrics")
def metrics(c: Ctx = Depends(ctx)):
    if c.role == "tenant":
        return {"scope": c.tenant["name"], **store.metrics(store.users(c.tenant["id"]))}
    if c.role in ("admin", "master"):
        return {"scope": "all", **store.metrics(store.users())}
    return {"scope": "public demo", **store.metrics(store.users(public=True))}


class TenantRequest(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    policy: Policy = Field(default_factory=Policy)


@app.post("/v1/admin/tenants")
def create_tenant(t: TenantRequest, c: Ctx = Depends(ctx)):
    if c.role != "admin":
        raise HTTPException(403, "Admin key required.")
    tid, key = store.create_tenant(t.name, t.policy.model_dump())
    return {"tenant_id": tid, "name": t.name, "api_key": key, "note": "Store this key now. It is shown once."}


@app.get("/v1/admin/tenants")
def list_tenants(c: Ctx = Depends(ctx)):
    if c.role != "admin":
        raise HTTPException(403, "Admin key required.")
    return store.tenants()


class WebhookRequest(BaseModel):
    url: str = Field(..., pattern=r"^https://", max_length=500)
    events: list[str] = Field(default_factory=lambda: ["escalation", "safety", "pact-broken"])


@app.put("/v1/tenant/webhook")
def set_webhook(req: WebhookRequest, c: Ctx = Depends(ctx)):
    """Register this tenant's webhook. The signing secret is shown once."""
    if c.role != "tenant":
        raise HTTPException(403, "Tenant key required.")
    secret = webhooks.register(store, c.tenant["id"], req.url, req.events)
    return {"ok": True, "url": req.url, "events": sorted(set(req.events) & webhooks.EVENTS), "secret": secret,
            "verify": "hmac_sha256(secret, raw_body) == x-substrate-signature[7:]"}


@app.get("/v1/admin/webhooks/log")
def webhook_log(c: Ctx = Depends(ctx)):
    if c.role not in ("admin", "master"):
        raise HTTPException(403, "Admin or master key required.")
    return list(webhooks.LOG)


@app.put("/v1/tenant/policy")
def set_policy(policy: Policy, c: Ctx = Depends(ctx)):
    if c.role != "tenant":
        raise HTTPException(403, "Tenant key required.")
    store.set_policy(c.tenant["id"], policy.model_dump())
    return {"ok": True, "policy": policy}


# ---------------------------------------------------------------- proof

@app.post("/v1/evals/run")
def evals():
    return run_evals()


@app.post("/v1/demo/reset")
def demo_reset():
    seed(store, reset=True)
    return {"ok": True, "users": DEMO_USERS}


# ---------------------------------------------------------------- console + embed

@app.get("/", include_in_schema=False)
def console():
    return FileResponse(STATIC / "index.html")


app.mount("/static", StaticFiles(directory=STATIC), name="static")


# ---------------------------------------------------------------- embedded SDK (publishable keys)

TISSUE = Literal["wealth", "venture", "founder", "wellbeing", "markets", "trading"]


class PkCreate(BaseModel):
    origins: list[str] = Field(..., min_length=1, max_length=20, description='e.g. ["app.mybank.com", "*.mybank.com"]')
    tissue: TISSUE = "wealth"
    label: str = Field("web", max_length=60)


@app.post("/v1/embed/keys", tags=["embed"])
def create_pk(req: PkCreate, c: Ctx = Depends(ctx)):
    """Create a publishable key (pk_live_...) for the browser SDK, locked to your origins. Tenant key required."""
    if c.role != "tenant":
        raise HTTPException(403, "Tenant key required. Admins create a tenant first via /v1/admin/tenants.")
    from substrate import embed
    pk = embed.create(store, c.tenant["id"], req.origins, req.tissue, req.label)
    return {"pk": pk, "origins": req.origins, "tissue": req.tissue,
            "snippet": f'<script src="https://YOUR-SUBSTRATE-HOST/sdk.js" data-pk="{pk}" data-user="YOUR_USER_ID"></script>'}


@app.get("/v1/embed/keys", tags=["embed"])
def list_pks(c: Ctx = Depends(ctx)):
    if c.role != "tenant":
        raise HTTPException(403, "Tenant key required.")
    from substrate import embed
    return embed.list_for(store, c.tenant["id"])


def _pk_ctx(request: Request, pk: str | None, tissue_hint: str | None) -> tuple[str, str, Policy]:
    """Resolve a publishable key to (tenant id, tissue, policy), enforcing origins."""
    from substrate import embed
    if not pk:
        raise HTTPException(401, "Missing x-substrate-pk header.")
    if pk == embed.DEMO_PK:
        if locked_down() and not os.environ.get("SUBSTRATE_DEMO_PK"):
            raise HTTPException(403, "pk_demo is disabled on this deployment.")
        return "demo", tissue_hint or "wealth", DEFAULT
    k = embed.lookup(store, pk)
    if not k:
        raise HTTPException(401, "Unknown or revoked publishable key.")
    if not embed.origin_ok(k["origins"], request.headers.get("origin")):
        raise HTTPException(403, "Origin not allowed for this key.")
    return k["tenant_id"], k["tissue"], _policy_of(k["tenant_id"])


class EmbedAdvise(BaseModel):
    user: str = Field(..., min_length=1, max_length=200, description="Your platform's user id (hashed, never stored raw)")
    message: str = Field("", max_length=4000, description="Free text from the user, if any")
    context: dict = Field(default_factory=dict, description="What is on screen: stake, price, side, leverage, instrument...")
    tissue: Optional[TISSUE] = None
    temperament: Optional[str] = None
    thread: list[dict] = Field(default_factory=list, max_length=20)


def _embed_user(tenant: str, tissue: str, external: str) -> str:
    from substrate import embed
    uid = embed.user_id(tenant, external, tissue)
    if not store.get_person(uid):
        base = store.get_person(DEMO_USERS.get(tissue, "")) if tenant == "demo" else None
        p = base.model_copy(deep=True) if base else Person(domain=tissue)
        p.user_id, p.name, p.domain = uid, "Member", tissue
        p.lessons, p.adherence, p.ancestry, p.pacts = [], {}, [], []
        p.biases = [b.model_copy(update={"evidence": []}) for b in p.biases] if base else []
        p.consent.allow_training, p.consent.inheritance.heirs = False, []
        if "support_contacts" in p.profile:
            p.profile["support_contacts"] = []
        store.put_person(p)
        if tenant != "demo":
            store.set_owner(uid, tenant)
    return uid


@app.post("/v1/embed/advise", tags=["embed"])
def embed_advise(req: EmbedAdvise, request: Request, x_substrate_pk: Optional[str] = Header(None)):
    """The browser SDK's single call: the honest pause before a click."""
    from substrate import embed
    from substrate.schemas import Turn
    tenant, tissue, policy = _pk_ctx(request, x_substrate_pk, req.tissue)
    if req.tissue and req.tissue != tissue:
        if tenant != "demo" and req.tissue not in policy.domains:
            raise HTTPException(403, f"Tissue '{req.tissue}' is not enabled for this tenant.")
        tissue = req.tissue
    uid = _embed_user(tenant, tissue, req.user)
    msg = embed.context_message(tissue, req.context, req.message) if req.context else (req.message or "Checking this.")
    thread = [Turn(role="user" if t.get("role") == "user" else "substrate", content=str(t.get("content", ""))[:4000])
              for t in req.thread if t.get("content")]
    r = engine.advise(AdviseRequest(user_id=uid, message=msg, thread=thread, temperament=req.temperament), policy=policy)
    webhooks.from_advice(store, r)
    return {**embed.compact(r), "read_as": msg}


class EmbedOutcome(BaseModel):
    user: str
    ledger_id: str
    action: Literal["followed", "ignored", "partial"]


@app.post("/v1/embed/outcome", tags=["embed"])
def embed_outcome(req: EmbedOutcome, request: Request, x_substrate_pk: Optional[str] = Header(None)):
    """Closes the loop from the widget: Cancel means followed, Proceed anyway means ignored."""
    from substrate import embed
    tenant, tissue, _ = _pk_ctx(request, x_substrate_pk, None)
    ev = store.get_event(req.ledger_id)
    if not ev or ev["user_id"] not in {embed.user_id(tenant, req.user, t) for t in domains.TISSUES}:
        raise HTTPException(404, "No such advice for this user.")
    engine.record_outcome(OutcomeRequest(ledger_id=req.ledger_id, action=req.action))
    return {"ok": True}


class EmbedPact(BaseModel):
    user: str
    ledger_id: str = ""
    tissue: Optional[TISSUE] = None


@app.post("/v1/embed/pact", tags=["embed"])
def embed_pact(req: EmbedPact, request: Request, x_substrate_pk: Optional[str] = Header(None)):
    from substrate import embed, pacts
    tenant, tissue, _ = _pk_ctx(request, x_substrate_pk, req.tissue)
    person = store.get_person(embed.user_id(tenant, req.user, req.tissue or tissue))
    if not person:
        raise HTTPException(404, "Unknown user.")
    p = pacts.make(store, person, req.ledger_id, person.domain)
    return {"ok": True, "pact": p, "local_until": pacts.local_hhmm(person, p.until)}


@app.get("/sdk.js", include_in_schema=False)
def sdk_js():
    return FileResponse(STATIC / "sdk.js", media_type="application/javascript")


@app.get("/developers", include_in_schema=False)
def developers():
    return FileResponse(STATIC / "developers.html")


@app.get("/embed.js", include_in_schema=False)
def embed():
    return FileResponse(STATIC / "embed.js", media_type="application/javascript")
