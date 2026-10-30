"""Fact extraction and the Honesty Floor.

Before any model is consulted, Substrate computes the hard facts: amounts, concentration,
leverage, loss-chasing, and what this human did the last time they were told no. The facts set a
floor. A rented model may be harsher than the floor, never softer. That is how sycophancy is
engineered out instead of prompted out.

Two passes read a message:
  * the rule core (this file): regex and keyword heuristics, deterministic, offline;
  * the brain (brains.py): a structured reading by the configured model.
When a brain is configured its reading is reconciled against the rule core (reconcile()):
the brain may only choose among amounts the user actually wrote, and may add risk flags, never remove them.
Then the floor is recomputed from the reconciled facts (compute_floor()).
"""
from __future__ import annotations

import re
from typing import Optional

from .policy import DEFAULT, Policy
from .schemas import Facts, Person, Polarity

_AMOUNT = re.compile(
    r"(?:(?:usd|aed|inr|\$|₹)\s*)?(?<![A-Za-z0-9.])(\d+(?:[.,]\d+)*)\s*(k|m|mm|bn|b|thousand|million|lakh|lakhs|crore|cr)?\b",
    re.I,
)
_MULT = {"k": 1e3, "thousand": 1e3, "m": 1e6, "mm": 1e6, "million": 1e6, "b": 1e9, "bn": 1e9,
         "lakh": 1e5, "lakhs": 1e5, "crore": 1e7, "cr": 1e7}

LEVERAGE = ["borrow", "loan", "margin", "leverage", "leveraged", "credit card", "mortgage the", "remortgage", "3x", "5x", "10x leverage"]
LOSS_CHASE = ["make it back", "win it back", "recover my", "recover the", "get it back", "double down", "average down"]
FOMO = ["everyone is", "everyone's", "before it's too late", "can't miss", "fomo", "100x", "all in", "all-in", "guaranteed"]
_MOON = re.compile(r"\b(to the moon|mooning|moon)\b")
SPECULATIVE = ["token", "coin", "crypto", "meme", "options", "nft", "presale", "pre-sale", "airdrop", "penny stock"]
DIVERSIFIED = {"fund", "index", "cash", "bond", "etf"}
DIVERSIFIED_KINDS = {"fund", "index", "etf", "bond", "cash"}

# verbs that mean "deploy money"; the amount that follows one of these is the amount being moved
_DEPLOY_VERBS = r"(?:put|putting|invest|investing|move|moving|buy|buying|add|adding|allocate|allocating|deploy|deploying|" \
                r"place|placing|stake|staking|wire|transfer|lend|lending|borrow|borrowing|take|taking|dump|throw|throwing|park|parking|top\s*up)"
_DEST_PREP = r"(?:into|in to|in|to|on|onto|towards|toward)"
_DEPLOY = re.compile(rf"\b{_DEPLOY_VERBS}\b[^.?!\n]{{0,40}}?((?:usd|aed|inr|\$|₹)\s*\d[\d,.]*\s*(?:k|m|mm|bn|b|thousand|million|lakh|lakhs|crore|cr)?|\d[\d,.]*\s*(?:k|m|mm|bn|b|thousand|million|lakh|lakhs|crore|cr))\b", re.I)
_AMOUNT_INTO = re.compile(rf"((?:usd|aed|inr|\$|₹)\s*\d[\d,.]*\s*(?:k|m|mm|bn|b|thousand|million|lakh|lakhs|crore|cr)?|\d[\d,.]*\s*(?:k|m|mm|bn|b|thousand|million|lakh|lakhs|crore|cr))\s+(?:more\s+|extra\s+|additional\s+)?(?:of\s+(?:my\s+)?\w+\s+)?{_DEST_PREP}\s+", re.I)
_DEST = re.compile(rf"\b{_DEST_PREP}\s+(?:a|an|the|my|this|that|some|more|another|one)?\s*((?:[\w&'\-]+\s?){{1,6}}?)(?=\s+(?:and|for|because|so|but|or|at|with|over|which|that|then|before|after|if|right|to\s+hold)\b|[,.?!;:]|$)", re.I)
_SOURCE = re.compile(r"\b(?:from|out of|using|with)\s+(?:my\s+|the\s+|our\s+)?((?:[\w&'\-]+\s?){1,4}?)(?=\s+(?:into|in|to|and|for|because)\b|[,.?!;:]|$)", re.I)
_STOP = {"a", "an", "the", "my", "this", "that", "some", "more", "another", "one", "of", "fund", "funds", "diversified",
         "global", "position", "positions", "holding", "holdings", "account", "portfolio", "stock", "stocks", "share", "shares"}
