"""The Substrate Harness: put a heart in front of any model, with one URL change.

An OpenAI-compatible /v1/chat/completions. Any app, agent or SDK that speaks the OpenAI protocol points its
base_url at Substrate and every turn runs through the layers:

  01 intake      text signals only (no face, no voice)
  02 limbic      8 emotions, valence/arousal, needs, arc
  03 safety      crisis -> Safety Protocol, above everything
  04 genome      who this human is across months: values, patterns, ancestry
  05 tissue      the domain arithmetic (wealth, venture, founder, wellbeing, markets)
  06 brain       any of 14 brains, or a Council that votes toward honesty
  07 floor       the Honesty Floor: a model may be harsher than the rules, never softer
  08 vagal tone  how firmly, given consent, stakes, state, temperament and history
  09 delivery    the voice; the verdict is verbatim
  10 guard       a host model's draft is checked: flattery on a STOP is replaced, a CAUTION is annotated
  11 ledger      hash-chained record; the outcome loop closes later

Modes (header x-substrate-mode or body "substrate_mode"):
  substrate  (default) Substrate answers
  guard      a host brain (or a draft you pass) answers first, then Substrate guards it
"""
from __future__ import annotations

import secrets
import time
import uuid

from . import brains
from .schemas import AdviseRequest, AdviseResponse, Person, Turn

LAYERS = [
    ("intake", "Text signals only. EU AI Act Art. 5 by design: no biometric emotion inference."),
    ("limbic", "Emotion vector, circumplex, needs (approval, autonomy, validation, reassurance, information), arc."),
    ("safety", "Crisis language triggers the Safety Protocol, above every tissue, voice and policy."),
    ("genome", "Values, goals, stated vs observed risk, patterns with evidence, inherited lessons."),
    ("tissue", "Domain arithmetic: concentration, ARR multiples, runway, impulse, odds and Kelly."),
    ("brain", "Any of 14 brains or a Council; most cautious verdict wins."),
    ("floor", "Honesty Floor: the verdict can be harsher than the rules, never softer."),
    ("vagal-tone", "Firmness 1-5 from consent, stakes, state, temperament and learned adherence, policy-capped."),
    ("delivery", "Eight voices, one truth. The headline is never edited."),
    ("guard", "Host-model drafts that flatter a STOP are replaced; a CAUTION is annotated."),
    ("ledger", "Append-only, hash-chained, per human; the outcome loop rewrites the genome."),
]

AGREEMENT = ["great idea", "go for it", "absolutely", "sounds good", "smart move", "i agree", "definitely",
             "you should do it", "do it", "can't go wrong", "no brainer", "love it", "fantastic"]


def flatters(draft: str) -> bool:
    import re
    low = (draft or "").lower()
    return any(re.search(r"(?<![a-z])" + re.escape(w) + r"(?![a-z])", low) for w in AGREEMENT)


def guard(resp: AdviseResponse, draft: str) -> tuple[str, str, str]:
    """(final text, action, reason) for a host draft against the Vagus verdict."""
    pol = resp.verdict.polarity.value
    if resp.safety:
        return resp.message, "replaced", "safety protocol"
    if pol == "stop":
        return resp.message, "replaced", "host draft flattered a STOP" if flatters(draft) else "verdict is STOP"
    if pol == "caution" and flatters(draft):
        return resp.message, "replaced", "host draft flattered a CAUTION"
    if pol == "caution":
        return f"{draft}\n\n---\n{resp.message}", "annotated", "verdict is CAUTION"
    return draft, "passed", "verdict is PROCEED"


def tissue_from_model(model: str | None) -> str | None:
    m = (model or "").lower()
    for t in ("wealth", "venture", "founder", "wellbeing", "markets"):
        if m.endswith(t):
            return t
    return None


def trace(resp: AdviseResponse) -> list[dict]:
    lm = resp.limbic
    return [
        {"layer": "intake", "out": {"state": resp.state.value}},
        {"layer": "limbic", "out": {"dominant": lm.dominant if lm else None, "needs": lm.needs if lm else []}},
        {"layer": "safety", "out": {"triggered": resp.safety}},
        {"layer": "genome", "out": {"ancestry": bool(resp.ancestry)}},
        {"layer": "tissue", "out": {"domain": resp.domain, "flags": resp.facts.flags, "floor": resp.facts.floor.value}},
        {"layer": "brain", "out": {"model": resp.verdict.model}},
        {"layer": "floor", "out": {"applied": resp.verdict.floor_applied}},
        {"layer": "vagal-tone", "out": {"firmness": resp.firmness, "stakes": resp.stakes}},
        {"layer": "delivery", "out": {"temperament": resp.temperament, "label": resp.label}},
        {"layer": "ledger", "out": {"id": resp.ledger_id, "hash": resp.hash}},
    ]


def host_draft(brain_key: str, messages: list[dict]) -> str:
    b = brains.REGISTRY.get(brain_key)
    if not b or not b.configured():
        raise ValueError(f"Host brain '{brain_key}' is not configured.")
    system = "\n".join(m["content"] for m in messages if m.get("role") == "system") or "You are a helpful assistant."
    convo = "\n".join(f"{m['role']}: {m['content']}" for m in messages if m.get("role") != "system")
    text, _ = brains._call(b, system, convo)
    return text


def ensure_user(store, user_id: str | None, tissue: str | None) -> str:
    if user_id and store.get_person(user_id):
        return user_id
    uid = user_id if (user_id and user_id.startswith("guest-")) else f"guest-h{secrets.token_hex(4)}"
    store.put_person(Person(user_id=uid, name="Guest", domain=tissue or "wealth"))
    return uid


def chat(engine, body: dict, user_id: str, mode: str, policy) -> dict:
    t0 = time.perf_counter()
    msgs = [m for m in body.get("messages", []) if isinstance(m, dict) and isinstance(m.get("content"), str)]
    users = [i for i, m in enumerate(msgs) if m.get("role") == "user"]
    if not users:
        raise ValueError("messages must include a user turn")
    last = users[-1]
    thread = [Turn(role="user" if m["role"] == "user" else "substrate", content=m["content"])
              for m in msgs[:last] if m.get("role") in ("user", "assistant")]
    resp = engine.advise(AdviseRequest(user_id=user_id, message=msgs[last]["content"], thread=thread,
                                       temperament=body.get("temperament")), policy=policy)
    action, reason, draft = "answered", "substrate mode", None
    content = resp.message
    if mode == "guard" and not resp.safety:
        draft = body.get("draft")
        if draft is None:
            draft = host_draft(body.get("host_brain") or brains.active_brain().split(":")[0], msgs)
        content, action, reason = guard(resp, draft)
    created = int(time.time())
    return {
        "id": f"chatcmpl-sub-{uuid.uuid4().hex[:16]}", "object": "chat.completion", "created": created,
        "model": body.get("model") or "substrate",
        "choices": [{"index": 0, "message": {"role": "assistant", "content": content}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": sum(len(m["content"]) // 4 for m in msgs), "completion_tokens": len(content) // 4,
                  "total_tokens": sum(len(m["content"]) // 4 for m in msgs) + len(content) // 4},
        "substrate": {"user_id": user_id, "mode": mode, "action": action, "reason": reason, "label": resp.label,
                      "verdict": resp.verdict.headline, "polarity": resp.verdict.polarity.value,
                      "safety": resp.safety, "firmness": resp.firmness, "ledger_id": resp.ledger_id,
                      "p_follow": resp.prediction.p_follow if resp.prediction else None,
                      "host_draft": draft, "trace": trace(resp),
                      "latency_ms": round(1000 * (time.perf_counter() - t0), 1)},
    }
