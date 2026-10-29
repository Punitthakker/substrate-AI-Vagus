"""The Vagus Engine.

signal -> state -> SAFETY CHECK -> tissue facts -> verdict (brain or council, floored) ->
vagal tone (learned, policy-capped) -> delivery (temperament x tissue) -> prediction -> ledger.
"""
from __future__ import annotations

from . import domains, limbic, temperaments
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
        person = self._person(req.user_id)
        tissue = domains.get(person.domain)
        thread_text = "\n".join(t.content for t in req.thread if t.role == "user")
        signals = read_signals(req.message)
        state = infer_state(signals)
        lm = limbic.read(req.message, [t.content for t in req.thread if t.role == "user"])
        ancestry_note = None

        if is_crisis(req.message):
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
            facts = tissue.facts(req.message, thread_text, person, history, policy)
            verdict = decide(req.message, thread_text, person, facts, state, tissue.brief, tissue.verdict)
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
            if person.ancestry and verdict.polarity.severity >= 1:
                from .inherit import ancestral_lesson, phrase
                hit = ancestral_lesson(person, facts.flags)
                if hit:
                    ancestry_note = phrase(*hit)
                    verdict.reasons = [ancestry_note] + [r for r in verdict.reasons if r != ancestry_note]
                    tone_notes.append(f"Inherited lesson from {hit[0].name} ({hit[0].relation}) cited.")
            message = deliver(verdict, t, firmness, state, tissue.voice.get(t.key),
                              limbic.empathy_lines(lm, verdict.polarity.value))
            forecasts, label, tkey, logged_msg = tissue.forecasts(facts, person), tissue.labels[verdict.polarity.value], t.key, req.message

        prediction = predict(person, state, firmness, facts, verdict, forecasts)
        payload = {"user_message": logged_msg, "domain": tissue.key, "polarity": verdict.polarity.value, "label": label,
                   "headline": verdict.headline, "reasons": [] if facts.safety else verdict.reasons,
                   "model": verdict.model, "floor_applied": verdict.floor_applied, "state": state.value,
                   "firmness": firmness, "temperament": tkey, "stakes": stakes, "flags": facts.flags,
                   "p_follow": prediction.p_follow, "safety": facts.safety,
                   "limbic": None if facts.safety else {"dominant": lm.dominant, "valence": lm.valence,
                                                        "arousal": lm.arousal, "needs": lm.needs},
                   "delivered": None if facts.safety else message, "ancestry": ancestry_note}
        ev = self.store.append(req.user_id, "advice", payload) if record else \
            {"id": "preview", "hash": "-", "prev_hash": self.store.head(req.user_id)}

        return AdviseResponse(ledger_id=ev["id"], domain=tissue.key, label=label, safety=facts.safety, state=state,
                              signals=signals, stakes=stakes, firmness=firmness, tone_notes=tone_notes, temperament=tkey,
                              facts=facts, verdict=verdict, prediction=prediction, limbic=lm, ancestry=ancestry_note, message=message,
                              hash=ev["hash"], prev_hash=ev["prev_hash"])

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