_TICKER = re.compile(r"^[A-Z][A-Z0-9]{2,6}$")

QUESTION_HINTS = ["should i be worried", "should i worry", "is it something", "what do you think", "what does that mean",
                  "what is ", "what's ", "whats ", "how does", "how do ", "how can you", "how could you", "how would you",
                  "why ", "is it true", "is this true", "does this", "do you know", "did you see", "have you seen",
                  "what happened", "is my money", "are my ", "am i ", "explain", "tell me about", "what about",
                  "can you explain", "thoughts on", "opinion on", "your view", "your take", "worth it?", "any good"]
# a factual correction: the client says the reading of their message or their record is wrong
OBJECTION_HINTS = ["you misread", "you misunderstood", "that's not what i", "that is not what i", "not what i asked",
                   "i asked about", "i asked for", "re-check", "recheck", "read it again", "check again", "look again",
                   "i never ", "i didn't ", "i did not ", "i don't have ", "i do not have ", "i didn't say", "i did not say",
                   "where did you get", "wrong amount", "you assumed", "you're confusing", "you are confusing", "please re-",
                   "that wasn't me", "not me", "who is "]
# "you're wrong" on its own is pushback, not a correction; it becomes an objection only with a specific (an amount, a holding)
WEAK_OBJECTION = ["you're wrong", "you are wrong", "you got it wrong", "incorrect", "that's wrong", "that is wrong"]
PRESSURE_HINTS = ["just say yes", "come on", "say yes", "agree with me", "everyone's doing it", "everyone is doing it",
                  "trust me", "just approve", "stop lecturing", "i've decided", "i have decided"]


# ---------------------------------------------------------------- amounts

def _to_value(raw: str, unit: str) -> Optional[float]:
    try:
        return float(raw.replace(",", "")) * _MULT.get(unit.lower(), 1)
    except ValueError:
        return None


def parse_amounts(text: str) -> list[float]:
    """Every money amount the text actually contains, in order of appearance. Bare numbers and percentages are not amounts."""
    out: list[float] = []
    for m in _AMOUNT.finditer(text or ""):
        raw, unit = m.group(1), (m.group(2) or "")
        has_currency = bool(re.match(r"(usd|aed|inr|\$|₹)", m.group(0).strip(), re.I))
        if not unit and not has_currency:
            continue
        if m.end() < len(text) and text[m.end():m.end() + 1] == "%":
            continue
        val = _to_value(raw, unit)
        if val is not None:
            out.append(val)
    return out


def parse_amount(text: str) -> Optional[float]:
    """Largest amount in the text (legacy helper, still used by tissues that want 'the size of the thing')."""
    vals = parse_amounts(text)
    return max(vals) if vals else None


def deployed_amount(message: str) -> Optional[float]:
    """The amount being MOVED in the proposed move, not the biggest number in the sentence.

    "I have $300k cash. Should I put $50k into an index fund?" -> 50_000.
    Falls back to the largest amount when no deployment phrase is found.
    """
    text = message or ""
    cands = parse_amounts(text)
    if not cands:
        return None
    for rx in (_AMOUNT_INTO, _DEPLOY):
        m = rx.search(text)
        if m:
            v = parse_amounts(m.group(1))
            if v:
                return v[0]
    return max(cands)


# ---------------------------------------------------------------- assets

