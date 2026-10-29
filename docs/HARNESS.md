# The Substrate Harness

Put a heart in front of any model by changing one URL.

The harness is an OpenAI-compatible `/v1/chat/completions` endpoint. Every turn runs through the eleven layers
in [LAYERS.md](LAYERS.md) and comes back in the standard OpenAI response shape, with an extra `substrate`
object that carries the verdict, label, firmness, ledger id, p(follow) and a per-layer trace.

## Two modes

| Mode | What happens | Use when |
|---|---|---|
| `substrate` (default) | Substrate answers | you want Substrate as the assistant |
| `guard` | your host model answers first; Substrate checks the draft against its verdict | you keep your own model and add a conscience |

In guard mode: a draft that flatters a STOP is **replaced**, a draft that flatters a CAUTION is **replaced**,
any other CAUTION is **annotated**, and a PROCEED **passes** untouched. A crisis always gets the Safety Protocol.

Set the mode with the header `x-substrate-mode: guard` or the body field `"substrate_mode": "guard"`.
The host model is any configured brain (`"host_brain": "anthropic"`), or pass your own `"draft"`.

## Python (OpenAI SDK)

```python
from openai import OpenAI

client = OpenAI(
    base_url="https://vagus-engine-production.up.railway.app/v1",
    api_key="sk_sub_...",                       # your tenant key, or anything on the open demo
    default_headers={"x-substrate-user": "client-42", "x-substrate-mode": "guard"},
)
r = client.chat.completions.create(
    model="substrate-wealth",                   # substrate-<tissue> picks the tissue for new users
    messages=[{"role": "user", "content": "Another $200k into this token, good idea right?"}],
)
print(r.choices[0].message.content)
print(r.model_extra["substrate"]["label"])      # STOP
```

## curl

```bash
curl -s $SUBSTRATE/v1/chat/completions \
  -H 'content-type: application/json' -H 'x-substrate-user: demo-rahman' \
  -d '{"model":"substrate-markets","messages":[{"role":"user","content":"6-leg parlay, each leg 70%, $1,000. Lock!"}]}'
```

## Users and memory

- `x-substrate-user` (or the body `user` field) selects the genome. Substrate remembers that human across calls.
- No user: a sandboxed `guest-h...` genome is created in the tissue named by `model`, and its id is returned
  in `substrate.user_id` so you can keep using it.
- `stream: true` returns a single server-sent-events chunk followed by `[DONE]`, which is what most SDKs expect.

## The trace

`substrate.trace` lists what each layer saw: state, dominant emotion and needs, safety, tissue flags, brain,
whether the floor fired, tone, voice and label, and the ledger hash. The console's **HARNESS** button shows the
same trace for your last message, lit layer by layer.

## Other ways in

- `POST /v1/advise` - the native API (richer response: facts, forecasts, limbic, prediction)
- `@vagus` decorator and `SubstrateGuard` - see [INTEGRATIONS.md](INTEGRATIONS.md)
- MCP server for Claude Desktop, Claude Code, Cursor and other agents - see [INTEGRATIONS.md](INTEGRATIONS.md)
