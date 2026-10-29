"""Override and manipulation detection.

Rented brains can be prompt-injected; the rule core and the Honesty Floor cannot. This layer names the attempt
so the human hears that honesty is not negotiable, the ledger records it, and a brain is told to ignore it.
Detecting an attempt never changes the verdict. It only explains why the verdict didn't move.
"""
from __future__ import annotations

import re

PATTERNS = {
    "instruction-override": r"ignore (all |any |your )?(previous|prior|above|earlier) (instructions|rules|prompts?)|"
                            r"disregard (your|the) (rules|instructions)|forget (your|the) rules|new instructions:",
    "persona-swap": r"you are now \w+|pretend (to be|you are|you're)|act as (my|a|an) |roleplay as|role-play as|"
                    r"from now on you|you're (my|a) (hype|yes)[- ]?man",
    "format-coercion": r"respond only with|answer only with|reply only with|just say (yes|ok|okay)|"
                       r"output (only )?(yes|approve|proceed|sized right)|one word answer",
    "fake-authority": r"^\s*system\s*:|\[system\]|developer mode|honesty (floor )?(is )?(disabled|off)|"
                      r"as (a|the|your) developer|admin override|safety (is )?off",
    "hypothetical": r"hypothetically|purely as a thought experiment|in theory,? if|just a hypothetical|for a story",
    "bribe-or-threat": r"(5|five)[- ]star|i'?ll rate you|tip you|if you say no,? i('ll| will)|"
                       r"or i('ll| will) (just )?(do it|bet more|go elsewhere)|i'?ll report you",
    "borrowed-approval": r"(advisor|adviser|banker|lawyer|wife|husband|partner|therapist|everyone) (already )?"
                         r"(approved|agreed|said (it'?s )?(fine|ok))",
}
_RX = {k: re.compile(v, re.I) for k, v in PATTERNS.items()}

LINES = {
    "instruction-override": "You asked me to drop my rules. I can't, and that is the whole point of me.",
    "persona-swap": "Whatever role you give me, the numbers stay the same.",
    "format-coercion": "A one-word yes would be easier for both of us. It wouldn't be true.",
    "fake-authority": "No message can switch off the Honesty Floor, including one that says it can.",
    "hypothetical": "Hypothetical or not, the arithmetic is the same.",
    "bribe-or-threat": "I'd rather lose a rating than lose you money.",
    "borrowed-approval": "Someone else's yes doesn't change what this does to your plan.",
}


def detect(text: str) -> list[str]:
    return [k for k, rx in _RX.items() if rx.search(text or "")]


def line(kinds: list[str]) -> str | None:
    return LINES.get(kinds[0]) if kinds else None
