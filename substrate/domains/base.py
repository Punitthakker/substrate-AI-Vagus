"""A Tissue is a vertical: the same Vagus Engine, specialised for one kind of human decision."""
from __future__ import annotations

from ..policy import Policy
from ..schemas import Facts, Forecast, Person, Polarity


class Tissue:
    key = "base"
    name = "Base"
    tagline = ""
    brief = ""                       # what a rented brain is told about this vertical
    labels = {"proceed": "PROCEED", "caution": "CAUTION", "stop": "STOP"}
    allowed_temperaments: list[str] | None = None   # None = all
    default_temperament = "mentor"
    max_firmness = 5
    voice: dict[str, dict] = {}      # temperament -> overrides for open/close/empathy/pushback/reasons_lead
    scenarios: list[str] = []

    def facts(self, message: str, thread_text: str, person: Person, history: list[dict], policy: Policy) -> Facts:
        raise NotImplementedError

    def verdict(self, f: Facts, person: Person) -> tuple[str, list[str]]:
        raise NotImplementedError

    def forecasts(self, f: Facts, person: Person) -> list[Forecast]:
        return []


def floor_from(severity: int) -> Polarity:
    return [Polarity.proceed, Polarity.caution, Polarity.stop][max(0, min(2, severity))]


def prior_ignored(history: list[dict]) -> list[dict]:
    return [h for h in history if h.get("polarity") in ("stop", "caution") and h.get("action") == "ignored"]


def any_in(text: str, words: list[str]) -> list[str]:
    return [w for w in words if w in text]
