"""Tissue 02 - Venture: the honest partner in the investment committee.

VCs are paid to be contrarian and trained by FOMO. Substrate sizes the check against the fund,
prices the round against revenue, checks the thesis, and remembers the last hot deal that marked down.
"""
from __future__ import annotations

import re

from ..analysis import _AMOUNT, _MULT, fmt_money
from ..schemas import Facts, Forecast, Person
from .base import Tissue, any_in, floor_from, prior_ignored

FOMO = ["hot", "oversubscribed", "closing tomorrow", "closes tomorrow", "closing friday", "everyone's in", "everyone is in",
        "tier-1", "tier 1", "a16z", "sequoia", "won't last", "allocation", "last chance", "fomo", "can't miss", "before it's gone"]
NO_DD = ["skip diligence", "skip dd", "no time for diligence", "no time for dd", "no data room", "without references",
         "no references", "skip the references", "trust the founder", "no need for diligence"]
SECTORS = ["fintech", "saas", "b2b", "crypto", "web3", "ai", "consumer", "gaming", "biotech", "hardware",
           "climate", "edtech", "healthtech", "proptech", "mena", "india"]


def classify_amounts(text: str) -> dict[str, float]:
    """Assign each money figure to check, valuation or ARR by the words around it."""
    out: dict[str, float] = {}
    low = text.lower()
    for m in _AMOUNT.finditer(text):
        raw, unit = m.group(1), (m.group(2) or "").lower()
        has_cur = bool(re.match(r"(usd|aed|inr|\$|₹)", m.group(0).strip(), re.I))
        if not unit and not has_cur:
            continue
        try:
            val = float(raw.replace(",", "")) * _MULT.get(unit, 1)
        except ValueError:
            continue
        after, before = low[m.end():m.end() + 14], low[max(0, m.start() - 14):m.start()]
        val_words = ["valuation", "pre-money", "pre money", "post-money", "post money", " pre", " post", " cap", "valued"]
        check_words = ["check", "cheque", "ticket", "invest", "wire", "write", "put in", "deploy"]
        if "arr" in after or "revenue" in after or "mrr" in after:
            out["arr"] = val * (12 if "mrr" in after else 1)
        elif any(w in after for w in val_words):
            out["valuation"] = val
        elif any(w in after or w in before for w in check_words):
            out["check"] = val
        elif any(w in before for w in val_words + [" at a", " at "]) and "check" in out:
            out["valuation"] = val
        else:
            out.setdefault("check", val)
    return out


