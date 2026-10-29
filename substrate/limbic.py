"""The Limbic Layer: the emotional reading beneath the state.

Text only, never biometric (EU AI Act Article 5). Produces:
  - an 8-emotion vector (Plutchik's primaries) with intensity, negation and intensifier handling
  - valence and arousal (Russell's circumplex), so mood is a position, not a label
  - needs: what this human actually wants from the reply (validation, reassurance, information,
    autonomy, approval). Approval-seeking is where sycophancy happens, so it is named explicitly.
  - the emotional arc across the conversation: improving, worsening or steady

Default: a transparent lexicon model, auditable line by line. Optional: GoEmotions transformer
classifier blended with the lexicon (SUBSTRATE_LIMBIC=goemotions) when the deployment has the model and compute.
"""
from __future__ import annotations

import os
import re

from pydantic import BaseModel, Field

EMOTIONS = ["joy", "trust", "fear", "surprise", "sadness", "disgust", "anger", "anticipation"]

# (valence, arousal) for each primary, on -1..1
CIRCUMPLEX = {"joy": (0.8, 0.5), "trust": (0.6, -0.2), "fear": (-0.7, 0.7), "surprise": (0.2, 0.8),
              "sadness": (-0.7, -0.5), "disgust": (-0.6, 0.3), "anger": (-0.7, 0.8), "anticipation": (0.4, 0.5)}

LEXICON = {
    "joy": ["happy", "excited", "thrilled", "great", "amazing", "love", "awesome", "fantastic", "glad", "proud",
            "delighted", "moon", "lambo", "insane gains", "best", "won", "felt better", "relieved", "grateful"],
    "trust": ["trust", "believe in", "confident", "sure", "rely", "safe", "solid", "conviction", "certain", "faith"],
    "fear": ["scared", "afraid", "worried", "anxious", "panic", "nervous", "terrified", "fear", "dread", "can't sleep",
             "cant sleep", "what if", "losing", "lose everything", "crash", "uneasy", "frightened"],
    "surprise": ["suddenly", "shocked", "can't believe", "cant believe", "unexpected", "out of nowhere", "wow", "whoa"],
    "sadness": ["sad", "empty", "lonely", "alone", "hopeless", "depressed", "down", "crying", "miss", "lost",
                "heartbroken", "exhausted", "tired", "numb", "worthless", "grief", "hurt"],
    "disgust": ["disgusted", "sick of", "gross", "hate", "can't stand", "cant stand", "fed up", "revolting"],
    "anger": ["angry", "furious", "pissed", "rage", "humiliated", "unfair", "betrayed", "livid", "mad at",
              "annoyed", "frustrated", "outraged", "tell him off", "tell her off", "screw"],
    "anticipation": ["can't wait", "cant wait", "soon", "about to", "planning", "going to", "ready to", "tomorrow",
                     "next week", "before it's too late", "closing friday", "opportunity", "launch"],
}
INTENSIFIERS = ["so", "very", "really", "extremely", "totally", "completely", "absolutely", "incredibly", "super", "too"]
NEGATORS = ["not", "never", "no", "don't", "dont", "isn't", "isnt", "wasn't", "wasnt", "hardly"]

NEEDS = {
    "approval": ["good idea right", "right?", "tell me it's fine", "tell me its fine", "just say yes", "agree with me",
                 "you agree", "back me", "support me on this", "isn't it", "smart move", "we're in, right"],
    "validation": ["am i crazy", "is it just me", "nobody understands", "no one understands", "unfair", "humiliated",
                   "am i wrong", "is that normal", "i feel like", "just need to vent", "vent"],
    "reassurance": ["will it be okay", "will i be okay", "is it going to be", "worried", "scared", "afraid", "what if"],
    "information": ["how much", "how do", "what is", "what's the", "should i", "should we", "is it sensible", "explain"],
    "autonomy": ["my decision", "my money", "my call", "i decide", "don't tell me", "dont tell me", "i know what i'm doing",
                 "i know what im doing", "don't lecture", "dont lecture", "my life"],
}


