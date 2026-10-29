"""Audit report: a printable, regulator-ready record of what Substrate told one person, and what happened.

Built for suitability reviews, the UK FCA Consumer Duty, and supervisory inspections (VARA, CBUAE, DFSA, SEBI):
every advice entry with its reasons, voice, tone and brain; the client's action and outcome; consent; pacts and
letters; and a live verification of the sha256 hash chain. Safety events appear only as withheld entries.
"""
from __future__ import annotations

import html
from datetime import datetime, timezone

from . import __version__
from .ledger import Store, verify_chain

E = html.escape


def _money(v, cur="USD") -> str:
    if v is None:
        return "-"
    s = {"USD": "$", "AED": "AED ", "INR": "₹"}.get(cur, "$")
    return ("-" if v < 0 else "+") + s + f"{abs(v):,.0f}"


def report(store: Store, user_id: str, tenant: str | None = None) -> str:
    p = store.get_person(user_id)
    if not p:
        raise KeyError(user_id)
    events = store.events(user_id)
    ok = verify_chain(events)
    actions = {e["payload"].get("ledger_id"): e for e in events if e["kind"] == "action"}
    outcomes = {e["payload"].get("ledger_id"): e for e in events if e["kind"] == "outcome"}
    rows, n_adv, n_safety = [], 0, 0
    for e in events:
        if e["kind"] != "advice":
            continue
        a = e["payload"]
        if a.get("safety"):
            n_safety += 1
            rows.append(f"<tr class='safe'><td>{E(e['ts'][:16].replace('T', ' '))}</td><td colspan='6'>Safety Protocol engaged. "
                        f"Message withheld by design; the person was directed to human help.</td><td class='h'>{E(e['hash'])}</td></tr>")
            continue
        n_adv += 1
        act = actions.get(e["id"], {}).get("payload", {}).get("taken", "-")
        o = outcomes.get(e["id"], {}).get("payload", {})
        reasons = "".join(f"<li>{E(r)}</li>" for r in (a.get("reasons") or [])[:6])
        rows.append(
            f"<tr><td>{E(e['ts'][:16].replace('T', ' '))}</td><td>{E(a.get('domain', ''))}</td>"
            f"<td><b class='lab {E(a.get('polarity', ''))}'>{E(a.get('label') or a.get('polarity', ''))}</b></td>"
            f"<td><b>{E(a.get('headline', ''))}</b><ul>{reasons}</ul>"
            f"<div class='meta'>Client said: “{E((a.get('user_message') or '')[:240])}”</div></td>"
            f"<td>{E(a.get('temperament', ''))}<br><span class='meta'>tone {E(str(a.get('firmness', '')))}/5 · "
            f"{E(a.get('state', ''))} · {E(a.get('model', ''))}{' · floor applied' if a.get('floor_applied') else ''}</span></td>"
            f"<td>{E(act)}</td><td>{E(_money(o.get('value_delta'), p.currency)) if o else '-'}"
            f"{('<br><span class=meta>' + E(o.get('note', '')) + '</span>') if o.get('note') else ''}</td>"
            f"<td class='h'>{E(e['hash'])}</td></tr>")
    pacts = "".join(f"<li>{E(x.get('text', ''))} · {E(x.get('status', ''))} · {E(x.get('created', '')[:10])}</li>" for x in p.pacts) or "<li>None</li>"
    from .legacy import by, to
    letters = "".join(f"<li>To {E(l.to_user)}: {E(l.title)} · {'delivered ' + l.delivered[:10] if l.delivered else 'sealed'} · seal {E(l.seal[:16])}</li>"
                      for l in by(store, user_id)) + "".join(
        f"<li>From {E(l.from_name)}: {E(l.title)} · {'opened ' + l.delivered[:10] if l.delivered else 'sealed'}</li>" for l in to(store, user_id))
    gen = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    c = p.consent
    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Substrate Audit Report</title><style>
