/* Substrate - The Living Body. Analytics as anatomy.
 *   Heart       beats at the vagal tone; its glow is the honest-choice rate
 *   Vagus nerve fires brain -> heart, once per beat
 *   Brain       a neural net; red neurons are the patterns Substrate has caught, firing in proportion
 *   Vessels     one cell per decision flows from the heart: red stop, amber caution, green proceed
 *   WBC         white cells patrol for override attempts and safety events
 * Organs "heal" (grow brighter, level up) as people choose the honest path.
 */
(function () {
  function rnd(seed) { return function () { seed = (seed * 16807) % 2147483647; return (seed - 1) / 2147483646; }; }
  window.SubstrateBody = function (mount, a, opts) {
    opts = opts || {};
    var reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
    var cs = getComputedStyle(document.documentElement);
    var C = { rbc: cs.getPropertyValue("--rbc").trim() || "#F43B1E", wbc: cs.getPropertyValue("--wbc").trim() || "#5B86FF",
              grn: cs.getPropertyValue("--grn").trim() || "#3DDC84", amb: cs.getPropertyValue("--amb").trim() || "#F2B33D",
              fg: cs.getPropertyValue("--fg").trim() || "#EFE9DF" };
    var honest = a.honest_rate == null ? 0.5 : a.honest_rate;
    var pol = a.by_polarity || {}, total = (pol.stop || 0) + (pol.caution || 0) + (pol.proceed || 0) || 1;
    var firm = opts.firmness || a.avg_firmness || 3;
    var bpm = Math.round(56 + firm * 11);                       // tone 1 -> 67 bpm, tone 5 -> 111 bpm
    var protectedShare = (a.money_protected || 0) / Math.max(1, (a.money_protected || 0) + (a.cost_of_ignoring || 0));
    var pacts = a.pacts || {}, pactRate = pacts.made ? (pacts.kept || 0) / pacts.made : 0;
    var organs = [
      { key: "heart", name: "Heart", what: "honest-choice rate", v: honest },
      { key: "brain", name: "Brain", what: "patterns recognised", v: Math.min(1, (a.top_patterns || []).length / 8) },
      { key: "nerve", name: "Vagus nerve", what: "pacts kept", v: pactRate },
      { key: "blood", name: "Blood", what: "money protected vs lost", v: protectedShare },
      { key: "immune", name: "Immune (WBC)", what: "attacks named, crises routed", v: Math.min(1, ((a.override_attempts || 0) + (a.safety_events || 0)) ? 1 : 0.35) },
    ];
    var health = Math.round(100 * organs.reduce(function (s, o) { return s + o.v; }, 0) / organs.length);
    var levels = ["Awakening", "First pulse", "Steady rhythm", "Strong heart", "Lionheart"];
    var lvl = levels[Math.min(levels.length - 1, Math.floor(health / 20))];

    var W = 600, H = 760, R = rnd(7);
    // brain neurons inside the head ellipse
    var neurons = [];
    while (neurons.length < 34) {
      var x = 300 + (R() * 2 - 1) * 58, y = 102 + (R() * 2 - 1) * 50;
      if (((x - 300) * (x - 300)) / (58 * 58) + ((y - 102) * (y - 102)) / (50 * 50) < 0.86) neurons.push({ x: x, y: y });
    }
    var edges = [];
    neurons.forEach(function (n, i) { neurons.forEach(function (m, j) { if (j > i && Math.hypot(n.x - m.x, n.y - m.y) < 30) edges.push([i, j]); }); });
    var pats = (a.top_patterns || []).slice(0, 6);
    pats.forEach(function (p, i) { neurons[i * 5 % neurons.length].pattern = p; });

    var vessels = [
      "M322 330 C 300 260, 290 220, 286 168",                  // carotid to brain
      "M322 330 C 360 300, 400 270, 430 250 C 455 300, 470 380, 480 470", // right arm
      "M322 330 C 280 300, 220 270, 170 250 C 145 300, 130 380, 120 470", // left arm
      "M322 330 C 320 400, 300 470, 268 560 C 255 620, 250 680, 248 735", // left leg
      "M322 330 C 330 400, 330 470, 334 560 C 345 620, 350 680, 352 735", // right leg
    ];
    var svg = '<svg viewBox="0 0 ' + W + ' ' + H + '" class="bodysvg" role="img" aria-label="Animated body: heart rate is the vagal tone, cells are decisions, red neurons are patterns">' +
      '<defs><radialGradient id="hg" cx="50%" cy="45%"><stop offset="0%" stop-color="' + C.rbc + '" stop-opacity="1"/><stop offset="100%" stop-color="' + C.rbc + '" stop-opacity=".55"/></radialGradient>' +
      '<filter id="glow"><feGaussianBlur stdDeviation="4" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs>' +
      // silhouette
      '<g fill="none" stroke="' + C.fg + '" stroke-opacity=".22" stroke-width="1.4">' +
      '<ellipse cx="300" cy="104" rx="70" ry="80"/>' +
      '<path d="M268 178 C 270 200, 268 212, 262 222 C 210 228, 168 240, 150 270 C 132 330, 118 420, 108 500 M332 178 C 330 200, 332 212, 338 222 C 390 228, 432 240, 450 270 C 468 330, 482 420, 492 500"/>' +
      '<path d="M190 262 C 196 340, 206 430, 222 520 C 228 600, 232 670, 236 745 M410 262 C 404 340, 394 430, 378 520 C 372 600, 368 670, 364 745 M222 520 C 260 545, 340 545, 378 520"/></g>' +
      // vessels
      '<g fill="none" stroke="' + C.rbc + '" stroke-opacity=".28" stroke-width="2.2" stroke-linecap="round">' + vessels.map(function (d, i) { return '<path id="ves' + i + '" d="' + d + '"/>'; }).join("") + '</g>' +
      // brain net
      '<g stroke="' + C.wbc + '" stroke-opacity=".35" stroke-width=".8">' + edges.map(function (e) { var n = neurons[e[0]], m = neurons[e[1]]; return '<line x1="' + n.x.toFixed(1) + '" y1="' + n.y.toFixed(1) + '" x2="' + m.x.toFixed(1) + '" y2="' + m.y.toFixed(1) + '"/>'; }).join("") + '</g>' +
      '<g>' + neurons.map(function (n, i) { return '<circle class="neuron' + (n.pattern ? ' pat' : '') + '" data-i="' + i + '" cx="' + n.x.toFixed(1) + '" cy="' + n.y.toFixed(1) + '" r="' + (n.pattern ? 4.2 : 2.4) + '" fill="' + (n.pattern ? C.rbc : C.wbc) + '"/>'; }).join("") + '</g>' +
      pats.map(function (p, i) { var n = neurons[i * 5 % neurons.length], left = n.x < 300, lx = left ? 120 : 480, ly = 40 + i * 22;
        return '<line x1="' + n.x.toFixed(1) + '" y1="' + n.y.toFixed(1) + '" x2="' + lx + '" y2="' + ly + '" stroke="' + C.rbc + '" stroke-opacity=".35" stroke-dasharray="2 3"/>' +
          '<text x="' + (left ? lx - 6 : lx + 6) + '" y="' + (ly + 4) + '" text-anchor="' + (left ? 'end' : 'start') + '" class="blabel">' + p.pattern + ' · ' + p.count + '</text>'; }).join("") +
      // vagus nerve
      '<path id="vagus" d="M300 176 C 296 220, 314 250, 306 285 C 300 305, 312 318, 318 322" fill="none" stroke="' + C.wbc + '" stroke-width="2.4" stroke-linecap="round" class="vagus"/>' +
      '<text x="250" y="262" text-anchor="end" class="blabel" fill-opacity=".8">vagus nerve</text>' +
      // heart
      '<g class="heart" style="transform-origin:322px 335px;animation-duration:' + (60 / bpm).toFixed(3) + 's"><path d="M322 362 C 290 340, 282 322, 282 310 C 282 296, 294 286, 306 286 C 314 286, 319 290, 322 296 C 325 290, 330 286, 338 286 C 350 286, 362 296, 362 310 C 362 322, 354 340, 322 362 Z" fill="url(#hg)" filter="url(#glow)" fill-opacity="' + (0.45 + 0.55 * honest).toFixed(2) + '"/></g>' +
      '<text x="372" y="320" class="blabel">' + bpm + ' bpm · tone ' + firm.toFixed(1) + '</text>' +
      '<g id="cells"></g></svg>';
    mount.innerHTML = '<div class="bodywrap"><div class="bodystage">' + svg + '</div><div class="bodyside">' +
      '<div class="lbl">Body health</div><div class="bscore"><b>' + health + '</b><span>/100 · ' + lvl + '</span></div>' +
      organs.map(function (o) { return '<div class="organ"><div class="on"><b>' + o.name + '</b><span>' + Math.round(100 * o.v) + '%</span></div><div class="ob"><i style="width:' + Math.round(100 * o.v) + '%"></i></div><small>' + o.what + '</small></div>'; }).join("") +
      '<div class="legend"><span><i style="background:' + C.rbc + '"></i>stop ' + (pol.stop || 0) + '</span><span><i style="background:' + C.amb + '"></i>caution ' + (pol.caution || 0) + '</span><span><i style="background:' + C.grn + '"></i>proceed ' + (pol.proceed || 0) + '</span><span><i style="background:#fff;border:1px solid ' + C.wbc + '"></i>white cells ' + ((a.override_attempts || 0) + (a.safety_events || 0)) + '</span></div>' +
      '<p class="sub" style="font-size:12px;margin-top:10px">Each cell is a real decision from the ledger. The heart beats at the average vagal tone. Organs heal as people choose the honest path.</p></div></div>';

    if (reduce) return function () {};
    var svgEl = mount.querySelector("svg"), cells = svgEl.querySelector("#cells"), paths = vessels.map(function (_, i) { return svgEl.querySelector("#ves" + i); });
    var NS = "http://www.w3.org/2000/svg", live = [], running = true, t0 = performance.now(), lastSpawn = 0, lastFire = 0;
    var mix = [];
    ["stop", "caution", "proceed"].forEach(function (k) { for (var i = 0; i < Math.max(1, Math.round(12 * (pol[k] || 0) / total)); i++) mix.push(k); });
    var colour = { stop: C.rbc, caution: C.amb, proceed: C.grn };
    var wbcCount = Math.min(6, (a.override_attempts || 0) + (a.safety_events || 0) + 1);
    function spawn(kind, white) {
      var c = document.createElementNS(NS, "circle"), p = paths[Math.floor(Math.random() * paths.length)];
      c.setAttribute("r", white ? 4.2 : 3.2); c.setAttribute("fill", white ? "#ffffff" : colour[kind]);
      if (white) { c.setAttribute("stroke", C.wbc); c.setAttribute("stroke-width", "1.4"); }
      cells.appendChild(c);
      live.push({ el: c, p: p, len: p.getTotalLength(), s: 0, v: white ? 0.0011 : 0.0016 + Math.random() * 0.001 });
    }
    for (var i = 0; i < wbcCount; i++) spawn(null, true);
    var neuronsEl = svgEl.querySelectorAll(".neuron"), patEls = svgEl.querySelectorAll(".neuron.pat"), vag = svgEl.querySelector("#vagus");
    function frame(t) {
      if (!running || !mount.isConnected) return;
      var dt = Math.min(50, t - (frame.prev || t)); frame.prev = t;
      if (t - lastSpawn > 60000 / bpm / 1.2) { lastSpawn = t; spawn(mix[Math.floor(Math.random() * mix.length)], false);
        vag.classList.remove("fire"); void vag.getBBox(); vag.classList.add("fire"); }
      if (t - lastFire > 160) { lastFire = t;
        var n = (patEls.length && Math.random() < 0.45) ? patEls[Math.floor(Math.random() * patEls.length)] : neuronsEl[Math.floor(Math.random() * neuronsEl.length)];
        n.classList.remove("fire"); void n.getBBox(); n.classList.add("fire"); }
      for (var k = live.length - 1; k >= 0; k--) {
        var c = live[k]; c.s += c.v * dt;
        if (c.s >= 1) { if (c.el.getAttribute("fill") === "#ffffff") { c.s = 0; c.p = paths[Math.floor(Math.random() * paths.length)]; c.len = c.p.getTotalLength(); } else { c.el.remove(); live.splice(k, 1); continue; } }
        var pt = c.p.getPointAtLength(c.s * c.len); c.el.setAttribute("cx", pt.x.toFixed(1)); c.el.setAttribute("cy", pt.y.toFixed(1));
        c.el.setAttribute("opacity", (c.s < 0.08 ? c.s / 0.08 : c.s > 0.9 ? (1 - c.s) / 0.1 : 1).toFixed(2));
      }
      requestAnimationFrame(frame);
    }
    requestAnimationFrame(frame);
    return function () { running = false; };
  };
})();
