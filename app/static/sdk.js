/*!
 * Substrate SDK - emotional AI for any platform, no code required.
 *
 * 1. One tag:
 *    <script src="https://YOUR-SUBSTRATE-HOST/sdk.js" data-pk="pk_live_..." data-user="USER_ID"
 *            data-tissue="markets" data-mode="check,widget" data-theme="dark" data-accent="#F43B1E"></script>
 *
 * 2. Gate any button, no JavaScript:
 *    <button data-substrate-check data-substrate-stake="500" data-substrate-price="0.62"
 *            data-substrate-side="YES" data-substrate-market="Fed cuts in December">Place bet</button>
 *    Or read a form:  <button data-substrate-check data-substrate-form="#order">Buy</button>
 *    with inputs named stake, price, side, amount, leverage, instrument, asset, note (or data-substrate-field="...").
 *
 *    Before the click goes through, Substrate shows an honest pause. "Cancel" closes the loop as followed,
 *    "Proceed anyway" as ignored, "Hold me to it" makes a pact. If Substrate is slow or down, the click goes
 *    through (fail-open) unless data-fail="closed".
 *
 * 3. Or call it:  const v = await Substrate.check({stake: 500, price: .62, side: "YES"}, "feeling lucky");
 *                 if (v.proceed) placeBet();
 *    Events: substrate:verdict, substrate:proceed, substrate:cancel, substrate:pact (on window).
 *
 * 4. Web component:  <substrate-check tissue="trading" instrument="XAUUSD" leverage="50" amount="100000" side="long">
 *                    </substrate-check>   renders an inline honest read.
 *
 * Vagal tone changes how truth is delivered. Never whether.
 */
