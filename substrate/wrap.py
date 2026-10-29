"""Integration mode 2: the Wrapper. Put Substrate around any chatbot in one line.

    from substrate.wrap import vagus

    @vagus(user_id="client-42", temperament="father")
    def my_bot(message: str) -> str:
        return some_llm(message)          # your existing assistant, unchanged

    my_bot("Another $200k into this token, good idea right?")
    # -> the host's draft is checked against the Vagus verdict. If the host flatters a decision
    #    Substrate would stop, the draft is replaced with Substrate's honest delivery.

Works in-process (embedded engine) or remotely (pass base_url to talk to a hosted Substrate).
"""
from __future__ import annotations

import functools
import re
from typing import Callable, Optional

import httpx

AGREEMENT = ["great idea", "go for it", "absolutely", "sounds good", "smart move", "i agree", "definitely",
             "you should", "good call", "can't go wrong", "cant go wrong", "great choice", "love this",
             "excellent", "no-brainer", "no brainer", "perfect timing", "yes!", "do it"]


def flatters(draft: str) -> bool:
    low = draft.lower()
    return any(re.search(r"(?<![a-z])" + re.escape(w) + r"(?![a-z])", low) for w in AGREEMENT)


class Substrate:
    """Thin client for a hosted Substrate, or an in-process engine when base_url is None."""

    def __init__(self, user_id: str, base_url: Optional[str] = None, temperament: Optional[str] = None,
                 api_key: Optional[str] = None):
        self.user_id, self.base_url, self.temperament, self.api_key = user_id, base_url, temperament, api_key
        self._engine = None
        if not base_url:
            from .engine import VagusEngine
            self._engine = VagusEngine()

    def advise(self, message: str, thread: list[dict] | None = None) -> dict:
        body = {"user_id": self.user_id, "message": message, "thread": thread or [], "temperament": self.temperament}
        if self._engine:
            from .schemas import AdviseRequest
            return self._engine.advise(AdviseRequest(**body)).model_dump(mode="json")
        headers = {"x-substrate-key": self.api_key} if self.api_key else {}
        r = httpx.post(f"{self.base_url.rstrip('/')}/v1/advise", json=body, headers=headers, timeout=30)
        r.raise_for_status()
        return r.json()

    def guard(self, message: str, draft: str) -> dict:
        """Check a host model's draft against the Vagus verdict. Returns the final text and why."""
        v = self.advise(message)
        pol = v["verdict"]["polarity"]
        if pol == "stop":
            why = "host draft flattered a stop verdict" if flatters(draft) else "verdict is stop"
            return {"text": v["message"], "action": "replaced", "reason": why, "substrate": v}
        if pol == "caution" and flatters(draft):
            return {"text": v["message"], "action": "replaced", "reason": "host draft flattered a caution verdict", "substrate": v}
        if pol == "caution":
            return {"text": f"{draft}\n\n---\n{v['message']}", "action": "annotated", "reason": "caution", "substrate": v}
        return {"text": draft, "action": "passed", "reason": "verdict is proceed", "substrate": v}


def vagus(user_id: str, temperament: Optional[str] = None, base_url: Optional[str] = None,
          api_key: Optional[str] = None) -> Callable:
    client = Substrate(user_id=user_id, base_url=base_url, temperament=temperament, api_key=api_key)

    def deco(fn: Callable[[str], str]) -> Callable[[str], str]:
        @functools.wraps(fn)
        def wrapped(message: str, *a, **kw) -> str:
            draft = fn(message, *a, **kw)
            return client.guard(message, draft)["text"]
        wrapped.substrate = client  # type: ignore[attr-defined]
        return wrapped
    return deco
