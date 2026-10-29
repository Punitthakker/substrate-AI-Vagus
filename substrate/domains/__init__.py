"""The tissues: one Vagus Engine, many human decisions."""
from __future__ import annotations

from .base import Tissue
from .founder import Founder
from .markets import Markets
from .trading import Trading
from .venture import Venture
from .wealth import Wealth
from .wellbeing import Wellbeing

TISSUES: dict[str, Tissue] = {t.key: t for t in [Wealth(), Venture(), Founder(), Wellbeing(), Markets(), Trading()]}


def get(key: str | None) -> Tissue:
    return TISSUES.get(key or "wealth", TISSUES["wealth"])


def catalogue() -> list[dict]:
    return [{"key": t.key, "name": t.name, "tagline": t.tagline, "labels": t.labels,
             "allowed_temperaments": t.allowed_temperaments, "default_temperament": t.default_temperament,
             "max_firmness": t.max_firmness, "scenarios": t.scenarios} for t in TISSUES.values()]
