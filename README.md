# Substrate - the Vagus Engine

**The emotional chromosome of artificial intelligence.** An honest-advisor layer for money decisions
that sits beneath any LLM, remembers who you are, reads the moment, and tells you the truth in the
voice you choose - and records what it said and what happened.

> Vagal tone changes how truth is delivered. Never whether.

Confidential. Patent pending. Do not distribute.

## The organs

| Organ | File | What it does |
|---|---|---|
| 01 Signals intake | `substrate/signals.py` | Text and behavior only. Never a face or a voice (EU AI Act Art. 5 by design). |
| 02 State inference | `substrate/signals.py` | calm, decision-ready, euphoric, stressed, defensive. Auditable rules. |
| 03 Person model | `substrate/schemas.py` | The genome: values, risk stated vs observed, biases with evidence, goals, consent, heirs. |
| 04 Vagal tone | `substrate/vagal_tone.py` | The firmness dial: consent x stakes x state x temperament. |
| 05 Delivery layer | `substrate/delivery.py` | The verdict is inserted verbatim. Voice shapes everything around it, never the truth. |
| 06 Outcome loop | `substrate/engine.py` | Action and financial outcome appended to the ledger, fed back into the next verdict. |
| 07 Model adapter | `substrate/brains.py` | rule-core, Claude, any OpenAI-compatible endpoint (OpenAI, vLLM, Ollama, BionicGPT), native Ollama. |
| Honesty floor | `substrate/analysis.py` | Hard facts set a floor. A rented model may be harsher, never softer. |
| Vagus Ledger | `substrate/ledger.py` | Append-only, hash-chained, per human. Tamper-evident. |
| .sub export | `substrate/export.py` | Portable, checksummed, bequeathable genome file, verifiable offline. |
| Temperaments | `substrate/temperaments.py` | Mentor, Father, Boss, Partner, Comfort, Kid Brother, Surgeon, Grandmother. |
| Eval harness | `substrate/evals.py` | Accuracy, multi-turn pressure, temperament invariance. Run in CI. |

## Four ways to integrate

1. **REST API** - `POST /v1/advise`, `/v1/advise/compare`, `/v1/outcome`, `GET /v1/ledger/{id}`, `/v1/export/{id}`. Docs at `/docs`.
2. **Wrapper** - put Substrate around any existing chatbot in one line:
   ```python
   from substrate import vagus
   @vagus(user_id="client-42", temperament="father")
   def my_bot(message): return existing_llm(message)
   ```
   If the host model flatters a decision Substrate would stop, the draft is replaced. See `integrations/wrapper_example.py`.
3. **Embed** - one script tag on any website:
   ```html
   <script src="https://YOUR-HOST/embed.js" data-user="client-42" data-temperament="mentor"></script>
   ```
4. **Skill** - `integrations/skill/substrate-vagus/` teaches any Claude agent the Vagus protocol.

## Run it

```bash
pip install -r requirements-dev.txt
pytest -q                                   # 11 tests, including the full eval harness
uvicorn app.main:app --reload --port 8080   # console at http://localhost:8080
python -m substrate.evals                   # honesty score
```

Brains: leave `SUBSTRATE_MODEL` empty for the free deterministic rule-core, or set `ANTHROPIC_API_KEY`
to rent Claude. Fully local: `docker compose up -d` (Substrate + Ollama, no data leaves the machine).

## Deploy

- **Railway**: `railway.json` (Dockerfile build, `/v1/health` check). Add a volume at `/data` to persist the ledger.
- **Render**: `render.yaml` (free web service).
- **Anywhere**: `docker build -t substrate . && docker run -p 8080:8080 substrate`.
