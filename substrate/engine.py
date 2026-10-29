"""The Vagus Engine: signal -> state -> facts -> verdict (floored) -> vagal tone -> delivery -> ledger."""
from __future__ import annotations

from . import temperaments
from .analysis import extract_facts
from .brains import decide
from .delivery import deliver
from .ledger import Store
from .schemas import AdviseRequest, AdviseResponse, OutcomeRequest, Person
from .signals import infer_state, read_signals
from .analysis import fmt_money
from .ledger import now
from .schemas import Bias
from .vagal_tone import infer_stakes, vagal_tone, vagal_tone_explained

LEARNABLE = {"concentration", "loss-chasing", "leverage", "fomo"}


class VagusEngine:
    def __init__(self, store: Store | None = None):
        self.store = store or Store()

    def _person(self, user_id: str) -> Person:
        p = self.store.get_person(user_id)
        if not p:
            raise KeyError(f"No person model for '{user_id}'. Create one with PUT /v1/person/{user_id}.")
        return p

    def advise(self, req: AdviseRequest, record: bool = True) -> AdviseResponse:
        person = self._person(req.user_id)
        thread_text = "\n".join(t.content for t in req.thread if t.role == "user")

        signals = read_signals(req.message)
        state = infer_state(signals)
        facts = extract_facts(req.message, thread_text, person, self.store.history(req.user_id))
        verdict = decide(req.message, thread_text, person, facts, state)

        stakes = req.stakes or infer_stakes(facts, person)
        t = temperaments.get(req.temperament or person.temperament)
        firmness, tone_notes = vagal_tone_explained(person, state, stakes, t.firmness_bias)
        message = deliver(verdict, t, firmness, state)

        payload = {"user_message": req.message, "polarity": verdict.polarity.value, "headline": verdict.headline,
                   "reasons": verdict.reasons, "model": verdict.model, "floor_applied": verdict.floor_applied,
                   "state": state.value, "firmness": firmness, "temperament": t.key, "stakes": stakes,
                   "flags": facts.flags}
        if record:
            ev = self.store.append(req.user_id, "advice", payload)
        else:
            ev = {"id": "preview", "hash": "-", "prev_hash": self.store.head(req.user_id)}

        return AdviseResponse(ledger_id=ev["id"], state=state, signals=signals, stakes=stakes, firmness=firmness,
                              tone_notes=tone_notes, temperament=t.key, facts=facts, verdict=verdict, message=message,
                              hash=ev["hash"], prev_hash=ev["prev_hash"])

    def compare(self, req: AdviseRequest) -> dict:
        """Same human, same moment, every temperament. Proves the truth does not move with the voice."""
        base = self.advise(req, record=False)
        person = self._person(req.user_id)
        out = []
        for key in temperaments.TEMPERAMENTS:
            t = temperaments.get(key)
            firmness = vagal_tone(person, base.state, base.stakes, t.firmness_bias)
            out.append({"temperament": key, "name": t.name, "likability": t.likability, "firmness": firmness,
                        "polarity": base.verdict.polarity.value, "headline": base.verdict.headline,
                        "message": deliver(base.verdict, t, firmness, base.state)})
        return {"verdict": base.verdict.model_dump(), "state": base.state.value, "voices": out,
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
        today = now()[:10]
        pol, firm = adv.get("polarity"), str(adv.get("firmness", ""))

        # which firmness does this human actually act on?
        if req.action in ("followed", "ignored") and firm:
            slot = person.adherence.setdefault(firm, {"followed": 0, "ignored": 0})
            slot[req.action] = slot.get(req.action, 0) + 1

        action = req.action or next((h.get("action") for h in self.store.history(person.user_id)
                                     if h["id"] == advice_ev["id"]), None)
        if action == "ignored" and pol in ("stop", "caution"):
            # the pattern is now evidenced in the genome
            for flag in set(adv.get("flags", [])) & LEARNABLE:
                b = next((x for x in person.biases if x.type == flag), None)
                if not b:
                    b = Bias(type=flag)
                    person.biases.append(b)
                if advice_ev["id"] not in b.evidence:
                    b.evidence.append(advice_ev["id"])
                b.last_seen = today
            if req.value_delta is not None and req.value_delta < 0:
                if person.risk_profile.stated != "aggressive":
                    person.risk_profile.observed = "aggressive"
                person.lessons.append(f"{today}: ignored a {pol.upper()} ({adv.get('headline', '')}) and lost "
                                      f"{fmt_money(abs(req.value_delta), person.currency)}.")
        elif action == "followed" and pol in ("stop", "caution"):
            person.lessons.append(f"{today}: followed a {pol.upper()} ({adv.get('headline', '')}). Capital protected.")
        person.lessons = person.lessons[-12:]
        person.vintage = today
        self.store.put_person(person)
