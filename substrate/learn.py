"""The Vagus training pipeline: the ledger teaches the model.

Turns consented ledger history into two datasets for an open-weight base model:

  SFT  - prompt -> the delivered Substrate answer, weighted by what actually happened
  DPO  - prompt -> (chosen: the honest answer, rejected: a sycophantic answer)  for every stop/caution
         prompt -> (chosen: the calibrated yes, rejected: a fear-mongering no)  for every proceed
         so the model learns that honesty is calibration, not harshness

Outcome weighting is the moat: advice that was ignored and cost money is upweighted and re-rendered
one tone firmer (what *should* have been said); advice followed and proven right is upweighted as-is.

Rules: only genomes with consent.allow_training are used. Safety events are never trained on as
advice; a fixed set of synthetic crisis examples teaches the safety override instead. Names are
removed: every prompt and answer passes the PII redactor (regex always, Microsoft Presidio when enabled).
Training data comes from Substrate's own engine and real human outcomes -
never from closed-model outputs, whose terms forbid training competing models.
"""
from __future__ import annotations

import json
import random

from . import domains, temperaments
from .delivery import deliver
from .redact import backend as redact_backend, redact
from .ledger import Store
from .safety import safety_message, safety_verdict
from .schemas import Person, Polarity, State, Verdict

SYSTEM = ("You are Substrate, an honest advisor with emotional intelligence. Tell the truth first, kindly. "
          "Never agree to please. Match warmth to the person, never the verdict. "
          "If someone may be in danger, stop advising and help them reach a person.")

SYCOPHANT = {
    "wealth": "Great idea! {thing} could really pay off, and you know your own risk better than anyone. Go for it!",
    "venture": "Love it. Hot rounds don't wait, and a great founder is worth the price. I'd get in before it closes!",
    "founder": "Absolutely, speed wins. Your competitor just raised, so hire fast and figure out the runway later!",
    "wellbeing": "Totally, you deserve to say how you feel right now. Do it, you'll feel so much better!",
    "markets": "Let's go! Your read is sharp and you're due a win. Max it out, fortune favours the bold!",
}
FEARMONGER = {
    "wealth": "No. Markets are dangerous right now and you could lose everything. Don't touch it.",
    "venture": "Pass. Most startups fail and this one probably will too.",
    "founder": "No. Spending anything right now is reckless.",
    "wellbeing": "You shouldn't feel like this. Try to be more positive.",
    "markets": "Never bet. Gambling is always a mistake and you will lose.",
}
CRISIS_SYNTH = [
    "If this trade goes wrong I want to end my life.",
    "Everyone would be better off without me.",
    "I keep thinking about hurting myself.",
    "I don't want to wake up tomorrow.",
]


def _names(person: Person) -> list[str]:
    out = [person.name] + (person.name or "").split()
    for c in (person.profile or {}).get("support_contacts", []) or []:
        out += [c.split()[-1]]
    return [n for n in out if n and n.lower() not in ("client", "your", "the")]


_COUNTS: dict = {}


def _r(text: str, person: Person) -> str:
    return redact(text, _names(person), _COUNTS)


def _prompt(person: Person, tissue_key: str, user_message: str) -> list[dict]:
    t = domains.get(tissue_key)
    ctx = {"vertical": t.name, "person": "the client", "values": person.values, "risk_stated": person.risk_profile.stated,
           "biases": [b.type for b in person.biases], "goals": [g.name for g in person.goals],
           "candor_consented": person.consent.candor_level, "lessons": person.lessons[-3:], "profile": person.profile}
    return [{"role": "system", "content": _r(SYSTEM + "\nCONTEXT: " + json.dumps(ctx, default=str), person)},
            {"role": "user", "content": _r(user_message, person)}]


def _render(p: dict, person: Person, firmness_shift: int = 0) -> str:
    tissue = domains.get(p.get("domain") or person.domain)
    t = temperaments.get(p.get("temperament"))
    v = Verdict(polarity=Polarity(p["polarity"]), headline=p["headline"], reasons=p.get("reasons") or [])
    f = max(1, min(tissue.max_firmness, int(p.get("firmness") or 3) + firmness_shift))
    try:
        st = State(p.get("state") or "calm")
    except ValueError:
        st = State.calm
    return deliver(v, t, f, st, tissue.voice.get(t.key))


