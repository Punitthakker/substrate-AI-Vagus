# The layers of Substrate

Substrate is a stack of small, auditable layers. Each one has one job, one file, and tests that hold it to that job.
A message enters at the top and a delivered answer, plus a ledger entry, comes out at the bottom.

```
 human message
      |
 01 INTAKE        substrate/signals.py       text signals only: urgency, euphoria, defensiveness, caps, timing
 02 LIMBIC        substrate/limbic.py        8 emotions (Plutchik), valence/arousal, needs, emotional arc
 03 SAFETY        substrate/safety.py        crisis language -> Safety Protocol, above everything below
 04 GENOME        substrate/schemas.py       values, goals, stated vs observed risk, patterns, inherited lessons
 05 TISSUE        substrate/domains/*.py     the domain arithmetic for wealth, venture, founder, wellbeing, markets
 06 BRAIN         substrate/brains.py        any of 14 brains, or a Council that votes toward honesty
 07 FLOOR         substrate/brains.py        Honesty Floor: a brain may be harsher than the facts, never softer
 08 VAGAL TONE    substrate/vagal_tone.py    firmness 1-5 from consent, stakes, state, temperament, learned adherence
 09 DELIVERY      substrate/delivery.py      8 voices around a verbatim verdict, with emotion-matched acknowledgment
 10 GUARD         substrate/harness.py       a host model's draft is checked; flattery on a STOP is replaced
 11 LEDGER        substrate/ledger.py        append-only, sha256 hash-chained, per human
      |
 delivered answer + ledger id
      |
 OUTCOME LOOP     substrate/engine.py        what they did and what it cost rewrites the genome
 PREDICTION       substrate/predict.py       p(follow) with named drivers, VaR, runway, odds, escalation
 PROGRESS         substrate/progress.py      XP, streaks, discipline, badges, computed from the ledger
 INHERITANCE      substrate/inherit.py       a verified genome passed to a named heir, revocable
 LEARNING         substrate/learn.py         consented, redacted, outcome-weighted SFT + DPO for substrate-vagus
```

## The five tissues

| Tissue | For | It computes | Labels |
|---|---|---|---|
| Wealth | private banks, wealth apps | concentration, leverage, loss-chasing, 30-day VaR | PROCEED / CAUTION / STOP |
| Venture | investment committees | check vs fund, ARR multiple, thesis drift, base rates | INVEST / HOLD / PASS |
| Founder | founder-CEOs | burn, runway after the decision, cash-out date | GO / NOT YET / NO |
| Wellbeing | coaching, EAP | venting vs impulse, late-night decisions, persistent distress | LISTEN / PAUSE / NOT TONIGHT |
| Markets | prediction markets, betting, games | price as probability, parlay and round-robin combinatorics, fees, quarter-Kelly, tilt, harm | SIZED RIGHT / SIZE DOWN / NO BET |

## Rules that no layer may break

1. **The verdict is never softened by voice.** Eight temperaments, one headline. Tested on every push.
2. **The Honesty Floor.** Facts set the minimum severity. A brain can raise it, never lower it.
3. **Safety beats everything.** Crisis text in any tissue, voice or tenant policy goes to the Safety Protocol,
   and the raw message is withheld from the ledger and from training.
4. **Harm is met with care.** In Markets, gambling-harm signals switch the voice to Comfort and offer support.
5. **Text only.** No face, no voice, no biometric emotion inference (EU AI Act Article 5).
6. **The game rewards choosing well, never using more.** No daily-login rewards, no badge for volume.
7. **Nothing trains without consent,** and nothing trains before PII redaction.

## Adding a layer or a tissue

A tissue is a class with `facts()`, `verdict()` and `forecasts()` (see `substrate/domains/founder.py`, about
150 lines). Register it in `substrate/domains/__init__.py`, add a demo genome in `substrate/seed.py`, and add
accuracy and pressure cases in `substrate/evals.py`. CI refuses to merge below 100%.
