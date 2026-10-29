/*!
 * Substrate embed - integration mode 3. One script tag puts the Vagus Engine on any page.
 *
 *   <script src="https://YOUR-SUBSTRATE-HOST/embed.js"
 *           data-user="client-42" data-temperament="mentor" data-key="optional-api-key"></script>
 *
 * Vagal tone changes how truth is delivered. Never whether.
 */
(function () {
  var me = document.currentScript;
  if (!me) return;
  var base = new URL(me.src).origin;
  var user = me.getAttribute("data-user") || "demo-kapoor";
  var temperament = me.getAttribute("data-temperament") || "";
  var key = me.getAttribute("data-key") || "";
  var thread = [];

  var css = "\
.sbx-btn{position:fixed;right:20px;bottom:20px;width:58px;height:58px;border-radius:50%;background:#0B0A08;border:1.5px solid #F43B1E;cursor:pointer;z-index:2147483000;display:flex;align-items:center;justify-content:center;box-shadow:0 8px 30px rgba(0,0,0,.35)}\
.sbx-btn svg{animation:sbxbeat 2.4s ease-in-out infinite}\
@keyframes sbxbeat{0%,100%{transform:scale(1)}8%{transform:scale(1.12)}16%{transform:scale(.96)}24%{transform:scale(1.07)}}\
.sbx-panel{position:fixed;right:20px;bottom:90px;width:min(380px,calc(100vw - 40px));height:min(560px,calc(100vh - 120px));background:#0B0A08;color:#EFE9DF;border:1px solid rgba(239,233,223,.18);border-radius:16px;z-index:2147483000;display:none;flex-direction:column;font:14px/1.5 'Space Grotesk',ui-sans-serif,system-ui,sans-serif;overflow:hidden;box-shadow:0 20px 60px rgba(0,0,0,.45)}\
.sbx-panel.open{display:flex}\
.sbx-head{padding:14px 16px;border-bottom:1px solid rgba(239,233,223,.14);display:flex;justify-content:space-between;align-items:center}\
.sbx-head b{font-weight:700;letter-spacing:3px;font-size:12px}\
.sbx-head span{font-size:10px;letter-spacing:2px;color:#F43B1E}\
.sbx-log{flex:1;overflow:auto;padding:14px 16px;display:flex;flex-direction:column;gap:10px}\
.sbx-m{padding:10px 12px;border-radius:12px;max-width:88%;white-space:pre-wrap;word-wrap:break-word}\
.sbx-u{align-self:flex-end;background:rgba(91,134,255,.18)}\
.sbx-s{align-self:flex-start;background:rgba(239,233,223,.06);border-left:2px solid #F43B1E}\
.sbx-s.proceed{border-left-color:#3DDC84}.sbx-s.caution{border-left-color:#F2B33D}\
.sbx-meta{font-size:10px;letter-spacing:1.5px;color:rgba(239,233,223,.5);margin-top:6px}\
.sbx-form{display:flex;gap:8px;padding:12px;border-top:1px solid rgba(239,233,223,.14)}\
.sbx-form input{flex:1;background:rgba(239,233,223,.06);border:1px solid rgba(239,233,223,.18);color:#EFE9DF;border-radius:10px;padding:10px;font:inherit}\
.sbx-form button{background:#F43B1E;color:#0B0A08;border:0;border-radius:10px;padding:0 14px;font-weight:700;cursor:pointer}";
  var st = document.createElement("style"); st.textContent = css; document.head.appendChild(st);

  var heart = '<svg width="26" height="26" viewBox="0 0 32 32"><path d="M16 28C6 20 2 15 2 9.5 2 5.4 5.2 2 9.2 2c2.6 0 5 1.4 6.8 3.8C17.8 3.4 20.2 2 22.8 2 26.8 2 30 5.4 30 9.5 30 15 26 20 16 28z" fill="#F43B1E"/></svg>';
  var btn = document.createElement("button"); btn.className = "sbx-btn"; btn.setAttribute("aria-label", "Open Substrate advisor"); btn.innerHTML = heart;
  var panel = document.createElement("div"); panel.className = "sbx-panel"; panel.setAttribute("role", "dialog");
  panel.innerHTML = '<div class="sbx-head"><b>SUBSTRATE</b><span>VAGUS ENGINE</span></div><div class="sbx-log" aria-live="polite"></div>' +
    '<form class="sbx-form"><input id="sbx-input" placeholder="Ask about a money decision..." autocomplete="off"><button type="submit">Ask</button></form>';
  document.body.appendChild(btn); document.body.appendChild(panel);
  var log = panel.querySelector(".sbx-log"), form = panel.querySelector("form"), input = panel.querySelector("input");

  btn.onclick = function () { panel.classList.toggle("open"); if (panel.classList.contains("open")) input.focus(); };

  function esc(s) { return s.replace(/[&<>]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]; }); }
  function md(s) { return esc(s).replace(/\*\*(.+?)\*\*/g, "<b>$1</b>").replace(/_(.+?)_/g, "<i>$1</i>"); }
  function add(cls, html) { var d = document.createElement("div"); d.className = "sbx-m " + cls; d.innerHTML = html; log.appendChild(d); log.scrollTop = log.scrollHeight; return d; }

  form.onsubmit = function (e) {
    e.preventDefault();
    var msg = input.value.trim(); if (!msg) return;
    input.value = ""; add("sbx-u", esc(msg));
    var pending = add("sbx-s", "...");
    var headers = { "content-type": "application/json" }; if (key) headers["x-substrate-key"] = key;
    fetch(base + "/v1/advise", { method: "POST", headers: headers,
      body: JSON.stringify({ user_id: user, message: msg, thread: thread, temperament: temperament || null }) })
      .then(function (r) { return r.json(); })
      .then(function (r) {
        if (!r.verdict) { pending.innerHTML = esc(r.detail || "Substrate is unavailable."); return; }
        pending.classList.add(r.verdict.polarity);
        pending.innerHTML = md(r.message) + '<div class="sbx-meta">' + r.state.toUpperCase() + " · TONE " + r.firmness + "/5 · LEDGER " + r.ledger_id + "</div>";
        thread.push({ role: "user", content: msg }, { role: "substrate", content: r.message });
      })
      .catch(function () { pending.innerHTML = "Could not reach Substrate."; });
  };
})();
