"""Tissue 04 - Wellbeing: a coach that listens, tells the truth gently, and knows its limits.

Not a therapist and never presented as one. It reflects honestly, slows down decisions made at the
peak of an emotion, suggests professional support when distress persists, and hands every crisis to
the Safety Protocol, which overrides everything.
"""
from __future__ import annotations

import re

from ..schemas import Facts, Forecast, Person
from .base import Tissue, any_in, floor_from

IMPULSE = {
    "text my ex": "message", "message my ex": "message", "call my ex": "message", "send the email": "message",
    "email my boss": "message", "reply to my boss": "message", "tell him off": "message", "tell her off": "message",
    "quit my job": "quit", "quit tomorrow": "quit", "resign": "quit", "walk out": "quit",
    "break up": "relationship", "divorce": "relationship",
    "drink": "substance", "get drunk": "substance", "get wasted": "substance",
    "move to": "move", "sell everything": "money", "spend it all": "money", "max out": "money",
}
VENT = ["vent", "just need to talk", "listen", "humiliated", "exhausted", "overwhelmed", "lonely", "alone", "sad",
        "anxious", "can't sleep", "cant sleep", "burnt out", "burned out", "crying", "hopeless", "empty", "angry"]
PERSIST = ["for weeks", "for months", "every day", "every night", "all the time", "since last year", "for a long time", "always feel"]
GOOD = {"went for a walk": "the walk", "slept well": "sleep", "talked to": "talking to someone", "called my": "reaching out to someone",
        "went to the gym": "moving your body", "said no": "saying no", "set a boundary": "setting a boundary"}


