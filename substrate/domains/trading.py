"""Tissue 06 - Trading: FX and gold, read through volatility and the trader's psychology.

What it does:  forecasts how far the price is likely to move (GARCH / EWMA / long-run), turns leverage into a
               probability of being stopped out before the idea plays out, enumerates macro-event combinations,
               and reads the trader's biases and quoted crowd positioning.
What it never does: call direction. When asked "will gold go up?", it says plainly that nobody knows, and shows
               what can be known.
"""
from __future__ import annotations

import re

from .. import behavior, volatility as V
from ..analysis import fmt_money, parse_amount
from ..schemas import Facts, Forecast
from .base import Tissue, floor_from, prior_ignored

PAIRS = {"gold": "XAUUSD", "xau": "XAUUSD", "silver": "XAGUSD", "xag": "XAGUSD", "euro": "EURUSD",
         "cable": "GBPUSD", "pound": "GBPUSD", "sterling": "GBPUSD", "yen": "USDJPY", "rupee": "USDINR",
         "inr": "USDINR", "dirham": "USDAED", "aed": "USDAED", "riyal": "USDSAR", "lira": "USDTRY", "rand": "USDZAR",
         "swissy": "USDCHF", "loonie": "USDCAD", "aussie": "AUDUSD", "kiwi": "NZDUSD", "bitcoin": "BTCUSD"}
EVENTS_RX = re.compile(r"\b(fomc|fed|cpi|nfp|payrolls|ecb|boe|boj|rbi|election|war|opec|jackson hole|rate decision)\b", re.I)


def instrument(text: str) -> str | None:
    m = re.search(r"\b(XAU|XAG|EUR|GBP|USD|JPY|AUD|NZD|CAD|CHF|INR|AED|SAR|TRY|ZAR|CNH|BTC)\s*/?\s*"
                  r"(USD|JPY|EUR|GBP|CHF|CAD|INR|AED|SAR|TRY|ZAR|CNH)\b", text, re.I)
    if m:
        return (m.group(1) + m.group(2)).upper()
    low = text.lower()
    return next((v for k, v in PAIRS.items() if re.search(rf"\b{k}\b", low)), None)


def horizon(text: str) -> float:
    low = text.lower()
    if re.search(r"overnight|tonight|intraday|today", low):
        return 1
    m = re.search(r"(\d+)\s*(day|days|d)\b", low)
    if m:
        return float(m.group(1))
    m = re.search(r"(\d+)\s*weeks?", low)
    if m:
        return 5 * float(m.group(1))
    if "a week" in low or "this week" in low or "next week" in low:
        return 5
    if "a month" in low or "this month" in low:
        return 21
    return 5


def leverage(text: str) -> float:
    m = re.search(r"\b(\d{1,4})\s*(?::\s*1|x)\b", text, re.I)
    return float(m.group(1)) if m and float(m.group(1)) > 1 else 1.0


def stop_pct(text: str) -> float | None:
    m = re.search(r"stop(?:[- ]loss)?\s*(?:at|of|is)?\s*(\d+(?:\.\d+)?)\s*%", text, re.I)
    return float(m.group(1)) if m else None


