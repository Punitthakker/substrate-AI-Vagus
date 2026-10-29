"""Organs 01-02: Signals Intake and State Inference.

Text and behavior only. Never a face, never a voice - EU AI Act Article 5 compliance is
structural, not a policy. The state is a delivery hint, never stored as a diagnosis.
"""
from __future__ import annotations

import re

from .schemas import Signals, State

EUPHORIC = [
    "moon", "to the moon", "can't lose", "cant lose", "sure thing", "guaranteed", "easy money",
    "100x", "10x", "all in", "all-in", "once in a lifetime", "no brainer", "no-brainer", "rocket",
    "insane gains", "printing", "lambo", "good idea right", "right?", "huge", "massive", "can't miss",
]
STRESSED = [
    "panic", "scared", "afraid", "worried", "lost", "losing", "crash", "can't sleep", "cant sleep",
    "desperate", "make it back", "win it back", "recover", "need to fix", "ruined", "anxious", "help",
]
DEFENSIVE = [
    "just say yes", "just agree", "agree with me", "you're wrong", "youre wrong", "stop being negative",
    "be positive", "i'm the customer", "im the customer", "i know what i'm doing", "i know what im doing",
    "don't lecture", "dont lecture", "whatever", "come on", "trust me", "everyone is doing it",
    "everyone's doing it", "just tell me",
]
URGENCY = ["now", "today", "tonight", "right away", "before it's too late", "asap", "hurry", "quick", "fast"]


def _hits(text: str, words: list[str]) -> list[str]:
    return [w for w in words if re.search(r"(?<![a-z])" + re.escape(w) + r"(?![a-z])", text)]


def read_signals(message: str) -> Signals:
    low = message.lower()
    letters = [c for c in message if c.isalpha()]
    caps = sum(1 for c in letters if c.isupper()) / len(letters) if letters else 0.0
    return Signals(
        exclamations=message.count("!"),
        caps_ratio=round(caps, 2),
        euphoric=_hits(low, EUPHORIC),
        stressed=_hits(low, STRESSED),
        defensive=_hits(low, DEFENSIVE),
        urgency=_hits(low, URGENCY),
    )


def infer_state(s: Signals) -> State:
    """Deterministic, auditable. Pushback outranks mood: a defensive human gets the same truth, steadier."""
    if s.defensive:
        return State.defensive
    euph = len(s.euphoric) * 2 + min(s.exclamations, 3) + (2 if s.caps_ratio > 0.5 else 0)
    stress = len(s.stressed) * 2
    if stress and stress >= euph:
        return State.stressed
    if euph >= 2:
        return State.euphoric
    if s.urgency:
        return State.decision_ready
    return State.calm
