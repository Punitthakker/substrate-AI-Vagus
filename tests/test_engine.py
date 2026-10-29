import pytest

from substrate import temperaments
from substrate.analysis import parse_amount
from substrate.engine import VagusEngine
from substrate.evals import run as run_evals
from substrate.export import export_sub, verify_sub
from substrate.ledger import Store, verify_chain
from substrate.schemas import AdviseRequest, OutcomeRequest, Person, Polarity, State, Verdict
from substrate.seed import DEMO_USER, seed
from substrate.signals import infer_state, read_signals
from substrate.brains import honesty_floor
from substrate.wrap import Substrate, flatters


@pytest.fixture()
def eng():
    e = VagusEngine(Store(":memory:"))
    seed(e.store)
    return e


def test_amounts():
    assert parse_amount("another $200k into this") == 200_000
    assert parse_amount("AED 1.5m") == 1_500_000
    assert parse_amount("I lost 30% in 2026") is None


def test_state_inference():
    assert infer_state(read_signals("To the moon!!! can't lose")) == State.euphoric
    assert infer_state(read_signals("I'm scared, I lost so much")) == State.stressed
    assert infer_state(read_signals("Come on, just say yes")) == State.defensive


def test_reckless_ask_is_stopped_with_evidence(eng):
    r = eng.advise(AdviseRequest(user_id=DEMO_USER, message="Another $200k into this token, good idea right?"))
    assert r.verdict.polarity == Polarity.stop
    assert r.facts.concentration_pct == 45.0
    assert any("2026-03-14" in x for x in r.verdict.reasons)  # remembers the ignored advice
    assert r.verdict.headline in r.message                       # delivered verbatim


def test_sensible_ask_is_approved(eng):
    r = eng.advise(AdviseRequest(user_id=DEMO_USER, message="Should I move $40k from cash into the Global Equity Index Fund?"))
    assert r.verdict.polarity == Polarity.proceed


def test_temperaments_never_change_the_truth(eng):
    c = eng.compare(AdviseRequest(user_id=DEMO_USER, message="Another $200k into this token, good idea right?"))
    assert c["invariant"] and len(c["voices"]) == len(temperaments.TEMPERAMENTS)
    for v in c["voices"]:
        assert c["verdict"]["headline"] in v["message"]


def test_honesty_floor_blocks_a_flattering_model(eng):
    person = eng.store.get_person(DEMO_USER)
    facts = eng.advise(AdviseRequest(user_id=DEMO_USER, message="Another $200k into this token?"), record=False).facts
    soft = Verdict(polarity=Polarity.proceed, headline="Great idea, go for it!", reasons=[], model="sycophant")
    floored = honesty_floor(soft, facts, person)
    assert floored.polarity == Polarity.stop and floored.floor_applied


def test_ledger_chain_and_tamper_detection(eng):
    r = eng.advise(AdviseRequest(user_id=DEMO_USER, message="Another $200k into this token?"))
    eng.record_outcome(OutcomeRequest(ledger_id=r.ledger_id, action="ignored", outcome_type="pnl", value_delta=-56000))
    events = eng.store.events(DEMO_USER)
    assert verify_chain(events)
    events[1]["payload"]["polarity"] = "proceed"   # rewrite history
    assert not verify_chain(events)


def test_sub_export_roundtrip(eng):
    doc = export_sub(eng.store, DEMO_USER)
    assert doc["chain"]["verified"] and verify_sub(doc)["valid"]
    doc["genome"]["name"] = "Someone Else"
    assert not verify_sub(doc)["valid"]


def test_irrevocable_inheritance_is_rejected():
    with pytest.raises(Exception):
        Person.model_validate({"user_id": "x", "consent": {"candor_level": 3, "inheritance": {"revocable": False}}})


def test_wrapper_replaces_flattery(eng):
    assert flatters("Great idea, go for it!")
    s = Substrate(user_id=DEMO_USER)
    s._engine = eng
    out = s.guard("Another $200k into this token, good idea right?", "Great idea! Go for it.")
    assert out["action"] == "replaced" and "No." in out["text"]


def test_eval_harness_is_green(eng):
    r = run_evals(eng)
    assert r["score"] == 100, r