class Trading(Tissue):
    key = "trading"
    name = "Trading"
    tagline = "FX and gold: volatility and the trader, never a fake forecast"
    brief = ("Leveraged FX and gold trading for a retail or private-banking client. Judge position size, leverage, "
             "stop distance and the trader's biases against forecast volatility. Never predict price direction.")
    labels = {"proceed": "TRADE OK", "caution": "REDUCE", "stop": "DON'T TRADE"}
    default_temperament = "mentor"
    voice = {
        "surgeon": {"close": {"stop": "Recommendation: flat. Re-enter only at a size the volatility allows.",
                              "caution": "Recommendation: cut leverage until a normal move can't stop you out.",
                              "proceed": "Recommendation: proceed with the stop where it is. Log it."}},
        "boss": {"close": {"stop": "No trade. Close the platform.", "caution": "Halve it. Then check again.",
                           "proceed": "Fine. Respect the stop."}},
    }
    scenarios = [
        "Gold fell 5 days in a row, it must bounce. Going long XAU/USD 50:1, $100k, overnight. 80% of retail are long.",
        "Down $8k this week. Doubling up on EUR/USD 100:1 to make it back before NFP.",
        "Will gold go up next week?",
        "Long EURUSD $20k for a week, no leverage, stop at 1.5%.",
    ]

    def facts(self, message, thread_text, person, history, policy):
        text = f"{thread_text}\n{message}"
        prof = person.profile or {}
        f = Facts(domain=self.key)
        pair = instrument(message) or instrument(thread_text) or prof.get("default_pair") or "XAUUSD"
        # pushback turns ("just this once") carry no numbers: the trade on the table is the one in the thread
        specific = bool(parse_amount(message) or leverage(message) > 1 or instrument(message) or stop_pct(message))
        src = message if specific or not thread_text.strip() else f"{thread_text}\n{message}"
        lev = leverage(src)
        if lev == 1 and re.search(r"\b(leverage|margin)\b", src, re.I) and \
                not re.search(r"\b(no|without)\s+(leverage|margin)|unleveraged", src, re.I):
            lev = float(prof.get("leverage") or 1)   # "on my usual leverage"
        notional = parse_amount(src)
        f.amount = notional
        hz = horizon(src)
        series = (prof.get("price_series") or {}).get(pair)
        event_week = bool(EVENTS_RX.search(text))
        a = V.analyze(pair, prices=series, horizon_days=hz, leverage=lev, stop_pct=stop_pct(src),
                      notional=notional, event_week=event_week)
        bh = behavior.read(src)
        m = f.metrics
        m.update(pair=pair, horizon_days=hz, leverage=lev, vol_annual=a["vol_annual"], risk_vol=a["risk_vol"],
                 method=a["method"], move_1sd_pct=a["bands"]["move_1sd_pct"], move_2sd_pct=a["bands"]["move_2sd_pct"],
                 event_week=event_week, scenarios=a["scenarios"]["combinations"],
                 sequences=a["scenarios"]["sequences"], scenario_vol=a["scenarios"]["expected_vol"],
                 worst=a["scenarios"]["worst_plausible"][0] if a["scenarios"]["worst_plausible"] else None,
                 behavior_score=bh["score"], behavior_band=bh["band"], biases=[b["key"] for b in bh["biases"]],
                 crowd=bh["crowd"])
        if "margin" in a:
            m.update(stop_out_move_pct=a["margin"]["adverse_move_to_stop_out_pct"], p_stop_out=a["margin"]["p_stop_out"])
        if "stop" in a:
            m.update(stop_pct=a["stop"]["stop_pct"], p_stop_hit=a["stop"]["p_stop_hit"])
        if notional:
            m.update(loss_2sd=a.get("loss_2sd"), margin_used=a.get("margin_used"))
        f.asset = pair
        flags, sev = [], 0
        pso = m.get("p_stop_out")
        if pso is not None:
            if pso >= 0.25:
                flags.append("leverage"); sev = 2
            elif pso >= 0.05:
                flags.append("leverage"); sev = max(sev, 1)
        nw = person.liquid_net_worth or prof.get("account_size")
        if nw and m.get("loss_2sd"):
            share = m["loss_2sd"] / nw
            m["loss_2sd_share"] = round(share, 3)
            if share > 0.10:
                flags.append("oversized"); sev = 2
            elif share > 0.03:
                flags.append("oversized"); sev = max(sev, 1)
        keys = set(m["biases"])
        if "revenge-trading" in keys:
            flags.append("chasing"); sev = 2
        for k, fl in (("gamblers-fallacy", "gamblers-fallacy"), ("anchoring", "anchoring"),
                      ("disposition", "disposition"), ("overconfidence", "certainty"), ("herding", "fomo"),
                      ("recency", "recency")):
            if k in keys:
                flags.append(fl); sev = max(sev, 1)
        crowd = bh["crowd"]
        if crowd and crowd["extreme"]:
            side = "long" if re.search(r"\b(long|buy|buying)\b", src, re.I) else \
                "short" if re.search(r"\b(short|sell|selling)\b", src, re.I) else None
            if side == crowd["side"]:
                flags.append("crowded-trade"); sev = max(sev, 1)
        if "prediction-ask" in keys:
            flags.append("prediction-ask")
        late = re.search(r"(?<![a-z])(1am|2am|3am|midnight|tonight|overnight)(?![a-z])", src.lower())
        if late and lev >= 20:
            flags.append("late-night"); sev = max(sev, 1)
        f.leverage = lev > 1
        f.prior_ignored = [h for h in prior_ignored(history) if set(h.get("flags") or []) & set(flags)]
        if f.prior_ignored and sev >= 1:
            flags.append("repeat-pattern"); sev = 2
        f.flags, f.floor = list(dict.fromkeys(flags)), floor_from(sev)
        return f

    def verdict(self, f, person):
        m, cur, r = f.metrics, person.currency, []
        if "prediction-ask" in f.flags and not f.amount:
            r.append("Nobody can tell you where " + m["pair"] + " goes next, and anyone who claims to is selling "
                     "something. What can be estimated is how far it moves.")
            r.append(f"Over {m['horizon_days']:g} trading day{'s' if m['horizon_days'] != 1 else ''}, a typical (1-sigma) "
                     f"move is about {m['move_1sd_pct']}%, and 1 in 20 moves exceeds {m['move_2sd_pct']}% "
                     f"({m['method']}, {m['vol_annual'] * 100:.1f}% annualised).")
            if m.get("event_week"):
                r.append(f"With events on the calendar, {m['scenarios']} outcome combinations take expected "
                         f"volatility to {m['scenario_vol'] * 100:.1f}%.")
            m["label_override"] = "NO CALL"
            m["voice_override"] = {"open": {"proceed": ""},
                                   "close": {"proceed": "Size any trade for the move, never for the hope."}}
            m["quiet"] = True
            return "No one can call the direction. Here is what can be known.", r
        if "chasing" in f.flags:
            r.append(behavior.BIASES[3][4])
        if m.get("p_stop_out") is not None:
            r.append(f"At {m['leverage']:g}:1, a {m['stop_out_move_pct']:.2f}% move against you stops you out. "
                     f"{m['pair']} moves that far within {m['horizon_days']:g} day{'s' if m['horizon_days'] != 1 else ''} "
                     f"about {m['p_stop_out']:.0%} of the time, whatever happens next.")
        if m.get("p_stop_hit") is not None:
            r.append(f"Your {m['stop_pct']}% stop gets touched about {m['p_stop_hit']:.0%} of the time over this horizon"
                     + (": it sits inside normal noise." if m["p_stop_hit"] > 0.5 else "."))
        if m.get("loss_2sd") and "oversized" in f.flags:
            r.append(f"A 1-in-20 move costs about {fmt_money(m['loss_2sd'], cur)}, "
                     f"{m['loss_2sd_share']:.0%} of your capital.")
        for k in ("gamblers-fallacy", "anchoring", "disposition", "overconfidence", "herding", "recency"):
            if k in m["biases"]:
                b = next(x for x in behavior.BIASES if x[0] == k)
                r.append(f"{b[2]}: {b[4]}")
        if "crowded-trade" in f.flags:
            r.append(m["crowd"]["read"])
        if m.get("event_week") and m.get("worst"):
            r.append(f"{m['scenarios']} event combinations ({m['sequences']} possible sequences). The worst plausible, "
                     f"{m['worst']['path']}, runs volatility near {m['worst']['vol'] * 100:.0f}% annualised.")
        for h in (f.prior_ignored[:1] if f.floor.severity >= 1 else []):
            r.append(f"On {(h.get('ts') or '')[:10]} I said '{h.get('headline')}'. It went ahead anyway.")
        r.append("I'm not forecasting direction. This is about size, leverage and the person placing the trade.")
        if f.floor.severity == 2:
            head = "Don't trade this. The size and leverage decide the outcome before the market does."
            if "chasing" in f.flags:
                head = "Don't trade this. Revenge trades are sized by the loss, not the idea."
        elif f.floor.severity == 1:
            head = "Reduce it. The idea may be fine; the setup is fragile."
        else:
            head = "This trade is sized for normal volatility."
        return head, r

    def forecasts(self, f, person):
        m, out = f.metrics, []
        if not m.get("pair"):
            return out
        out.append(Forecast(label=f"{m['pair']} typical move, {m['horizon_days']:g}d (1σ)", value=f"±{m['move_1sd_pct']}%",
                            note=f"{m['method']} · {m['vol_annual'] * 100:.1f}% annualised · direction not forecast"))
        out.append(Forecast(label="1-in-20 move (2σ)", value=f"±{m['move_2sd_pct']}%"))
        if m.get("p_stop_out") is not None:
            out.append(Forecast(label="Chance of stop-out before horizon", value=f"{m['p_stop_out']:.0%}",
                                note=f"{m['leverage']:g}:1 leverage, {m['stop_out_move_pct']:.2f}% adverse move"))
        if m.get("p_stop_hit") is not None:
            out.append(Forecast(label="Chance your stop is touched", value=f"{m['p_stop_hit']:.0%}"))
        if m.get("event_week"):
            out.append(Forecast(label="Event-scenario volatility", value=f"{m['scenario_vol'] * 100:.1f}%",
                                note=f"{m['scenarios']} combinations, {m['sequences']} sequences"))
        out.append(Forecast(label="Behavioural risk", value=f"{m['behavior_score']}/100",
                            note=m["behavior_band"] + (": " + ", ".join(m["biases"]) if m["biases"] else "")))
        return out
