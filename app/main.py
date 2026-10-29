"""Substrate API - the Vagus Engine over HTTP, plus the investor console and the embed widget."""
from __future__ import annotations

import os
import secrets
import time
from collections import defaultdict, deque
from pathlib import Path
from typing import Literal

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, Field
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from substrate import __version__, temperaments
from substrate.brains import active_brain
from substrate.engine import VagusEngine
from substrate.evals import run as run_evals
from substrate.export import export_sub, verify_sub
from substrate.ledger import Store, verify_chain
from substrate.schemas import AdviseRequest, OutcomeRequest, Person
from substrate.seed import DEMO_USER, seed

STATIC = Path(__file__).parent / "static"
store = Store()
seed(store)
engine = VagusEngine(store)

app = FastAPI(title="Substrate AI - Vagus Engine", version=__version__,
              description="The emotional chromosome of AI. Vagal tone changes how truth is delivered. Never whether.")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def is_public(user_id: str) -> bool:
    return user_id == DEMO_USER or user_id.startswith("guest-")


def guard(user_id: str, key: str | None) -> None:
    """Optional API key. The demo genome and sandboxed guest genomes stay open; everything else is protected."""
    required = os.environ.get("SUBSTRATE_API_KEY")
    if required and not is_public(user_id) and key != required:
        raise HTTPException(401, "Missing or invalid x-substrate-key header.")


# ---------------------------------------------------------------- rate limit (public demo protection)
RATE = int(os.environ.get("SUBSTRATE_RATE_PER_MIN", "40"))
_hits: dict[str, deque] = defaultdict(deque)


@app.middleware("http")
async def rate_limit(request: Request, call_next):
    if request.method == "POST" and request.url.path.startswith("/v1/"):
        ip = (request.headers.get("x-forwarded-for") or (request.client.host if request.client else "?")).split(",")[0].strip()
        q, t = _hits[ip], time.monotonic()
        while q and t - q[0] > 60:
            q.popleft()
        if len(q) >= RATE:
            return JSONResponse({"detail": "Slow down: rate limit reached. Try again in a minute."}, status_code=429)
        q.append(t)
    return await call_next(request)


def keyhdr(x_substrate_key: str | None = Header(default=None)) -> str | None:
    return x_substrate_key


# ---------------------------------------------------------------- system

@app.get("/v1/health")
def health():
    return {"ok": True, "engine": "vagus", "version": __version__, "brain": active_brain(),
            "temperaments": len(temperaments.TEMPERAMENTS), "demo_user": DEMO_USER}


@app.get("/v1/temperaments")
def list_temperaments():
    return temperaments.catalogue()


# ---------------------------------------------------------------- genome

@app.put("/v1/person/{user_id}")
def put_person(user_id: str, person: Person, key=Depends(keyhdr)):
    guard(user_id, key)
    person.user_id = user_id
    return store.put_person(person)


@app.get("/v1/person/{user_id}")
def get_person(user_id: str, key=Depends(keyhdr)):
    guard(user_id, key)
    p = store.get_person(user_id)
    if not p:
        raise HTTPException(404, "person not found")
    return p


class Holding(BaseModel):
    asset: str = Field(min_length=1, max_length=60)
    value: float = Field(ge=0, le=1e12)
    kind: Literal["token", "stock", "fund", "property", "cash", "bond", "other"] = "other"


class GuestRequest(BaseModel):
    name: str = Field("Guest", max_length=60)
    liquid_net_worth: float = Field(gt=0, le=1e12)
    currency: Literal["USD", "AED", "INR"] = "USD"
    risk: Literal["conservative", "moderate", "aggressive"] = "moderate"
    candor: int = Field(3, ge=1, le=5)
    temperament: str = "mentor"
    holdings: list[Holding] = Field(default_factory=list, max_length=8)
    goals: list[str] = Field(default_factory=list, max_length=4)


@app.post("/v1/guest")
def create_guest(g: GuestRequest):
    """Try it on yourself: a sandboxed genome, open without a key, never mixed with client data."""
    from substrate.schemas import Consent, Goal, Position, RiskProfile
    user_id = f"guest-{secrets.token_hex(4)}"
    p = Person(user_id=user_id, name=g.name.strip() or "Guest", consent=Consent(candor_level=g.candor),
               temperament=temperaments.get(g.temperament).key, risk_profile=RiskProfile(stated=g.risk),
               liquid_net_worth=g.liquid_net_worth, currency=g.currency,
               positions=[Position(**h.model_dump()) for h in g.holdings],
               goals=[Goal(name=x[:80], priority=i + 1) for i, x in enumerate(g.goals) if x.strip()])
    store.put_person(p)
    return {"user_id": user_id, "person": p}


@app.delete("/v1/person/{user_id}")
def delete_person(user_id: str, key=Depends(keyhdr)):
    guard(user_id, key)
    if user_id == DEMO_USER:
        raise HTTPException(400, "Use POST /v1/demo/reset for the demo genome.")
    store.delete_person(user_id)
    return {"ok": True, "deleted": user_id}


# ---------------------------------------------------------------- the engine

@app.post("/v1/advise")
def advise(req: AdviseRequest, key=Depends(keyhdr)):
    guard(req.user_id, key)
    try:
        return engine.advise(req)
    except KeyError as e:
        raise HTTPException(404, str(e))


@app.post("/v1/advise/compare")
def compare(req: AdviseRequest, key=Depends(keyhdr)):
    guard(req.user_id, key)
    try:
        return engine.compare(req)
    except KeyError as e:
        raise HTTPException(404, str(e))


@app.post("/v1/outcome")
def outcome(req: OutcomeRequest, key=Depends(keyhdr)):
    ev = store.get_event(req.ledger_id)
    if not ev:
        raise HTTPException(404, "ledger entry not found")
    guard(ev["user_id"], key)
    try:
        return {"ok": True, "events": engine.record_outcome(req)}
    except KeyError as e:
        raise HTTPException(404, str(e))


# ---------------------------------------------------------------- ledger + inheritance

@app.get("/v1/ledger/{user_id}")
def ledger(user_id: str, limit: int = 50, key=Depends(keyhdr)):
    guard(user_id, key)
    events = store.events(user_id)
    return {"user_id": user_id, "verified": verify_chain(events), "length": len(events),
            "head": events[-1]["hash"] if events else None, "events": events[-limit:]}


@app.get("/v1/export/{user_id}")
def export(user_id: str, key=Depends(keyhdr)):
    guard(user_id, key)
    try:
        doc = export_sub(store, user_id)
    except KeyError:
        raise HTTPException(404, "person not found")
    return JSONResponse(doc, headers={"content-disposition": f'attachment; filename="{user_id}.sub"'})


@app.post("/v1/export/verify")
def verify(doc: dict):
    return verify_sub(doc)


# ---------------------------------------------------------------- proof

@app.post("/v1/evals/run")
def evals():
    return run_evals()


@app.post("/v1/demo/reset")
def demo_reset():
    seed(store, reset=True)
    return {"ok": True, "user_id": DEMO_USER}


# ---------------------------------------------------------------- console + embed

@app.get("/", include_in_schema=False)
def console():
    return FileResponse(STATIC / "index.html")


app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/embed.js", include_in_schema=False)
def embed():
    return FileResponse(STATIC / "embed.js", media_type="application/javascript")
