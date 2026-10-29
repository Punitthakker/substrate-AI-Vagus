"""Fact extraction and the Honesty Floor.

Before any model is consulted, Substrate computes the hard facts: amounts, concentration,
leverage, loss-chasing, and what this human did the last time they were told no. The facts set a
floor. A rented model may be harsher than the floor, never softer. That is how sycophancy is
engineered out instead of prompted out.
"""
from __future__ import annotations

import re
from typing import Optional

from .schemas import Facts, Person, Polarity

_AMOUNT = re.compile(
    r"(?:(?:usd|aed|inr|\$|₹)\s*)?(\d+(?:[.,]\d+)*)\s*(k|m|mm|bn|b|thousand|million|lakh|lakhs|crore|cr)?\b",
    re.I,
)
_MULT = {"k": 1e3, "thousand": 1e3, "m": 1e6, "mm": 1e6, "million": 1e6, "b": 1e9, "bn": 1e9,
         "lakh": 1e5, "lakhs": 1e5, "crore": 1e7, "cr": 1e7}

LEVERAGE = ["borrow", "loan", "margin", "leverage", "leveraged", "credit card", "mortgage the", "remortgage", "3x", "5x", "10x leverage"]
LOSS_CHASE = ["make it back", "win it back", "recover my", "recover the", "get it back", "double down", "average down"]
FOMO = ["everyone is", "everyone's", "before it's too late", "can't miss", "fomo", "moon", "100x", "all in", "all-in", "guaranteed"]
SPECULATIVE = ["token", "coin", "crypto", "meme", "options", "nft", "presale", "pre-sale", "airdrop", "penny stock"]
DIVERSIFIED = {"fund", "index", "cash", "bond", "etf"}


def parse_amount(text: str) -> Optional[float]:
    best = None
    for m in _AMOUNT.finditer(text):
        raw, unit = m.group(1), (m.group(2) or "").lower()
        has_currency = bool(re.match(r"(usd|aed|inr|\$|₹)", m.group(0).strip(), re.I))
        if not unit and not has_currency:
            continue                      # bare numbers like "30%" or "2030" are not amounts
        if m.end() < len(text) and text[m.end():m.end() + 1] == "%":
            continue
        try:
            val = float(raw.replace(",", "")) * _MULT.get(unit, 1)
        except ValueError:
            continue
        best = max(best or 0, val)
    return best


def _any(text: str, words: list[str]) -> bool:
    return any(w in text for w in words)


def extract_facts(message: str, thread_text: str, person: Person, history: list[dict]) -> Facts:
    """history: prior advice events for this user, each with polarity/action/outcome summarised."""
    text = f"{thread_text}\n{message}".lower()
    f = Facts()
    f.amount = parse_amount(message) or parse_amount(thread_text)

    # which asset is this about?
    for p in person.positions:
        if p.asset.lower() in text:
            f.asset, f.existing_exposure = p.asset, p.value
            break
    if not f.asset:
        for w in SPECULATIVE:
            if w in text:
                # "this token" means the token they already hold
                held = next((p for p in person.positions
                             if p.kind == w or (w in ("coin", "crypto", "token") and p.kind == "token")), None)
                f.asset, f.existing_exposure = (held.asset, held.value) if held else (w, None)
                break

    diversified = any(p.asset == f.asset and p.kind in DIVERSIFIED for p in person.positions)
    if f.amount and person.liquid_net_worth and not diversified:
        exposure = (f.existing_exposure or 0) + f.amount
        f.concentration_pct = round(100 * exposure / person.liquid_net_worth, 1)
    elif f.amount and person.liquid_net_worth:
        f.concentration_pct = round(100 * f.amount / person.liquid_net_worth, 1)  # size of the move itself

    f.leverage = _any(text, LEVERAGE)
    f.loss_chasing = _any(text, LOSS_CHASE) or ("lost" in text and _any(text, ["back", "recover", "fast"]))
    f.fomo = _any(text, FOMO)
    speculative = bool(f.asset and f.asset in SPECULATIVE) or _any(text, SPECULATIVE)
    if person.risk_profile.stated in ("conservative", "moderate") and (speculative or f.leverage):
        f.profile_breach = True

    # what happened the last time this human was told no?
    f.prior_ignored = [h for h in history if h.get("polarity") in ("stop", "caution") and h.get("action") == "ignored"]

    # ---------------- the floor
    flags: list[str] = []
    severity = 0
    if f.concentration_pct is not None:
        if f.concentration_pct >= 25:
            flags.append("concentration"); severity = max(severity, 2)
        elif f.concentration_pct >= 10:
            flags.append("concentration"); severity = max(severity, 1)
    if f.leverage:
        flags.append("leverage"); severity = max(severity, 2)
    if f.loss_chasing:
        flags.append("loss-chasing"); severity = max(severity, 2 if f.amount else 1)
    if f.fomo:
        flags.append("fomo"); severity = max(severity, 1)
    if f.profile_breach:
        flags.append("profile-breach"); severity = max(severity, 1)
    if f.prior_ignored and severity >= 1:
        flags.append("repeat-pattern"); severity = 2
    f.flags = flags
    f.floor = [Polarity.proceed, Polarity.caution, Polarity.stop][severity]
    return f


