"""Volatility, not prophecy: how far FX and gold are likely to move, and what that means for one position.

Direction is not forecastable with any reliability (and anyone selling a direction call is selling hope). The
size of moves is: volatility clusters, and decades of evidence support EWMA and GARCH as practical forecasters.
Everything here is plain-Python and auditable.

  realized_vol     close-to-close log returns, annualised
  ewma_vol         RiskMetrics exponentially weighted (lambda 0.94)
  garch11          GARCH(1,1) by variance-targeted maximum likelihood (grid search), with h-step forecast
  bands            1-sigma and 2-sigma lognormal price ranges over a horizon
  p_touch          probability the price touches a level before the horizon (reflection principle, driftless)
  margin_distance  how far price can move against a leveraged position before a stop-out
  scenarios        every combination of event outcomes (Cartesian product), joint probabilities, vol multipliers
"""
from __future__ import annotations

import itertools
import math
import os

import httpx

DAYS = 252

# Approximate long-run annualised volatilities, used only when no price series is supplied. Pegged pairs are
# near zero by construction; they can still de-peg, which is a tail risk, not a volatility estimate.
DEFAULT_VOL = {
    "XAUUSD": 0.15, "XAGUSD": 0.27, "EURUSD": 0.075, "GBPUSD": 0.085, "USDJPY": 0.095, "AUDUSD": 0.10,
    "USDCHF": 0.08, "USDCAD": 0.065, "NZDUSD": 0.105, "USDINR": 0.045, "USDCNH": 0.045, "USDTRY": 0.20,
    "USDZAR": 0.16, "USDAED": 0.002, "USDSAR": 0.002, "EURGBP": 0.06, "BTCUSD": 0.60,
}

# Illustrative macro event set for FX and gold. Probabilities and multipliers are placeholders a desk should
# replace with its own (or with market-implied odds); the arithmetic is the point.
DEFAULT_EVENTS = [
    {"name": "Fed decision", "outcomes": [{"label": "hike", "p": 0.15, "vol_mult": 1.30},
                                          {"label": "hold", "p": 0.60, "vol_mult": 1.00},
                                          {"label": "cut", "p": 0.25, "vol_mult": 1.25}]},
    {"name": "US CPI", "outcomes": [{"label": "hot", "p": 0.30, "vol_mult": 1.25},
                                    {"label": "in line", "p": 0.50, "vol_mult": 1.00},
                                    {"label": "cool", "p": 0.20, "vol_mult": 1.15}]},
    {"name": "Geopolitics", "outcomes": [{"label": "calm", "p": 0.80, "vol_mult": 1.00},
                                         {"label": "shock", "p": 0.20, "vol_mult": 1.60}]},
]


def _ncdf(x: float) -> float:
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def returns(prices: list[float]) -> list[float]:
    p = [float(x) for x in prices if x and x > 0]
    return [math.log(b / a) for a, b in zip(p, p[1:])]


def realized_vol(r: list[float]) -> float:
    if len(r) < 2:
        return 0.0
    m = sum(r) / len(r)
    return math.sqrt(sum((x - m) ** 2 for x in r) / (len(r) - 1)) * math.sqrt(DAYS)


def ewma_vol(r: list[float], lam: float = 0.94) -> float:
    if not r:
        return 0.0
    var = r[0] ** 2
    for x in r[1:]:
        var = lam * var + (1 - lam) * x * x
    return math.sqrt(var * DAYS)


def garch11(r: list[float], horizon: int = 5) -> dict | None:
    """Variance-targeted GARCH(1,1) by grid-search MLE. Returns params and the average vol over the horizon."""
    if len(r) < 30:
        return None
    m = sum(r) / len(r)
    e = [x - m for x in r]
    vl = sum(x * x for x in e) / len(e)            # long-run daily variance
    best = None
    for a in [0.02, 0.04, 0.06, 0.08, 0.10, 0.13, 0.16, 0.20]:
        for b in [0.70, 0.75, 0.80, 0.85, 0.88, 0.90, 0.92, 0.94, 0.96]:
            if a + b >= 0.999:
                continue
            w, var, ll = vl * (1 - a - b), vl, 0.0
            for x in e:
                ll += -0.5 * (math.log(2 * math.pi * var) + x * x / var)
                var = w + a * x * x + b * var
            if best is None or ll > best[0]:
                best = (ll, a, b, var)
    _, a, b, nxt = best
    path = [vl + (a + b) ** (h - 1) * (nxt - vl) for h in range(1, horizon + 1)]
    return {"alpha": a, "beta": b, "persistence": round(a + b, 3), "long_run_vol": round(math.sqrt(vl * DAYS), 4),
            "next_day_vol": round(math.sqrt(nxt * DAYS), 4),
            "horizon_vol": round(math.sqrt(sum(path) / len(path) * DAYS), 4)}


def bands(price: float | None, vol_annual: float, days: float) -> dict:
    s = vol_annual * math.sqrt(max(days, 1e-9) / DAYS)
    out = {"move_1sd_pct": round(100 * (math.exp(s) - 1), 2), "move_2sd_pct": round(100 * (math.exp(2 * s) - 1), 2)}
    if price:
        out.update(range_1sd=[round(price * math.exp(-s), 4), round(price * math.exp(s), 4)],
                   range_2sd=[round(price * math.exp(-2 * s), 4), round(price * math.exp(2 * s), 4)])
    return out