(function () {
  "use strict";
  if (window.Substrate && window.Substrate.__v) return;
  var me = document.currentScript;
  var attr = function (k, d) { return (me && me.getAttribute("data-" + k)) || d; };
  var cfg = {
    base: me ? new URL(me.src).origin : location.origin,
    pk: attr("pk", "pk_demo"),
    user: attr("user", null),
    tissue: attr("tissue", "wealth"),
    mode: attr("mode", "check"),
    theme: attr("theme", "dark"),
    accent: attr("accent", "#F43B1E"),
    temperament: attr("temperament", ""),
    gate: attr("gate", "caution"),            // interrupt on: caution (caution+stop) | stop (stop only) | all
    fail: attr("fail", "open"),
    position: attr("position", "right"),
    timeout: +attr("timeout", "4000"),
    title: attr("title", "Substrate"),
  };
  if (!cfg.user) {
    try { cfg.user = localStorage.getItem("substrate-anon") || ("anon-" + Math.random().toString(36).slice(2, 12)); localStorage.setItem("substrate-anon", cfg.user); }
    catch (e) { cfg.user = "anon-" + Math.random().toString(36).slice(2, 12); }
  }
  var listeners = {};
  function emit(name, detail) {
    try { window.dispatchEvent(new CustomEvent("substrate:" + name, { detail: detail })); } catch (e) {}
    (listeners[name] || []).forEach(function (fn) { try { fn(detail); } catch (e) {} });
  }

  function api(path, body) {
    var ctl = typeof AbortController !== "undefined" ? new AbortController() : null;
    var t = setTimeout(function () { if (ctl) ctl.abort(); }, cfg.timeout);
    return fetch(cfg.base + path, { method: "POST", signal: ctl && ctl.signal,
      headers: { "content-type": "application/json", "x-substrate-pk": cfg.pk }, body: JSON.stringify(body) })
      .then(function (r) { return r.json().then(function (j) { if (!r.ok) throw new Error(j.detail || r.statusText); return j; }); })
      .finally(function () { clearTimeout(t); });
  }

  // ---------------- theme + shadow host
  var DARK = { bg: "#0B0A08", panel: "#12110E", fg: "#EFE9DF", dim: "rgba(239,233,223,.64)", hair: "rgba(239,233,223,.14)", soft: "rgba(239,233,223,.06)" };
  var LIGHT = { bg: "#F7F3EC", panel: "#FFFFFF", fg: "#0B0A08", dim: "rgba(11,10,8,.62)", hair: "rgba(11,10,8,.13)", soft: "rgba(11,10,8,.04)" };
  function palette() { var t = cfg.theme === "auto" ? (matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark") : cfg.theme; return t === "light" ? LIGHT : DARK; }
  var host = document.createElement("div"); host.id = "substrate-sdk";
  var root = host.attachShadow ? host.attachShadow({ mode: "open" }) : host;
  function css() {
    var p = palette();
    return ":host{all:initial}*{box-sizing:border-box;font-family:'Space Grotesk',ui-sans-serif,system-ui,-apple-system,sans-serif}" +
      ".wrap{--bg:" + p.bg + ";--panel:" + p.panel + ";--fg:" + p.fg + ";--dim:" + p.dim + ";--hair:" + p.hair + ";--soft:" + p.soft + ";--acc:" + cfg.accent + ";--ok:#3DDC84;--amb:#F2B33D}" +
      ".veil{position:fixed;inset:0;background:rgba(0,0,0,.45);backdrop-filter:blur(3px);z-index:2147483600;display:flex;align-items:center;justify-content:center;padding:16px;opacity:0;transition:opacity .25s}" +
      ".veil.on{opacity:1}" +
      ".card{width:min(520px,100%);max-height:calc(100vh - 32px);overflow:auto;background:var(--panel);color:var(--fg);border:1px solid var(--hair);border-radius:18px;box-shadow:0 30px 80px rgba(0,0,0,.4);transform:translateY(12px) scale(.98);transition:transform .35s cubic-bezier(.2,1.2,.3,1)}" +
      ".veil.on .card{transform:none}" +
      ".top{display:flex;align-items:center;gap:10px;padding:16px 18px;border-bottom:1px solid var(--hair)}" +
      ".beat{animation:beat 2.4s ease-in-out infinite;display:inline-flex}@keyframes beat{0%,100%{transform:scale(1)}8%{transform:scale(1.14)}16%{transform:scale(.95)}24%{transform:scale(1.07)}}" +
      ".brand{font-weight:800;letter-spacing:3px;font-size:11px}.pill{margin-left:auto;font-size:10.5px;font-weight:700;letter-spacing:2px;padding:5px 10px;border-radius:999px;color:#0B0A08}" +
      ".pill.stop{background:var(--acc)}.pill.caution{background:var(--amb)}.pill.proceed{background:var(--ok)}.pill.safety{background:#7FB2FF}" +
      ".body{padding:16px 18px;font-size:14px;line-height:1.55}.body h3{margin:0 0 8px;font-size:17px;line-height:1.35}" +
      ".body p{margin:0 0 10px;color:var(--fg)}.body ul{margin:0 0 10px;padding-left:18px;color:var(--dim)}.body li{margin:3px 0}" +
      ".body blockquote{margin:8px 0;padding:10px 14px;border-left:3px solid var(--ok);background:var(--soft);font-style:italic;border-radius:0 10px 10px 0}" +
      ".fc{display:flex;flex-wrap:wrap;gap:6px;margin:6px 0 4px}.fc span{font-size:11px;border:1px solid var(--hair);border-radius:999px;padding:3px 9px;color:var(--dim)}.fc b{color:var(--fg);font-weight:600}" +
      ".acts{display:flex;gap:8px;flex-wrap:wrap;padding:14px 18px;border-top:1px solid var(--hair)}" +
      "button{font:600 13px inherit;border-radius:12px;padding:11px 14px;cursor:pointer;border:1px solid var(--hair);background:var(--soft);color:var(--fg)}" +
      "button.pri{background:var(--fg);color:var(--bg);border-color:var(--fg)}button.pact{border-color:#5B86FF;color:#5B86FF}button.ghost{margin-left:auto;color:var(--dim)}" +
      ".foot{padding:0 18px 14px;font-size:10.5px;color:var(--dim);letter-spacing:.4px}" +
      ".thinking{display:flex;gap:6px;padding:28px 18px}.thinking i{width:7px;height:7px;border-radius:50%;background:var(--acc);animation:dot 1s infinite}.thinking i:nth-child(2){animation-delay:.15s}.thinking i:nth-child(3){animation-delay:.3s}@keyframes dot{0%,100%{opacity:.25}50%{opacity:1}}" +
      ".fab{position:fixed;bottom:20px;" + cfg.position + ":20px;width:56px;height:56px;border-radius:50%;background:var(--bg);border:1.5px solid var(--acc);display:flex;align-items:center;justify-content:center;cursor:pointer;z-index:2147483500;box-shadow:0 8px 30px rgba(0,0,0,.3)}" +
      ".chat{position:fixed;bottom:88px;" + cfg.position + ":20px;width:min(380px,calc(100vw - 32px));height:min(540px,calc(100vh - 120px));background:var(--panel);color:var(--fg);border:1px solid var(--hair);border-radius:18px;z-index:2147483500;display:none;flex-direction:column;overflow:hidden;box-shadow:0 20px 60px rgba(0,0,0,.35)}" +
      ".chat.on{display:flex}.log{flex:1;overflow:auto;padding:14px;display:flex;flex-direction:column;gap:10px}" +
      ".m{padding:10px 12px;border-radius:12px;max-width:90%;font-size:13.5px;line-height:1.5}.m.u{align-self:flex-end;background:color-mix(in srgb,#5B86FF 20%,transparent)}.m.s{align-self:flex-start;background:var(--soft);border-left:2px solid var(--acc)}" +
      ".m.s.proceed{border-left-color:var(--ok)}.m.s.caution{border-left-color:var(--amb)}" +
      "form{display:flex;gap:8px;padding:12px;border-top:1px solid var(--hair);margin:0}input{flex:1;background:var(--soft);border:1px solid var(--hair);color:var(--fg);border-radius:10px;padding:10px;font:inherit;font-size:13.5px}" +
      "@media (prefers-reduced-motion: reduce){.beat{animation:none}.card,.veil{transition:none}}";
  }
  var HEART = '<svg width="20" height="20" viewBox="0 0 32 32" aria-hidden="true"><path d="M16 28C6 20 2 15 2 9.5 2 5.4 5.2 2 9.2 2c2.6 0 5 1.4 6.8 3.8C17.8 3.4 20.2 2 22.8 2 26.8 2 30 5.4 30 9.5 30 15 26 20 16 28z" fill="' + cfg.accent + '"/></svg>';
  var wrap;
  function mount() {
    if (host.isConnected) return;
    root.innerHTML = "<style>" + css() + "</style>";
    wrap = document.createElement("div"); wrap.className = "wrap"; root.appendChild(wrap);
    document.body.appendChild(host);
  }

  // ---------------- tiny markdown (bold, italic, lists, quotes)
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function inl(s) { return esc(s).replace(/\*\*(.+?)\*\*/g, "<b>$1</b>").replace(/(^|\s)_(.+?)_(?=\s|$|[.,])/g, "$1<i>$2</i>"); }
  function md(s) {
    return String(s || "").split("\n\n").map(function (b) {
      var ls = b.split("\n");
      if (ls.every(function (l) { return l.indexOf(">") === 0; })) return "<blockquote>" + ls.map(function (l) { return inl(l.replace(/^>\s?/, "")); }).join("<br>") + "</blockquote>";
      var li = ls.filter(function (l) { return l.indexOf("- ") === 0; }), lead = ls.filter(function (l) { return l.indexOf("- ") !== 0; });
      return (lead.length ? "<p>" + inl(lead.join(" ")) + "</p>" : "") + (li.length ? "<ul>" + li.map(function (l) { return "<li>" + inl(l.slice(2)) + "</li>"; }).join("") + "</ul>" : "");
    }).join("");
  }

  // ---------------- the honest pause
  function modal(v, opts) {
    mount();
    return new Promise(function (resolve) {
      var veil = document.createElement("div"); veil.className = "veil"; veil.setAttribute("role", "dialog"); veil.setAttribute("aria-modal", "true");
      var pol = v.safety ? "safety" : v.polarity;
      var fc = (v.forecasts || []).slice(0, 4).map(function (f) { return "<span>" + esc(f.label) + ": <b>" + esc(f.value) + "</b></span>"; }).join("");
      var body = md(v.message.replace(/\n\n_This advice is recorded in your Vagus Ledger._$/, ""));
      veil.innerHTML = '<div class="card"><div class="top"><span class="beat">' + HEART + '</span><span class="brand">' + esc(cfg.title.toUpperCase()) +
        '</span><span class="pill ' + pol + '">' + esc(v.label) + '</span></div><div class="body">' + body + (fc ? '<div class="fc">' + fc + '</div>' : '') + '</div>' +
        '<div class="acts">' + (v.safety ? '<button class="pri" data-a="cancel">I\'ll reach out now</button>' :
          '<button class="pri" data-a="cancel">' + (pol === "proceed" ? "Go ahead" : "Cancel, good call") + '</button>' +
          (v.pact_offer ? '<button class="pact" data-a="pact">Hold me to it: ' + esc(v.pact_offer.text) + '</button>' : '') +
          (pol !== "proceed" ? '<button class="ghost" data-a="proceed">Proceed anyway</button>' : '')) +
        '</div><div class="foot">Honest by design · recorded privately · ' + esc(v.ledger_id) + '</div></div>';
      wrap.appendChild(veil);
      requestAnimationFrame(function () { veil.classList.add("on"); });
      var first = veil.querySelector("button"); if (first) first.focus();
      function done(a) {
        veil.classList.remove("on"); setTimeout(function () { veil.remove(); }, 250);
        document.removeEventListener("keydown", onKey, true);
        resolve(a);
      }
      function onKey(e) { if (e.key === "Escape") { e.stopPropagation(); done("cancel"); } }
      document.addEventListener("keydown", onKey, true);
      veil.addEventListener("click", function (e) {
        var a = e.target.getAttribute && e.target.getAttribute("data-a");
        if (a) done(a); else if (e.target === veil) done("cancel");
      });
    });
  }

  function check(context, note, opts) {
    opts = opts || {};
    var tissue = opts.tissue || cfg.tissue;
    return api("/v1/embed/advise", { user: cfg.user, tissue: tissue, context: context || {}, message: note || "", temperament: cfg.temperament || undefined })
      .then(function (v) {
        emit("verdict", v);
        var gate = opts.gate || cfg.gate;
        var interrupt = v.safety || gate === "all" || (gate === "caution" ? v.polarity !== "proceed" : v.polarity === "stop");
        if (!interrupt) return { proceed: true, verdict: v, action: "auto" };
        return modal(v, opts).then(function (a) {
          var proceed = a === "proceed" || (a === "cancel" && v.polarity === "proceed" && !v.safety);
          if (a === "pact") api("/v1/embed/pact", { user: cfg.user, ledger_id: v.ledger_id, tissue: tissue }).then(function (p) { emit("pact", p); }).catch(function () {});
          if (v.polarity !== "proceed" && !v.safety)
            api("/v1/embed/outcome", { user: cfg.user, ledger_id: v.ledger_id, action: proceed ? "ignored" : "followed" }).catch(function () {});
          emit(proceed ? "proceed" : "cancel", { verdict: v, action: a });
          return { proceed: proceed, verdict: v, action: a };
        });
      })
      .catch(function (err) {
        emit("error", { message: err.message });
        return { proceed: cfg.fail !== "closed", verdict: null, error: err.message };
      });
  }

  // ---------------- no-code gating of any element
  var FIELDS = ["stake", "price", "side", "market", "belief", "legs", "leg_prob", "amount", "asset", "leverage", "instrument",
                "horizon", "stop_pct", "check", "valuation", "arr", "company", "item", "monthly", "borrowed", "note"];
  function readContext(el) {
    var ctx = {}, form = el.getAttribute("data-substrate-form") ? document.querySelector(el.getAttribute("data-substrate-form")) : el.closest("form");
    if (form) FIELDS.forEach(function (f) {
      var inp = form.querySelector('[data-substrate-field="' + f + '"]') || form.querySelector('[name="' + f + '"]');
      if (inp && inp.value !== "") ctx[f] = inp.type === "checkbox" ? inp.checked : inp.value;
    });
    FIELDS.forEach(function (f) { var v = el.getAttribute("data-substrate-" + f.replace("_", "-")); if (v != null) ctx[f] = v; });
    ["price", "belief", "leg_prob"].forEach(function (k) { if (ctx[k] != null && +ctx[k] > 1) ctx[k] = +ctx[k] / 100; });
    var note = ctx.note || ""; delete ctx.note;
    return { ctx: ctx, note: note, tissue: el.getAttribute("data-substrate-tissue") || cfg.tissue };
  }
  document.addEventListener("click", function (e) {
    var el = e.target.closest && e.target.closest("[data-substrate-check]");
    if (!el || el.__substratePass) return;
    e.preventDefault(); e.stopImmediatePropagation();
    var r = readContext(el);
    el.setAttribute("aria-busy", "true");
    check(r.ctx, r.note, { tissue: r.tissue, gate: el.getAttribute("data-substrate-gate") || undefined }).then(function (res) {
      el.removeAttribute("aria-busy");
      if (!res.proceed) return;
      el.__substratePass = true;
      try { if (el.form && el.type === "submit" && el.form.requestSubmit) el.form.requestSubmit(el); else el.click(); }
      finally { setTimeout(function () { el.__substratePass = false; }, 0); }
    });
  }, true);

  // ---------------- chat widget
  function widget() {
    mount();
    var fab = document.createElement("button"); fab.className = "fab"; fab.setAttribute("aria-label", "Open " + cfg.title); fab.innerHTML = '<span class="beat">' + HEART.replace('width="20" height="20"', 'width="26" height="26"') + "</span>";
    var chat = document.createElement("div"); chat.className = "chat"; chat.setAttribute("role", "dialog");
    chat.innerHTML = '<div class="top"><span class="brand">' + esc(cfg.title.toUpperCase()) + '</span><span class="pill proceed" style="margin-left:auto">HONEST</span></div><div class="log"></div><form><input placeholder="Ask something you want to hear yes to..." aria-label="Message"><button class="pri" type="submit">Ask</button></form>';
    wrap.appendChild(fab); wrap.appendChild(chat);
    var log = chat.querySelector(".log"), thread = [];
    fab.onclick = function () { chat.classList.toggle("on"); if (chat.classList.contains("on")) chat.querySelector("input").focus(); };
    chat.querySelector("form").onsubmit = function (e) {
      e.preventDefault(); var inp = chat.querySelector("input"), q = inp.value.trim(); if (!q) return; inp.value = "";
      var u = document.createElement("div"); u.className = "m u"; u.textContent = q; log.appendChild(u);
      var s = document.createElement("div"); s.className = "m s"; s.innerHTML = '<div class="thinking"><i></i><i></i><i></i></div>'; log.appendChild(s); log.scrollTop = log.scrollHeight;
      api("/v1/embed/advise", { user: cfg.user, tissue: cfg.tissue, message: q, thread: thread, temperament: cfg.temperament || undefined }).then(function (v) {
        s.classList.add(v.safety ? "stop" : v.polarity); s.innerHTML = md(v.message); thread.push({ role: "user", content: q }, { role: "substrate", content: v.message });
        log.scrollTop = log.scrollHeight; emit("verdict", v);
      }).catch(function (err) { s.textContent = "Substrate is unavailable right now. " + err.message; });
    };
  }

  // ---------------- web component: <substrate-check ...>
  if (window.customElements && !customElements.get("substrate-check")) {
    customElements.define("substrate-check", class extends HTMLElement {
      connectedCallback() {
        var self = this, sh = this.attachShadow({ mode: "open" }), ctx = {};
        FIELDS.forEach(function (f) { var v = self.getAttribute(f.replace("_", "-")); if (v != null) ctx[f] = v; });
        ["price", "belief", "leg_prob"].forEach(function (k) { if (ctx[k] != null && +ctx[k] > 1) ctx[k] = +ctx[k] / 100; });
        sh.innerHTML = "<style>" + css() + ".inline{border:1px solid var(--hair);border-radius:14px;background:var(--panel);color:var(--fg);overflow:hidden}</style><div class='wrap'><div class='inline'><div class='thinking'><i></i><i></i><i></i></div></div></div>";
        var note = ctx.note || ""; delete ctx.note;
        api("/v1/embed/advise", { user: cfg.user, tissue: this.getAttribute("tissue") || cfg.tissue, context: ctx, message: note }).then(function (v) {
          sh.querySelector(".inline").innerHTML = '<div class="top"><span class="beat">' + HEART + '</span><span class="brand">' + esc(cfg.title.toUpperCase()) + '</span><span class="pill ' + (v.safety ? "safety" : v.polarity) + '">' + esc(v.label) + '</span></div><div class="body"><h3>' + esc(v.headline) + '</h3><ul>' + v.reasons.slice(0, 4).map(function (r) { return "<li>" + inl(r) + "</li>"; }).join("") + '</ul><div class="fc">' + (v.forecasts || []).slice(0, 3).map(function (f) { return "<span>" + esc(f.label) + ": <b>" + esc(f.value) + "</b></span>"; }).join("") + "</div></div>";
          emit("verdict", v);
        }).catch(function () { sh.querySelector(".inline").innerHTML = '<div class="body">Substrate is unavailable.</div>'; });
      }
    });
  }

  function boot() { if (cfg.mode.indexOf("widget") >= 0) widget(); }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot); else boot();

  window.Substrate = {
    __v: "1.0.0",
    config: cfg,
    init: function (o) { for (var k in o) if (o.hasOwnProperty(k)) cfg[k] = o[k]; if (host.isConnected) { root.querySelector("style").textContent = css(); } return this; },
    identify: function (userId) { cfg.user = String(userId); return this; },
    check: check,
    advise: function (message, tissue) { return api("/v1/embed/advise", { user: cfg.user, tissue: tissue || cfg.tissue, message: message }); },
    on: function (name, fn) { (listeners[name] = listeners[name] || []).push(fn); return this; },
  };
})();
