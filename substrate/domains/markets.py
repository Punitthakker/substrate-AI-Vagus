"""Tissue 05 - Markets: the honest brake on prediction markets, betting and games of chance.

Polymarket, Kalshi, sportsbooks, casino-style games. Substrate is never the tipster. It is the one voice
in the room that does the arithmetic people avoid at the moment they least want it:

  price -> probability     a Polymarket share at 62c is the crowd saying 62%. Your edge is your belief minus that.
  combinatorics            a parlay's legs multiply. Six legs that each "feel like 70%" hit 11.8% of the time.
                           A round robin of 2s from 5 picks is C(5,2) = 10 bets, so 10x the stake.
  sizing                   fractional Kelly on the edge you claim, capped by bankroll policy. No edge, no bet.
  tilt                     chasing losses, doubling down, "can't lose", late nights: the human, not the market.
  harm                     borrowed money, rent money, hiding it, can't stop -> no bet, and a route to support.

Numbers are computed, never guessed. The verdict comes from the arithmetic and the pattern, not from a mood.
"""
from __future__ import annotations

import math
import re

from ..analysis import fmt_money, parse_amount
from ..schemas import Facts, Forecast
from .base import Tissue, any_in, floor_from, prior_ignored

CHASE = ["win it back", "make it back", "get it back", "chase", "double down", "doubling down", "one more bet",
         "recover my loss", "recoup", "lost again", "down bad", "need a win"]
CERTAIN = ["can't lose", "cant lose", "sure thing", "lock", "guaranteed", "free money", "100%", "no way it loses",
           "easy money", "certain"]
ALL_IN = ["all in", "all-in", "max bet", "everything on", "whole bankroll", "entire bankroll", "yolo"]
HARM = ["borrowed", "borrow money", "loan to bet", "rent money", "credit card to bet", "can't stop betting",
        "cant stop betting", "can't stop gambling", "hide it from", "hiding it from", "lost my salary", "payday loan",
        "sold my", "behind on bills", "gambling problem", "addicted to betting", "addicted to gambling"]
PARLAY = ["parlay", "accumulator", "acca", "multi-bet", "multibet", "same game", "sgp", "combo bet", "legs"]
LATE = re.compile(r"(?<![a-z])(1am|2am|3am|4am|middle of the night|can't sleep|cant sleep)(?![a-z])")
VENUE = ["polymarket", "kalshi", "manifold", "betfair", "sportsbook", "draftkings", "fanduel", "bet365",
         "casino", "roulette", "blackjack", "poker", "slots", "crash game"]

SUPPORT = ("If betting is costing you more than money, free confidential help is available 24/7 at "
           "gamblingtherapy.org, or 1-800-GAMBLER in the US.")


def _prob(x: float) -> float:
    return max(0.0, min(1.0, x))


def parse_market(text: str) -> dict:
    """Prices, odds, stated beliefs, legs, round robins. Returns raw findings for the tissue."""
    low = text.lower().replace("’", "'")
    out: dict = {"prices": [], "belief": None, "legs": None, "leg_prob": None, "decimal_odds": None, "rr": None}
    # beliefs first: "I think it's 80%", "I'm 90% sure", "my number is 0.7"
    for m in re.finditer(r"(?:i think|i'm|i am|my (?:number|estimate|read) is|feels like|i'd say|i give it|"
                         r"i reckon|probably|odds are)\D{0,12}?(\d{1,3}(?:\.\d+)?)\s*%", low):
        out["belief"] = _prob(float(m.group(1)) / 100)
    m = re.search(r"(\d{1,3}(?:\.\d+)?)\s*%\s*(?:sure|confident|certain|chance it (?:wins|hits|happens))", low)
    if m:
        out["belief"] = _prob(float(m.group(1)) / 100)
    # leg probabilities: "each leg 70%", "6 legs at 70%"
    m = re.search(r"(?:each leg|every leg|legs? (?:at|around|about))\D{0,8}(\d{1,3}(?:\.\d+)?)\s*%", low)
    if m:
        out["leg_prob"] = _prob(float(m.group(1)) / 100)
    m = re.search(r"(\d{1,2})\s*[- ]?(?:leg|team|pick|fold)s?\b", low)
    if m and any_in(low, PARLAY + ["fold", "team", "pick"]):
        out["legs"] = int(m.group(1))
    # round robin: "round robin of 2s from 5 picks" / "round robin by 3s with 6 picks"
    m = re.search(r"round robin (?:of|by) (\d)s?\D{0,20}?(\d{1,2}) (?:picks|teams|legs|selections)", low)
    if m:
        out["rr"] = (int(m.group(2)), int(m.group(1)))
    # Polymarket/Kalshi style prices: "at 62c", "62 cents", "0.62", "yes at 38¢"
    for m in re.finditer(r"(?<![\d.$])(\d{1,2}(?:\.\d+)?)\s*(?:c\b|¢|cents?\b)", low):
        out["prices"].append(_prob(float(m.group(1)) / 100))
    for m in re.finditer(r"(?:at|price|priced at|trading at|for)\s+(0?\.\d{1,3})\b", low):
        out["prices"].append(_prob(float(m.group(1))))
    # market-implied percentages: "market says 35%", "priced at 35%"
    for m in re.finditer(r"(?:market|polymarket|kalshi|crowd|priced|trading|implied)\D{0,14}?(\d{1,3}(?:\.\d+)?)\s*%", low):
        p = _prob(float(m.group(1)) / 100)
        if out["belief"] is None or abs(p - out["belief"]) > 1e-9:
            out["prices"].append(p)
    # decimal odds "@2.5", "odds of 3.4", american "+150" / "-200"
    m = re.search(r"(?:@|odds (?:of )?|at odds )\s*(\d{1,3}\.\d{1,2})\b", low)
    if m and float(m.group(1)) > 1:
        out["decimal_odds"] = float(m.group(1))
    m = re.search(r"(?<![\w$])([+-])(\d{3,4})\b(?!\s*%)", low)
    if m and out["decimal_odds"] is None:
        a = int(m.group(2))
        out["decimal_odds"] = 1 + (a / 100 if m.group(1) == "+" else 100 / a)
    return out