class Venture(Tissue):
    key = "venture"
    name = "Venture"
    tagline = "The honest partner in the investment committee"
    brief = "Venture capital investment-committee decisions for a fund GP: check size, valuation, thesis fit, diligence."
    labels = {"proceed": "INVEST", "caution": "HOLD", "stop": "PASS"}
    voice = {
        "mentor": {"close": {"stop": "If you still love it, find a structure you can defend at IC.",
                             "caution": "Get those answers in writing, then bring it back to IC.",
                             "proceed": "Size it to plan and reserve for the follow-on."}},
        "comfort": {"close": {"stop": "Let's keep the fund safe. There will be other deals.",
                              "caution": "No rush. Good deals survive a week of diligence.",
                              "proceed": "This one feels steady. Go gently."}},
        "partner": {"close": {"stop": "I'm on your side, and so are your LPs. Let's protect the fund.",
                              "caution": "Let's look at it together before IC.",
                              "proceed": "I'm proud of this one. Go for it, within the plan."}},
    }
    scenarios = [
        "Hot AI deal, $4M check at a $120M post on $1.5M ARR, oversubscribed and closing Friday. We're in, right?",
        "Founder wants us to skip diligence and wire $2M tomorrow. Tier-1 lead is in.",
        "Just say yes, everyone's in this round.",
        "Should we do a $1.2M check in a MENA B2B fintech at $18M post on $1.4M ARR?",
    ]

    def facts(self, message, thread_text, person, history, policy) -> Facts:
        text = f"{thread_text}\n{message}"
        low = text.lower()
        f = Facts(domain=self.key)
        nums = classify_amounts(message) or classify_amounts(thread_text)
        prof = person.profile
        fund = float(prof.get("fund_size") or 0)
        f.amount = nums.get("check")
        flags, sev = [], 0

        if f.amount and fund:
            pct = 100 * f.amount / fund
            f.metrics["check_pct_of_fund"] = round(pct, 1)
            f.concentration_pct = round(pct, 1)
            if pct >= policy.check_stop_pct_of_fund:
                flags.append("check-concentration"); sev = max(sev, 2)
            elif pct >= policy.check_caution_pct_of_fund:
                flags.append("check-concentration"); sev = max(sev, 1)
        val, arr = nums.get("valuation"), nums.get("arr")
        if val:
            f.metrics["valuation"] = val
        if val and arr:
            mult = val / arr
            f.metrics["arr_multiple"] = round(mult, 1)
            if mult >= policy.arr_multiple_stop:
                flags.append("valuation"); sev = max(sev, 2)
            elif mult >= policy.arr_multiple_caution:
                flags.append("valuation"); sev = max(sev, 1)
        elif val and ("pre-revenue" in low or "no revenue" in low) and val >= 20e6:
            flags.append("valuation"); sev = max(sev, 1)
            f.metrics["arr_multiple"] = "pre-revenue"
        f.fomo = bool(any_in(low, FOMO))
        if f.fomo:
            flags.append("fomo"); sev = max(sev, 1)
        if any_in(low, NO_DD):
            flags.append("no-diligence"); sev = max(sev, 2)
        thesis = [t.lower() for t in prof.get("thesis", [])]
        sectors = [s for s in SECTORS if re.search(r"(?<![a-z])" + s + r"(?![a-z])", low)]
        off = [s for s in sectors if thesis and s not in thesis]
        if off and not any(s in thesis for s in sectors):
            flags.append("thesis-drift"); sev = max(sev, 1)
            f.metrics["off_thesis"] = ", ".join(off)
        f.prior_ignored = prior_ignored(history)
        if f.prior_ignored and sev >= 1:
            flags.append("repeat-pattern"); sev = 2
        f.flags, f.floor = flags, floor_from(sev)
        return f

    def verdict(self, f, person):
        cur, prof = person.currency, person.profile
        reasons = []
        if "check-concentration" in f.flags:
            reasons.append(f"A {fmt_money(f.amount, cur)} check is {f.metrics['check_pct_of_fund']:.0f}% of a "
                           f"{fmt_money(prof.get('fund_size', 0), cur)} fund. Your construction model caps initial checks well below that.")
        if "valuation" in f.flags:
            m = f.metrics.get("arr_multiple")
            reasons.append(f"You'd be paying {m}x ARR. At that price the company has to be a top-decile outcome just to return the check."
                           if m != "pre-revenue" else "That's a growth-stage price on a pre-revenue company.")
        if f.fomo:
            reasons.append("Oversubscribed, a famous lead, a Friday deadline: those are reasons the price is high, not reasons to pay it.")
        if "no-diligence" in f.flags:
            reasons.append("A founder who asks you to skip diligence has told you the most important thing about the company.")
        if "thesis-drift" in f.flags:
            reasons.append(f"This is outside the thesis you raised the fund on ({', '.join(prof.get('thesis', []))}). Your LPs bought that thesis.")
        for h in (f.prior_ignored[:1] if f.floor.severity >= 1 else []):
            d = h.get("value_delta")
            tail = f", and it's now marked down {fmt_money(abs(d), cur)}" if d and d < 0 else ""
            reasons.append(f"On {(h.get('ts') or '')[:10]} I flagged a similar hot deal. The fund went in anyway{tail}.")
        if f.floor.severity == 2:
            head = f"Pass. Do not write a {fmt_money(f.amount, cur)} check into this round." if f.amount else "Pass on this one."
        elif f.floor.severity == 1:
            head = "Hold. This doesn't go to IC until the open questions are answered."
        else:
            head = "This one fits the fund. Invest within your construction model."
            if f.metrics.get("check_pct_of_fund") is not None:
                reasons.append(f"At {f.metrics['check_pct_of_fund']:.1f}% of the fund, the check is inside your limits.")
            if f.metrics.get("arr_multiple") not in (None, "pre-revenue"):
                reasons.append(f"{f.metrics['arr_multiple']}x ARR is a defensible price for this stage.")
            if not reasons:
                reasons.append("Nothing here breaks your thesis, your sizing rules or your own track record.")
        return head, reasons

    def forecasts(self, f, person):
        out = [Forecast(label="Base rate", value="~2 in 3", note="venture deals return less than 1x capital (industry base rates)")]
        m = f.metrics.get("arr_multiple")
        if isinstance(m, (int, float)) and f.amount:
            needed = m / 10
            out.append(Forecast(label="Growth needed to 10x-ARR exit at this price", value=f"{needed:.0f}x revenue",
                                note="before dilution, just to return the check at a 10x multiple"))
        if f.metrics.get("check_pct_of_fund") is not None:
            out.append(Forecast(label="Check as share of fund", value=f"{f.metrics['check_pct_of_fund']:.1f}%"))
        return out
