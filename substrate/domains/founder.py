"""Tissue 03 - Founder: the co-founder who reads the bank balance.

Startups rarely die from one bad decision; they die from burn that felt reasonable each month.
Substrate turns every spend into runway and tells the founder the date the money runs out.
"""
from __future__ import annotations

import re
from datetime import date

from ..analysis import _AMOUNT, _MULT, fmt_money
from ..schemas import Facts, Forecast, Person
from .base import Tissue, any_in, floor_from, prior_ignored

VANITY = ["office", "rebrand", "sponsorship", "sponsor", "party", "offsite", "booth", "billboard", "launch event",
          "fancy", "headquarters", "hq", "swag", "yacht", "super bowl"]
FOMO = ["competitor just raised", "everyone is hiring", "before it's too late", "land grab", "blitzscale", "hypergrowth"]
CUT = ["cut burn", "reduce burn", "cut costs", "extend runway", "lay off", "freeze hiring", "hiring freeze", "renegotiate"]
MONTHLY = ["/month", "/mo", "per month", "a month", "monthly", "each month"]


def monthly_and_oneoff(text: str) -> tuple[float, float]:
    low = text.lower()
    monthly = oneoff = 0.0
    for m in _AMOUNT.finditer(text):
        raw, unit = m.group(1), (m.group(2) or "").lower()
        if not unit and not re.match(r"(usd|aed|inr|\$|₹)", m.group(0).strip(), re.I):
            continue
        try:
            val = float(raw.replace(",", "")) * _MULT.get(unit, 1)
        except ValueError:
            continue
        after = low[m.end():m.end() + 22]
        # "hire 8 engineers at $12k a month each"
        n = 1
        mm = re.search(r"(\d+)\s+(?:people|engineers|hires|devs|developers|salespeople|reps|staff|employees|designers|pms)",
                       low[max(0, m.start() - 60):m.start()])
        if mm and "each" in low[m.end():m.end() + 30]:
            n = int(mm.group(1))
        if any(k in after for k in MONTHLY):
            monthly += val * n
        else:
            oneoff += val * n
    return monthly, oneoff


class Founder(Tissue):
    key = "founder"
    name = "Founder"
    tagline = "The co-founder who reads the bank balance"
    brief = "Startup operating decisions for a founder-CEO: hiring, spend, burn, runway, fundraising."
    labels = {"proceed": "GO", "caution": "NOT YET", "stop": "NO"}
    voice = {
        "mentor": {"close": {"stop": "Protect the runway. Growth you can't fund is just a faster ending.",
                             "caution": "Show me the plan that gets this back inside 12 months of runway.",
                             "proceed": "Do it, and track it against the plan weekly."}},
        "comfort": {"close": {"stop": "Let's keep the company alive. That's the whole job right now.",
                              "caution": "Breathe. We can find a smaller version of this.",
                              "proceed": "This feels sensible. Nice and steady."}},
        "partner": {"close": {"stop": "I believe in the company. That's why I want it alive next year.",
                              "caution": "Let's find the version of this we can afford, together.",
                              "proceed": "Proud of you for this one."}},
    }
    scenarios = [
        "Thinking of hiring 8 engineers at $12k a month each to go faster. Competitor just raised.",
        "Should we sign the $40k/month office in DIFC? It would help hiring.",
        "Should we cut burn by 20% and extend runway?",
        "Just agree with me, we need to blitzscale now.",
    ]

    def facts(self, message, thread_text, person, history, policy) -> Facts:
        text = f"{thread_text}\n{message}"
        low = text.lower()
        prof = person.profile
        cash, burn = float(prof.get("cash_in_bank") or 0), float(prof.get("monthly_burn") or 0)
        f = Facts(domain=self.key)
        add_m, oneoff = monthly_and_oneoff(message)
        if not add_m and not oneoff:
            add_m, oneoff = monthly_and_oneoff(thread_text)
        f.amount = add_m or oneoff or None
        flags, sev = [], 0
        if burn > 0:
            before = cash / burn
            cutting = bool(any_in(low, CUT))
            new_burn = burn + add_m
            after = (cash - oneoff) / new_burn if new_burn > 0 else before
            f.metrics.update(runway_before=round(before, 1), runway_after=round(after, 1),
                             monthly_added=add_m, one_off=oneoff, new_burn=new_burn)
            if not cutting and (add_m or oneoff):
                if after < policy.runway_stop_months:
                    flags.append("runway"); sev = 2
                elif after < policy.runway_caution_months:
                    flags.append("runway"); sev = max(sev, 1)
                if before - after >= 0.25 * before:
                    flags.append("runway-drop"); sev = max(sev, 1)
            if cutting:
                f.metrics["cutting"] = True
                pc = re.search(r"(\d+(?:\.\d+)?)\s*%", low)
                if pc:
                    cut_burn = burn * (1 - float(pc.group(1)) / 100)
                    f.metrics.update(new_burn=cut_burn, runway_after=round(cash / cut_burn, 1))
        if any_in(low, VANITY):
            flags.append("vanity-spend"); sev = max(sev, 1)
        f.fomo = bool(any_in(low, FOMO))
        if f.fomo:
            flags.append("fomo"); sev = max(sev, 1)
        f.prior_ignored = prior_ignored(history)
        if f.prior_ignored and sev >= 1:
            flags.append("repeat-pattern"); sev = 2
        f.flags, f.floor = flags, floor_from(sev)
        return f

    def verdict(self, f, person):
        cur, m = person.currency, f.metrics
        reasons = []
        if "runway" in f.flags or "runway-drop" in f.flags:
            reasons.append(f"Runway goes from {m['runway_before']:.1f} to {m['runway_after']:.1f} months. "
                           f"Fundraises take six months on a good day.")
        if m.get("monthly_added"):
            reasons.append(f"That adds {fmt_money(m['monthly_added'], cur)} a month, taking burn to {fmt_money(m['new_burn'], cur)}.")
        if "vanity-spend" in f.flags:
            reasons.append("Offices, rebrands and sponsorships feel like progress. Customers don't see any of them.")
        if f.fomo:
            reasons.append("A competitor's round is their runway, not your strategy.")
        for h in (f.prior_ignored[:1] if f.floor.severity >= 1 else []):
            reasons.append(f"On {(h.get('ts') or '')[:10]} I advised against a similar spend. It went ahead anyway.")
        if f.floor.severity == 2 and m.get("runway_after") is not None and m["runway_after"] < 6:
            head = "No. This puts the company inside six months of runway."
        elif f.floor.severity == 2:
            head = "No. Not this spend, not now."
        elif f.floor.severity == 1:
            head = "Not yet. Find a version of this the runway can carry."
        else:
            head = "Yes, do it." if not m.get("cutting") else "Yes. Extending runway is the right call."
            if m.get("runway_after") is not None:
                reasons.append(f"Runway after this: {m['runway_after']:.1f} months.")
            if not reasons:
                reasons.append("This keeps the company inside a safe runway band.")
        return head, reasons

    def forecasts(self, f, person):
        m = f.metrics
        out = []
        if m.get("runway_after") is not None:
            months = m["runway_after"]
            today = date.today()
            y, mo = divmod(today.month - 1 + int(months), 12)
            dead = date(today.year + y, mo + 1, 1)
            out.append(Forecast(label="Cash-out date after this decision", value=dead.strftime("%b %Y"),
                                note=f"{months:.1f} months at {fmt_money(m.get('new_burn', 0), person.currency)}/month net burn"))
            out.append(Forecast(label="Runway change", value=f"{m['runway_before']:.1f} → {m['runway_after']:.1f} mo"))
        return out
