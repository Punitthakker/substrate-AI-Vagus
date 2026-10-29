"""Trader psychology: the biases behavioural finance has documented for fifty years, read from the trader's words.

Each detector names a documented effect (Kahneman and Tversky, Shefrin and Statman, Odean, Barber) and explains it
in one plain sentence. Crowd sentiment, when the trader quotes it, is read as a contrarian signal at extremes.
The output never predicts the price. It predicts the trader: how likely this decision is being made by the bias.
"""
from __future__ import annotations

import re

BIASES = [
    ("gamblers-fallacy", 30, "Gambler's fallacy",
     r"(fell|dropped|down|up|rose|rallied|red|green)\s+(for\s+)?\d+\s+(days|sessions|weeks|candles|times)(\s+in a row|\s+straight)?|"
     r"(must|has to|bound to|due (for|to)|surely)\s+(bounce|reverse|correct|go (back )?up|come (back )?down|turn)",
     "A run of down days doesn't make an up day more likely. Markets have no memory of what they owe you."),
    ("anchoring", 20, "Anchoring",
     r"(was|were|used to be|back to|traded at|it hit)\s+(at\s+)?\$?\d[\d,.]*k?\s*(last|a|in)\s+(week|month|year|march|april|may|june|july|summer)|"
     r"back to \$?\d[\d,.]*",
     "The price you remember is not the price the market owes you. Last month's level is information, not a target."),
    ("disposition", 25, "Disposition effect",
     r"won'?t sell at a loss|not a loss until i sell|wait (until|till) it comes back|break ?even|hold (it )?until it recovers|"
     r"cut (my )?winners|take (the )?profit (early|now) and hold the loser",
     "People hold losers too long and sell winners too soon. Ask: would you open this position today, at this price?"),
    ("revenge-trading", 40, "Revenge trading",
     r"make it back|win it back|get it back|revenge|get even|recover (my|the) loss|double (the size|up|down)",
     "Trading to recover a loss raises size exactly when judgment is worst. The market doesn't know you're down."),
    ("overconfidence", 25, "Overconfidence",
     r"can'?t lose|sure thing|guaranteed|free money|easy money|100% sure|no way it|trust me|i just know|definitely going",
     "Certainty is a feeling. Traders who feel most certain trade most, and on average earn least (Barber and Odean)."),
    ("herding", 20, "Herding",
     r"everyone('s| is) (buying|selling|long|short)|twitter says|x says|telegram (group|channel)|signal(s)? group|"
     r"youtube|influencer|my group chat",
     "When everyone is on one side, the people left to push the price further are running out."),
    ("recency", 15, "Recency bias",
     r"(been|keeps) (going|rallying|falling|dropping) (up|down)? ?(all|this) (week|month)|trend is (my|your) friend|only goes up",
     "The last few days feel like the future. They are a tiny sample of a very noisy history."),
    ("leverage", 25, "Leverage",
     r"\b\d{2,4}\s*(:1|x)\b|\bleverage\b|\bmargin\b|\bon margin\b",
     "Leverage doesn't change where the price goes. It changes whether you're still in the trade when it gets there."),
    ("prediction-ask", 0, "Asking for a direction call",
     r"will (gold|it|the (euro|dollar|yen|rupee|pound)|eur|usd|xau)\s+(go|be|hit|reach|rise|fall)|where (is|will) .{0,20}(go|be)|"
     r"predict|what('s| is) (the )?(target|price) (for|by|next)",
     "No model predicts FX or gold direction reliably. What can be estimated is how far it is likely to move."),
]
_RX = [(k, w, n, re.compile(rx, re.I), why) for k, w, n, rx, why in BIASES]
CROWD = re.compile(r"(\d{1,3})\s*%\s*(of\s+)?(retail|traders|clients|the crowd|crowd|positions|accounts)\s*(are\s+|is\s+)?(long|short|buying|selling)",
                   re.I)


def read(text: str) -> dict:
    found = [{"key": k, "name": n, "weight": w, "why": why} for k, w, n, rx, why in _RX if rx.search(text or "")]
    if re.search(r"\b(no|without|zero)\s+(leverage|margin)|unleveraged|\b1:1\b|\bcash only\b", text or "", re.I):
        found = [f for f in found if f["key"] != "leverage"]
    crowd = None
    m = CROWD.search(text or "")
    if m:
        pct, side = int(m.group(1)), m.group(5).lower()
        side = "long" if side in ("long", "buying") else "short"
        crowd = {"pct": pct, "side": side, "extreme": pct >= 70,
                 "read": (f"{pct}% {side} is a crowded trade. At extremes, retail positioning has tended to be a "
                          f"contrarian signal; it says more about risk of a squeeze than about direction.")
                 if pct >= 70 else f"{pct}% {side}: not an extreme."}
    score = min(100, sum(f["weight"] for f in found) + (15 if crowd and crowd["extreme"] else 0))
    return {"biases": found, "crowd": crowd, "score": score,
            "band": "high" if score >= 50 else "elevated" if score >= 25 else "low"}
