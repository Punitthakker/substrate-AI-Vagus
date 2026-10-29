"""Substrate API - the Vagus Engine over HTTP, plus the investor console and the embed widget."""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException
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


def guard(user_id: str, key: str | None) -> None:
    """Optional API key. The public demo genome stays open so the console and embed always work."""
    required = os.environ.get("SUBSTRATE_API_KEY")
    if required and user_id != DEMO_USER and key != required:
        raise HTTPException(401, "Missing or invalid x-substrate-key header.")


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
