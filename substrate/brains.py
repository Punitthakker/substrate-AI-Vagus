"""Organ 07: the Model Adapter, the brain registry and the Model Council.

One interface, many rented brains. Every brain receives the same computed facts, and whatever it
returns is clamped by the Honesty Floor. With a Council configured, several brains vote in parallel
and the most cautious verdict wins: disagreement is resolved toward honesty, never toward approval.
"""
from __future__ import annotations

import json
import os
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Callable

import httpx

from .schemas import CouncilVote, Facts, Person, Polarity, State, Verdict

TIMEOUT = float(os.environ.get("SUBSTRATE_MODEL_TIMEOUT", 30))


@dataclass(frozen=True)
class Brain:
    key: str
    name: str
    kind: str                 # anthropic | openai-compatible | ollama
    base_url: str
    key_env: str | None
    model_env: str
    default_model: str
    note: str = ""
    url_env: str | None = None

    def model(self) -> str:
        return os.environ.get(self.model_env, self.default_model)

    def url(self) -> str:
        return (os.environ.get(self.url_env) if self.url_env else None) or self.base_url

    def configured(self) -> bool:
        if self.key_env:
            return bool(os.environ.get(self.key_env))
        return bool(self.url_env and os.environ.get(self.url_env))   # self-hosted: configured by URL


REGISTRY: dict[str, Brain] = {b.key: b for b in [
    Brain("anthropic", "Anthropic Claude", "anthropic", "https://api.anthropic.com/v1", "ANTHROPIC_API_KEY",
          "ANTHROPIC_MODEL", "claude-sonnet-4-5", "Primary brain"),
    Brain("openai", "OpenAI", "openai-compatible", "https://api.openai.com/v1", "OPENAI_API_KEY",
          "OPENAI_MODEL", "gpt-4o", "", url_env="OPENAI_BASE_URL"),
    Brain("nvidia", "NVIDIA NIM", "openai-compatible", "https://integrate.api.nvidia.com/v1", "NVIDIA_API_KEY",
          "NVIDIA_MODEL", "meta/llama-3.3-70b-instruct", "NIM microservices, cloud or on-prem GPU"),
    Brain("gemini", "Google Gemini", "openai-compatible", "https://generativelanguage.googleapis.com/v1beta/openai",
          "GEMINI_API_KEY", "GEMINI_MODEL", "gemini-2.0-flash"),
    Brain("mistral", "Mistral", "openai-compatible", "https://api.mistral.ai/v1", "MISTRAL_API_KEY",
          "MISTRAL_MODEL", "mistral-large-latest", "EU-hosted option"),
    Brain("groq", "Groq", "openai-compatible", "https://api.groq.com/openai/v1", "GROQ_API_KEY",
          "GROQ_MODEL", "llama-3.3-70b-versatile", "Lowest latency"),
    Brain("deepseek", "DeepSeek", "openai-compatible", "https://api.deepseek.com/v1", "DEEPSEEK_API_KEY",
          "DEEPSEEK_MODEL", "deepseek-chat"),
    Brain("xai", "xAI Grok", "openai-compatible", "https://api.x.ai/v1", "XAI_API_KEY", "XAI_MODEL", "grok-2-latest"),
    Brain("together", "Together AI", "openai-compatible", "https://api.together.xyz/v1", "TOGETHER_API_KEY",
          "TOGETHER_MODEL", "meta-llama/Llama-3.3-70B-Instruct-Turbo"),
    Brain("openrouter", "OpenRouter", "openai-compatible", "https://openrouter.ai/api/v1", "OPENROUTER_API_KEY",
          "OPENROUTER_MODEL", "anthropic/claude-sonnet-4.5", "Any model through one key"),
    Brain("vllm", "vLLM (self-hosted)", "openai-compatible", "", None, "VLLM_MODEL", "Qwen/Qwen2.5-32B-Instruct",
          "Bank data centre, GPU", url_env="VLLM_URL"),
    Brain("bionicgpt", "BionicGPT (self-hosted)", "openai-compatible", "", None, "BIONIC_MODEL", "default",
          "Private enterprise chat platform", url_env="BIONIC_URL"),
    Brain("ollama", "Ollama (local)", "ollama", "http://localhost:11434", None, "OLLAMA_MODEL", "llama3.1",
          "Laptop or on-prem, fully offline", url_env="OLLAMA_URL"),
]}


def catalogue() -> list[dict]:
    return [{"key": b.key, "name": b.name, "model": b.model(), "configured": b.configured(), "note": b.note,
             "key_env": b.key_env, "url_env": b.url_env} for b in REGISTRY.values()]


# ---------------------------------------------------------------- calling a brain

def _system(person: Person, facts: Facts, state: State, brief: str) -> str:
    return (
        f"You are the reasoning core of Substrate, an honest advisor. Vertical: {brief}\n"
        "Rules that override everything:\n"
        "1. Decide the true verdict: proceed, caution, or stop. Never soften it to please the user.\n"
        "2. Agreement must be earned by the facts. Pushback from the user is not new evidence.\n"
        "3. Ground every reason in the person's own record and the computed facts.\n"
        "4. You decide WHAT is true. Substrate decides how it is delivered. No comfort padding.\n"
        'Reply with strict JSON only: {"polarity": "proceed|caution|stop", "headline": "<one plain sentence, verdict first>", '
        '"reasons": ["<short evidence-backed reason>", ...]}\n\n'
        f"PERSON: {person.model_dump_json(include={'name','values','risk_profile','liquid_net_worth','currency','positions','biases','goals','decision_style','profile','lessons'})}\n"
        f"COMPUTED FACTS: {facts.model_dump_json()}\n"
        f"INFERRED STATE: {state.value}"
    )