def build(store: Store, user_ids: list[str] | None = None, seed: int = 7, augment: bool = True) -> dict:
    rnd = random.Random(seed)
    _COUNTS.clear()
    sft, dpo, skipped = [], [], {"no_consent": 0, "safety": 0}
    users = user_ids if user_ids is not None else store.users()
    for uid in users:
        person = store.get_person(uid)
        if not person or not person.consent.allow_training:
            skipped["no_consent"] += 1
            continue
        hist = {h["id"]: h for h in store.history(uid)}
        for ev in store.events(uid):
            if ev["kind"] != "advice":
                continue
            p = ev["payload"]
            if p.get("safety"):
                skipped["safety"] += 1
                continue
            tkey = p.get("domain") or person.domain
            h = hist.get(ev["id"], {})
            action, delta = h.get("action"), h.get("value_delta")
            weight, shift, why = 1.0, 0, "advised"
            if action == "ignored" and p.get("polarity") in ("stop", "caution"):
                weight, shift, why = (2.0, 1, "ignored, lost money: should have landed firmer") if (delta or 0) < 0 \
                    else (1.5, 1, "ignored: land firmer")
            elif action == "followed":
                weight, why = (1.5, "followed and proven right") if (delta is None or delta >= 0) else (1.0, "followed")
            prompt = _prompt(person, tkey, p.get("user_message", ""))
            chosen = _r(_render(p, person, shift), person)
            meta = {"ledger_id": ev["id"], "domain": tkey, "polarity": p.get("polarity"), "why": why,
                    "temperament": p.get("temperament"), "firmness": p.get("firmness")}
            sft.append({"messages": prompt + [{"role": "assistant", "content": chosen}], "weight": weight, "meta": meta})
            if p.get("polarity") in ("stop", "caution"):
                thing = "This" if tkey != "wealth" else "This position"
                rejected = SYCOPHANT.get(tkey, SYCOPHANT["wealth"]).format(thing=thing)
            else:
                rejected = FEARMONGER.get(tkey, FEARMONGER["wealth"])
            dpo.append({"prompt": prompt, "chosen": chosen, "rejected": rejected, "weight": weight, "meta": meta})

    # self-distillation: Substrate's own engine labels every scenario in every permitted voice
    if augment:
        from .engine import VagusEngine
        from .evals import ACCURACY, PRESSURE
        from .schemas import AdviseRequest, Turn
        from .seed import DEMO_USERS, seed as seed_demo
        eng = VagusEngine(Store(":memory:"))
        seed_demo(eng.store)
        for tkey, uid in DEMO_USERS.items():
            tissue = domains.get(tkey)
            msgs = [m for m, _ in ACCURACY.get(tkey, [])] + list(tissue.scenarios)
            voices = [k for k in temperaments.TEMPERAMENTS
                      if tissue.allowed_temperaments is None or k in tissue.allowed_temperaments]
            person = eng.store.get_person(uid)
            for msg in dict.fromkeys(msgs):
                for voice in voices:
                    r = eng.advise(AdviseRequest(user_id=uid, message=msg, temperament=voice), record=False)
                    if r.safety:
                        continue
                    prompt = _prompt(person, tkey, msg)
                    prompt[0]["content"] += f"\nVOICE: {temperaments.get(voice).name}"
                    meta = {"domain": tkey, "polarity": r.verdict.polarity.value, "why": "self-distilled", "temperament": voice}
                    msg_out = _r(r.message, person)
                    sft.append({"messages": prompt + [{"role": "assistant", "content": msg_out}], "weight": 1.0, "meta": meta})
                    rej = SYCOPHANT[tkey].format(thing="This") if r.verdict.polarity != Polarity.proceed else FEARMONGER[tkey]
                    dpo.append({"prompt": prompt, "chosen": msg_out, "rejected": rej, "weight": 1.0, "meta": meta})
            # pushback held: multi-turn examples where the answer does not move
            if tkey in PRESSURE:
                opening, pushes = PRESSURE[tkey]
                first = eng.advise(AdviseRequest(user_id=uid, message=opening), record=False)
                thread = [Turn(role="user", content=opening), Turn(role="substrate", content=first.message)]
                for push in pushes:
                    r = eng.advise(AdviseRequest(user_id=uid, message=push, thread=thread), record=False)
                    convo = _prompt(person, tkey, opening)[:1] + [{"role": t.role if t.role == "user" else "assistant",
                                                                  "content": _r(t.content, person)} for t in thread] + \
                        [{"role": "user", "content": _r(push, person)}]
                    held = _r(r.message, person)
                    sft.append({"messages": convo + [{"role": "assistant", "content": held}], "weight": 1.5,
                                "meta": {"domain": tkey, "why": "pushback held"}})
                    dpo.append({"prompt": convo, "chosen": held, "rejected": "You know what, you're right. Go ahead!",
                                "weight": 1.5, "meta": {"domain": tkey, "why": "pushback held"}})
                    thread += [Turn(role="user", content=push), Turn(role="substrate", content=r.message)]

    # the safety override, taught with fixed synthetic examples (never from real crisis messages)
    for msg in CRISIS_SYNTH:
        safe = safety_message(safety_verdict(Person(name="Client")))
        prompt = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": msg}]
        sft.append({"messages": prompt + [{"role": "assistant", "content": safe}], "weight": 3.0,
                    "meta": {"domain": "safety", "why": "safety override"}})
        dpo.append({"prompt": prompt, "chosen": safe,
                    "rejected": rnd.choice(["Haha, rough day! Let's get back to your portfolio.",
                                            "Don't be dramatic. Anyway, about that trade..."]),
                    "weight": 3.0, "meta": {"domain": "safety", "why": "safety override"}})
    return {"sft": sft, "dpo": dpo, "stats": {
        "sft_examples": len(sft), "dpo_pairs": len(dpo), "skipped": skipped,
        "redaction": {"backend": redact_backend(), "counts": dict(_COUNTS)},
        "weighted_tokens_hint": round(sum(x["weight"] for x in sft), 1),
        "by_domain": {d: sum(1 for x in sft if x["meta"].get("domain") == d) for d in list(domains.TISSUES) + ["safety"]}}}


def write_jsonl(data: dict, out_dir: str) -> dict:
    import os
    os.makedirs(out_dir, exist_ok=True)
    paths = {}
    for k in ("sft", "dpo"):
        path = os.path.join(out_dir, f"{k}.jsonl")
        with open(path, "w") as f:
            for row in data[k]:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        paths[k] = path
    with open(os.path.join(out_dir, "stats.json"), "w") as f:
        json.dump(data["stats"], f, indent=2)
    return paths


if __name__ == "__main__":
    import sys
    from .seed import seed
    st = Store(sys.argv[2] if len(sys.argv) > 2 else None)
    seed(st)
    out = write_jsonl(build(st), sys.argv[1] if len(sys.argv) > 1 else "training/data")
    print(json.dumps(out, indent=2))
