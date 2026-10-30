"""Self-check: proves the outside world is reachable from where Substrate actually runs.

Runs at startup on a background thread and on demand (/v1/admin/selfcheck). Each check reports ok, detail and
latency. Results are logged as one line starting with SELFCHECK so they can be read from the platform's logs.
"""
from __future__ import annotations

import json
import os
import threading
import time

import httpx

LAST: dict = {}


def _timed(fn):
    t0 = time.perf_counter()
    try:
        ok, detail = fn()
    except Exception as e:  # report, never raise
        ok, detail = False, f"{type(e).__name__}: {str(e)[:160]}"
    return {"ok": ok, "detail": detail, "ms": round(1000 * (time.perf_counter() - t0))}


def polymarket():
    from .markets_api import GAMMA, polymarket_price
    r = httpx.get(f"{GAMMA}/markets", params={"active": "true", "closed": "false", "limit": 1}, timeout=8)
    r.raise_for_status()
    rows = r.json()
    if not rows:
        return False, "Gamma API answered with no active markets"
    slug = rows[0].get("slug")
    p = polymarket_price(slug)
    return True, f"{slug}: {p['outcome']} at {p['price']:.3f}"


def ecb_fx():
    from .volatility import analyze, fx_history
    s = fx_history("EURUSD", 120)
    if len(s) < 30:
        from .volatility import LAST_FX_ERROR
        return False, f"only {len(s)} observations; {LAST_FX_ERROR}"
    a = analyze("EURUSD", prices=s, horizon_days=5)
    return True, f"{len(s)} daily EURUSD closes, last {s[-1]:.4f}, {a['method']} vol {a['vol_annual'] * 100:.1f}%"


def mem0():
    if not os.environ.get("MEM0_API_KEY"):
        return False, "not configured (set MEM0_API_KEY to enable)"
    from mem0 import MemoryClient  # type: ignore
    c = MemoryClient(api_key=os.environ["MEM0_API_KEY"])
    c.add([{"role": "user", "content": "Substrate self-check: values honesty."}], user_id="substrate-selfcheck")
    return True, "write accepted"


def brains():
    from .brains import REGISTRY, active_brain
    on = [k for k, b in REGISTRY.items() if b.configured()]
    return True, f"active {active_brain()}; configured: {', '.join(on) or 'none (rule-core)'}"


def brain_roundtrip():
    """A real call to the active brain with a canned decision. Configured is not the same as working."""
    from .brains import active_brain, ping
    if active_brain() == "rule-core":
        return False, "no brain configured: every verdict will come from the rule core"
    r = ping()
    return r["ok"], r["detail"]


def database(store):
    t0 = time.perf_counter()
    store.db.execute("select count(*) from persons").fetchone()
    return True, f"{store.engine}, round trip {round(1000 * (time.perf_counter() - t0), 1)} ms"


def whatsapp():
    need = ["WHATSAPP_VERIFY_TOKEN", "WHATSAPP_APP_SECRET", "WHATSAPP_TOKEN", "WHATSAPP_PHONE_ID"]
    missing = [k for k in need if not os.environ.get(k)]
    return (not missing), ("configured" if not missing else "dry-run; missing " + ", ".join(missing))


def run(store) -> dict:
    global LAST
    res = {"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "checks": {
        "database": _timed(lambda: database(store)), "polymarket": _timed(polymarket), "ecb_fx": _timed(ecb_fx),
        "mem0": _timed(mem0), "brains": _timed(brains), "brain_roundtrip": _timed(brain_roundtrip), "whatsapp": _timed(whatsapp)}}
    res["ok"] = all(v["ok"] for k, v in res["checks"].items() if k in ("database", "polymarket", "ecb_fx", "brain_roundtrip"))
    if not res["checks"]["brain_roundtrip"]["ok"]:
        print("SELFCHECK WARNING: the brain round trip failed; verdicts are coming from the rule core only -> "
              + res["checks"]["brain_roundtrip"]["detail"], flush=True)
    elif os.environ.get("SUBSTRATE_SELFTEST_ON_BOOT", "1") == "1":
        try:   # the tester's questions through the live engine: the deployment proves itself in its own logs
            from .engine import VagusEngine
            from . import selftest
            res["selftest"] = {k: v for k, v in selftest.run(VagusEngine(store)).items() if k != "cases"}
        except Exception as e:  # report, never raise
            print(f"SELFTEST FAILED TO RUN: {type(e).__name__}: {str(e)[:200]}", flush=True)
    LAST = res
    print("SELFCHECK " + json.dumps(res), flush=True)
    return res


def start(store) -> None:
    if os.environ.get("SUBSTRATE_SELFCHECK", "1") == "1":
        threading.Thread(target=run, args=(store,), daemon=True).start()
