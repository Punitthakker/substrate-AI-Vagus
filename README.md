# Substrate - the Vagus Engine

**The emotional chromosome of artificial intelligence.** An honest-advisor EQ layer that sits beneath
any LLM, remembers who you are, reads the moment, tells you the truth in the voice you choose,
predicts whether you'll act on it, and records what happened.

> Vagal tone changes how truth is delivered. Never whether.

Confidential. Patent pending. Do not distribute.

## Tissues: one engine, four verticals

| Tissue | For | It knows |
|---|---|---|
| **Wealth** | private banks, wealth platforms | concentration, leverage, loss-chasing, 30-day VaR |
| **Venture** | VC investment committees | check vs fund size, ARR multiple, thesis drift, skipped diligence, base rates |
| **Founder** | founder-CEOs, accelerators | burn, runway after each decision, cash-out date, vanity spend |
| **Wellbeing** | coaching, EAP, consumer | venting, impulsive decisions at the peak of a feeling, persistent distress |

Wellbeing is a **coach, not a therapist**: it listens, reflects honestly, slows impulsive decisions,
and recommends professional support when distress persists.

## The Safety Protocol

Any crisis signal, in any tissue, in any voice, under any tenant policy, overrides everything:
no persona, no tone dial, emergency and crisis-line resources, escalation to a human, and the raw
message is withheld from the ledger. Policy cannot disable it. 32 safety cases run in CI.

## Organs

| Organ | File |
|---|---|
| Signals intake + state inference (text only, EU AI Act Art. 5 by design) | `substrate/signals.py` |
| Person model (the genome) | `substrate/schemas.py` |
| Tissues | `substrate/domains/` |
| Honesty Floor: facts set a floor; a model may be harsher, never softer | `substrate/brains.py` |
| Vagal Tone: consent x stakes x state x temperament x **learned adherence**, policy-capped | `substrate/vagal_tone.py` |
| Temperaments: Mentor, Father, Boss, Partner, Comfort, Kid Brother, Surgeon, Grandmother | `substrate/temperaments.py` |
| Delivery layer: verdict verbatim, voice around it | `substrate/delivery.py` |
| Predictive layer: p(follow) with drivers, forecasts, escalation, Candor ROI | `substrate/predict.py` |
| Vagus Ledger: append-only, hash-chained, per human | `substrate/ledger.py` |
| Outcome loop: consequences rewrite the genome | `substrate/engine.py` |
| .sub export: portable, checksummed, bequeathable genome | `substrate/export.py` |
| Eval harness: accuracy, pressure, temperament invariance, safety | `substrate/evals.py` |

## Any brain: 13 adapters + the Model Council

Claude, OpenAI, **NVIDIA NIM**, Gemini, Mistral, Groq, DeepSeek, xAI, Together, OpenRouter, and
self-hosted vLLM, BionicGPT and Ollama. Set a key and it's live (`GET /v1/models`).

`SUBSTRATE_COUNCIL=anthropic,nvidia,gemini` runs several brains in parallel; disagreement resolves
toward the more cautious verdict, then the Honesty Floor applies. Votes are returned per request.

## Enterprise

- **Multi-tenant**: `POST /v1/admin/tenants` (admin key) issues a tenant key. Each tenant sees only its
  own genomes and runs under its own **policy**: concentration limits, check-size limits, runway bands,
  permitted temperaments, max tone, enabled tissues. Policy tightens Substrate; it never disables the
  Honesty Floor or the Safety Protocol.
- **Metrics**: `GET /v1/metrics` - advice volume, floor saves, safety events, avg tone, avg p(follow),
  follow rate, cost of ignoring.
- **Insights**: `GET /v1/insights/{user}` - Candor ROI for one human.
- Rate-limited public demo, sandboxed guest genomes, hashed tenant keys.

## Four ways to integrate

1. **REST API** - docs at `/docs`.
2. **Wrapper** - `@vagus(user_id=..., temperament=...)` around any chatbot; flattering drafts are replaced.
3. **Embed** - `<script src="https://HOST/embed.js" data-user="client-42"></script>`.
4. **Skill** - `integrations/skill/substrate-vagus/` teaches any Claude agent the protocol.

## Run

```bash
pip install -r requirements-dev.txt
pytest -q                                  # 21 tests
python -m substrate.evals                  # 63 evals, must be 100%
uvicorn app.main:app --reload --port 8080  # console at http://localhost:8080
./scripts/run_local.sh                     # fully offline on a Mac with Ollama
docker compose up -d                       # Substrate + Ollama, nothing leaves the machine
```

Deploy: `railway.json` (Railway), `render.yaml` (Render), or the `Dockerfile` anywhere.