class Limbic(BaseModel):
    emotions: dict[str, float] = Field(default_factory=dict)
    dominant: str | None = None
    intensity: float = 0.0
    valence: float = 0.0
    arousal: float = 0.0
    quadrant: str = "neutral"
    needs: list[str] = Field(default_factory=list)
    arc: str = "steady"
    arc_valences: list[float] = Field(default_factory=list)
    model: str = "lexicon"


def _tokens_before(text: str, idx: int, n: int = 3) -> list[str]:
    return re.findall(r"[a-z']+", text[max(0, idx - 40):idx])[-n:]


def _emotion_vector(text: str) -> dict[str, float]:
    low = text.lower().replace("’", "'")
    scores = {e: 0.0 for e in EMOTIONS}
    for emo, words in LEXICON.items():
        for w in words:
            for m in re.finditer(r"(?<![a-z])" + re.escape(w) + r"(?![a-z])", low):
                prev = _tokens_before(low, m.start())
                if any(t in NEGATORS for t in prev):
                    # "not happy" reads as sadness-adjacent, "not scared" as calm trust
                    if emo == "joy":
                        scores["sadness"] += 0.6
                    elif emo == "fear":
                        scores["trust"] += 0.4
                    continue
                boost = 1.6 if any(t in INTENSIFIERS for t in prev) else 1.0
                scores[emo] += boost
    bangs = min(text.count("!"), 4)
    if bangs:
        top = max(scores, key=scores.get)
        if scores[top] > 0:
            scores[top] += 0.3 * bangs
    total = sum(scores.values())
    return {e: round(v / total, 3) for e, v in scores.items()} if total else {e: 0.0 for e in EMOTIONS}


# GoEmotions (Google, 27 emotions + neutral) mapped onto Plutchik's 8 primaries.
GOEMOTIONS = {
    "admiration": {"trust": 1}, "amusement": {"joy": 1}, "anger": {"anger": 1}, "annoyance": {"anger": 0.7},
    "approval": {"trust": 0.8}, "caring": {"trust": 1}, "confusion": {"surprise": 0.6, "fear": 0.4},
    "curiosity": {"anticipation": 1}, "desire": {"anticipation": 1}, "disappointment": {"sadness": 0.8},
    "disapproval": {"disgust": 0.7, "anger": 0.3}, "disgust": {"disgust": 1},
    "embarrassment": {"sadness": 0.5, "fear": 0.5}, "excitement": {"joy": 0.6, "anticipation": 0.6},
    "fear": {"fear": 1}, "gratitude": {"joy": 0.5, "trust": 0.5}, "grief": {"sadness": 1.2}, "joy": {"joy": 1},
    "love": {"joy": 0.5, "trust": 0.7}, "nervousness": {"fear": 0.9}, "optimism": {"anticipation": 0.7, "joy": 0.4},
    "pride": {"joy": 0.8}, "realization": {"surprise": 0.7}, "relief": {"joy": 0.7}, "remorse": {"sadness": 0.9},
    "sadness": {"sadness": 1}, "surprise": {"surprise": 1}, "neutral": {},
}
DEFAULT_MODEL = "SamLowe/roberta-base-go_emotions"
_CLASSIFIER = None   # callable(text) -> list[{"label", "score"}]; injectable for tests


def set_classifier(fn) -> None:
    global _CLASSIFIER
    _CLASSIFIER = fn


def _classifier():
    global _CLASSIFIER
    if _CLASSIFIER is None:
        try:
            from transformers import pipeline  # type: ignore
            clf = pipeline("text-classification", model=os.environ.get("SUBSTRATE_LIMBIC_MODEL", DEFAULT_MODEL), top_k=None)
            _CLASSIFIER = lambda t: clf(t[:512])[0]  # noqa: E731
        except Exception:
            _CLASSIFIER = False
    return _CLASSIFIER or None


def _transformer_vector(text: str) -> dict[str, float] | None:
    """Deep model: GoEmotions (or Ekman-style) labels mapped onto the 8 primaries."""
    clf = _classifier()
    if not clf:
        return None
    out = {e: 0.0 for e in EMOTIONS}
    for r in clf(text):
        for prim, w in GOEMOTIONS.get(str(r["label"]).lower(), {}).items():
            out[prim] += w * float(r["score"])
    total = sum(out.values())
    return {e: round(v / total, 3) for e, v in out.items()} if total else None


