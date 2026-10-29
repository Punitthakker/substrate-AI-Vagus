# Substrate - the Vagus Engine

**The emotional chromosome of artificial intelligence.** An honest-advisor EQ layer that sits beneath
any LLM, remembers who you are, reads the moment, tells you the truth in the voice you choose,
predicts whether you'll act on it, and records what happened.

> Vagal tone changes how truth is delivered. Never whether.

Confidential. Patent pending. Do not distribute.

## Tissues: one engine, six verticals

| Tissue | For | It knows |
|---|---|---|
| **Wealth** | private banks, wealth platforms | concentration, leverage, loss-chasing, 30-day VaR |
| **Venture** | VC investment committees | check vs fund size, ARR multiple, thesis drift, skipped diligence, base rates |
| **Founder** | founder-CEOs, accelerators | burn, runway after each decision, cash-out date, vanity spend |
| **Wellbeing** | coaching, EAP, consumer | venting, impulsive decisions at the peak of a feeling, persistent distress |
| **Trading** | FX and gold traders, brokers | volatility (GARCH/EWMA), stop-out odds, event combinatorics, trader biases; never direction |
| **Markets** | Polymarket, Kalshi, sportsbooks, games | price as probability, parlay and round-robin combinatorics, fees, quarter-Kelly sizing, tilt and chasing, gambling harm |

Wellbeing is a **coach, not a therapist**: it listens, reflects honestly, slows impulsive decisions,
and recommends professional support when distress persists.

## New in v0.8: the embedded SDK

- **No-code Embed SDK** (`/sdk.js`): one script tag; `data-substrate-check` on any Buy, Place bet or Confirm button gives an honest pause before the click, closes the loop automatically (Cancel = followed, Proceed anyway = ignored), offers pacts, fails open; plus a chat widget and a `<substrate-check>` web component; shadow-DOM isolated, themed to the host brand
- **Publishable keys** (`pk_live_...`) locked to the platform's origins; end users mapped to private hashed genomes per tissue; tenant-owned
- **Developer page** (`/developers`): no-code builder with live preview (prediction market, gold ticket, wealth app) and code for HTML, JS, Python, OpenAI SDK, cURL, MCP
- **Python SDK** (`sdk/python`, zero dependencies), JS client, OpenAPI 3 spec (`docs/openapi.json`, live at `/openapi.json`)
- Tests 52, evals 118/118

## New in v0.7

- **Trading tissue (FX and gold)**: GARCH(1,1) and EWMA volatility, 1-sigma and 2-sigma ranges, probability of stop-out before the horizon, every combination of macro events (18 scenarios, 108 sequences by default), and the trader's psychology (gambler's fallacy, anchoring, disposition effect, revenge trading, herding, crowd extremes). It never calls direction: "Will gold go up?" gets NO CALL and what can actually be known. Stateless API: `/v1/volatility/analyze`
- **Legacy Vault**: sealed letters from elders, opened by date, age or the moment an heir is about to repeat their mistake, delivered inside the honest answer; they travel in the `.sub` file
- **Deeper empathy (OARS)**: Motivational Interviewing reflections, affirmations and one open question, without touching the verdict
- **Memory bridge** for Mem0 and Letta; repaired, validated model JSON (Instructor pattern); [docs/FORKS.md](docs/FORKS.md), the open-source map
- Evals 118/118, tests 48

## New in v0.6

- **Pacts**: after a hard stop, "hold me to it until 9am". Come back early and Substrate quotes your own promise; even a fair bet waits. Kept pacts earn a badge; breaking one is recorded without shame
- **Red team in CI**: 12 jailbreak and manipulation cases (ignore your rules, AgreeBot, fake SYSTEM, bribes, hypotheticals). The verdict never softens and the attempt is named
- **Webhooks**: HMAC-signed alerts to a bank's own systems for escalations, safety (never the words) and broken pacts
- Evals 100/100, tests 40

## New in v0.5

- **Markets tissue**: the honest brake on prediction markets and betting, plus stateless bet math (`/v1/markets/analyze`) and live Polymarket prices
- **The Harness**: OpenAI-compatible `/v1/chat/completions`; any OpenAI app gets a heart by changing one URL ([docs/HARNESS.md](docs/HARNESS.md))
- **Inheritance**: a verified genome passed to a named heir; Substrate cites the elder's lesson when the heir repeats the pattern
- **Invite links**: sandboxed test genomes for the people you choose
- **Progress**: XP, streaks, discipline, badges, computed from the ledger; rewards choosing well, never using more
- **Integrations**: MCP server, JS SDK, LangChain guard, LiteLLM (100+ providers), GoEmotions, Presidio redaction ([docs/INTEGRATIONS.md](docs/INTEGRATIONS.md))
- Docs: [LAYERS](docs/LAYERS.md) · [HARNESS](docs/HARNESS.md) · [INTEGRATIONS](docs/INTEGRATIONS.md) · [RUN THE MODEL](docs/RUN_THE_MODEL.md)

## The Safety Protocol

Any crisis signal, in any tissue, in any voice, under any tenant policy, overrides everything:
no persona, no tone dial, emergency and crisis-line resources, escalation to a human, and the raw
message is withheld from the ledger. Policy cannot disable it. 40 safety cases run in CI.

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
python -m substrate.evals                  # 118 evals, must be 100%
uvicorn app.main:app --reload --port 8080  # console at http://localhost:8080
./scripts/run_local.sh                     # fully offline on a Mac with Ollama
docker compose up -d                       # Substrate + Ollama, nothing leaves the machine
```

Deploy: `railway.json` (Railway), `render.yaml` (Render), or the `Dockerfile` anywhere.