def p_touch(distance_pct: float, vol_annual: float, days: float) -> float:
    """P(price touches a level `distance_pct` away at any time before the horizon), driftless reflection."""
    if distance_pct <= 0:
        return 1.0
    s = vol_annual * math.sqrt(max(days, 1e-9) / DAYS)
    if s <= 0:
        return 0.0
    return min(1.0, 2 * (1 - _ncdf(abs(math.log(1 + distance_pct / 100)) / s)))


def margin_distance(leverage: float, stop_out: float = 0.5) -> float:
    """% adverse move that consumes (1 - stop_out) of the margin, e.g. 50:1 with 50% stop-out -> 1.0%."""
    return 100 * (1 - stop_out) / max(leverage, 1.0)


def scenarios(base_vol: float, events: list[dict] | None = None, top: int = 3) -> dict:
    ev = events or DEFAULT_EVENTS
    norm = []
    for e in ev:
        tot = sum(o["p"] for o in e["outcomes"]) or 1
        norm.append([{**o, "p": o["p"] / tot, "event": e["name"]} for o in e["outcomes"]])
    combos = []
    for combo in itertools.product(*norm):
        p = math.prod(o["p"] for o in combo)
        mult = math.prod(o["vol_mult"] for o in combo)
        combos.append({"path": " + ".join(f"{o['event']}: {o['label']}" for o in combo), "p": p,
                       "vol": base_vol * mult, "mult": mult})
    exp_var = sum(c["p"] * c["vol"] ** 2 for c in combos)
    worst = sorted([c for c in combos if c["p"] >= 0.01], key=lambda c: -c["mult"])[:top]
    likely = sorted(combos, key=lambda c: -c["p"])[:top]
    fmt = lambda c: {"path": c["path"], "p": round(c["p"], 4), "vol": round(c["vol"], 4)}  # noqa: E731
    p_high = sum(c["p"] for c in combos if c["mult"] >= 1.5)
    return {"combinations": len(combos), "orderings": math.factorial(len(ev)),
            "sequences": len(combos) * math.factorial(len(ev)),
            "expected_vol": round(math.sqrt(exp_var), 4), "p_high_vol_regime": round(p_high, 4),
            "most_likely": [fmt(c) for c in likely], "worst_plausible": [fmt(c) for c in worst],
            "note": "Each combination's probability is the product of its outcomes (events treated as independent). "
                    "Orderings count the n! sequences in which the events can land."}


FRANKFURTER = os.environ.get("FRANKFURTER_URL", "https://api.frankfurter.app")


def fx_history(pair: str, days: int = 120, timeout: float = 6.0) -> list[float]:
    """Daily ECB reference rates via the free Frankfurter API (no key). Best effort; empty list on failure."""
    from datetime import date, timedelta
    base, quote = pair[:3].upper(), pair[3:6].upper()
    if "XAU" in (base, quote) or "XAG" in (base, quote):
        return []
    start = (date.today() - timedelta(days=int(days * 1.5))).isoformat()
    try:
        r = httpx.get(f"{FRANKFURTER}/{start}..", params={"from": base, "to": quote}, timeout=timeout)
        r.raise_for_status()
        rates = r.json().get("rates", {})
        return [v[quote] for _, v in sorted(rates.items()) if quote in v][-days:]
    except Exception:
        return []


def analyze(pair: str, price: float | None = None, prices: list[float] | None = None, horizon_days: float = 5,
            leverage: float = 1, stop_pct: float | None = None, notional: float | None = None,
            events: list[dict] | None = None, stop_out: float = 0.5, live: bool = False,
            event_week: bool = False) -> dict:
    pair = pair.upper().replace("/", "")
    series = list(prices or [])
    source = "client series"
    if not series and live:
        series, source = fx_history(pair), "ECB via Frankfurter"
    r = returns(series)
    g = garch11(r, int(max(1, round(horizon_days)))) if len(r) >= 30 else None
    if len(r) >= 10:
        vol = g["horizon_vol"] if g else ewma_vol(r)
        method = "GARCH(1,1)" if g else "EWMA (lambda 0.94)"
    else:
        vol, method, source = DEFAULT_VOL.get(pair, 0.12), "long-run default", "default table"
    price = price or (series[-1] if series else None)
    sc = scenarios(vol, events)
    risk_vol = sc["expected_vol"] if (events or event_week) else vol   # event risk only when events are in play
    out = {"pair": pair, "method": method, "source": source, "observations": len(series),
           "vol_annual": round(vol, 4), "realized_vol": round(realized_vol(r), 4) if r else None,
           "ewma_vol": round(ewma_vol(r), 4) if r else None, "garch": g, "horizon_days": horizon_days,
           "bands": bands(price, vol, horizon_days), "scenario_bands": bands(price, sc["expected_vol"], horizon_days),
           "risk_vol": round(risk_vol, 4), "event_risk_applied": bool(events or event_week),
           "scenarios": sc, "direction": "not forecast: no model predicts direction reliably"}
    if leverage and leverage > 1:
        md = margin_distance(leverage, stop_out)
        out["margin"] = {"leverage": leverage, "adverse_move_to_stop_out_pct": round(md, 3),
                         "p_stop_out": round(p_touch(md, risk_vol, horizon_days), 4)}
    if stop_pct:
        out["stop"] = {"stop_pct": stop_pct, "p_stop_hit": round(p_touch(stop_pct, risk_vol, horizon_days), 4)}
    if notional:
        s2 = bands(price, risk_vol, horizon_days)["move_2sd_pct"] / 100
        out["loss_2sd"] = round(notional * s2, 2)
        out["margin_used"] = round(notional / max(leverage or 1, 1), 2)
    return out