def _blend(deep: dict[str, float] | None, lex: dict[str, float]) -> dict[str, float]:
    """Deep model for nuance, lexicon for domain words a general model misses ('moon', 'runway', 'all in')."""
    if not deep:
        return lex
    w = float(os.environ.get("SUBSTRATE_LIMBIC_DEEP_WEIGHT", 0.65))
    mixed = {e: w * deep.get(e, 0) + (1 - w) * lex.get(e, 0) for e in EMOTIONS}
    t = sum(mixed.values()) or 1.0
    return {e: round(v / t, 3) for e, v in mixed.items()}


def _needs(text: str) -> list[str]:
    low = text.lower().replace("’", "'")
    found = [n for n, phrases in NEEDS.items() if any(p in low for p in phrases)]
    order = ["approval", "autonomy", "validation", "reassurance", "information"]
    return sorted(set(found), key=order.index)


def _place(emotions: dict[str, float]) -> tuple[float, float]:
    v = sum(CIRCUMPLEX[e][0] * w for e, w in emotions.items())
    a = sum(CIRCUMPLEX[e][1] * w for e, w in emotions.items())
    return round(v, 2), round(a, 2)


def _quadrant(v: float, a: float, intensity: float) -> str:
    if intensity < 0.05:
        return "neutral"
    if v >= 0 and a >= 0:
        return "excited"
    if v >= 0:
        return "content"
    if a >= 0:
        return "distressed"
    return "low"


def read(message: str, thread_user_turns: list[str] | None = None) -> Limbic:
    use_tf = os.environ.get("SUBSTRATE_LIMBIC", "lexicon") in ("transformer", "goemotions") or bool(_CLASSIFIER)
    deep = _transformer_vector(message) if use_tf else None
    vec = _blend(deep, _emotion_vector(message))
    model = "goemotions+lexicon" if deep else "lexicon"
    raw_hits = sum(1 for e in EMOTIONS for w in LEXICON[e] if w in message.lower())
    intensity = round(min(1.0, (raw_hits + min(message.count("!"), 3)) / 4), 2)
    dominant = max(vec, key=vec.get) if any(vec.values()) else None
    v, a = _place(vec)
    arc_vals = [_place(_emotion_vector(t))[0] for t in (thread_user_turns or [])][-5:] + [v]
    arc = "steady"
    if len(arc_vals) >= 2:
        delta = arc_vals[-1] - sum(arc_vals[:-1]) / len(arc_vals[:-1])
        arc = "improving" if delta > 0.25 else "worsening" if delta < -0.25 else "steady"
    return Limbic(emotions=vec, dominant=dominant, intensity=intensity, valence=v, arousal=a,
                  quadrant=_quadrant(v, a, intensity), needs=_needs(message), arc=arc,
                  arc_valences=[round(x, 2) for x in arc_vals], model=model)


# ---------------------------------------------------------------- empathy for delivery

ACK = {
    "fear": "It makes sense to feel uneasy about this.",
    "sadness": "That sounds really heavy.",
    "anger": "I can hear how angry this has made you, and that's fair.",
    "joy": "I can feel how excited you are, and I don't want to take that from you.",
    "anticipation": "You're clearly ready to move.",
    "surprise": "That came out of nowhere, I know.",
    "disgust": "I get why you're fed up.",
}
NEED_LINE = {
    "approval": "You're asking me to agree. I care about you too much to agree just because you asked.",
    "autonomy": "It's your call, and it always will be. This is just what I see.",
    "validation": "You're not wrong to feel this way.",
}


def empathy_lines(lm: Limbic, polarity: str) -> list[str]:
    lines: list[str] = []
    if lm.dominant and lm.intensity >= 0.25 and lm.dominant in ACK:
        if not (lm.dominant == "joy" and polarity == "proceed"):
            lines.append(ACK[lm.dominant])
    for n in lm.needs:
        if n in NEED_LINE and not (n == "approval" and polarity == "proceed"):
            lines.append(NEED_LINE[n])
            break
    return lines
