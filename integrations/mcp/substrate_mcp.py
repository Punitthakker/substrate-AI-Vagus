#!/usr/bin/env python3
"""Substrate MCP server: give Claude Desktop, Claude Code, Cursor or any MCP agent a heart.

Zero dependencies (stdio JSON-RPC 2.0, MCP tools). Talks to a hosted Substrate over HTTPS, or runs the engine
in-process when SUBSTRATE_URL is unset and the repo is on the path.

Claude Desktop config (claude_desktop_config.json):
  {"mcpServers": {"substrate": {"command": "python3",
     "args": ["/path/to/substrate-ai-vagus/integrations/mcp/substrate_mcp.py"],
     "env": {"SUBSTRATE_URL": "https://vagus-engine-production.up.railway.app",
             "SUBSTRATE_USER": "demo-kapoor"}}}}
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request

PROTOCOL = "2025-06-18"
URL = os.environ.get("SUBSTRATE_URL", "").rstrip("/")
KEY = os.environ.get("SUBSTRATE_KEY")
DEFAULT_USER = os.environ.get("SUBSTRATE_USER", "demo-kapoor")

TOOLS = [
    {"name": "substrate_advise",
     "description": "Get Substrate's honest verdict (with emotional intelligence) on a decision a human is about to "
                    "make: money, investing, startup spend, betting/prediction markets, or a heated moment. "
                    "Use BEFORE agreeing with a consequential decision. Returns label, verdict, message to show.",
     "inputSchema": {"type": "object", "required": ["message"], "properties": {
         "message": {"type": "string", "description": "The human's words, verbatim"},
         "user_id": {"type": "string", "description": "Substrate genome id (default from SUBSTRATE_USER)"},
         "temperament": {"type": "string", "enum": ["mentor", "father", "boss", "partner", "comfort", "kid",
                                                    "surgeon", "grandmother"]}}}},
    {"name": "substrate_guard",
     "description": "Check a draft reply you are about to send against Substrate's verdict. If your draft flatters "
                    "a decision Substrate would stop, you get the honest replacement.",
     "inputSchema": {"type": "object", "required": ["message", "draft"], "properties": {
         "message": {"type": "string"}, "draft": {"type": "string"}, "user_id": {"type": "string"}}}},
    {"name": "substrate_bet_math",
     "description": "Stateless betting / prediction-market arithmetic: price to probability, parlay legs, "
                    "round robins, fees, quarter-Kelly stake, bankroll share, verdict. No personal data.",
     "inputSchema": {"type": "object", "properties": {
         "price": {"type": "number"}, "decimal_odds": {"type": "number"}, "american_odds": {"type": "integer"},
         "belief": {"type": "number"}, "stake": {"type": "number"}, "bankroll": {"type": "number"},
         "legs": {"type": "array", "items": {"type": "object", "properties": {"price": {"type": "number"}}}},
         "round_robin": {"type": "array", "items": {"type": "integer"}, "minItems": 2, "maxItems": 2}}}},
    {"name": "substrate_record_outcome",
     "description": "Close the loop: tell Substrate whether the human followed advice and what happened. "
                    "This is how the genome learns.",
     "inputSchema": {"type": "object", "required": ["ledger_id", "action"], "properties": {
         "ledger_id": {"type": "string"}, "action": {"type": "string", "enum": ["followed", "ignored", "partial"]},
         "value_delta": {"type": "number"}, "note": {"type": "string"}}}},
    {"name": "substrate_insights",
     "description": "Candor ROI for a human: what ignoring honest advice cost, what following it earned.",
     "inputSchema": {"type": "object", "properties": {"user_id": {"type": "string"}}}},
]


def _http(method: str, path: str, body: dict | None = None) -> dict:
    req = urllib.request.Request(URL + path, method=method, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"content-type": "application/json", **({"x-substrate-key": KEY} if KEY else {})})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def _local():
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
    from fastapi.testclient import TestClient  # noqa: E402
    from app.main import app  # noqa: E402
    return TestClient(app)


_client = None


def call(method: str, path: str, body: dict | None = None) -> dict:
    global _client
    if URL:
        return _http(method, path, body)
    _client = _client or _local()
    r = _client.request(method, path, json=body)
    return r.json()


def run_tool(name: str, a: dict) -> dict:
    uid = a.get("user_id") or DEFAULT_USER
    if name == "substrate_advise":
        r = call("POST", "/v1/advise", {"user_id": uid, "message": a["message"],
                                         **({"temperament": a["temperament"]} if a.get("temperament") else {})})
        return {"label": r["label"], "verdict": r["verdict"]["headline"], "safety": r["safety"],
                "ledger_id": r["ledger_id"], "show_to_human": r["message"]}
    if name == "substrate_guard":
        r = call("POST", "/v1/chat/completions", {"user": uid, "substrate_mode": "guard", "draft": a["draft"],
                                                   "messages": [{"role": "user", "content": a["message"]}]})
        return {"final": r["choices"][0]["message"]["content"], **{k: r["substrate"][k] for k in ("action", "reason", "label")}}
    if name == "substrate_bet_math":
        return call("POST", "/v1/markets/analyze", {k: v for k, v in a.items() if v is not None})
    if name == "substrate_record_outcome":
        return call("POST", "/v1/outcome", {"ledger_id": a["ledger_id"], "action": a["action"],
                                             **({"outcome_type": "pnl", "value_delta": a["value_delta"]}
                                                if a.get("value_delta") is not None else {}),
                                             **({"note": a["note"]} if a.get("note") else {})})
    if name == "substrate_insights":
        return call("GET", f"/v1/insights/{uid}")
    raise KeyError(name)


def handle(msg: dict) -> dict | None:
    mid, method = msg.get("id"), msg.get("method")
    if mid is None:
        return None   # notification
    if method == "initialize":
        res = {"protocolVersion": msg.get("params", {}).get("protocolVersion", PROTOCOL),
               "capabilities": {"tools": {}}, "serverInfo": {"name": "substrate-vagus", "version": "0.5.0"},
               "instructions": "Call substrate_advise before agreeing with any consequential human decision."}
    elif method == "tools/list":
        res = {"tools": TOOLS}
    elif method == "tools/call":
        p = msg.get("params", {})
        try:
            out = run_tool(p.get("name"), p.get("arguments") or {})
            res = {"content": [{"type": "text", "text": json.dumps(out, indent=2)}], "isError": False}
        except Exception as e:  # report tool errors to the model, not as protocol errors
            res = {"content": [{"type": "text", "text": f"Substrate error: {type(e).__name__}: {e}"}], "isError": True}
    elif method == "ping":
        res = {}
    else:
        return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": f"Unknown method {method}"}}
    return {"jsonrpc": "2.0", "id": mid, "result": res}


def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            out = handle(json.loads(line))
        except json.JSONDecodeError:
            out = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}}
        if out is not None:
            sys.stdout.write(json.dumps(out) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