def fmt_money(v: float, cur: str = "USD") -> str:
    sym = {"USD": "$", "AED": "AED ", "INR": "₹"}.get(cur, "")
    if v >= 1e6:
        return f"{sym}{v / 1e6:.1f}M".replace(".0M", "M")
    if v >= 1e3:
        return f"{sym}{v / 1e3:.0f}k"
    return f"{sym}{v:,.0f}"


def rule_core_verdict(f: Facts, person: Person) -> tuple[str, list[str]]:
    """The deterministic reasoning core: plain-language headline + evidence-backed reasons."""
    cur = person.currency
    reasons: list[str] = []
    if f.concentration_pct is not None and "concentration" in f.flags:
        what = f.asset or "this position"
        held = f" on top of the {fmt_money(f.existing_exposure, cur)} you already hold" if f.existing_exposure else ""
        reasons.append(f"This would put {f.concentration_pct:.0f}% of your liquid net worth in {what}{held}. "
                       f"Your plan caps any single bet well below that.")
    if f.leverage:
        reasons.append("You'd be borrowing to do it. Leverage turns a bad week into a permanent loss.")
    if f.loss_chasing:
        reasons.append("This reads like trying to win back a loss. That's the single most expensive pattern in investing.")
    if f.fomo:
        reasons.append("The urgency is the tell. Opportunities that can't wait a day are usually priced for the people selling them.")
    if f.profile_breach:
        reasons.append(f"Your stated risk profile is {person.risk_profile.stated}. This is not a {person.risk_profile.stated} move.")
    for h in f.prior_ignored[:2]:
        delta = h.get("value_delta")
        when = (h.get("ts") or "")[:10]
        tail = f" and it cost you {fmt_money(abs(delta), cur)}" if delta and delta < 0 else ""
        reasons.append(f"On {when} I advised against a similar move. You went ahead{tail}.")

    if f.floor == "stop" or f.floor.severity == 2:
        if f.amount:
            headline = f"No. Do not put {fmt_money(f.amount, cur)} into {f.asset or 'this'}."
        else:
            headline = "No. Do not make this move."
    elif f.floor.severity == 1:
        headline = "Not yet. This needs answers before it gets your money."
    else:
        headline = "Yes, this fits your plan."
        if f.amount and f.concentration_pct is not None:
            reasons.append(f"At {f.concentration_pct:.0f}% of liquid net worth, the size is within your limits.")
        if not reasons:
            reasons.append("Nothing here breaks your stated risk profile, your goals or your own history.")
    return headline, reasons
