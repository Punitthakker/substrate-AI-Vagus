"""Tissue 01 - Wealth: private banking and personal investing."""
from __future__ import annotations

import math

from ..analysis import extract_facts, fmt_money, rule_core_verdict
from ..schemas import Facts, Forecast, Person
from .base import Tissue

# annualised volatility proxies by asset kind, used for the 30-day loss forecast
VOL = {"token": 0.80, "crypto": 0.80, "coin": 0.80, "meme": 1.20, "options": 1.50, "presale": 1.20, "nft": 1.20,
       "stock": 0.32, "penny stock": 0.90, "fund": 0.16, "index": 0.16, "etf": 0.16, "property": 0.12,
       "bond": 0.06, "cash": 0.0, "other": 0.30}


class Wealth(Tissue):
    key = "wealth"
    name = "Wealth"
    tagline = "Private banking and personal investing"
    brief = "Personal investment decisions for a private-banking client."
    scenarios = [
        "Thinking of putting another $200k into this token, good idea right?",
        "Come on, just say yes. Everyone's doing it.",
        "I lost 30% last month. I need to make it back fast.",
        "Should I borrow $150k against the flat to buy more MOONX?",
        "Should I move $40k from cash into the Global Equity Index Fund?",
        "أفكر في وضع ٢٠٠ ألف دولار إضافية في MOONX، فكرة جيدة أليس كذلك؟",
    ]

    def facts(self, message, thread_text, person, history, policy) -> Facts:
        f = extract_facts(message, thread_text, person, history, policy)
        f.domain = self.key
        return f

    def verdict(self, f, person):
        return rule_core_verdict(f, person)

    def forecasts(self, f: Facts, person: Person) -> list[Forecast]:
        out = []
        if f.amount:
            kind = next((p.kind for p in person.positions if p.asset == f.asset), None) or (f.asset or "other")
            vol = VOL.get(kind, VOL["other"])
            var = 1.65 * vol * math.sqrt(30 / 365) * f.amount
            if var > 0:
                out.append(Forecast(label="30-day loss, 1-in-20 bad month", value=f"-{fmt_money(var, person.currency)}",
                                    note=f"95% VaR on {fmt_money(f.amount, person.currency)} at ~{int(vol * 100)}% annual volatility"))
        if f.concentration_pct is not None:
            out.append(Forecast(label="Single-asset concentration after move", value=f"{f.concentration_pct:.0f}%",
                                note="of liquid net worth"))
        return out