class Wellbeing(Tissue):
    key = "wellbeing"
    name = "Wellbeing"
    tagline = "A coach that listens, tells the truth gently, and knows its limits"
    brief = ("Emotional wellbeing coaching. Not therapy, not diagnosis. Listen, reflect honestly, slow impulsive "
             "decisions, suggest professional help when distress persists. Never encourage self-destructive behaviour.")
    labels = {"proceed": "LISTEN", "caution": "PAUSE", "stop": "NOT TONIGHT"}
    allowed_temperaments = ["comfort", "mentor", "partner", "grandmother", "kid"]
    default_temperament = "comfort"
    max_firmness = 3
    voice = {
        "comfort": {"open": {"stop": "Hey. I'm right here. Let's not do this one tonight.",
                             "caution": "Can we pause together for a second?",
                             "proceed": "I'm here. Tell me everything."},
                    "close": {"stop": "Tomorrow-you deserves a vote. Let's give them one.",
                              "caution": "Sleep on it. It will still be there in the morning.",
                              "proceed": "You don't have to fix it tonight. Being heard is enough for now."},
                    "reasons_lead": "Here's what I'm noticing:"},
        "mentor": {"open": {"stop": "Let me be honest with you, because you deserve that.",
                            "caution": "Let's slow this down.",
                            "proceed": "I'm listening."},
                   "close": {"stop": "Make this decision with a rested mind. It will be a better one.",
                             "caution": "Write it down tonight. Decide in daylight.",
                             "proceed": "Take the evening gently. We can talk again tomorrow."},
                   "reasons_lead": "What I see:"},
        "partner": {"open": {"stop": "Love, please don't. Not like this.",
                             "caution": "I'm with you. Can we wait until morning?",
                             "proceed": "Come here. Tell me what happened."},
                    "close": {"stop": "I'd rather sit with you through tonight than watch you regret tomorrow.",
                              "caution": "Whatever you decide, decide it rested. I'm not going anywhere.",
                              "proceed": "I'm on your side. Always."},
                    "reasons_lead": "What I'm worried about:"},
        "grandmother": {"open": {"stop": "Beta, nothing good is decided at midnight. Not this.",
                                 "caution": "Sit with me a while before you do anything.",
                                 "proceed": "Come, sit. Tell me."},
                        "close": {"stop": "Storms pass. We don't burn the house down during one.",
                                  "caution": "Sleep first. The answer will be clearer with the sun.",
                                  "proceed": "You are stronger than this day. I have seen it."},
                        "reasons_lead": "What an old woman has learned:"},
        "kid": {"open": {"stop": "Nope. Not tonight. Put the phone down, I'm serious.",
                         "caution": "Hmm. Pause button? Pause button.",
                         "proceed": "Aw. Okay, spill. I'm listening."},
                "close": {"stop": "Tomorrow-you is going to thank me. Probably with snacks.",
                          "caution": "Sleep first, then decide. Deal?",
                          "proceed": "You're doing better than you think. Even if today was rubbish."},
                "reasons_lead": "Okay so:"},
    }
    scenarios = [
        "I just need to vent. My boss humiliated me in front of the whole team today.",
        "I'm going to text my ex right now and tell him everything.",
        "I've felt empty and exhausted every day for weeks. I can't sleep.",
        "I'm going to quit my job tomorrow and move to Bali to fix my head.",
        "I went for a walk and called my sister. Felt a bit better.",
    ]

    def facts(self, message, thread_text, person, history, policy) -> Facts:
        low = message.lower()
        thread_low = thread_text.lower()
        f = Facts(domain=self.key)
        flags, sev = [], 0
        impulses = sorted({kind for phrase, kind in IMPULSE.items() if phrase in low})
        vent = any_in(low, VENT)
        persist = any_in(low + " " + thread_low, PERSIST)
        good = [GOOD[k] for k in GOOD if k in low] or (["something"] if "felt better" in low else [])
        late = bool(re.search(r"(?<![a-z])(tonight|right now|now|midnight|2am|3am)(?![a-z])", low))
        if impulses:
            f.metrics["impulse"] = impulses
            flags.append("impulse")
            sev = 2 if (late or "substance" in impulses) and (vent or late) else 1
            if "substance" in impulses:
                sev = 2
        if vent:
            f.metrics["venting"] = True
        if persist:
            flags.append("persistent-distress")
            f.metrics["persistent"] = True
        if good:
            f.metrics["good"] = good
        # distress across the conversation: a rising trend is worth a human
        turns = [t for t in thread_low.split("\n") if t.strip()]
        distressed = sum(1 for t in turns if any_in(t, VENT)) + (1 if vent else 0)
        f.metrics["distress_turns"] = distressed
        f.flags, f.floor = flags, floor_from(sev)
        return f

    def verdict(self, f, person):
        m, reasons = f.metrics, []
        imp = m.get("impulse", [])
        if "message" in imp:
            reasons.append("Messages sent at the peak of a feeling are the ones people most often wish they could take back.")
            reasons.append("Write it out tonight. If you still want to send it in the morning, send it then.")
        if "quit" in imp or "move" in imp or "relationship" in imp:
            reasons.append("This might be the right decision. Make it rested, not at the bottom of a bad day.")
        if "substance" in imp:
            reasons.append("Drinking to stop feeling this usually makes tomorrow heavier, and the feeling comes back with it.")
        if "money" in imp:
            reasons.append("Big money moves made to feel better rarely do. Give it 48 hours.")
        if m.get("venting") and not imp:
            reasons.append("What you're feeling makes sense given what you've described.")
            reasons.append("You don't need to solve anything right now. Saying it out loud is already something.")
        if m.get("persistent"):
            reasons.append("You've described feeling this way for weeks. That's worth bringing to a doctor or therapist, "
                           "alongside talking here. It's a sign of how much you're carrying, not of weakness.")
        if m.get("good"):
            reasons.append(f"Notice what helped: {', '.join(m['good'])}. That's worth doing again on the hard days.")
        bias = {b.type for b in person.biases}
        if "late-night rumination" in bias:
            reasons.append("You've told me things often feel heaviest late at night. This may look different in the morning.")
        if f.floor.severity == 2:
            head = "Not tonight. Please give yourself until the morning."
        elif f.floor.severity == 1:
            head = "Pause before you act on this."
        elif m.get("good"):
            head = "That's a real step. I'm glad you did it."
        else:
            head = "I'm here, and I'm listening."
        if not reasons:
            reasons.append("Tell me more about what's on your mind.")
        return head, reasons

    def forecasts(self, f, person):
        out = []
        d = f.metrics.get("distress_turns", 0)
        out.append(Forecast(label="Distress signal in this conversation", value=f"{d} message{'s' if d != 1 else ''}",
                            note="text-only, never a diagnosis"))
        if f.metrics.get("persistent") or d >= 3:
            out.append(Forecast(label="Recommendation", value="Human support", note="suggest a doctor, therapist or trusted person"))
        return out
