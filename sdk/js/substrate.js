/**
 * Substrate JS SDK - zero dependencies, browser or Node 18+.
 *
 *   import { Substrate } from "./substrate.js";
 *   const s = new Substrate({ baseUrl: "https://vagus-engine-production.up.railway.app", userId: "demo-kapoor" });
 *   const r = await s.advise("Another $200k into MOONX, good idea?");
 *   const g = await s.guard("Should I go all in?", draftFromYourModel);   // replaces flattery on a STOP
 *   const m = await s.betMath({ legs: [{price: .7}, {price: .7}], stake: 100, bankroll: 5000 });
 *
 * Or skip the SDK entirely: any OpenAI client works against the harness.
 *   new OpenAI({ baseURL: BASE + "/v1", apiKey: "unused", defaultHeaders: {"x-substrate-user": "demo-kapoor"} })
 */
export class Substrate {
  constructor({ baseUrl, userId, apiKey, temperament } = {}) {
    this.base = (baseUrl || "").replace(/\/$/, "");
    this.userId = userId; this.apiKey = apiKey; this.temperament = temperament;
  }
  async _req(path, body, method) {
    const r = await fetch(this.base + path, {
      method: method || (body ? "POST" : "GET"),
      headers: { "content-type": "application/json", ...(this.apiKey ? { "x-substrate-key": this.apiKey } : {}) },
      body: body ? JSON.stringify(body) : undefined,
    });
    const j = await r.json();
    if (!r.ok) throw new Error(j.detail || r.statusText);
    return j;
  }
  advise(message, thread = []) {
    return this._req("/v1/advise", { user_id: this.userId, message, thread, ...(this.temperament ? { temperament: this.temperament } : {}) });
  }
  async guard(message, draft) {
    const r = await this._req("/v1/chat/completions", { user: this.userId, substrate_mode: "guard", draft,
      messages: [{ role: "user", content: message }] });
    return { text: r.choices[0].message.content, ...r.substrate };
  }
  chat(messages, opts = {}) { return this._req("/v1/chat/completions", { user: this.userId, messages, ...opts }); }
  betMath(input) { return this._req("/v1/markets/analyze", input); }
  outcome(ledgerId, action, valueDelta) {
    return this._req("/v1/outcome", { ledger_id: ledgerId, action,
      ...(valueDelta != null ? { outcome_type: "pnl", value_delta: valueDelta } : {}) });
  }
  progress() { return this._req(`/v1/progress/${this.userId}`); }
  insights() { return this._req(`/v1/insights/${this.userId}`); }
}
export default Substrate;