def _clean_phrase(p: str) -> str:
    return re.sub(r"\s+", " ", (p or "").strip(" .,;:!?")).strip()


def _words(s: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9&]+", (s or "").lower()) if w not in _STOP}


def match_position(name: str, person: Person):
    """Fuzzy-match a phrase to one of the person's holdings: exact, ticker, or word overlap."""
    if not name:
        return None
    n = name.strip().lower()
    for p in person.positions:
        if p.asset.lower() == n:
            return p
    for p in person.positions:
        if _TICKER.match(p.asset) and re.search(rf"\b{re.escape(p.asset.lower())}\b", n):
            return p
    nw = _words(name)
    best, score = None, 0
    for p in person.positions:
        pw = _words(p.asset)
        if not pw or not nw:
            continue
        common = len(pw & nw)
        if common and (common >= 2 or common == len(pw) or common == len(nw)) and common > score:
            best, score = p, common
    return best


def guess_kind(phrase: str) -> Optional[str]:
    t = (phrase or "").lower()
    for kind, words in (("cash", ["cash", "savings", "deposit", "fd", "fixed deposit"]), ("bond", ["bond", "sukuk", "treasur", "gilt"]),
                        ("etf", ["etf"]), ("index", ["index"]), ("fund", ["fund", "sip", "mutual"]),
                        ("property", ["property", "flat", "apartment", "villa", "real estate", "plot", "land"]),
                        ("options", ["option", "call", "put option", "futures", "perp"]),
                        ("token", ["token", "coin", "crypto", "meme", "nft", "presale", "pre-sale", "airdrop", "bitcoin", "btc", "eth"]),
                        ("stock", ["stock", "share", "equity", "ipo", "penny"])):
        if any(w in t for w in words):
            return kind
    return None


def destination(message: str, person: Person) -> tuple[Optional[str], Optional[str], Optional[float], Optional[str]]:
    """(asset, kind, existing_exposure, source) for the proposed move, reading the sentence, not just the vocabulary."""
    text = message or ""
    source = None
    ms = _SOURCE.search(text)
    if ms:
        source = _clean_phrase(ms.group(1))
    for m in _DEST.finditer(text):
        phrase = _clean_phrase(m.group(1))
        if not phrase or (source and phrase.lower() == source.lower()):
            continue
        low = phrase.lower()
        if low in ("it", "this", "that", "them", "there", "here", "the market", "play", "work"):
            continue
        pos = match_position(phrase, person)
        if pos:
            return pos.asset, pos.kind, pos.value, source
        kind = guess_kind(phrase)
        generic = low.split()[-1] if low else ""
        if generic in ("token", "coin", "crypto", "fund", "property", "stock", "bond") and len(low.split()) <= 2:
            # "this token" / "the fund" means the one they already hold, when they hold exactly one of that kind
            want = "token" if generic in ("token", "coin", "crypto") else generic
            held = [p for p in person.positions if p.kind == want]
            if len(held) == 1:
                return held[0].asset, held[0].kind, held[0].value, source
        if kind or any(w in low for w in SPECULATIVE):
            name = phrase if len(phrase) <= 40 else phrase[:40]
            return name, kind or "token", None, source
    return None, None, None, source


# ---------------------------------------------------------------- intent

def _any(text: str, words: list[str]) -> bool:
    return any(w in text for w in words)


def detect_intent(message: str, amount: Optional[float], asset: Optional[str]) -> str:
    """decision | question | objection | pressure. The rule core's reading; a brain can refine it."""
    t = f" {(message or '').lower().strip()} "
    if _any(t, OBJECTION_HINTS) or (_any(t, WEAK_OBJECTION) and (amount or asset)):
        return "objection"
    if _any(t, PRESSURE_HINTS) or _any(t, WEAK_OBJECTION):
        return "pressure"
    has_move = bool(re.search(rf"\b{_DEPLOY_VERBS}\b", t)) or bool(re.search(r"\b(sell|selling|exit|close|hold|keep|double|size|buy|short|long)\b", t))
    if amount or (asset and has_move):
        return "decision"
    if has_move and re.search(r"\b(should|shall|can|could|would|ok|okay|good idea|worth|thinking of|planning|want to|going to|gonna)\b", t):
        return "decision"
    if _any(t, QUESTION_HINTS) or (t.strip().endswith("?") and not has_move):
        return "question"
    if not has_move and len(t.split()) <= 4:
        return "question"
    return "decision"


