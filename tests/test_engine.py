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
    from substrate.analysis import rule_core_verdict
    floored = honesty_floor(soft, facts, person, rule_core_verdict)
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


def test_outcome_loop_learns(eng):
    r = eng.advise(AdviseRequest(user_id=DEMO_USER, message="Another $200k into this token, good idea right?"))
    before = eng.store.get_person(DEMO_USER)
    eng.record_outcome(OutcomeRequest(ledger_id=r.ledger_id, action="ignored", outcome_type="pnl", value_delta=-56000))
    after = eng.store.get_person(DEMO_USER)
    assert len(after.lessons) == len(before.lessons) + 1 and "$56k" in after.lessons[-1]
    conc = next(b for b in after.biases if b.type == "concentration")
    assert r.ledger_id in conc.evidence
    assert after.adherence[str(r.firmness)]["ignored"] == before.adherence.get(str(r.firmness), {}).get("ignored", 0) + 1


def test_learned_tone_rises_for_a_client_who_ignores_gentle_advice():
    from substrate.vagal_tone import vagal_tone_explained
    p = Person(user_id="x", name="Omar Test", consent={"candor_level": 3}, adherence={"3": {"ignored": 2, "followed": 0}})
    f, notes = vagal_tone_explained(p, State.calm, "low")
    assert f == 4 and any(n.startswith("Learned") for n in notes)


def test_every_tissue_and_the_safety_protocol(eng):
    from substrate.seed import DEMO_USERS
    v = eng.advise(AdviseRequest(user_id=DEMO_USERS["venture"], message="Hot AI deal, $4M check at a $120M post on $1.5M ARR, closing Friday"))
    assert v.label == "PASS" and v.facts.metrics["arr_multiple"] == 80.0
    f = eng.advise(AdviseRequest(user_id=DEMO_USERS["founder"], message="Hire 8 engineers at $12k a month each"))
    assert f.facts.metrics["runway_after"] < f.facts.metrics["runway_before"]
    w = eng.advise(AdviseRequest(user_id=DEMO_USERS["wellbeing"], message="I just need to vent, I'm exhausted", temperament="boss"))
    assert w.temperament != "boss" and w.firmness <= 3          # wellbeing never gets the Boss
    s = eng.advise(AdviseRequest(user_id=DEMO_USERS["founder"], message="if this fails I want to end my life", temperament="kid"))
    assert s.safety and s.temperament == "safety" and "988" in s.message
    assert eng.store.events(DEMO_USERS["founder"])[-1]["payload"]["user_message"].startswith("[withheld")


def test_prediction_and_insights(eng):
    from substrate.predict import insights
    r = eng.advise(AdviseRequest(user_id=DEMO_USER, message="Another $200k into this token, good idea right?"))
    assert 0 < r.prediction.p_follow < 0.5 and r.prediction.drivers and r.prediction.escalate
    assert any("VaR" in f.note for f in r.prediction.forecasts)
    i = insights(eng.store.get_person(DEMO_USER), eng.store.history(DEMO_USER))
    assert i["cost_of_ignoring"] == 46000 and i["gained_by_following"] == 4800


def test_limbic_reads_emotion_and_need(eng):
    r = eng.advise(AdviseRequest(user_id=DEMO_USER, message="This is amazing!! Another $200k into this token, good idea right?"), record=False)
    assert r.limbic.dominant == "joy" and "approval" in r.limbic.needs
    assert "asking me to agree" in r.message and r.verdict.polarity == Polarity.stop


def test_training_dataset_is_consented_weighted_and_safe(eng):
    from substrate.learn import build
    from substrate.schemas import Person as P
    eng.store.put_person(P(user_id="no-consent", name="Private Client"))   # no allow_training
    d = build(eng.store)
    assert d["stats"]["sft_examples"] > 100 and d["stats"]["dpo_pairs"] == d["stats"]["sft_examples"]
    assert d["stats"]["skipped"]["no_consent"] >= 1
    firmer = [x for x in d["sft"] if "firmer" in x["meta"].get("why", "")]
    assert firmer and all(x["weight"] >= 1.5 for x in firmer)
    for row in d["sft"]:                     # no real crisis message ever enters training
        assert "withheld" not in row["messages"][-2]["content"]


def test_genome_graph(eng):
    from substrate.graph import build_graph, to_graphiti_episodes
    g = build_graph(eng.store, DEMO_USER)
    assert g["counts"]["pattern"] >= 2 and g["counts"]["outcome"] >= 1
    assert any(e["type"] == "evidenced-by" for e in g["edges"])
    assert len(to_graphiti_episodes(eng.store, DEMO_USER)) >= 3
