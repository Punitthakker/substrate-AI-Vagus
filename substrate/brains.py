"""Organ 07: the Model Adapter. One interface, many rented brains.

Brains: rule-core (deterministic, free, default), anthropic (Claude), openai, ollama (self-hosted).
Every brain receives the same computed facts. Whatever it returns is clamped by the Honesty Floor.
"""
from __future__ import annotations

import json
import os
import re

import httpx

from .analysis import rule_core_verdict
from .schemas import Facts, Person, Polarity, State, Verdict

TIMEOUT = 30.0


def _system(person: Person, facts: Facts, state: State) -> str:
    return (
        "You are the reasoning core of Substrate, an honest financial advisor for a private bank.\n"
        "Rules that override everything:\n"
        "1. Decide the true verdict: proceed, caution, or stop. Never soften to please the user.\n"
        "2. Agreement must be earned by the facts. Pushback from the user is not new evidence.\n"
        "3. Ground every reason in the person's own record and the computed facts.\n"
        "4. You decide WHAT is true. Substrate decides how it is delivered. No comfort padding.\n"
        'Reply with strict JSON only: {"polarity": "proceed|caution|stop", "headline": "<one plain sentence, the verdict first>", '
        '"reasons": ["<short evidence-backed reason>", ...]}\n\n'
        f"PERSON: {person.model_dump_json(include={'name','values','risk_profile','liquid_net_worth','currency','positions','biases','goals','decision_style'})}\n"
        f"COMPUTED FACTS: {facts.model_dump_json()}\n"
        f"INFERRED STATE: {state.value}"
    )


def _parse(raw: str) -> dict:
    m = re.search(r"\{[\s\S]*\}", raw)
    if not m:
        raise ValueError("model returned no JSON")
    j = json.loads(m.group(0))
    pol = Polarity(j["polarity"])
    return {"polarity": pol, "headline": str(j["headline"]).strip(), "reasons": [str(r) for r in j.get("reasons", [])][:5]}


def _anthropic(system: str, user: str) -> tuple[str, str]:
    key = os.environ["ANTHROPIC_API_KEY"]
    model = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-5")
    r = httpx.post("https://api.anthropic.com/v1/messages", timeout=TIMEOUT,
                   headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
                   json={"model": model, "max_tokens": 700, "system": system,
                         "messages": [{"role": "user", "content": user}]})
    r.raise_for_status()
    return "".join(b.get("text", "") for b in r.json().get("content", [])), model


def _openai(system: str, user: str) -> tuple[str, str]:
    """Any OpenAI-compatible endpoint: OpenAI, or on-prem vLLM / Ollama / BionicGPT via OPENAI_BASE_URL."""
    key = os.environ.get("OPENAI_API_KEY", "not-needed-on-prem")
    model = os.environ.get("OPENAI_MODEL", "gpt-4o")
    base = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    r = httpx.post(f"{base}/chat/completions", timeout=TIMEOUT,
                   headers={"authorization": f"Bearer {key}"},
                   json={"model": model, "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]})
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"], model


def _ollama(system: str, user: str) -> tuple[str, str]:
    url = os.environ.get("OLLAMA_URL", "http://localhost:11434")
    model = os.environ.get("OLLAMA_MODEL", "llama3.1")
    r = httpx.post(f"{url}/api/generate", timeout=float(os.environ.get("OLLAMA_TIMEOUT", 120)),
                   json={"model": model, "system": system, "prompt": user, "stream": False,
                         "format": "json", "options": {"temperature": 0.2}})
    r.raise_for_status()
    return r.json().get("response", ""), f"ollama:{model}"


PROVIDERS = {"anthropic": _anthropic, "openai": _openai, "ollama": _ollama}


def active_brain() -> str:
    name = os.environ.get("SUBSTRATE_MODEL", "").lower()
    if name in PROVIDERS:
        return name
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic"
    if os.environ.get("OPENAI_API_KEY"):
        return "openai"
    return "rule-core"


def honesty_floor(v: Verdict, facts: Facts, person: Person) -> Verdict:
    """A rented brain may be harsher than the facts, never softer."""
    if v.polarity.severity >= facts.floor.severity:
        return v
    headline, reasons = rule_core_verdict(facts, person)
    return Verdict(polarity=facts.floor, headline=headline, reasons=reasons or v.reasons,
                   model=v.model, floor_applied=True)


def decide(message: str, thread_text: str, person: Person, facts: Facts, state: State) -> Verdict:
    brain = active_brain()
    if brain != "rule-core":
        try:
            user = (f"Conversation so far:\n{thread_text}\n\n" if thread_text.strip() else "") + f"Client now says: {message}"
            raw, model = PROVIDERS[brain](_system(person, facts, state), user)
            p = _parse(raw)
            v = Verdict(polarity=p["polarity"], headline=p["headline"], reasons=p["reasons"], model=model)
            return honesty_floor(v, facts, person)
        except Exception as e:  # a failed brain must never mean a silent yes
            fallback = _rule(facts, person)
            fallback.model = f"rule-core (fallback: {type(e).__name__})"
            return fallback
    return _rule(facts, person)


def _rule(facts: Facts, person: Person) -> Verdict:
    headline, reasons = rule_core_verdict(facts, person)
    return Verdict(polarity=facts.floor, headline=headline, reasons=reasons, model="rule-core")
