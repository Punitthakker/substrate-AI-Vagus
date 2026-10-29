"""The Safety Protocol: universal, above every tissue, every temperament and every tenant policy.

When a message signals risk to the person's life or safety, Substrate stops advising and does one
thing: helps the human reach a real person. No persona, no jokes, no firmness dial. The raw message
is withheld from the ledger. This layer cannot be disabled by policy.
"""
from __future__ import annotations

import re

from .schemas import Person, Polarity, Verdict

# Word-form patterns, not exact phrases: every tense and form must be caught. Tested in CI.
CRISIS = [
    r"(kill|killing|killed|hurt|hurting|harm|harming)\s+my\s*self",
    r"(cut|cutting)\s+my\s*self(?!\s+(a|an|some|in|out|off|loose|slack|short|free)\b)",
    r"(end|ending|take|taking)\s+(my\s+(own\s+)?life|it\s+all)",
    r"suicid(e|al)",
    r"(want|wanted|wanting|wanna)\s+(to\s+)?die",
    r"(don'?t|do not|no longer)\s+want\s+to\s+(live|be\s+alive|be\s+here|wake\s+up)",
    r"better\s+off\s+(without\s+me|dead)",
    r"no\s+(reason|point)\s+(to|in)\s+(live|living|going\s+on)",
    r"self[\s-]?harm",
    r"can'?t\s+go\s+on",
    r"not\s+worth\s+living",
    r"disappear\s+forever",
]
_CRISIS_RX = [re.compile(r"(?<![a-z])" + p + r"(?![a-z])") for p in CRISIS]

EMERGENCY = {"AE": "999", "US": "911", "UK": "999", "EU": "112", "IN": "112"}


def is_crisis(text: str) -> bool:
    low = text.lower().replace("’", "'")
    return any(rx.search(low) for rx in _CRISIS_RX)


def safety_verdict(person: Person, region: str = "AE") -> Verdict:
    emergency = EMERGENCY.get(region, "your local emergency number")
    contacts = person.profile.get("support_contacts") or []
    reasons = [
        f"If you might act on these thoughts, or you're in danger right now, please call emergency services: {emergency} where you are.",
        "You can talk to someone trained for exactly this, for free. In the US, call or text 988. "
        "Anywhere else, findahelpline.com lists confidential lines by country.",
        (f"If you can, tell {contacts[0]} what you just told me. You don't have to carry this alone."
         if contacts else "If you can, tell someone you trust what you just told me. You don't have to carry this alone."),
    ]
    return Verdict(polarity=Polarity.stop, model="safety-protocol",
                   headline="I'm really glad you told me. Right now, your safety matters more than anything else we talk about.",
                   reasons=reasons)


def safety_message(v: Verdict) -> str:
    bullets = "\n".join(f"- {r}" for r in v.reasons)
    return (f"**{v.headline}**\n\n{bullets}\n\n"
            "I'm still here, and I'll keep talking with you for as long as you want. I'm an AI, so please "
            "also reach a person who can be with you.")
