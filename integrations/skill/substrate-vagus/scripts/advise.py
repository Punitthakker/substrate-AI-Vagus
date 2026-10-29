#!/usr/bin/env python3
"""Substrate Vagus skill helper: ask the engine, or record an outcome. Prints JSON."""
import argparse
import json
import os
import sys
import urllib.request


def call(path: str, body: dict) -> dict:
    base = os.environ.get("SUBSTRATE_URL", "").rstrip("/")
    if not base:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
        from substrate.engine import VagusEngine
        from substrate.schemas import AdviseRequest, OutcomeRequest
        eng = VagusEngine()
        if path == "/v1/advise":
            return eng.advise(AdviseRequest(**body)).model_dump(mode="json")
        return {"events": eng.record_outcome(OutcomeRequest(**body))}
    headers = {"content-type": "application/json"}
    if os.environ.get("SUBSTRATE_API_KEY"):
        headers["x-substrate-key"] = os.environ["SUBSTRATE_API_KEY"]
    req = urllib.request.Request(base + path, data=json.dumps(body).encode(), headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--user", default=os.environ.get("SUBSTRATE_USER", "demo-kapoor"))
    ap.add_argument("--message")
    ap.add_argument("--temperament")
    ap.add_argument("--outcome", help="ledger id to attach an action/outcome to")
    ap.add_argument("--action", choices=["followed", "ignored", "partial"])
    ap.add_argument("--delta", type=float)
    a = ap.parse_args()
    if a.outcome:
        body = {"ledger_id": a.outcome, "action": a.action}
        if a.delta is not None:
            body.update(outcome_type="pnl", value_delta=a.delta)
        print(json.dumps(call("/v1/outcome", body), indent=2))
    else:
        print(json.dumps(call("/v1/advise", {"user_id": a.user, "message": a.message, "temperament": a.temperament}), indent=2))


if __name__ == "__main__":
    main()