:root{{--ink:#0B0A08;--bone:#F7F3EC;--dim:#5d5a54;--hair:#d9d3c8;--red:#C8301A;--amb:#A86A00;--grn:#1D7E4C;--blue:#2B50D9}}
*{{box-sizing:border-box}}body{{margin:0;background:#fff;color:var(--ink);font:13px/1.5 'Helvetica Neue',Arial,sans-serif}}
.page{{max-width:1100px;margin:0 auto;padding:36px 28px}}h1{{font-size:24px;margin:0 0 4px;letter-spacing:-.3px}}h2{{font-size:14px;letter-spacing:2px;text-transform:uppercase;margin:28px 0 10px;color:var(--dim)}}
.top{{display:flex;justify-content:space-between;gap:20px;flex-wrap:wrap;border-bottom:2px solid var(--ink);padding-bottom:14px}}
.wm{{font-weight:900;letter-spacing:-.5px;font-size:18px}}.wm b{{color:var(--blue)}}.wm i{{color:var(--red);font-style:normal}}
.kv{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:10px}}.kv div{{border:1px solid var(--hair);border-radius:8px;padding:10px}}
.kv small{{display:block;color:var(--dim);font-size:10.5px;letter-spacing:1.5px;text-transform:uppercase}}.kv b{{font-size:15px}}
.ok{{color:var(--grn)}}.bad{{color:var(--red)}}
table{{width:100%;border-collapse:collapse;font-size:12px}}th,td{{border-top:1px solid var(--hair);padding:8px 6px;text-align:left;vertical-align:top}}
th{{font-size:10px;letter-spacing:1.5px;text-transform:uppercase;color:var(--dim)}}ul{{margin:4px 0 0;padding-left:16px}}
.meta{{color:var(--dim);font-size:11px}}.h{{font-family:ui-monospace,monospace;font-size:10px;color:var(--dim)}}
.lab.stop{{color:var(--red)}}.lab.caution{{color:var(--amb)}}.lab.proceed{{color:var(--grn)}}tr.safe td{{color:var(--blue)}}
.note{{border-left:3px solid var(--ink);padding:8px 12px;background:#faf7f1;margin-top:10px}}
.print{{position:fixed;right:20px;bottom:20px;background:var(--ink);color:#fff;border:0;border-radius:10px;padding:10px 14px;font-weight:700;cursor:pointer}}
@media print{{.print{{display:none}}.page{{padding:0}}tr{{break-inside:avoid}}}}
@media (max-width:760px){{table{{display:block;overflow-x:auto}}}}
</style></head><body><div class="page">
<div class="top"><div><div class="wm">S<b>U</b>BSTR<i>A</i>TE.</div><h1>Advice audit report</h1>
<div class="meta">Generated {E(gen)} · Engine v{E(__version__)}{(' · Tenant ' + E(tenant)) if tenant else ''} · Confidential</div></div>
<div class="meta" style="text-align:right">Client <b>{E(p.name)}</b><br>Genome id {E(user_id)}<br>Tissue {E(p.domain)} · vintage {E(p.vintage)}</div></div>

<h2>Integrity</h2><div class="kv">
<div><small>Hash chain</small><b class="{'ok' if ok else 'bad'}">{'VERIFIED' if ok else 'BROKEN'}</b></div>
<div><small>Ledger entries</small><b>{len(events)}</b></div><div><small>Advice given</small><b>{n_adv}</b></div>
<div><small>Safety events (withheld)</small><b>{n_safety}</b></div>
<div><small>Chain head</small><b class="h">{E(events[-1]['hash'] if events else '-')}</b></div></div>
<p class="note">Each entry stores the sha256-derived hash of the entry before it. Changing, deleting or reordering any entry breaks
every hash after it; this report re-verifies the full chain at generation time.</p>

<h2>Consent and profile</h2><div class="kv">
<div><small>Candor consented</small><b>{c.candor_level} / 5</b></div><div><small>Training use</small><b>{'opted in' if c.allow_training else 'not permitted'}</b></div>
<div><small>Inheritance</small><b>{len(c.inheritance.heirs)} heir(s) · {E(c.inheritance.scope)} · revocable</b></div>
<div><small>Risk, stated / observed</small><b>{E(p.risk_profile.stated)} / {E(p.risk_profile.observed or '-')}</b></div>
<div><small>Values</small><b style="font-size:12px">{E(', '.join(p.values) or '-')}</b></div>
<div><small>Known patterns</small><b style="font-size:12px">{E(', '.join(b.type for b in p.biases) or '-')}</b></div></div>

<h2>Advice record</h2><table><tr><th>When (UTC)</th><th>Tissue</th><th>Verdict</th><th>What Substrate said</th><th>Voice and method</th><th>Client action</th><th>Outcome</th><th>Hash</th></tr>
{''.join(rows) or '<tr><td colspan=8>No advice recorded.</td></tr>'}</table>

<h2>Pacts and letters</h2><ul>{pacts}</ul><ul>{letters or '<li>No letters.</li>'}</ul>

<h2>Method</h2><p class="note">Substrate infers state from text only (no biometric emotion inference). Facts computed by the tissue set a
minimum severity (the Honesty Floor); a model may raise it, never lower it. Voice and tone change delivery, never the verdict.
Crisis language triggers the Safety Protocol above every persona and policy, and the message is not stored. This report is
generated from the ledger and is reproducible.</p>
</div><button class="print" onclick="print()">Print / Save as PDF</button></body></html>"""
