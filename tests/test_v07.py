"""v0.7: Legacy Vault, OARS empathy, memory bridge, robust parsing, Trading tissue, volatility, trader psychology."""
import math
import random

from substrate import behavior, legacy, memory_bridge, volatility as V
from substrate.brains import _parse
from substrate.engine import VagusEngine
from substrate.export import export_sub, verify_sub
from substrate.ledger import Store
from substrate.schemas import AdviseRequest
from substrate.seed import seed


def eng():
    e = VagusEngine(Store(":memory:"))
    seed(e.store)
    return e


def test_letter_opens_at_its_moment_once_and_is_sealed():
    e = eng()
    calm = e.advise(AdviseRequest(user_id="demo-maya", message="Should I move $20k from cash into the index fund?"))
    assert calm.letter is None
    r = e.advise(AdviseRequest(user_id="demo-maya", message="Putting $120k into a new AI token before it lists!"))
    assert r.letter and "A letter from your father" in r.message and "I love you more than any return" in r.message
    again = e.advise(AdviseRequest(user_id="demo-maya", message="Putting $120k into a new AI token before it lists!"))
    assert again.letter is None
    assert all(l.intact() for l in legacy.to(e.store, "demo-maya"))
    sealed = [l.public() for l in legacy.to(e.store, "demo-maya") if not l.delivered]
    assert sealed and sealed[0]["body"] is None                      # the heir never sees a sealed letter early


def test_letters_travel_in_the_sub_file():
    e = eng()
    doc = export_sub(e.store, "demo-kapoor")
    assert verify_sub(doc)["valid"] and len(doc["letters"]) == 2
    s2 = Store(":memory:")
    assert legacy.import_from_sub(s2, doc, "demo-maya") == 2


def test_oars_reflects_affirms_asks():
    r = eng().advise(AdviseRequest(user_id="demo-sara", message="I'm going to text my ex right now and tell him everything."),
                     record=False)
    assert "holding this in" in r.message and "took real strength" in r.message and "morning-you" in r.message


def test_memory_bridge_carries_who_not_balances():
    mem = memory_bridge.memories(eng().store.get_person("demo-kapoor"))
    text = " ".join(mem)
    assert "family security" in text and "loss-chasing" in text and "340" not in text


def test_parse_repairs_model_json():
    assert _parse("```json\n{'polarity': 'pass', 'headline': 'Pass', 'reasons': 'too rich',}\n```")["polarity"].value == "stop"
    assert _parse('ok {"verdict": "not yet", "summary": "Wait"}')["polarity"].value == "caution"


def test_garch_sees_a_regime_shift_and_touch_odds_are_sane():
    rnd, p = random.Random(1), [2400.0]
    for i in range(300):
        p.append(p[-1] * math.exp(rnd.gauss(0, 0.004 if i < 150 else 0.012)))
    g = V.garch11(V.returns(p), 5)
    assert g["horizon_vol"] > g["long_run_vol"] and 0.9 < g["persistence"] < 1
    assert V.p_touch(0.1, 0.15, 5) > V.p_touch(3, 0.15, 5)
    assert abs(V.margin_distance(50) - 1.0) < 1e-9
    sc = V.scenarios(0.15)
    assert sc["combinations"] == 18 and sc["sequences"] == 108 and abs(sum(c["p"] for c in sc["most_likely"]) - 0) > 0


def test_trading_never_calls_direction_and_stops_revenge():
    e = eng()
    q = e.advise(AdviseRequest(user_id="demo-farah", message="Will gold go up next week?"), record=False)
    assert q.label == "NO CALL" and "No one can call the direction" in q.message
    r = e.advise(AdviseRequest(user_id="demo-farah",
                               message="Down $8k this week. Doubling up on EUR/USD 100:1 to make it back before NFP."),
                 record=False)
    assert r.label == "DON'T TRADE" and r.facts.metrics["p_stop_out"] > 0.5 and "chasing" in r.facts.flags
    assert r.facts.metrics["method"] in ("GARCH(1,1)", "EWMA (lambda 0.94)", "long-run default")


def test_trader_biases_detected():
    b = behavior.read("Gold fell 5 days in a row, it must bounce. 80% of retail are long. I won't sell at a loss.")
    keys = {x["key"] for x in b["biases"]}
    assert {"gamblers-fallacy", "disposition"} <= keys and b["crowd"]["extreme"] and b["band"] == "high"
    assert "leverage" not in {x["key"] for x in behavior.read("Long EURUSD, no leverage")["biases"]}
