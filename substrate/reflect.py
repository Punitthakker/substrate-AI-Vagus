"""Motivational Interviewing for machines: OARS (Open questions, Affirmations, Reflections, Summaries).

MI (Miller and Rollnick) is one of the best-evidenced methods for helping people change behaviour, used in
addiction care, medicine and coaching. Its core finding: people defend what they are told and act on what they
hear themselves say. So before the truth, Substrate reflects the person back to themselves, accurately and
without judgment; it affirms what they did right (asking before acting); and in the gentler voices it ends with
one open question that lets them argue for the wiser choice in their own words.

None of this touches the verdict. It changes whether the verdict can be heard.
"""
from __future__ import annotations

from .schemas import Facts

# Reflections: what the person is feeling and wanting, in plain words, keyed by tissue and the live flags.
REFLECT = [
    ("markets", {"harm"}, "Betting has started to cost more than money, and part of you knows it."),
    ("markets", {"chasing"}, "You're down, and you want this one to put it right."),
    ("markets", {"certainty", "parlay-math"}, "This one feels close to certain to you."),
    ("markets", {"all-in", "bankroll"}, "You want this to be the one that really counts."),
    ("trading", {"chasing"}, "You're down, and you want the next trade to undo it."),
    ("trading", {"gamblers-fallacy"}, "After a run like that, a turn feels overdue."),
    ("trading", {"anchoring"}, "You remember where it was, and it feels like it should go back there."),
    ("trading", {"disposition"}, "Selling would make the loss real, and you're not ready for that."),
    ("trading", {"leverage", "oversized"}, "You see the setup clearly and want it to count."),
    ("trading", {"crowded-trade", "fomo"}, "Everyone around you is on this side, and that feels like confirmation."),
    ("wealth", {"loss-chasing"}, "You want back what you lost, and you want it fast."),
    ("wealth", {"leverage"}, "You're confident enough to borrow for this."),
    ("wealth", {"concentration", "fomo"}, "You can see this running, and you don't want to watch it go without you."),
    ("venture", {"fomo", "valuation"}, "The round is hot and the clock is loud."),
    ("venture", {"no-diligence"}, "You trust this founder enough to skip the homework."),
    ("venture", {"check-concentration"}, "You believe in this one more than the rest of the fund."),
    ("founder", {"fomo"}, "You can feel the competitor moving and you want to move faster."),
    ("founder", {"runway", "runway-drop"}, "You want to grow, and this feels like the way to do it."),
    ("founder", {"vanity-spend"}, "You want the company to look like the company you're building."),
    ("wellbeing", {"impulse"}, "You've been holding this in, and you want it out, now."),
    ("wellbeing", {"vent"}, "That hurt, and you need someone to hear it."),
]

AFFIRM = {
    "markets": "Checking with me before you placed it is the disciplined move.",
    "wealth": "Pausing to ask before you act is exactly what good investors do.",
    "venture": "Pressure-testing this before the wire is the job, done well.",
    "founder": "Running the numbers before you commit is what keeps companies alive.",
    "trading": "Checking the setup before you click is what separates traders from gamblers.",
    "wellbeing": "Telling me instead of acting on it took real strength.",
}

ASK = {
    "markets": "What would make walking away tonight feel like a win?",
    "wealth": "What does this money need to do for your family in ten years?",
    "venture": "What would you need to see to be glad you waited a week?",
    "founder": "Which smaller version of this could the runway carry?",
    "trading": "If this trade stopped you out tomorrow, what would you wish you had sized it at?",
    "wellbeing": "What would morning-you want tonight-you to do?",
}

GENTLE = {"mentor", "comfort", "partner", "grandmother", "father"}


def reflection(domain: str, facts: Facts, needs: list[str]) -> str | None:
    flags = set(facts.flags)
    if domain == "wellbeing" and facts.metrics.get("venting"):
        flags.add("vent")
    for tissue, keys, line in REFLECT:
        if tissue == domain and keys & flags:
            return line
    if "approval" in needs:
        return "You'd like me to say yes."
    return None


def affirmation(domain: str, severity: int) -> str | None:
    return AFFIRM.get(domain) if severity >= 1 else None


def open_question(domain: str, severity: int, firmness: int, temperament: str) -> str | None:
    if severity >= 1 and firmness <= 4 and temperament in GENTLE:
        return ASK.get(domain)
    return None
