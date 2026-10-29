"""Bet math as a service, and live prices from public prediction markets.

`analyze` is stateless: price, belief, stake, bankroll, legs -> the arithmetic Substrate would use, with no
genome needed. Built for platforms (Polymarket front-ends, Kalshi clients, sportsbooks) that want an honest
"before you place this" panel without sending any user data.

`polymarket_price` reads Polymarket's public Gamma API (no key) for a market slug. Best effort: if the
network or schema fails, callers fall back to the price the user typed.
"""
from __future__ import annotations

import json
import math
import os

import httpx
from pydantic import BaseModel, Field

from .domains.markets import kelly_binary

GAMMA = os.environ.get("POLYMARKET_GAMMA_URL", "https://gamma-api.polymarket.com")


class Leg(BaseModel):
    price: float = Field(..., gt=0, lt=1, description="Contract price 0-1, or 1/decimal odds")
    belief: float | None = Field(None, ge=0, le=1)


class BetMath(BaseModel):
    price: float | None = Field(None, gt=0, lt=1, description="Single-market price 0-1 (62c = 0.62)")
    decimal_odds: float | None = Field(None, gt=1)
    american_odds: int | None = None
    belief: float | None = Field(None, ge=0, le=1, description="Your probability")
    stake: float | None = Field(None, gt=0)
    bankroll: float | None = Field(None, gt=0)
    fee: float = Field(0.02, ge=0, le=0.2)
    kelly_fraction: float = Field(0.25, gt=0, le=1)
    max_bet_fraction: float = Field(0.02, gt=0, le=1)
    legs: list[Leg] = Field(default_factory=list, description="Parlay legs; probabilities multiply")
    round_robin: tuple[int, int] | None = Field(None, description="(picks, size), e.g. (5, 2) -> C(5,2) bets")


def _price(b: BetMath) -> float | None:
    if b.price:
        return b.price
    if b.decimal_odds:
        return 1 / b.decimal_odds
    if b.american_odds:
        a = b.american_odds
        return 1 / (1 + (a / 100 if a > 0 else 100 / abs(a)))
    return None


def analyze(b: BetMath) -> dict:
    out: dict = {"inputs": b.model_dump()}
    price, belief = _price(b), b.belief
    if b.legs:
        joint_mkt = math.prod(l.price for l in b.legs)
        beliefs = [l.belief for l in b.legs]
        joint_you = math.prod(beliefs) if all(x is not None for x in beliefs) else None
        out["parlay"] = {"legs": len(b.legs), "joint_market_prob": round(joint_mkt, 5),
                         "joint_your_prob": round(joint_you, 5) if joint_you is not None else None,
                         "one_in": round(1 / joint_mkt, 1),
                         "note": "Assumes independent legs. Correlated legs are usually priced worse by the book."}
        price, belief = joint_mkt, joint_you if joint_you is not None else belief
    if b.round_robin:
        n, k = b.round_robin
        bets = math.comb(n, k)
        out["round_robin"] = {"picks": n, "size": k, "bets": bets,
                              "total_stake": round(b.stake * bets, 2) if b.stake else None}
    if price is None:
        out["verdict"] = "Need a price or odds."
        return out
    cost = min(0.999, price * (1 + b.fee))
    out["market"] = {"implied_prob": round(price, 4), "cost_after_fees": round(cost, 4),
                     "ev_per_dollar_at_market": round(price / cost - 1, 4)}
    if belief is not None:
        k = kelly_binary(belief, cost)
        out["edge"] = {"your_prob": round(belief, 4), "edge_points": round(100 * (belief - cost), 2),
                       "ev_per_dollar_yours": round(belief / cost - 1, 4),
                       "kelly_full": round(k, 4), "kelly_used": round(k * b.kelly_fraction, 4)}
        if b.bankroll:
            frac = min(k * b.kelly_fraction, b.max_bet_fraction)
            out["edge"]["recommended_stake"] = round(b.bankroll * frac, 2)
    total = (out.get("round_robin") or {}).get("total_stake") or b.stake
    if total and b.bankroll:
        out["bankroll_share"] = round(total / b.bankroll, 4)
    p_hit = belief if belief is not None else price
    out["risk"] = {"p_lose_stake": round(1 - p_hit, 4), "p_five_losses_in_row": round((1 - p_hit) ** 5, 4),
                   "expected_loss_at_market": round(-(price / cost - 1) * total, 2) if total else None}
    edge = out.get("edge", {}).get("edge_points")
    share = out.get("bankroll_share")
    if (share or 0) > 0.15:
        v = "NO BET"
    elif edge is not None and edge <= 0:
        v = "NO BET"
    elif (share or 0) > 0.05 or (b.legs and price < 0.2) or (
            edge is not None and b.bankroll and total and total > 2 * out["edge"].get("recommended_stake", 0)):
        v = "SIZE DOWN"
    elif edge is None:
        v = "NO EDGE STATED"
    else:
        v = "SIZED RIGHT"
    out["verdict"] = v
    return out


def polymarket_price(slug: str, outcome: str = "Yes", timeout: float = 6.0) -> dict:
    r = httpx.get(f"{GAMMA}/markets", params={"slug": slug}, timeout=timeout)
    r.raise_for_status()
    rows = r.json()
    m = rows[0] if isinstance(rows, list) and rows else rows
    outcomes = m.get("outcomes")
    prices = m.get("outcomePrices")
    outcomes = json.loads(outcomes) if isinstance(outcomes, str) else outcomes
    prices = [float(x) for x in (json.loads(prices) if isinstance(prices, str) else prices)]
    idx = next((i for i, o in enumerate(outcomes) if str(o).lower() == outcome.lower()), 0)
    return {"slug": slug, "question": m.get("question"), "outcome": outcomes[idx], "price": prices[idx],
            "outcomes": dict(zip(outcomes, prices)), "volume": m.get("volume"), "end_date": m.get("endDate"),
            "source": "polymarket-gamma"}
