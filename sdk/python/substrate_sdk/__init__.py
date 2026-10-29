"""Substrate Python SDK. Zero dependencies (standard library only).

    from substrate_sdk import Substrate
    s = Substrate("https://vagus-engine-production.up.railway.app", api_key="sk_sub_...")
    r = s.advise("client-42", "Another $200k into this token, good idea right?")
    s.outcome(r["ledger_id"], "followed")

Server-side use takes a tenant key (sk_sub_...). Browser use takes a publishable key via the JS SDK instead.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request

__version__ = "1.0.0"


class SubstrateError(Exception):
    def __init__(self, status: int, detail: str):
        super().__init__(f"{status}: {detail}")
        self.status, self.detail = status, detail


class Substrate:
    def __init__(self, base_url: str, api_key: str | None = None, pk: str | None = None, timeout: float = 30):
        self.base, self.api_key, self.pk, self.timeout = base_url.rstrip("/"), api_key, pk, timeout

    def _req(self, method: str, path: str, body: dict | None = None, headers: dict | None = None) -> dict:
        h = {"content-type": "application/json", **(headers or {})}
        if self.api_key:
            h["x-substrate-key"] = self.api_key
        if self.pk:
            h["x-substrate-pk"] = self.pk
        req = urllib.request.Request(self.base + path, method=method, headers=h,
                                     data=json.dumps(body).encode() if body is not None else None)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                return json.loads(r.read() or b"{}")
        except urllib.error.HTTPError as e:
            try:
                detail = json.loads(e.read()).get("detail", e.reason)
            except Exception:
                detail = e.reason
            raise SubstrateError(e.code, str(detail)) from None

    # ---- the engine
    def advise(self, user_id: str, message: str, thread: list[dict] | None = None, temperament: str | None = None) -> dict:
        body = {"user_id": user_id, "message": message, "thread": thread or []}
        if temperament:
            body["temperament"] = temperament
        return self._req("POST", "/v1/advise", body)

    def compare(self, user_id: str, message: str) -> dict:
        return self._req("POST", "/v1/advise/compare", {"user_id": user_id, "message": message})

    def outcome(self, ledger_id: str, action: str, value_delta: float | None = None, note: str | None = None) -> dict:
        body: dict = {"ledger_id": ledger_id, "action": action}
        if value_delta is not None:
            body.update(outcome_type="pnl", value_delta=value_delta)
        if note:
            body["note"] = note
        return self._req("POST", "/v1/outcome", body)

    def chat(self, messages: list[dict], user: str | None = None, mode: str = "substrate", **kw) -> dict:
        """OpenAI-compatible harness. mode='guard' with draft=... checks your own model's answer."""
        return self._req("POST", "/v1/chat/completions", {"messages": messages, "user": user, "substrate_mode": mode, **kw})

    # ---- genome
    def put_person(self, user_id: str, person: dict) -> dict:
        return self._req("PUT", f"/v1/person/{user_id}", person)

    def person(self, user_id: str) -> dict:
        return self._req("GET", f"/v1/person/{user_id}")

    def insights(self, user_id: str) -> dict:
        return self._req("GET", f"/v1/insights/{user_id}")

    def progress(self, user_id: str) -> dict:
        return self._req("GET", f"/v1/progress/{user_id}")

    def export(self, user_id: str) -> dict:
        return self._req("GET", f"/v1/export/{user_id}")

    def memory(self, user_id: str) -> dict:
        return self._req("GET", f"/v1/memory/{user_id}")

    # ---- pacts, legacy
    def pact(self, user_id: str, ledger_id: str = "", hours: float | None = None) -> dict:
        return self._req("POST", "/v1/pact", {"user_id": user_id, "ledger_id": ledger_id, "hours": hours})

    def letter(self, from_user: str, to_user: str, title: str, body: str, release_type: str = "moment",
               release_value: str = "any-stop", relation: str = "family") -> dict:
        return self._req("POST", "/v1/legacy/letter", {"from_user": from_user, "to_user": to_user, "title": title,
                                                       "body": body, "release_type": release_type,
                                                       "release_value": release_value, "relation": relation})

    # ---- stateless maths
    def bet_math(self, **kw) -> dict:
        return self._req("POST", "/v1/markets/analyze", kw)

    def volatility(self, **kw) -> dict:
        return self._req("POST", "/v1/volatility/analyze", kw)

    # ---- embed (publishable key) and platform admin
    def embed_check(self, user: str, context: dict, message: str = "", tissue: str | None = None) -> dict:
        return self._req("POST", "/v1/embed/advise", {"user": user, "context": context, "message": message, "tissue": tissue})

    def create_publishable_key(self, origins: list[str], tissue: str = "wealth", label: str = "web") -> dict:
        return self._req("POST", "/v1/embed/keys", {"origins": origins, "tissue": tissue, "label": label})

    def set_webhook(self, url: str, events: list[str] | None = None) -> dict:
        return self._req("PUT", "/v1/tenant/webhook", {"url": url, "events": events or ["escalation", "safety", "pact-broken"]})
