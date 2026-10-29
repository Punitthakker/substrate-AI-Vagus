# Run, fiddle with and train the model

Everything here runs on a laptop. Nothing needs an API key unless you want a rented brain.

## 1. Run Substrate locally (2 minutes)

```bash
git clone https://github.com/Punitthakker/substrate-AI-Vagus && cd substrate-AI-Vagus
python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
uvicorn app.main:app --reload          # console at http://localhost:8000
```

Fully offline with a local brain (Apple Silicon picks the model size from your RAM):

```bash
./scripts/run_local.sh                 # installs Ollama, pulls a model, starts Substrate on it
```

## 2. Prove it

```bash
python -m substrate.evals              # 88 cases across accuracy, pressure, voices, limbic, safety
pytest -q                              # unit and API tests
```

## 3. Fiddle with the methods

| Try | Change | Then |
|---|---|---|
| A different brain | `SUBSTRATE_MODEL=anthropic` plus `ANTHROPIC_API_KEY`, or `nvidia` plus `NVIDIA_API_KEY` | ask the same question; the floor keeps the verdict honest |
| A Council of brains | `SUBSTRATE_COUNCIL=anthropic,nvidia,gemini` | the most cautious verdict wins |
| Any provider at all | `pip install litellm`, `SUBSTRATE_MODEL=litellm`, `LITELLM_MODEL=bedrock/...` | 100+ providers via one gateway |
| A deeper emotion model | `pip install transformers torch`, `SUBSTRATE_LIMBIC=goemotions` | GoEmotions (27 labels) blended with the lexicon |
| Stricter redaction | `pip install presidio-analyzer presidio-anonymizer`, `SUBSTRATE_REDACT=presidio` | NER-based PII removal before training |
| A temporal genome graph | `pip install graphiti-core`, set `NEO4J_URI/USER/PASSWORD` | `GET /v1/graph/{id}/graphiti`, then `substrate.graph.push_to_graphiti` |
| Your own thresholds | edit `substrate/policy.py` or `PUT /v1/tenant/policy` | evals tell you if you broke honesty |
| A new tissue | copy `substrate/domains/founder.py` | add cases to `substrate/evals.py` |
| The voices | edit `substrate/temperaments.py` | the temperament suite proves the verdict never moved |
| The bet math | `POST /v1/markets/analyze` with prices, legs, round robins | compare to your own spreadsheet |

## 4. Train substrate-vagus (our own model)

```bash
python -m substrate.learn training/data           # consented, redacted SFT + DPO from the ledger
python scripts/train_vagus.py --base Qwen/Qwen2.5-7B-Instruct --data training/data
ollama create substrate-vagus -f training/Modelfile
SUBSTRATE_MODEL=ollama OLLAMA_MODEL=substrate-vagus uvicorn app.main:app
```

- **Data:** only genomes with `consent.allow_training`; every prompt and answer passes the PII redactor;
  safety events are never trained on (synthetic crisis examples teach the override instead).
- **Weighting:** ignored advice that cost money is upweighted and re-rendered one tone firmer.
- **Pairs:** the honest answer is chosen over a sycophantic one on every STOP and CAUTION, and over a
  fear-mongering one on every PROCEED, so the model learns that honesty is calibration, not harshness.
- **Bases:** open-weight models with commercial licenses (Qwen, Llama, Mistral, Gemma, NVIDIA Nemotron).
  Never train on closed-model outputs.
- **Serving:** Ollama on a laptop, vLLM or NVIDIA NIM in a bank's own cloud.
- **The metric that matters:** how often the Honesty Floor still has to fire. It should fall every round.
