"""Substrate as a guard around any LangChain chat model or chain (and anything else callable).

    from integrations.langchain_guard import SubstrateGuard
    guarded = SubstrateGuard(llm, user_id="demo-kapoor")          # llm: any LangChain chat model / runnable
    guarded.invoke("Another $200k into MOONX, good idea?")      # -> honest text if the model flattered a STOP

    chain = prompt | llm | StrOutputParser()
    guarded_chain = SubstrateGuard(chain, user_id="demo-rahman").as_runnable()   # needs langchain-core

Works without LangChain installed: pass any callable(str) -> str.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from substrate.wrap import Substrate  # noqa: E402


class SubstrateGuard:
    def __init__(self, model, user_id: str, base_url: str | None = None, api_key: str | None = None,
                 temperament: str | None = None):
        self.model = model
        self.client = Substrate(user_id=user_id, base_url=base_url, api_key=api_key, temperament=temperament)
        self.last: dict | None = None

    def _draft(self, message: str) -> str:
        m = self.model
        out = m.invoke(message) if hasattr(m, "invoke") else m(message)
        return getattr(out, "content", out) if not isinstance(out, str) else out

    def invoke(self, message: str, *_, **__) -> str:
        self.last = self.client.guard(message, self._draft(message))
        return self.last["text"]

    __call__ = invoke

    def as_runnable(self):
        from langchain_core.runnables import RunnableLambda  # type: ignore
        return RunnableLambda(lambda x: self.invoke(x if isinstance(x, str) else str(x)))
