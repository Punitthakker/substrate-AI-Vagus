# Substrate SDKs

| SDK | Where | For |
|---|---|---|
| **Embed SDK (no code)** | served at `/sdk.js` (source `app/static/sdk.js`) | any web platform: gate buttons, chat widget, `<substrate-check>` |
| JavaScript client | `sdk/js/substrate.js` | web and Node apps calling the API directly |
| Python client | `sdk/python` (`pip install ./sdk/python`) | servers, notebooks, back offices |
| OpenAI-compatible | `/v1/chat/completions` | any OpenAI SDK, one URL change |
| MCP server | `integrations/mcp/substrate_mcp.py` | Claude Desktop, Claude Code, Cursor |

The no-code builder with a live preview is at `/developers`. Full OpenAPI 3 spec at `/openapi.json`.

## Keys

- **Tenant key** `sk_sub_...`: server-side only. Create via `POST /v1/admin/tenants` (admin).
- **Publishable key** `pk_live_...`: safe in the browser, locked to your origins, can only touch genomes it created.
  Create with the tenant key: `POST /v1/embed/keys {"origins": ["app.mybank.com"], "tissue": "wealth"}`.
- `pk_demo` works on the open demo deployment only.

End-user ids are hashed with your tenant id (`ext-...`); the raw id is never stored.
