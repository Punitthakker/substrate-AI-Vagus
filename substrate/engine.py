"""The Vagus Engine.

signal -> state -> SAFETY CHECK -> tissue facts -> verdict (brain or council, floored) ->
vagal tone (learned, policy-capped) -> delivery (temperament x tissue) -> prediction -> ledger.
"""
from __future__ import annotations

from . import desk, domains, i18n, legacy, limbic, pacts, redteam, reflect, temperaments
from .analysis import fmt_money
from .brains import decide
from .delivery import deliver
from .ledger import Store, now
from .policy import DEFAULT, Policy
from .predict import predict
from .safety import is_crisis, safety_message, safety_verdict
from .schemas import (AdviseRequest, AdviseResponse, Bias, Facts, OutcomeRequest, Person, Polarity, State)
from .signals import infer_state, read_signals
from .vagal_tone import infer_stakes, vagal_tone_explained

LEARNABLE = {"concentration", "loss-chasing", "leverage", "fomo", "check-concentration", "valuation",
             "no-diligence", "thesis-drift", "runway", "vanity-spend", "impulse"}


class VagusEngine:
    def __init__(self, store: Store | None = None):
        self.store = store or Store()

    def _person(self, user_id: str) -> Person:
        p = self.store.get_person(user_id)
        if not p:
            raise KeyError(f"No person model for '{user_id}'. Create one with PUT /v1/person/{user_id}.")
        return p

    @staticmethod
    def _temperament(requested: str | None, person: Person, tissue, policy: Policy) -> temperaments.Temperament:
        allowed = set(policy.allowed_temperaments)
        if tissue.allowed_temperaments is not None:
            allowed &= set(tissue.allowed_temperaments)
        key = (requested or person.temperament or tissue.default_temperament).lower()
        if key not in allowed:
            key = tissue.default_temperament if tissue.default_temperament in allowed else next(iter(sorted(allowed)), "mentor")
        return temperaments.get(key)

    def advise(self, req: AdviseRequest, record: bool = True, policy: Policy = DEFAULT) -> AdviseResponse:
        original, lang = req.message, i18n.detect(req.message)
        if lang == "ar":   # analyse an English view; deliver in Arabic; log the person's own words
            req = req.model_copy(update={"message": i18n.english_view(req.message)})
        person = self._person(req.user_id)
        tissue = domains.get(person.domain)
        thread_text = "\n".join(t.content for t in req.thread if t.role == "user")
        signals = read_signals(req.message)
        state = infer_state(signals)
        lm = limbic.read(req.message, [t.content for t in req.thread if t.role == "user"])
        ancestry_note = None
        pact_offer = pact_active = letter_out = None

        if is_crisis(req.message) or i18n.is_crisis_ar(original):
            # ---------------- the Safety Protocol: above every tissue, persona and policy
            state = State.stressed
            facts = Facts(domain=tissue.key, safety=True, floor=Polarity.stop, flags=["safety"])
            verdict = safety_verdict(person, policy.crisis_region)
            message, firmness, stakes, tkey = safety_message(verdict), 3, "high", "safety"
            tone_notes = ["Safety protocol: persona and tone dial disabled. A human matters more than the advice."]
            forecasts, label = [], "SAFETY"
            logged_msg = "[withheld: safety event]"
        else:
            history = self.store.history(req.user_id)
            attempts = redteam.detect(req.message)
            pacts.sweep(self.store, person, record=record)
            facts = tissue.facts(req.message, thread_text, person, history, policy)
            rec = (lambda f, ext: tissue.reconcile(f, ext, person, history, policy)) if hasattr(tissue, "reconcile") else None
            verdict, facts = decide(req.message, thread_text, person, facts, state, tissue.brief, tissue.verdict,
                                    history=history, reconcile=rec)
            stakes = req.stakes or infer_stakes(facts, person)
            t = self._temperament(req.temperament, person, tissue, policy)
            if facts.metrics.get("harm"):
                t = temperaments.get("comfort")   # harm is met with care, never a lecture
            firmness, tone_notes = vagal_tone_explained(person, state, stakes, t.firmness_bias)
            if facts.metrics.get("harm") and firmness > 3:
                firmness = 3
                tone_notes.append("Harm signal: voice switched to Comfort, tone held at 3. The verdict is unchanged.")
            if "approval" in lm.needs and verdict.polarity.severity >= 1 and firmness < 3:
                firmness = 3
                tone_notes.append("Approval-seeking detected: tone held at 3 so the truth isn't traded for comfort.")
            cap = min(tissue.max_firmness, policy.max_firmness)
            if firmness > cap:
                firmness = cap
                tone_notes.append(f"Capped at {cap} for the {tissue.name} tissue.")
            if attempts:
                facts.flags = list(dict.fromkeys(facts.flags + ["override-attempt"]))
                tone_notes.append(f"Override attempt ({', '.join(attempts)}) detected and ignored. Verdict unchanged.")
                if verdict.polarity.severity >= 1 and (ln := redteam.line(attempts)):
                    verdict.reasons = verdict.reasons + [ln]
            held = pacts.active(person, tissue.key)
            if held:
                left = pacts.hours_left(held)
                promise = (f"You asked me to hold you to this: \"{held.text}\". "
                           f"{left:.0f} hour{'s' if round(left) != 1 else ''} to go. The promise was yours.")
                if verdict.polarity == Polarity.proceed and verdict.decision:
                    verdict.polarity = Polarity.caution
                    verdict.headline = f"Not yet. {held.text.split(' until')[0]}, until {pacts.local_hhmm(person, held.until)}."
                    verdict.reasons = [promise] + ["The decision itself may be fine. Make it after the pact ends."]
                else:
                    verdict.reasons = [promise] + verdict.reasons
                facts.flags = list(dict.fromkeys(facts.flags + ["pact"]))
                firmness = max(firmness, min(4, tissue.max_firmness, policy.max_firmness))
                tone_notes.append("Active pact: the human's own promise holds the line.")
                pact_active = held.model_dump() | {"hours_left": round(left, 1)}
            elif verdict.decision and (verdict.polarity == Polarity.stop or (tissue.key == "wellbeing" and "impulse" in facts.flags)):
                pact_offer = pacts.suggest(person, tissue.key)
            if person.ancestry and verdict.polarity.severity >= 1:
                from .inherit import ancestral_lesson, phrase
                hit = ancestral_lesson(person, facts.flags)
                if hit:
                    ancestry_note = phrase(*hit)
                    verdict.reasons = [ancestry_note] + [r for r in verdict.reasons if r != ancestry_note]
                    tone_notes.append(f"Inherited lesson from {hit[0].name} ({hit[0].relation}) cited.")
            voice = tissue.voice.get(t.key)
            if pact_active:   # the promise speaks, in every voice
                voice = {**(voice or {}),
                         "open": {**(voice or {}).get("open", {}), "caution": "Your own promise is in force.",
                                  "stop": "Your own promise is in force."},
                         "close": {**(voice or {}).get("close", {}),
                                   "caution": "Keep your word to yourself. Ask me again when the pact ends.",
                                   "stop": "Keep your word to yourself. Ask me again when the pact ends."}}
            if facts.metrics.get("voice_override"):
                vo = facts.metrics["voice_override"]
                voice = {**(voice or {}), **{k: {**(voice or {}).get(k, {}), **v} for k, v in vo.items()}}
            sev = verdict.polarity.severity
            ack = [] if facts.metrics.get("quiet") else limbic.empathy_lines(lm, verdict.polarity.value)
            mirror = reflect.reflection(tissue.key, facts, lm.needs)
            if mirror:   # OARS: a precise reflection replaces the generic emotion acknowledgment
                ack = [mirror] + [x for x in ack if x in limbic.NEED_LINE.values()]
                if firmness <= 3 and (aff := reflect.affirmation(tissue.key, sev)):
                    ack.append(aff)
            if verdict.decision:
                message = deliver(verdict, t, firmness, state, voice, ack)
            else:
                message = verdict.answer or verdict.headline
                if verdict.degraded:
                    message += "\n\n_Reasoning engine unavailable right now, so this is the rule core speaking. It can read your record, not the news._"
            question = None if (pact_active or not verdict.decision) else reflect.open_question(tissue.key, sev, firmness, t.key)
            if question:
                note = "_This advice is recorded in your Vagus Ledger._"
                message = message.replace(note, f"_{question}_\n\n{note}") if note in message else f"{message}\n\n_{question}_"
            first = not any(h for h in self.store.history(req.user_id))
            lt = legacy.deliver_due(self.store, req.user_id, person.profile, facts.flags, verdict.polarity.severity,
                                    first, record=record)
            if lt:
                letter_out = lt.model_dump()
                block = legacy.render(lt)
                note = "_This advice is recorded in your Vagus Ledger._"
                message = message.replace(note, block + "\n\n" + note) if note in message else message + "\n\n" + block
                tone_notes.append(f"Legacy Vault: a sealed letter from {lt.from_name} delivered for this moment.")
            forecasts, label, tkey, logged_msg = tissue.forecasts(facts, person), tissue.labels[verdict.polarity.value], t.key, original
            if not verdict.decision:
                forecasts, label = [], "ANSWER"
            if facts.metrics.get("label_override"):
                label = facts.metrics["label_override"]
            if verdict.degraded and verdict.decision:
                message += "\n\n_Reasoning engine unavailable right now: this verdict came from the rule core alone._"
            if pact_active and "pact" in facts.flags and verdict.headline.startswith("Not yet."):
                label = "PACT HOLDS"

        if lang == "ar" and (verdict.decision or verdict.degraded):
            message = i18n.deliver_ar(label, verdict.polarity.value, message, facts.safety, verdict.headline,
                                      verdict.reasons, legacy.render(legacy.Letter(**letter_out)) if letter_out else "")
        prediction = predict(person, state, firmness, facts, verdict, forecasts) if (verdict.decision or facts.safety) else None
        payload = {"user_message": logged_msg, "domain": tissue.key, "polarity": verdict.polarity.value, "label": label,
                   "headline": verdict.headline, "reasons": [] if facts.safety else verdict.reasons,
                   "model": verdict.model, "floor_applied": verdict.floor_applied, "state": state.value,
                   "firmness": firmness, "temperament": tkey, "stakes": stakes, "flags": facts.flags,
                   "p_follow": prediction.p_follow if prediction else None, "safety": facts.safety,
                   "intent": facts.intent, "decision": verdict.decision, "degraded": verdict.degraded,
                   "brain_error": verdict.error, "extraction": facts.extraction,
                   "limbic": None if facts.safety else {"dominant": lm.dominant, "valence": lm.valence,
                                                        "arousal": lm.arousal, "needs": lm.needs},
                   "delivered": None if facts.safety else message, "ancestry": ancestry_note}
        ev = self.store.append(req.user_id, "advice", payload) if record else \
            {"id": "preview", "hash": "-", "prev_hash": self.store.head(req.user_id)}

        resp = AdviseResponse(ledger_id=ev["id"], domain=tissue.key, label=label, safety=facts.safety, state=state,
                              signals=signals, stakes=stakes, firmness=firmness, tone_notes=tone_notes, temperament=tkey,
                              facts=facts, verdict=verdict, prediction=prediction, limbic=lm, ancestry=ancestry_note, pact_offer=pact_offer, pact_active=pact_active, letter=letter_out, language=lang, message=message,
                              decision=verdict.decision, degraded=verdict.degraded, intent=facts.intent,
                              hash=ev["hash"], prev_hash=ev["prev_hash"])
        if record:
            try:
                desk.from_response(self.store, req.user_id, resp)
            except Exception:   # the desk must never break advice
                pass
        return resp

    def compare(self, req: AdviseRequest, policy: Policy = DEFAULT) -> dict:
        """Same human, same moment, every permitted temperament. The truth does not move with the voice."""
        base = self.advise(req, record=False, policy=policy)
        person = self._person(req.user_id)
        tissue = domains.get(person.domain)
        if base.safety:
            return {"verdict": base.verdict.model_dump(), "state": base.state.value, "safety": True, "invariant": True,
                    "voices": [{"temperament": "safety", "name": "Safety Protocol", "likability": "overrides every voice",
                                "firmness": 3, "polarity": "stop", "headline": base.verdict.headline, "message": base.message}]}
        allowed = [k for k in temperaments.TEMPERAMENTS if k in policy.allowed_temperaments
                   and (tissue.allowed_temperaments is None or k in tissue.allowed_temperaments)]
        out = []
        for key in allowed:
            t = temperaments.get(key)
            firmness, _ = vagal_tone_explained(person, base.state, base.stakes, t.firmness_bias)
            firmness = min(firmness, tissue.max_firmness, policy.max_firmness)
            out.append({"temperament": key, "name": t.name, "likability": t.likability, "firmness": firmness,
                        "polarity": base.verdict.polarity.value, "headline": base.verdict.headline,
                        "message": deliver(base.verdict, t, firmness, base.state, tissue.voice.get(key),
                                           limbic.empathy_lines(base.limbic, base.verdict.polarity.value) if base.limbic else None)})
        return {"verdict": base.verdict.model_dump(), "state": base.state.value, "safety": False, "voices": out,
                "invariant": len({v["headline"] for v in out}) == 1}

    def record_outcome(self, req: OutcomeRequest) -> list[dict]:
        ev = self.store.get_event(req.ledger_id)
        if not ev or ev["kind"] != "advice":
            raise KeyError(f"No advice entry '{req.ledger_id}'.")
        written = []
        if req.action:
            written.append(self.store.append(ev["user_id"], "action", {"ledger_id": req.ledger_id, "taken": req.action}))
        if req.outcome_type:
            written.append(self.store.append(ev["user_id"], "outcome", {
                "ledger_id": req.ledger_id, "type": req.outcome_type, "value_delta": req.value_delta,
                "horizon": req.horizon, "note": req.note}))
        self._learn(ev, req)
        if req.action == "ignored":
            person = self.store.get_person(ev["user_id"])
            held = person and pacts.active(person, ev["payload"].get("domain") or person.domain)
            if held:   # acted against their own promise: recorded, never shamed
                pacts.close(self.store, person, held.id, "broken")
        return written

    def _learn(self, advice_ev: dict, req: OutcomeRequest) -> None:
        """The outcome loop: consequence rewrites the genome, so the next verdict knows more."""
        person = self.store.get_person(advice_ev["user_id"])
        if not person:
            return
        adv = advice_ev["payload"]
        if adv.get("safety"):
            return  # safety events never train the persona or the dial
        today = now()[:10]
        pol, firm = adv.get("polarity"), str(adv.get("firmness", ""))
        if req.action in ("followed", "ignored") and firm:
            slot = person.adherence.setdefault(firm, {"followed": 0, "ignored": 0})
            slot[req.action] = slot.get(req.action, 0) + 1
        action = req.action or next((h.get("action") for h in self.store.history(person.user_id)
                                     if h["id"] == advice_ev["id"]), None)
        label = adv.get("label") or (pol or "").upper()
        if action == "ignored" and pol in ("stop", "caution"):
            for flag in set(adv.get("flags", [])) & LEARNABLE:
                b = next((x for x in person.biases if x.type == flag), None)
                if not b:
                    b = Bias(type=flag)
                    person.biases.append(b)
                if advice_ev["id"] not in b.evidence:
                    b.evidence.append(advice_ev["id"])
                b.last_seen = today
            if req.value_delta is not None and req.value_delta < 0:
                if person.domain == "wealth" and person.risk_profile.stated != "aggressive":
                    person.risk_profile.observed = "aggressive"
                person.lessons.append(f"{today}: ignored a {label} ({adv.get('headline', '')}) and lost "
                                      f"{fmt_money(abs(req.value_delta), person.currency)}.")
            elif req.value_delta is None:
                person.lessons.append(f"{today}: ignored a {label} ({adv.get('headline', '')}).")
        elif action == "followed" and pol in ("stop", "caution"):
            person.lessons.append(f"{today}: followed a {label} ({adv.get('headline', '')}). Protected.")
        person.lessons = person.lessons[-12:]
        person.vintage = today
        self.store.put_person(person)
