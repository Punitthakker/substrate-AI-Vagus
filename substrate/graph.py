"""The Genome Graph: the person model as a living knowledge graph.

Nodes: the human, their values, goals, patterns, decisions, actions, outcomes and lessons.
Edges: holds, pursues, shows, evidenced-by, flagged, chose, led-to, taught.

The built-in graph is computed from the genome and the Vagus Ledger, no extra infrastructure.
For production, the same facts can be streamed into Graphiti (getzep/graphiti, Apache-2.0), a
temporal knowledge graph on Neo4j, so every fact carries when it became true and when it stopped.
"""
from __future__ import annotations

import os

from .analysis import fmt_money
from .ledger import Store

PATTERN_FLAGS = {"concentration", "loss-chasing", "leverage", "fomo", "check-concentration", "valuation",
                 "no-diligence", "thesis-drift", "runway", "runway-drop", "vanity-spend", "impulse"}


def build_graph(store: Store, user_id: str, limit: int = 12) -> dict:
    p = store.get_person(user_id)
    if not p:
        raise KeyError(user_id)
    nodes, edges = [], []
    seen = set()

    def node(nid, ntype, label, weight=1.0, **kw):
        if nid not in seen:
            seen.add(nid)
            nodes.append({"id": nid, "type": ntype, "label": label, "weight": weight, **kw})

    def edge(a, b, etype):
        edges.append({"source": a, "target": b, "type": etype})

    me = f"person:{p.user_id}"
    node(me, "person", p.name, 3)
    for v in p.values:
        node(f"value:{v}", "value", v, 1.2); edge(me, f"value:{v}", "holds")
    for g in p.goals:
        node(f"goal:{g.name}", "goal", g.name, 1.4); edge(me, f"goal:{g.name}", "pursues")
    for b in p.biases:
        node(f"pattern:{b.type}", "pattern", b.type, 1 + 0.5 * len(b.evidence)); edge(me, f"pattern:{b.type}", "shows")

    history = store.history(user_id)[-limit:]
    for h in history:
        did = f"decision:{h['id']}"
        node(did, "decision", h.get("headline") or h["id"], 1.3, polarity=h.get("polarity"), ts=(h.get("ts") or "")[:10])
        edge(me, did, "advised")
        for b in p.biases:
            if h["id"] in b.evidence:
                edge(f"pattern:{b.type}", did, "evidenced-by")
        if h.get("action"):
            aid = f"action:{h['id']}"
            node(aid, "action", f"{h['action']}", 1.0, taken=h["action"])
            edge(did, aid, "chose")
            if h.get("value_delta") is not None:
                d = h["value_delta"]
                oid = f"outcome:{h['id']}"
                node(oid, "outcome", ("+" if d >= 0 else "-") + fmt_money(abs(d), p.currency), 1 + min(3, abs(d) / 50_000),
                     delta=d)
                edge(aid, oid, "led-to")
    # flags recorded on advice events that are not yet named patterns
    for ev in store.events(user_id)[-limit * 3:]:
        if ev["kind"] == "advice":
            for f in set(ev["payload"].get("flags") or []) & PATTERN_FLAGS:
                pid = f"pattern:{f}"
                node(pid, "pattern", f, 1.0)
                if f"decision:{ev['id']}" in seen:
                    edge(f"decision:{ev['id']}", pid, "flagged")
    for i, l in enumerate(p.lessons[-5:]):
        lid = f"lesson:{i}"
        node(lid, "lesson", l[:90], 1.1)
        edge(me, lid, "learned")
    return {"user_id": user_id, "nodes": nodes, "edges": edges,
            "counts": {t: sum(1 for n in nodes if n["type"] == t) for t in
                       ("value", "goal", "pattern", "decision", "action", "outcome", "lesson")}}


def to_graphiti_episodes(store: Store, user_id: str) -> list[dict]:
    """Ledger events as Graphiti episodes: plain-language facts with the time they became true."""
    p = store.get_person(user_id)
    if not p:
        raise KeyError(user_id)
    out = [{"name": f"genome:{user_id}", "reference_time": p.vintage,
            "body": f"{p.name} values {', '.join(p.values)}. Goals: {', '.join(g.name for g in p.goals)}. "
                    f"Known patterns: {', '.join(b.type for b in p.biases)}."}]
    for h in store.history(user_id):
        body = f"Substrate advised {p.name}: {h.get('headline')}"
        if h.get("action"):
            body += f" {p.name} {h['action']} the advice."
        if h.get("value_delta") is not None:
            body += f" Outcome: {fmt_money(abs(h['value_delta']), p.currency)} {'gain' if h['value_delta'] >= 0 else 'loss'}."
        out.append({"name": h["id"], "reference_time": h.get("ts"), "body": body})
    return out


async def push_to_graphiti(store: Store, user_id: str) -> int:
    """Optional: stream a genome into Graphiti/Neo4j (needs graphiti-core and NEO4J_* env vars)."""
    from datetime import datetime

    from graphiti_core import Graphiti  # type: ignore
    from graphiti_core.nodes import EpisodeType  # type: ignore
    g = Graphiti(os.environ["NEO4J_URI"], os.environ["NEO4J_USER"], os.environ["NEO4J_PASSWORD"])
    eps = to_graphiti_episodes(store, user_id)
    for e in eps:
        ts = datetime.fromisoformat((e["reference_time"] or "2026-01-01").replace("Z", "+00:00"))
        await g.add_episode(name=e["name"], episode_body=e["body"], source=EpisodeType.text,
                            source_description="Substrate Vagus Ledger", reference_time=ts, group_id=user_id)
    await g.close()
    return len(eps)