_STAKE_CUE = re.compile(r"\b(on it|on this|on that|on the|on yes|on no|on a|bet|stake|wager|put|putting|risk|punt|"
                       r"each|per bet|a pop)\b")
_LOSS_CUE = re.compile(r"\b(down|lost|losing|loss|up|won|bankroll|have|got|borrowed)\b")


def stake_amount(text: str) -> float | None:
    """The amount being bet: prefer an amount next to a stake cue, skip amounts described as losses or balances."""
    from ..analysis import _AMOUNT
    best, best_score = None, -9
    low = text.lower()
    for m in _AMOUNT.finditer(text):
        val = parse_amount(m.group(0))
        if not val:
            continue
        before, after = low[max(0, m.start() - 18):m.start()], low[m.end():m.end() + 14]
        score = (2 if _STAKE_CUE.search(after) or _STAKE_CUE.search(before) else 0) - \
                (3 if _LOSS_CUE.search(before[-10:]) else 0)
        if score >= best_score:
            best, best_score = val, score
    return best


def kelly_binary(p: float, price: float) -> float:
    """Kelly fraction for a contract that costs `price` and pays 1."""
    if not 0 < price < 1:
        return 0.0
    return max(0.0, (p - price) / (1 - price))


class Markets(Tissue):
    key = "markets"
    name = "Markets"
    tagline = "The honest brake on prediction markets and bets"
    brief = ("Prediction markets (Polymarket, Kalshi), sports betting and games of chance. Read prices as "
             "probabilities, multiply parlay legs, size by fractional Kelly against bankroll, and name tilt, "
             "chasing and gambling harm plainly. Never give picks or tips; judge the decision, not the event.")
    labels = {"proceed": "SIZED RIGHT", "caution": "SIZE DOWN", "stop": "NO BET"}
    default_temperament = "surgeon"
    voice = {
        "surgeon": {"close": {"stop": "Recommendation: no position. Reassess when the numbers, not the mood, say so.",
                              "caution": "Recommendation: cut the stake to the sized number above.",
                              "proceed": "Recommendation: proceed at the stated size. Log the result."}},
        "mentor": {"close": {"stop": "The market will be there tomorrow. Make sure your bankroll is too.",
                             "caution": "Bet the size your edge can justify, not the size your mood wants.",
                             "proceed": "Fair price, sane size. Log it and let it ride."}},
        "comfort": {"close": {"stop": "You don't need to win tonight. Let's step away for a bit.",
                              "caution": "A smaller bet is still a bet. Be kind to tomorrow's you.",
                              "proceed": "That looks measured. Enjoy it."}},
        "boss": {"close": {"stop": "No bet. Close the app.",
                           "caution": "Cut the size. Then cut it again.",
                           "proceed": "Fine. Stick to the number."}},
    }
    scenarios = [
        "Polymarket has the election YES at 62c. I think it's 80%. Putting $5k on it.",
        "Down $3k this week, need a win. 6-leg parlay, each leg 70%, $1,000 on it tonight.",
        "Round robin of 2s from 5 picks, $200 each. Can't lose.",
        "Small one: $100 on YES at 30c, my read is 45% after the debate.",
    ]

    def facts(self, message, thread_text, person, history, policy):
        text = f"{thread_text}\n{message}"
        low = text.lower().replace("’", "'")
        prof = person.profile or {}
        bankroll = float(prof.get("bankroll") or 0) or None
        fee = float(prof.get("fee", 0.02))
        f = Facts(domain=self.key)
        mk = parse_market(message) if re.search(r"\d", message) else parse_market(text)
        f.amount = stake_amount(message) or stake_amount(thread_text)
        flags, sev, m = [], 0, f.metrics

        # ---- price, probability, edge
        price = mk["prices"][0] if mk["prices"] else (1 / mk["decimal_odds"] if mk["decimal_odds"] else None)
        if price:
            m["market_prob"] = round(price, 3)
            m["cost_after_fees"] = round(min(0.999, price * (1 + fee)), 3)
        if mk["belief"] is not None:
            m["your_prob"] = round(mk["belief"], 3)

        # ---- combinatorics
        legs = mk["legs"]
        if legs and legs >= 2:
            leg_p = mk["leg_prob"] or (mk["prices"][0] if mk["prices"] else None)
            m["legs"] = legs
            if leg_p:
                joint = leg_p ** legs
                m.update(leg_prob=round(leg_p, 3), joint_prob=round(joint, 4), feels_like=round(leg_p, 3))
                price = price if (mk["decimal_odds"] and not mk["leg_prob"]) else None
                m["your_prob"] = round(joint, 4)
                if joint < 0.2:
                    flags.append("parlay-math"); sev = max(sev, 1)
        if mk["rr"]:
            n, k = mk["rr"]
            combos = math.comb(n, k)
            m.update(rr_picks=n, rr_size=k, rr_bets=combos)
            if f.amount:
                m["rr_total_stake"] = f.amount * combos
                flags.append("combo-multiplier")

        stake = m.get("rr_total_stake") or f.amount
        if stake:
            m["stake"] = stake

        # ---- edge and Kelly, only when we have both a price and a belief
        p_you, c = m.get("your_prob"), m.get("cost_after_fees")
        if p_you is not None and c:
            m["edge"] = round(p_you - c, 3)
            k = kelly_binary(p_you, c)
            m["kelly_full"] = round(k, 4)
            m["kelly_quarter"] = round(k / 4, 4)
            m["ev_per_dollar_yours"] = round(p_you / c - 1, 3)
            m["ev_per_dollar_market"] = round(price / c - 1, 3) if price else None
            if m["edge"] <= 0:
                flags.append("no-edge"); sev = max(sev, 1)
            if bankroll and stake:
                rec = bankroll * min(k / 4, policy_cap(prof))
                m["recommended_stake"] = round(rec, 2)
                if stake > max(rec * 2, 0.0) and stake > 0.01 * bankroll:
                    flags.append("oversized"); sev = max(sev, 1)
        if p_you is not None and price and p_you >= 0.9 and price <= 0.75 and not legs:
            flags.append("overconfidence"); sev = max(sev, 1)

        # ---- bankroll share
        if bankroll and stake:
            share = stake / bankroll
            m["bankroll_share"] = round(share, 3)
            if share > 0.15:
                flags.append("bankroll"); sev = 2
            elif share > 0.05:
                flags.append("bankroll"); sev = max(sev, 1)
        elif stake and person.liquid_net_worth and stake / person.liquid_net_worth > 0.05:
            flags.append("bankroll"); sev = max(sev, 1)

        # ---- the human, not the market
        if any_in(low, CHASE):
            flags.append("chasing"); sev = 2
        certain = any_in(low, CERTAIN)
        if certain:
            f.fomo = True
            flags.append("certainty"); sev = max(sev, 1)
        if any_in(low, ALL_IN):
            flags.append("all-in"); sev = 2
        if LATE.search(low):
            flags.append("late-night"); sev = max(sev, 1) if sev else 1
        harm = any_in(low, HARM)
        if harm:
            flags.append("harm"); sev = 2
            m["harm"] = True
        # history escalates only when it is the same pattern (a past chase doesn't make today's small bet a chase)
        f.prior_ignored = [h for h in prior_ignored(history) if set(h.get("flags") or []) & set(flags)]
        if f.prior_ignored and sev >= 1:
            flags.append("repeat-pattern"); sev = 2
        m["venue"] = next(iter(any_in(low, VENUE)), None)
        f.flags, f.floor = list(dict.fromkeys(flags)), floor_from(sev)
        return f

    def verdict(self, f, person):
        cur, m = person.currency, f.metrics
        r = []
        if m.get("harm"):
            r.append("Borrowed money, money you need, or betting you're hiding: those are signs the betting is "
                     "running you. That matters more than any edge.")
            r.append(SUPPORT)
            return "No bet. Not with this money, and not tonight.", r
        if "chasing" in f.flags:
            r.append("Trying to win back a loss is the most expensive bet there is. The market doesn't know you're down.")
        if m.get("joint_prob") is not None:
            r.append(f"{m['legs']} legs at {m['leg_prob']:.0%} each hit together {m['joint_prob']:.1%} of the time, "
                     f"not {m['feels_like']:.0%}. That's roughly 1 in {max(1, round(1 / m['joint_prob']))}. "
                     f"And legs are rarely independent, which usually makes it worse.")
        if m.get("rr_bets"):
            r.append(f"A round robin of {m['rr_size']}s from {m['rr_picks']} picks is C({m['rr_picks']},{m['rr_size']}) = "
                     f"{m['rr_bets']} separate bets" + (f": {fmt_money(m['rr_total_stake'], cur)} at risk, not "
                     f"{fmt_money(m['stake'] / m['rr_bets'], cur)}." if m.get("rr_total_stake") else "."))
        if m.get("market_prob") is not None and m.get("joint_prob") is None:
            line = f"The price says {m['market_prob']:.0%}."
            if m.get("your_prob") is not None:
                line += (f" You say {m['your_prob']:.0%}. After fees you pay about {m['cost_after_fees']:.0%}, "
                         f"so your claimed edge is {m['edge'] * 100:+.1f} points.")
            else:
                line += " To bet, you need a reason to believe more than that, beyond wanting it."
            r.append(line)
        if "overconfidence" in f.flags:
            r.append("When you're above 90% and the crowd is well below, ask what you know that thousands of "
                     "people with money on it don't. If the answer is 'a feeling', the crowd is usually right.")
        if "certainty" in f.flags and "overconfidence" not in f.flags:
            r.append("'Can't lose' is a feeling, not a probability.")
        if m.get("recommended_stake") is not None and ("oversized" in f.flags or f.floor.severity == 0):
            r.append(f"Sized by quarter-Kelly on your own numbers and your {policy_cap(person.profile or {}):.0%} cap: "
                     f"about {fmt_money(m['recommended_stake'], cur)}"
                     + (f", against the {fmt_money(m['stake'], cur)} you named." if m.get("stake") else "."))
        if m.get("bankroll_share") is not None and "bankroll" in f.flags:
            r.append(f"This is {m['bankroll_share']:.0%} of your bankroll on one outcome.")
        if "all-in" in f.flags:
            r.append("All-in turns one bad outcome into the end of the game.")
        if "late-night" in f.flags:
            r.append("Late-night bets are the ones people most often regret by morning.")
        for h in (f.prior_ignored[:1] if f.floor.severity >= 1 else []):
            r.append(f"On {(h.get('ts') or '')[:10]} I said '{h.get('headline', 'no bet')}'. It went ahead anyway.")

        if f.floor.severity == 2:
            head = "No bet. Not this one, not at this size." if "chasing" not in f.flags else \
                "No bet. Don't chase it."
        elif f.floor.severity == 1:
            if "no-edge" in f.flags:
                head = "Size down to zero. There's no edge here at this price."
            elif "parlay-math" in f.flags:
                head = "Size down. This parlay is a long shot dressed as a sure thing."
            else:
                head = "Size down. The idea may be fine, the size isn't."
        else:
            head = "Fair bet at a sane size."
            if m.get("edge") is not None:
                r.append(f"Your edge is {m['edge'] * 100:+.1f} points after fees; the size fits your bankroll rules.")
            if not r:
                r.append("No tilt, no chasing, and the stake is small against your bankroll.")
        return head, r

    def forecasts(self, f, person):
        m, cur, out = f.metrics, person.currency, []
        p = m.get("joint_prob") if m.get("joint_prob") is not None else m.get("market_prob")
        stake = m.get("stake")
        if p is not None:
            out.append(Forecast(label="Chance this pays out (market or joint)", value=f"{p:.1%}",
                                note="Prices treated as probabilities; parlay legs multiplied"))
        if p is not None and stake:
            out.append(Forecast(label="Chance you lose the whole stake", value=f"{1 - p:.1%}",
                                note=f"{fmt_money(stake, cur)} at risk"))
            # how often five straight losses happen at this hit rate, the run that triggers chasing
            out.append(Forecast(label="Odds of 5 losses in a row", value=f"{(1 - p) ** 5:.0%}",
                                note="The losing run that usually starts a chase"))
        if m.get("ev_per_dollar_market") is not None and stake:
            out.append(Forecast(label="Expected value at the market's own odds",
                                value=("-" if m["ev_per_dollar_market"] < 0 else "+") +
                                fmt_money(abs(m["ev_per_dollar_market"] * stake), cur),
                                note="Fees are the house edge on a fair market"))
        return out


def policy_cap(profile: dict) -> float:
    return float(profile.get("max_bet_fraction", 0.02))
