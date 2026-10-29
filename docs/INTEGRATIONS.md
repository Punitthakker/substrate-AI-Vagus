# Integrations: nine ways to add Substrate

**Start here for platforms:** the no-code Embed SDK. One script tag, then `data-substrate-check` on any button.
Live builder and preview at `/developers`; details in [sdk/README.md](../sdk/README.md).


| # | Way in | Where | Best for |
|---|---|---|---|
| 0 | **Embed SDK (no code)** | `<script src=".../sdk.js" data-pk="pk_live_...">` | wealth apps, prediction markets, brokers, sportsbooks |
| 1 | REST API | `POST /v1/advise` | banks and platforms building their own UI |
| 2 | OpenAI-compatible harness | `POST /v1/chat/completions` | any app already on the OpenAI SDK: change one URL |
| 3 | Python decorator | `substrate/wrap.py` (`@vagus`) | wrapping an existing bot function |
| 4 | LangChain guard | `integrations/langchain_guard.py` | chains and agents; works without LangChain too |
| 5 | MCP server | `integrations/mcp/substrate_mcp.py` | Claude Desktop, Claude Code, Cursor, any MCP agent |
| 6 | JS SDK | `integrations/js/substrate.js` | web and Node apps, zero dependencies |
| 7 | Embed widget | `<script src=".../embed.js">` | a floating Substrate heart on any page |
| 8 | Claude skill | `integrations/skill/substrate-vagus/` | Claude agents that should consult Substrate |

Plus stateless services: `POST /v1/volatility/analyze` (FX and gold volatility, stop-out odds, event
combinatorics, trader biases; `live: true` pulls ECB daily rates for FX), and `POST /v1/markets/analyze` (bet math, no personal data) and
`GET /v1/markets/polymarket/{slug}` (live Polymarket price via the public Gamma API).

## 3. Decorator

```python
from substrate.wrap import vagus

@vagus(user_id="demo-kapoor")                  # in-process; add base_url=... for a hosted Substrate
def my_bot(message: str) -> str:
    return my_llm(message)                      # whatever your bot already does

my_bot("Another $200k into MOONX, good idea right?")   # flattery replaced with the honest answer
```

## 4. LangChain guard

```python
from integrations.langchain_guard import SubstrateGuard
guarded = SubstrateGuard(llm, user_id="client-42", base_url=SUBSTRATE)
guarded.invoke("Should I go all in?")
runnable = guarded.as_runnable()                # drop into an LCEL chain
```

## 5. MCP server (zero dependencies)

`claude_desktop_config.json`:

```json
{"mcpServers": {"substrate": {
  "command": "python3",
  "args": ["/path/to/substrate-ai-vagus/integrations/mcp/substrate_mcp.py"],
  "env": {"SUBSTRATE_URL": "https://vagus-engine-production.up.railway.app", "SUBSTRATE_USER": "demo-kapoor"}
}}}
```

Tools: `substrate_advise`, `substrate_guard`, `substrate_bet_math`, `substrate_record_outcome`, `substrate_insights`.
Claude Code: `claude mcp add substrate -- python3 /path/to/integrations/mcp/substrate_mcp.py`.

## 6. JS SDK

```js
import { Substrate } from "./substrate.js";
const s = new Substrate({ baseUrl: SUBSTRATE, userId: "demo-rahman" });
const r = await s.advise("Polymarket YES at 62c, I think 80%. $5k on it.");   // NO BET, sized stake in the reasons
const m = await s.betMath({ legs: [{ price: .7 }, { price: .7 }, { price: .7 }], stake: 100, bankroll: 5000 });
```

## WhatsApp

Set `WHATSAPP_VERIFY_TOKEN`, `WHATSAPP_APP_SECRET`, `WHATSAPP_TOKEN`, `WHATSAPP_PHONE_ID` (and optionally
`WHATSAPP_TISSUE`, `WHATSAPP_GRAPH_VERSION`). Webhook: `https://YOUR-HOST/v1/channels/whatsapp/webhook`.
Every delivery's `X-Hub-Signature-256` is verified. Without a token the channel runs dry; try it in the console
(**WhatsApp** button) or `POST /v1/channels/whatsapp/simulate {"phone": "+9715...", "text": "tissue markets"}`.

## Voice

The console and the embed widget accept speech (browser speech recognition) and can read answers aloud.
Substrate analyses the transcribed words only. It never analyses the sound of a voice: no pitch, tremor or
other acoustic emotion inference.

## Legacy Vault

```bash
curl -X POST $SUBSTRATE/v1/legacy/letter -d '{"from_user":"demo-kapoor","to_user":"demo-maya","relation":"father",
  "title":"Before you put too much into one thing","body":"Maya, if you are reading this...",
  "release_type":"moment","release_value":"concentration"}'
curl $SUBSTRATE/v1/legacy/demo-maya          # sealed letters show title and release only, never the words
```

Release types: `moment` (concentration, chasing, fomo, leverage, runway, impulse, trading-leverage, any-stop),
`age` (needs `birth_year` in the heir's profile), `date` (ISO), `first`. Letters travel in the `.sub` file.

## Memory bridge

`GET /v1/memory/{user}` returns the genome as plain-language memories plus a Letta-style core block.
`POST /v1/memory/{user}/mem0` writes them into Mem0 (`pip install mem0ai`, `MEM0_API_KEY` for the platform).

## Webhooks (enterprise)

```bash
curl -X PUT $SUBSTRATE/v1/tenant/webhook -H 'x-substrate-key: sk_sub_...' \
  -d '{"url":"https://bank.example/substrate","events":["escalation","safety","pact-broken"]}'
# -> {"secret":"whsec_...", ...}   shown once
```

Verify each delivery: `hmac_sha256(secret, raw_body)` must equal the hex after `sha256=` in `x-substrate-signature`.
Safety events never carry the person's words, only that the Safety Protocol engaged and where.

## Pacts

`POST /v1/pact {"user_id": "...", "ledger_id": "..."}` after a hard stop (the advice response carries `pact_offer`).
While a pact is active, every answer in that tissue cites it and even a fair decision waits. `GET /v1/pact/{user}`
lists them; `DELETE /v1/pact/{user}/{id}` releases one, on the record.

## Invite links (test access for people you choose)

```bash
curl -X POST $SUBSTRATE/v1/invites -H 'x-substrate-key: $ADMIN' \
  -d '{"tissue":"markets","label":"NVIDIA preview","max_uses":25,"days":14}'
# -> {"code":"AAuZ9zKS","path":"/?invite=AAuZ9zKS",...}
```

Share `https://<your-host>/?invite=<code>`. Each person names themselves and gets a private, sandboxed
genome in that tissue, never mixed with client data and never used for training. Or use **Enterprise ->
Invite people** in the console. Once `SUBSTRATE_ADMIN_KEY` is set, only the admin or master key can create invites.