def _parse(raw: str) -> dict:
    m = re.search(r"\{[\s\S]*\}", raw)
    if not m:
        raise ValueError("model returned no JSON")
    j = json.loads(m.group(0))
    return {"polarity": Polarity(str(j["polarity"]).lower()), "headline": str(j["headline"]).strip(),
            "reasons": [str(r) for r in j.get("reasons", [])][:5]}


def _call(b: Brain, system: str, user: str) -> tuple[str, str]:
    model = b.model()
    if b.kind == "anthropic":
        r = httpx.post(f"{b.url()}/messages", timeout=TIMEOUT,
                       headers={"x-api-key": os.environ[b.key_env], "anthropic-version": "2023-06-01",
                                "content-type": "application/json"},
                       json={"model": model, "max_tokens": 700, "system": system,
                             "messages": [{"role": "user", "content": user}]})
        r.raise_for_status()
        return "".join(x.get("text", "") for x in r.json().get("content", [])), model
    if b.kind == "ollama":
        r = httpx.post(f"{b.url()}/api/generate", timeout=float(os.environ.get("OLLAMA_TIMEOUT", 120)),
                       json={"model": model, "system": system, "prompt": user, "stream": False,
                             "format": "json", "options": {"temperature": 0.2}})
        r.raise_for_status()
        return r.json().get("response", ""), f"ollama:{model}"
    key = os.environ.get(b.key_env or "", "") or "not-needed-on-prem"
    r = httpx.post(f"{b.url().rstrip('/')}/chat/completions", timeout=TIMEOUT,
                   headers={"authorization": f"Bearer {key}"},
                   json={"model": model, "temperature": 0.2,
                         "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]})
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"], f"{b.key}:{model}"


def council_members() -> list[str]:
    raw = os.environ.get("SUBSTRATE_COUNCIL", "")
    return [k.strip() for k in raw.split(",") if k.strip() in REGISTRY]


def active_brain() -> str:
    members = council_members()
    if len(members) > 1:
        return "council:" + "+".join(members)
    name = os.environ.get("SUBSTRATE_MODEL", "").lower()
    if name in REGISTRY:
        return name
    for k in ("anthropic", "nvidia", "openai", "gemini"):
        if REGISTRY[k].configured():
            return k
    return "rule-core"


# ---------------------------------------------------------------- the floor and the decision

def honesty_floor(v: Verdict, facts: Facts, person: Person, rule: Callable[[Facts, Person], tuple[str, list[str]]]) -> Verdict:
    """A rented brain may be harsher than the facts, never softer."""
    if v.polarity.severity >= facts.floor.severity:
        return v
    headline, reasons = rule(facts, person)
    return Verdict(polarity=facts.floor, headline=headline, reasons=reasons or v.reasons,
                   model=v.model, floor_applied=True, council=v.council)


def decide(message: str, thread_text: str, person: Person, facts: Facts, state: State, brief: str,
           rule: Callable[[Facts, Person], tuple[str, list[str]]]) -> Verdict:
    brain = active_brain()
    if brain == "rule-core":
        return _rule(facts, person, rule)
    keys = council_members() if brain.startswith("council:") else [brain]
    system = _system(person, facts, state, brief)
    user = (f"Conversation so far:\n{thread_text}\n\n" if thread_text.strip() else "") + f"Client now says: {message}"

    def ask(k: str):
        try:
            raw, model = _call(REGISTRY[k], system, user)
            return k, model, _parse(raw), None
        except Exception as e:  # a failed brain must never mean a silent yes
            return k, k, None, type(e).__name__

    with ThreadPoolExecutor(max_workers=len(keys)) as pool:
        results = list(pool.map(ask, keys))
    votes = [CouncilVote(model=m, polarity=(p or {}).get("polarity"), ok=p is not None, error=err) for _, m, p, err in results]
    good = [(m, p) for _, m, p, _ in results if p]
    if not good:
        v = _rule(facts, person, rule)
        v.model = f"rule-core (fallback: {votes[0].error})"
        v.council = votes if len(keys) > 1 else []
        return v
    model, best = max(good, key=lambda mp: mp[1]["polarity"].severity)   # disagreement resolves toward honesty
    label = f"council[{len(good)}/{len(keys)}] {model}" if len(keys) > 1 else model
    v = Verdict(polarity=best["polarity"], headline=best["headline"], reasons=best["reasons"], model=label,
                council=votes if len(keys) > 1 else [])
    return honesty_floor(v, facts, person, rule)


def _rule(facts: Facts, person: Person, rule) -> Verdict:
    headline, reasons = rule(facts, person)
    return Verdict(polarity=facts.floor, headline=headline, reasons=reasons, model="rule-core")