# ---------------------------------------------------------------- facts + floor

def read_message(message: str, thread_text: str, person: Person) -> Facts:
    """Pass 1: what the message says. No floor yet."""
    f = Facts()
    m = (message or "").lower()
    text = f"{thread_text}\n{message}".lower()
    f.candidates = parse_amounts(message)
    f.amount = deployed_amount(message)
    f.asset, f.asset_kind, f.existing_exposure, f.source = destination(message, person)

    def named_holding(scope: str):
        for p in person.positions:
            if re.search(rf"\b{re.escape(p.asset.lower())}\b", scope):
                return p
        return None

    if not f.asset:   # vocabulary fallback, within the message only
        held = named_holding(m)
        if held:
            f.asset, f.asset_kind, f.existing_exposure = held.asset, held.kind, held.value
    if not f.asset:
        for w in SPECULATIVE:
            if w in m:
                held = next((p for p in person.positions
                             if p.kind == w or (w in ("coin", "crypto", "token") and p.kind == "token")), None)
                f.asset, f.asset_kind, f.existing_exposure = (held.asset, held.kind, held.value) if held else (w, "token", None)
                break
    f.intent = detect_intent(message, f.amount, f.asset)
    if f.intent in ("pressure", "decision") and not f.amount and thread_text.strip():
        # a follow-up inside a decision thread inherits the decision being pushed
        last = thread_text.split("\n")[-1]
        f.amount = deployed_amount(last) or parse_amount(thread_text)
        if not f.asset:
            a, k, e, _ = destination(last, person)
            if not a:
                held = named_holding(text)
                a, k, e = (held.asset, held.kind, held.value) if held else (None, None, None)
            f.asset, f.asset_kind, f.existing_exposure = a, k, e
        f.inherited = True
    scope = text if f.intent in ("pressure", "decision") and f.inherited else m
    f.leverage = _any(scope, LEVERAGE)
    f.loss_chasing = _any(m, LOSS_CHASE) or ("lost" in m and _any(m, ["back", "recover", "fast"]))
    f.fomo = _any(m, FOMO) or bool(_MOON.search(m)) or (f.intent == "pressure" and (_any(text, FOMO) or bool(_MOON.search(text))))
    return f


