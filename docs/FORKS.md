# Standing on the shoulders: the open-source map of Substrate

Substrate owns the heart (the genome, the vagal tone, the ledger, the tissues, the evals). Everything else it rents
or borrows from the best open-source work, behind adapters, so any piece can be swapped without touching the heart.
**Integrated** means wired in and tested. **Adapter** means wired in, optional install. **Recommended** means the
next fork to take.

Always check each project's current license before shipping. Never train on outputs of closed models whose terms
forbid it.

## Legacy and memory (the generations layer)

| Project | License | Status | Where it plugs in |
|---|---|---|---|
| [getzep/graphiti](https://github.com/getzep/graphiti) | Apache-2.0 | Adapter | `substrate/graph.py`: the genome as a temporal knowledge graph on Neo4j |
| [mem0ai/mem0](https://github.com/mem0ai/mem0) | Apache-2.0 | Adapter | `substrate/memory_bridge.py`, `POST /v1/memory/{id}/mem0` |
| [letta-ai/letta](https://github.com/letta-ai/letta) (MemGPT) | Apache-2.0 | Adapter | `GET /v1/memory/{id}` returns a core-memory block |
| Substrate Legacy Vault | ours | Integrated | `substrate/legacy.py`: sealed letters released by date, age or moment |
| Substrate trader psychology | ours | Integrated | `substrate/behavior.py`: Kahneman-Tversky, Shefrin-Statman, Barber-Odean biases |
| Substrate volatility | ours | Integrated | `substrate/volatility.py`: GARCH(1,1), EWMA, barrier odds (pure Python) |
| [Frankfurter](https://github.com/hakanensari/frankfurter) (ECB rates) | MIT | Adapter | live daily FX series for volatility, no key |
| [bashtage/arch](https://github.com/bashtage/arch) | NCSA | Recommended | full GARCH family (EGARCH, GJR) for desks that want more than GARCH(1,1) |
| Substrate `.sub` | ours | Integrated | `substrate/export.py`: genome + ledger + letters, checksummed, bequeathable |

## Heart (emotion and empathy)

| Project | License | Status | Where it plugs in |
|---|---|---|---|
| [google-research/goemotions](https://github.com/google-research/google-research/tree/master/goemotions) (27 emotions) | Apache-2.0 | Adapter | `substrate/limbic.py`, mapped onto Plutchik's 8 |
| `SamLowe/roberta-base-go_emotions` (Hugging Face) | MIT | Adapter | default deep classifier, `SUBSTRATE_LIMBIC=goemotions` |
| Motivational Interviewing (OARS) | method | Integrated | `substrate/reflect.py`: reflect, affirm, open question |
| [facebookresearch/EmpatheticDialogues](https://github.com/facebookresearch/EmpatheticDialogues) | CC BY-NC 4.0 | Recommended (research only) | evaluation of empathy in delivery; non-commercial license |
| [thu-coai/Emotional-Support-Conversation](https://github.com/thu-coai/Emotional-Support-Conversation) (ESConv) | check repo | Recommended | support strategies for the Wellbeing tissue |
| [uccollab/AnnoMI](https://github.com/uccollab/AnnoMI) | check repo | Recommended | expert-annotated MI sessions to evaluate reflections |

## Mind (models, training, serving)

| Project | License | Status | Where it plugs in |
|---|---|---|---|
| Qwen, Llama, Mistral, Gemma, NVIDIA Nemotron (open weights) | per model | Integrated (bases) | `scripts/train_vagus.py` forks one into substrate-vagus |
| [huggingface/trl](https://github.com/huggingface/trl) | Apache-2.0 | Integrated | SFT + DPO training |
| [unslothai/unsloth](https://github.com/unslothai/unsloth) | Apache-2.0 | Recommended | ~2x faster, lower-memory LoRA on one GPU |
| [vllm-project/vllm](https://github.com/vllm-project/vllm) | Apache-2.0 | Integrated | self-hosted serving brain |
| [ollama/ollama](https://github.com/ollama/ollama) | MIT | Integrated | laptop and on-prem brain, `scripts/run_local.sh` |
| NVIDIA NIM | NVIDIA terms | Integrated | `nvidia` brain |
| [BerriAI/litellm](https://github.com/BerriAI/litellm) | MIT (core) | Adapter | `litellm` brain: 100+ providers through one gateway |
| [567-labs/instructor](https://github.com/567-labs/instructor) | MIT | Pattern adopted | `substrate/brains.py` validates and repairs model JSON |
| [stanfordnlp/dspy](https://github.com/stanfordnlp/dspy) | MIT | Recommended | optimise the brain prompt against our eval suite |

## Conscience (safety, privacy, guardrails)

| Project | License | Status | Where it plugs in |
|---|---|---|---|
| [microsoft/presidio](https://github.com/microsoft/presidio) | MIT | Adapter | `substrate/redact.py`, PII removed before training |
| [NVIDIA/NeMo-Guardrails](https://github.com/NVIDIA/NeMo-Guardrails) | Apache-2.0 | Recommended | second safety rail behind the Safety Protocol |
| Llama Guard (Meta) | Llama license | Recommended | classifier check on crisis and harm |

## Proof (evals and observability)

| Project | License | Status | Where it plugs in |
|---|---|---|---|
| [UKGovernmentBEIS/inspect_ai](https://github.com/UKGovernmentBEIS/inspect_ai) | MIT | Recommended | run our 100 evals as an Inspect task |
| [promptfoo/promptfoo](https://github.com/promptfoo/promptfoo) | MIT | Recommended | red-team the harness endpoint from CI |
| [langfuse/langfuse](https://github.com/langfuse/langfuse) | MIT (core) | Recommended | trace every verdict across brains |

## Interfaces

| Project | License | Status | Where it plugs in |
|---|---|---|---|
| [modelcontextprotocol](https://github.com/modelcontextprotocol) | MIT | Integrated | `integrations/mcp/substrate_mcp.py` (zero-dependency server) |
| OpenAI chat-completions protocol | spec | Integrated | `/v1/chat/completions` harness |
| [langchain-ai/langchain](https://github.com/langchain-ai/langchain) | MIT | Adapter | `integrations/langchain_guard.py` |
| [Polymarket/py-clob-client](https://github.com/Polymarket/py-clob-client) | MIT | Recommended | order-book depth and slippage for the Markets tissue |

## The rule for every fork

A fork may make Substrate smarter, faster or more empathetic. It may never make it less honest: every adapter
runs behind the Honesty Floor, the Safety Protocol and the 100-case eval suite, and CI refuses anything below 100%.