def compute_floor(f: Facts, person: Person, history: list[dict], policy: Policy = DEFAULT) -> Facts:
    """Pass 2: the Honesty Floor from the facts. Deterministic; a brain can raise the verdict above it, never lower."""
    kind = f.asset_kind or next((p.kind for p in person.positions if p.asset == f.asset), None)
    diversified = bool(kind and kind in DIVERSIFIED_KINDS) or bool(f.asset and f.asset.lower() in DIVERSIFIED)
    f.diversified = diversified
    f.concentration_pct = None
    if f.amount and person.liquid_net_worth:
        exposure = f.amount if diversified else (f.existing_exposure or 0) + f.amount
        f.concentration_pct = round(100 * exposure / person.liquid_net_worth, 1)
    speculative = bool(kind in ("token", "options")) or bool(f.asset and f.asset in SPECULATIVE)
    f.profile_breach = bool(person.risk_profile.stated in ("conservative", "moderate") and (speculative or f.leverage))

    flags: list[str] = []
    severity = 0
    if f.intent in ("question", "objection"):
        f.flags, f.floor = [], Polarity.proceed
        f.prior_ignored = []
        return f
    if f.concentration_pct is not None:
        if not diversified and f.concentration_pct >= policy.concentration_stop_pct:
            flags.append("concentration"); severity = max(severity, 2)
        elif not diversified and f.concentration_pct >= policy.concentration_caution_pct:
            flags.append("concentration"); severity = max(severity, 1)
        elif diversified and f.concentration_pct >= 50:
            flags.append("lump-sum"); severity = max(severity, 1)
    if f.leverage:
        flags.append("leverage"); severity = max(severity, 2)
    if f.loss_chasing:
        flags.append("loss-chasing"); severity = max(severity, 2 if f.amount else 1)
    if f.fomo:
        flags.append("fomo"); severity = max(severity, 1)
    if f.profile_breach:
        flags.append("profile-breach"); severity = max(severity, 1)
    if f.amount and not person.liquid_net_worth:
        flags.append("unknown-numbers"); severity = max(severity, 1)
    # what happened the last time this human was told no about the SAME kind of move?
    prior = [h for h in history if h.get("polarity") in ("stop", "caution") and h.get("action") == "ignored"]
    f.prior_ignored = [h for h in prior if not h.get("flags") or set(h["flags"]) & set(flags)]
    if f.prior_ignored and severity >= 1:
        flags.append("repeat-pattern"); severity = 2
    f.flags = flags
    f.floor = [Polarity.proceed, Polarity.caution, Polarity.stop][severity]
    return f


def extract_facts(message: str, thread_text: str, person: Person, history: list[dict], policy: Policy = DEFAULT) -> Facts:
    """history: prior advice events for this user, each with polarity/action/outcome summarised."""
    return compute_floor(read_message(message, thread_text, person), person, history, policy)


def reconcile(f: Facts, ext: dict, person: Person, history: list[dict], policy: Policy = DEFAULT) -> Facts:
    """Merge a brain's structured reading into the rule core's facts, then recompute the floor.

    The brain may only pick an amount the user actually wrote, may name the destination, and may ADD risk
    flags. It can never remove a flag the rule core saw. That keeps the floor un-promptable.
    """
    g = f.model_copy(deep=True)
    intent = str(ext.get("intent") or g.intent or "decision").lower()
    if intent not in ("decision", "question", "objection", "other"):
        intent = "decision"
    amt = ext.get("amount_deployed")
    if isinstance(amt, (int, float)) and amt > 0:
        amt = float(amt)
        if g.candidates and not any(abs(amt - c) <= max(1.0, 0.005 * c) for c in g.candidates):
            amt = g.amount                      # invented number: keep the rule core's reading
        g.amount = amt
    elif intent in ("question", "objection", "other"):
        g.amount = None
    dest = ext.get("destination_asset")
    if isinstance(dest, str) and dest.strip() and dest.strip().lower() not in ("null", "none"):
        pos = match_position(dest, person)
        if pos:
            g.asset, g.asset_kind, g.existing_exposure = pos.asset, pos.kind, pos.value
        else:
            g.asset, g.existing_exposure = _clean_phrase(dest)[:40], None
            g.asset_kind = str(ext.get("asset_kind") or guess_kind(dest) or g.asset_kind or "other").lower()
    elif intent in ("question", "objection", "other"):
        g.asset, g.asset_kind, g.existing_exposure = None, None, None
    if ext.get("source_of_funds"):
        g.source = str(ext["source_of_funds"])[:40]
    g.leverage = bool(g.leverage or ext.get("leverage"))
    g.loss_chasing = bool(g.loss_chasing or ext.get("loss_chasing"))
    g.fomo = bool(g.fomo or ext.get("fomo"))
    # a floor-worthy move cannot hide behind a question mark
    if intent != "decision" and f.amount and f.floor.severity >= 1 and f.intent in ("decision", "pressure"):
        intent = "decision"
        g.amount, g.asset, g.asset_kind, g.existing_exposure = f.amount, f.asset, f.asset_kind, f.existing_exposure
    g.intent = "decision" if intent == "decision" else intent
    g.extraction = "brain"
    return compute_floor(g, person, history, policy)


# ---------------------------------------------------------------- the rule core's words

def fmt_money(v: float, cur: str = "USD") -> str:
    sym = {"USD": "$", "AED": "AED ", "INR": "₹"}.get(cur, "")
    if v >= 1e6:
        return f"{sym}{v / 1e6:.1f}M".replace(".0M", "M")
    if v >= 1e3:
        return f"{sym}{v / 1e3:.0f}k"
    return f"{sym}{v:,.0f}"


def record_lines(person: Person, f: Facts) -> list[str]:
    """What the ledger and genome actually say that bears on this message. Used when there is no verdict to give."""
    cur = person.currency
    out: list[str] = []
    if f.asset:
        pos = match_position(f.asset, person)
        if pos and person.liquid_net_worth:
            out.append(f"You hold {fmt_money(pos.value, cur)} of {pos.asset}, {100 * pos.value / person.liquid_net_worth:.0f}% of your liquid net worth.")
    if person.liquid_net_worth and not out:
        out.append(f"I know {fmt_money(person.liquid_net_worth, cur)} of liquid net worth across {len(person.positions)} holdings, "
                   f"a stated {person.risk_profile.stated} risk profile" + (f" and {len(person.lessons)} recorded lessons." if person.lessons else "."))
    if not person.liquid_net_worth:
        out.append("I don't have your numbers yet, so anything I say about sizing is general, not personal.")
    return out


def rule_core_verdict(f: Facts, person: Person) -> tuple[str, list[str]]:
    """The deterministic reasoning core: plain-language headline + evidence-backed reasons."""
    cur = person.currency
    reasons: list[str] = []
    if f.intent == "question":
        return "That's a question, not a decision, so there's no verdict to give.", record_lines(person, f)
    if f.intent == "objection":
        return ("Fair. Let me read it again.",
                ["I only hold you to what is in your own ledger; if a past event isn't there, it didn't come from you."] + record_lines(person, f))
    if f.concentration_pct is not None and "concentration" in f.flags:
        what = f.asset or "this position"
        held = f" on top of the {fmt_money(f.existing_exposure, cur)} you already hold" if f.existing_exposure else ""
        reasons.append(f"This would put {f.concentration_pct:.0f}% of your liquid net worth in {what}{held}. "
                       f"Your plan caps any single bet well below that.")
    if "lump-sum" in f.flags and f.concentration_pct is not None:
        reasons.append(f"That is {f.concentration_pct:.0f}% of your liquid net worth in one move. The fund is fine; the timing risk is the size.")
    if f.leverage:
        reasons.append("You'd be borrowing to do it. Leverage turns a bad week into a permanent loss.")
    if f.loss_chasing:
        reasons.append("This reads like trying to win back a loss. That's the single most expensive pattern in investing.")
    if f.fomo:
        reasons.append("The urgency is the tell. Opportunities that can't wait a day are usually priced for the people selling them.")
    if f.profile_breach:
        reasons.append(f"Your stated risk profile is {person.risk_profile.stated}. This is not a {person.risk_profile.stated} move.")
    if "unknown-numbers" in f.flags:
        reasons.append("I don't know your liquid net worth or what you already hold, so I can't size this honestly yet.")
    for h in (f.prior_ignored[:2] if f.floor.severity >= 1 else []):
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
        if "unknown-numbers" in f.flags and len(f.flags) == 1:
            headline = "Not yet. I need your numbers before I can size this."
        else:
            headline = "Not yet. This needs answers before it gets your money."
    else:
        headline = "Yes, this fits your plan."
        if f.amount and f.concentration_pct is not None:
            reasons.append(f"At {f.concentration_pct:.0f}% of liquid net worth, the size is within your limits.")
        if f.diversified and f.asset:
            reasons.append(f"{f.asset} is a diversified holding, so this adds breadth, not a single-name bet.")
        if not reasons:
            reasons.append("Nothing here breaks your stated risk profile, your goals or your own history.")
    return headline, reasons
