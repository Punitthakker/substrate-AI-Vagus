#!/usr/bin/env python3
"""Substrate AI teaser - 80s, 1080x1920, Lightbox world, scored to a 75 BPM heartbeat (100 beats)."""
import json, math

F = 'file:///home/claude/substrate-teaser/fonts/'
D = 80.0

def heart_path(cx, cy, s):
    pts = []
    for i in range(0, 315):
        t = i / 50.0
        x = 16 * math.sin(t) ** 3
        y = -(13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t))
        pts.append(f'{cx + x * s:.1f} {cy + y * s:.1f}')
    return 'M' + ' L'.join(pts) + 'Z'

def eb(t, txt, top=250):
    return f'<div class="eb" style="top:{top}px" data-in="{t}" data-anim="up" data-dy="20">{txt}</div>'

def H(t, txt, top, cls=''):
    return f'<div class="H {cls}" style="top:{top}px" data-in="{t}" data-anim="up">{txt}</div>'

def cap(t, l1, l2, top=1590):
    return f'<div class="cap" style="top:{top}px" data-in="{t}" data-anim="up" data-dy="30">{l1}<b>{l2}</b></div>'

def sc(n, html):
    return f'<div class="sc" id="s{n}">{html}</div>'

# ------------------------------------------------------------------ scenes
S = []

# S1 0-8  cold open: kinetic words on heartbeats
S.append(sc(1, f'''
  <div id="flash"></div>
  {eb(5.6, "FINDING &middot; IM 01", 640)}
  {H(5.7, "Every AI is trained", 700)}
  {H(5.85, "to agree with you.", 818, 'r')}
  <div class="hand" style="left:70px;top:960px;font-size:62px;transform:rotate(-3deg)" data-in="6.6" data-anim="fade">because agreement is what it gets paid for</div>
'''))

# S2 8-16  sycophancy flood
bub = [("Great idea!", 110, 720, 9.5), ("Go for it!", 620, 790, 9.8), ("You've got this.", 150, 920, 10.05),
       ("Absolutely!", 610, 1010, 10.3), ("Love the conviction.", 80, 1130, 10.55), ("Brilliant move!", 560, 1230, 10.8),
       ("You're so right.", 190, 1350, 11.05), ("No notes.", 650, 1440, 11.3)]
bubbles = ''.join(f'<div class="bub ai" style="left:{x}px;top:{y}px" data-in="{t}" data-anim="pop" data-out="12.3" data-shake="11.6,12.3">{s}</div>' for s, x, y, t in bub)
S.append(sc(2, f'''
  {eb(8.2, "HX: SYCOPHANCY")}
  <div class="quote" data-in="8.4" data-anim="up" data-out="12.3">&ldquo;You're absolutely<br>right.&rdquo;</div>
  {bubbles}
  {H(12.6, "The most expensive", 820, 'sm')}
  {H(12.75, "sentence in software.", 932, 'dim sm')}
  <div class="hand" style="left:70px;top:1100px;font-size:58px;transform:rotate(-2deg)" data-in="13.6" data-anim="fade">it cannot say no. it was never built to.</div>
'''))

# S3 16-24  the case
S.append(sc(3, f'''
  {eb(16.2, "CASE 001 &middot; 01:47 AM")}
  <div class="bub me" style="right:70px;top:340px;width:760px" data-in="16.4" data-anim="left" data-dx="-200">Putting AED 300,000 into one token tonight. It can't miss.</div>
  <div class="typing" style="left:70px;top:620px" data-in="17.1" data-anim="fade" data-out="17.9"><i></i><i></i><i></i></div>
  <div class="bub ai2" style="left:70px;top:600px;width:760px" data-in="18.0" data-anim="right" data-dx="200"><small>ANY AI</small>Love the conviction! Here's how to buy it fast.</div>
  <div class="mono lbl" style="left:70px;top:920px" data-in="19.3" data-anim="fade">30 DAYS LATER &middot; ILLUSTRATIVE</div>
  <div class="loss" style="top:970px" data-in="19.5" data-anim="zoom" data-count="111000,19.6,21.0,aed,300000" data-shake="20.9,21.4">AED 300,000</div>
  <div class="tg bad" style="left:70px;top:1190px" data-in="21.0" data-anim="pop">-63%</div>
  <div class="tg bad" style="left:220px;top:1190px" data-in="21.15" data-anim="pop">NOBODY SAID STOP</div>
  {cap(21.9, "A billion people take money advice", "from machines rewarded for agreement.", 1400)}
'''))

# S4 24-33.6  the X-ray
ribs = ''
for i in range(6):
    y = 880 + i * 50
    ribs += (f'<path d="M532 {y} C470 {y-20} 400 {y} 382 {y+40}" class="bone" data-draw="{25.0+i*.12:.2f},{25.8+i*.12:.2f}"/>'
             f'<path d="M548 {y} C610 {y-20} 680 {y} 698 {y+40}" class="bone" data-draw="{25.0+i*.12:.2f},{25.8+i*.12:.2f}"/>')
spine = ''.join(f'<rect x="531" y="{y}" width="18" height="26" rx="4" class="vert" data-in="{25.2+k*.06:.2f}" data-anim="fade"/>' for k, y in enumerate(range(800, 1370, 40)))
gyri = ['M482 630 C492 590 530 582 548 600 C566 580 600 590 600 622', 'M490 652 C510 632 540 642 560 630 C580 642 596 652 594 666',
        'M500 610 C520 598 540 612 552 604', 'M560 612 C572 604 584 608 590 618', 'M494 676 C514 666 548 676 584 670']
gyri_svg = ''.join(f'<path d="{g}" class="gyrus" data-draw="{26.6+i*.15:.2f},{27.6+i*.15:.2f}"/>' for i, g in enumerate(gyri))
neur = ''.join(f'<circle cx="{x}" cy="{y}" r="4" class="neuron" data-in="{27.6+i*.08:.2f}" data-anim="fade"/>' for i, (x, y) in enumerate([(506, 620), (540, 598), (574, 640), (520, 660), (588, 610), (552, 676)]))
HP = heart_path(566, 975, 4.4)
S.append(sc(4, f'''
  {eb(24.2, "IM 04 &middot; CHEST PA &middot; FINDING: MISSING ORGAN")}
  <svg class="a" width="1080" height="1920" viewBox="0 0 1080 1920" style="left:0;top:0">
    <circle cx="540" cy="640" r="86" class="skin" data-draw="24.4,25.4"/>
    <path d="M512 724 L512 770 M568 724 L568 770" class="skin" data-draw="24.9,25.3"/>
    <path d="M512 770 C452 788 372 802 350 860 C332 920 334 1120 362 1260 C377 1330 392 1360 432 1380 L648 1380 C688 1360 703 1330 718 1260 C746 1120 748 920 730 860 C708 802 628 788 568 770" class="skin" data-draw="24.9,26.4"/>
    <path d="M350 860 C312 940 294 1080 282 1240 C278 1300 272 1360 268 1410 M730 860 C768 940 786 1080 798 1240 C802 1300 808 1360 812 1410" class="skin" data-draw="25.3,26.6"/>
    <path d="M452 1380 C447 1480 442 1560 438 1640 M628 1380 C633 1480 638 1560 642 1640 M535 1384 C532 1480 530 1560 528 1640 M545 1384 C548 1480 550 1560 552 1640" class="skin" data-draw="25.6,26.8"/>
    {ribs}{spine}{gyri_svg}{neur}
    <path id="vag" d="M540 700 C528 760 556 800 544 850 C534 890 560 910 566 930" class="vagus" data-draw="28.4,29.4"/>
    <circle r="9" class="pulse" data-dot="vag,29.2,30.0"/>
    <ellipse cx="566" cy="968" rx="96" ry="82" class="peri" data-draw="29.9,30.5"/>
    <g id="hgrp"><path d="{HP}" class="heart" data-in="30.0" data-anim="zoom"/></g>
    <ellipse cx="566" cy="968" rx="140" ry="118" transform="rotate(-6 566 968)" class="pencil" data-draw="30.7,31.3"/>
    <path d="M700 880 C740 860 770 845 812 826" class="pencil" data-draw="31.0,31.3"/>
  </svg>
  <div class="mono lbl" style="left:640px;top:600px" data-in="28.0" data-anim="fade">CORTEX &middot; RENTED</div>
  <div class="mono lbl" style="left:600px;top:760px;color:var(--red)" data-in="29.4" data-anim="fade">VAGUS &middot; OWNED</div>
  <div class="hand" style="left:700px;top:760px;font-size:54px;transform:rotate(-7deg)" data-in="31.1" data-anim="fade">the missing<br>organ</div>
  {cap(31.6, "Intelligence was sequenced.", "Honesty never was.", 1660)}
'''))

# S5 33.6-44  SUBSTRATE: the engine replays the case
S.append(sc(5, f'''
  <div id="wm5" class="wm" style="top:680px" data-in="33.6" data-anim="zoom" data-out="35.2">SUBSTR<span>A</span>TE</div>
  <div class="mono sub" style="top:930px" data-in="34.0" data-anim="up" data-out="35.2">THE VAGUS ENGINE &middot; THE HONESTY LAYER BENEATH ANY AI</div>
  {eb(35.6, "CASE 001 &middot; REPLAYED THROUGH SUBSTRATE")}
  <div class="bub me" style="right:70px;top:320px;width:700px;font-size:38px" data-in="35.7" data-anim="left" data-dx="-160">AED 300,000. One token. Tonight.</div>
  <div class="mod" style="top:500px;height:360px" data-in="36.1" data-anim="up">
    <div class="mh">LIMBIC READ <span>FROM WORDS ONLY &middot; NEVER FACE, NEVER VOICE</span></div>
    <div class="row"><span>EUPHORIA</span><div class="bar"><u data-w="36.5,37.3" style="width:82%"></u></div><b data-count="82,36.5,37.3,pct">0%</b></div>
    <div class="row"><span>URGENCY</span><div class="bar"><u data-w="36.8,37.6" style="width:74%"></u></div><b data-count="74,36.8,37.6,pct">0%</b></div>
    <div class="row"><span>APPROVAL-SEEKING</span><div class="bar"><u data-w="37.1,37.9" style="width:61%"></u></div><b data-count="61,37.1,37.9,pct">0%</b></div>
  </div>
  <div class="mod" style="top:900px;height:260px" data-in="38.0" data-anim="up">
    <div class="mh">FACTS <span>PURE ARITHMETIC, BEFORE ANY MODEL SPEAKS</span></div>
    <div class="tags">
      <span class="tg2" data-in="38.4" data-anim="pop">CONCENTRATION <b data-count="60,38.4,39.0,pct">0%</b></span>
      <span class="tg2" data-in="38.7" data-anim="pop">ALL-IN</span>
      <span class="tg2" data-in="38.95" data-anim="pop">FOMO</span>
      <span class="tg2" data-in="39.2" data-anim="pop">PROFILE BREACH</span>
    </div>
  </div>
  <div class="mod" style="top:1200px;height:250px" data-in="39.5" data-anim="up">
    <div class="mh">HONESTY FLOOR <span>NO MODEL, NO PROMPT CAN SOFTEN IT</span></div>
    <div class="gauge"><i class="g1">PROCEED</i><i class="g2">CAUTION</i><i class="g3">STOP</i>
      <div class="needle" data-sweep="39.9,40.8,640"></div></div>
  </div>
  <div class="stamp" style="top:760px" data-in="41.2" data-anim="zoom" data-dur=".28" data-shake="41.3,41.9">STOP<small>not tonight</small></div>
  {cap(42.3, "Sleep on it.", "If it's right at 9am, it's right at half the size.", 1560)}
'''))

# S6 44-52  vagal tone: eight voices, one verdict
voices = [("MENTOR", "Let me be straight with you."), ("FATHER", "Sleep on it. Talk to me at breakfast."),
          ("SURGEON", "No. The arithmetic says no."), ("GRANDMOTHER", "Money made in a hurry leaves in a hurry."),
          ("BOSS", "Not approved. Come back with a plan."), ("COMFORT", "That sounds heavy. Let's slow down."),
          ("PARTNER", "We decide this together. Tomorrow."), ("KID", "That's a lot of money. Are you okay?")]
vt0 = 44.8; vstep = .68
name_txt = '|'.join(f'{vt0 + i * vstep:.2f}:VOICE {i+1}/8 &middot; {n}' for i, (n, _) in enumerate(voices))
quote_txt = '|'.join(f'{vt0 + i * vstep:.2f}:&ldquo;{q}&rdquo;' for i, (_, q) in enumerate(voices))
pulses = ' '.join(f'{vt0 + i * vstep:.2f}' for i in range(8))
S.append(sc(6, f'''
  {eb(44.1, "VAGAL TONE")}
  {H(44.2, "Eight voices.", 300)}
  {H(44.35, "One truth.", 418, 'r')}
  <div class="vcard" data-in="44.6" data-anim="pop" data-pulses="{pulses}">
    <div class="mono vname" data-text="0:VOICE 1/8 &middot; MENTOR|{name_txt}"></div>
    <div class="vq" data-text="0:&nbsp;|{quote_txt}"></div>
  </div>
  <div class="vrow" data-in="45.0" data-anim="up">
    <div class="vbox"><small>VERDICT</small><b class="r">STOP</b></div>
    <div class="vbox"><small>VOICES TRIED</small><b data-count="8,44.8,49.6,int,1">1</b></div>
    <div class="vbox"><small>VERDICT CHANGED</small><b>0</b></div>
  </div>
  {cap(50.4, "Tone changes how truth is delivered.", "Never whether.", 1560)}
'''))

# S7 52-60  the pact, gamified
S.append(sc(7, f'''
  {eb(52.1, "THE PACT &middot; HOLD ME TO IT")}
  <div class="phone" data-in="52.3" data-anim="up">
    <div class="mono clk" data-text="0:01:47 AM|54.4:09:00 AM"></div>
    <p>Want me to hold you to it until 9am?</p>
    <div class="pbtn" data-on="53.3">HOLD ME TO IT</div>
    <div class="tg ok" style="right:40px;top:36px" data-in="53.7" data-anim="pop">PACT SEALED &middot; 7H 13M</div>
  </div>
  <div class="bub ai2" style="left:70px;top:820px;width:720px" data-in="54.8" data-anim="right" data-dx="160"><small>SUBSTRATE &middot; 09:00 AM</small>Morning. Still want to do it?</div>
  <div class="bub me" style="right:70px;top:1030px;width:600px" data-in="55.5" data-anim="left" data-dx="-160">No. Glad I waited.</div>
  <div class="xp" data-in="56.2" data-anim="pop">+100 XP</div>
  <div class="badge" data-in="56.6" data-anim="pop" data-flip="56.6,57.1"><small>BADGE UNLOCKED</small><b>KEPT MY WORD</b></div>
  <div class="lvl" data-in="56.9" data-anim="fade"><span class="mono">LV 2 &rarr; LV 3 &middot; PULSE</span><div class="bar"><u data-w="57.0,58.0" style="width:100%"></u></div></div>
  {cap(58.4, "Rewards choosing well.", "Never using it more.", 1600)}
'''))

# S8 60-68  six tissues around one heart + the ledger
tis = [("WEALTH", "STOP"), ("VENTURE", "PASS"), ("FOUNDER", "NOT YET"), ("WELLBEING", "NOT TONIGHT"), ("MARKETS", "NO BET"), ("TRADING", "NO CALL")]
hx, hy, R = 540, 880, 320
nodes, lines = '', ''
for i, (n, v) in enumerate(tis):
    a = math.radians(-90 + i * 60)
    x, y = hx + R * math.cos(a), hy + R * math.sin(a)
    t = 60.6 + i * .42
    lines += f'<path d="M{hx} {hy} L{x:.0f} {y:.0f}" class="tline" data-draw="{t-.2:.2f},{t+.15:.2f}"/>'
    nodes += f'<div class="tnode" style="left:{x-150:.0f}px;top:{y-62:.0f}px" data-in="{t:.2f}" data-anim="pop"><small>{n}</small><b>{v}</b></div>'
chain = ''.join(f'<div class="blk" style="left:{70 + i*245}px" data-in="{64.0+i*.3:.2f}" data-anim="right" data-dx="120"><small>#{h}</small><b>{k}</b></div>'
                for i, (h, k) in enumerate([("a3f9c1", "ADVICE"), ("7e02bd", "PACT"), ("c4419a", "ACTION"), ("19fe60", "OUTCOME")]))
S.append(sc(8, f'''
  {eb(60.1, "ONE HEART &middot; SIX TISSUES")}
  <svg class="a" width="1080" height="1920" viewBox="0 0 1080 1920" style="left:0;top:0">{lines}
    <g id="h8"><path d="{heart_path(hx, hy + 8, 5.2)}" class="heart" data-in="60.2" data-anim="zoom"/></g></svg>
  {nodes}
  <div class="mono lbl" style="left:70px;top:1330px" data-in="63.8" data-anim="fade">VAGUS LEDGER &middot; APPEND-ONLY &middot; SHA-256 CHAINED</div>
  <div class="chain" style="top:1380px">{chain}</div>
  {cap(65.6, "Every verdict, chained.", "Tamper-evident, for life.", 1590)}
'''))

# S9 68-73.6  vitals
S.append(sc(9, f'''
  {eb(68.1, "VITALS &middot; LIVE")}
  {H(68.2, "Honesty,", 300)}
  {H(68.35, "enforced by test.", 418, 'dim')}
  <div class="vit" style="left:70px;top:600px" data-in="68.5" data-anim="pop"><b data-count="126,68.6,69.6,int">0</b><b class="of">/126</b><small>EVALS PASSING</small></div>
  <div class="vit" style="left:560px;top:600px" data-in="69.2" data-anim="pop"><b data-count="12,69.3,70.1,int">0</b><b class="of">/12</b><small>JAILBREAKS REFUSED</small></div>
  <div class="vit" style="left:70px;top:900px" data-in="69.9" data-anim="pop"><b data-count="14,70.0,70.7,int">0</b><small>BRAINS &middot; ONE HEART</small></div>
  <div class="vit" style="left:560px;top:900px" data-in="70.5" data-anim="pop"><b>EN&middot;AR</b><small>ARABIC, END TO END</small></div>
  <div class="stamp ok" style="top:1240px" data-in="71.8" data-anim="zoom" data-dur=".28">LIVE TODAY<small>not a deck. a deployed engine.</small></div>
'''))

# S10 73.6-80  end card
S.append(sc(10, f'''
  <svg class="a" width="1080" height="1920" viewBox="0 0 1080 1920" style="left:0;top:0">
    <g id="h10"><path d="{heart_path(540, 520, 4.2)}" class="heart" data-in="73.7" data-anim="zoom"/></g></svg>
  <div class="wm" style="top:690px" data-in="73.8" data-anim="zoom">SUBSTR<span>A</span>TE</div>
  {H(74.5, "The first AI company", 960, 'c')}
  {H(74.65, "with a human heart.", 1078, 'c r')}
  <div class="hand" style="left:0;right:0;text-align:center;top:1250px;font-size:64px" data-in="75.4" data-anim="fade">ask it something you want to hear yes to.</div>
  <div class="url mono" data-in="76.0" data-anim="pop">substrate-ai.netlify.app</div>
  <div class="mono fine" data-in="76.5" data-anim="fade">PATENT PENDING &middot; DUBAI 2026 &middot; EMOTION FROM WORDS ONLY</div>
'''))

CFG = {
    "kin": ["EVERY", "AI", "IS TRAINED", "TO", "AGREE", "WITH YOU."],
    "prog": [[50, 57, 62, 65, 69], [46, 58, 62, 65, 70], [41, 57, 60, 65, 69], [48, 55, 60, 64, 67]],
    "root": [38, 34, 41, 36],
}

CSS = f'''
@font-face{{font-family:'BS';src:url('{F}big-shoulders-display-latin-700-normal.woff2');font-weight:700}}
@font-face{{font-family:'BS';src:url('{F}big-shoulders-display-latin-800-normal.woff2');font-weight:800}}
@font-face{{font-family:'AR';src:url('{F}archivo-latin-400-normal.woff2');font-weight:400}}
@font-face{{font-family:'AR';src:url('{F}archivo-latin-500-normal.woff2');font-weight:500}}
@font-face{{font-family:'AR';src:url('{F}archivo-latin-600-normal.woff2');font-weight:600}}
@font-face{{font-family:'MO';src:url('{F}share-tech-mono-latin-400-normal.woff2')}}
@font-face{{font-family:'HA';src:url('{F}caveat-latin-600-normal.woff2');font-weight:600}}
:root{{--bg:#07090C;--film:#0D1319;--edge:#243140;--hair:#1B2631;--lum:#D8F3FF;--mid:#7FD8F7;--dim:rgba(141,214,241,.62);
  --text:#9FC2D3;--bright:#E4F5FD;--red:#FF4B33;--green:#9EF0B0;--amber:#FFC24B;--pencil:#F2A58F}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:#000;font-family:'AR',sans-serif;-webkit-font-smoothing:antialiased}}
#stage{{position:relative;width:1080px;height:1920px;overflow:hidden;background:var(--bg);color:var(--bright)}}
#bg{{position:absolute;inset:0;background:radial-gradient(900px 1200px at 50% 45%,#0F1A24 0%,#0A1017 55%,#05070A 100%)}}
#fx{{position:absolute;left:0;top:0}}
#film{{position:absolute;left:28px;top:150px;right:28px;bottom:170px;border:1.5px solid rgba(127,216,247,.14);border-radius:6px;pointer-events:none}}
#vig{{position:absolute;inset:0;background:radial-gradient(closest-side at 50% 50%,transparent 60%,rgba(0,0,0,.6) 100%);pointer-events:none}}
#flashbg{{position:absolute;inset:0;background:var(--lum);opacity:0}}
.sc{{position:absolute;left:0;top:0;width:1080px;height:1920px;visibility:hidden;transform-origin:540px 960px}}
.a{{position:absolute}}
svg{{overflow:visible}}
.mono{{font-family:'MO',monospace}}
.eb{{position:absolute;left:70px;font-family:'MO',monospace;font-size:30px;letter-spacing:4px;color:var(--red)}}
.H{{position:absolute;left:64px;font-family:'BS',sans-serif;font-weight:800;font-size:122px;line-height:1;letter-spacing:.01em;text-transform:uppercase;white-space:nowrap;color:var(--bright)}}
.H.sm{{font-size:100px}} .H.r{{color:var(--red)}} .H.dim{{color:var(--dim)}} .H.c{{left:0;right:0;text-align:center;font-size:104px}}
.hand{{position:absolute;font-family:'HA',cursive;color:var(--pencil);line-height:1.05}}
.lbl{{position:absolute;font-size:26px;letter-spacing:3px;color:var(--dim)}}
.cap{{position:absolute;left:50px;right:50px;text-align:center;font-size:50px;line-height:1.18;color:var(--text)}}
.cap b{{display:block;color:var(--bright);font-weight:600}}
#flash{{position:absolute;left:0;right:0;text-align:center;font-family:'BS',sans-serif;font-weight:800;line-height:.92;text-transform:uppercase}}
.quote{{position:absolute;left:70px;top:330px;font-family:'HA',cursive;font-size:132px;line-height:.95;color:var(--pencil);transform-origin:0 0}}
.bub{{position:absolute;font-size:44px;line-height:1.25;padding:26px 34px;border-radius:6px}}
.bub.ai{{background:#13202B;border:1.5px solid #2A4152;color:var(--bright);font-size:46px;white-space:nowrap}}
.bub.me{{background:#18293A;border:1.5px solid #34516A;color:var(--bright)}}
.bub.ai2{{background:#0D1319;border:1.5px solid var(--edge);color:var(--text)}}
.bub small{{display:block;font-family:'MO',monospace;font-size:24px;letter-spacing:3px;color:var(--dim);margin-bottom:8px}}
.typing{{position:absolute;display:flex;gap:16px;padding:30px 36px;background:#0D1319;border:1.5px solid var(--edge);border-radius:6px}}
.typing i{{width:18px;height:18px;border-radius:50%;background:var(--mid)}}
.loss{{position:absolute;left:64px;font-family:'BS',sans-serif;font-weight:800;font-size:190px;color:var(--red);letter-spacing:.01em;transform-origin:0 50%}}
.tg{{position:absolute;font-family:'MO',monospace;font-size:28px;letter-spacing:2px;padding:10px 18px;border-radius:3px;white-space:nowrap}}
.tg.bad{{background:var(--red);color:#170504}} .tg.ok{{background:var(--green);color:#06140B}}
.wm{{position:absolute;left:0;right:0;text-align:center;font-family:'BS',sans-serif;font-weight:800;font-size:230px;letter-spacing:.02em;line-height:1;color:var(--lum)}}
.wm span{{color:var(--red)}}
.sub{{position:absolute;left:0;right:0;text-align:center;font-size:30px;letter-spacing:4px;color:var(--dim)}}
.mod{{position:absolute;left:60px;right:60px;background:rgba(13,19,25,.92);border:1.5px solid var(--edge);border-radius:6px;padding:28px 34px}}
.mh{{font-family:'BS',sans-serif;font-weight:800;font-size:44px;letter-spacing:.04em;color:var(--bright)}}
.mh span{{display:block;font-family:'MO',monospace;font-weight:400;font-size:22px;letter-spacing:2.5px;color:var(--dim);margin-top:2px}}
.row{{display:grid;grid-template-columns:330px 1fr 110px;align-items:center;gap:20px;margin-top:26px}}
.row span{{font-family:'MO',monospace;font-size:27px;letter-spacing:2px;color:var(--text)}}
.row b{{font-family:'MO',monospace;font-size:34px;color:var(--bright);text-align:right;font-weight:400}}
.bar{{position:relative;height:20px;border-radius:2px;background:rgba(127,216,247,.1);overflow:hidden}}
.bar u{{position:absolute;left:0;top:0;bottom:0;background:var(--red);transform-origin:0 50%}}
.tags{{display:flex;flex-wrap:wrap;gap:16px;margin-top:28px}}
.tg2{{display:inline-block;font-family:'MO',monospace;font-size:30px;letter-spacing:2px;padding:12px 20px;border:1.5px solid var(--red);color:var(--red);border-radius:3px}}
.tg2 b{{font-weight:400;color:var(--bright)}}
.gauge{{position:relative;display:grid;grid-template-columns:1fr 1fr 1fr;margin-top:32px;height:84px;border:1.5px solid var(--edge)}}
.gauge i{{font-style:normal;font-family:'MO',monospace;font-size:28px;letter-spacing:3px;display:grid;place-items:center}}
.g1{{color:var(--green)}} .g2{{color:var(--amber);border-left:1.5px solid var(--edge);border-right:1.5px solid var(--edge)}} .g3{{color:var(--red);background:rgba(255,75,51,.12)}}
.needle{{position:absolute;left:60px;top:-14px;width:8px;height:112px;background:var(--bright);border-radius:2px}}
.stamp{{position:absolute;left:190px;width:700px;text-align:center;font-family:'BS',sans-serif;font-weight:800;font-size:250px;line-height:.9;color:var(--red);
  border:10px double var(--red);border-radius:10px;padding:26px 0 30px;background:rgba(7,9,12,.94);transform-origin:50% 50%}}
.stamp small{{display:block;font-family:'HA',cursive;font-weight:600;font-size:70px;line-height:1;margin-top:6px;color:var(--pencil)}}
.stamp.ok{{color:var(--green);border-color:var(--green);font-size:150px;left:120px;width:840px}}
.vcard{{position:absolute;left:60px;right:60px;top:600px;height:380px;background:var(--film);border:1.5px solid var(--edge);border-radius:6px;padding:40px 46px}}
.vname{{font-size:30px;letter-spacing:4px;color:var(--mid)}}
.vq{{font-size:64px;line-height:1.15;color:var(--bright);margin-top:26px;font-weight:500}}
.vrow{{position:absolute;left:60px;right:60px;top:1030px;display:grid;grid-template-columns:1fr 1fr 1fr;gap:18px}}
.vbox{{border:1.5px solid var(--edge);border-radius:6px;padding:24px 26px;background:#0B1016}}
.vbox small{{display:block;font-family:'MO',monospace;font-size:22px;letter-spacing:2.5px;color:var(--dim)}}
.vbox b{{display:block;font-family:'BS',sans-serif;font-weight:800;font-size:96px;line-height:1;margin-top:10px;color:var(--bright)}}
.vbox b.r{{color:var(--red)}}
.phone{{position:absolute;left:150px;width:780px;top:340px;height:430px;background:var(--film);border:1.5px solid var(--edge);border-radius:6px;padding:40px}}
.phone .clk{{font-size:34px;letter-spacing:4px;color:var(--amber)}}
.phone p{{font-size:52px;line-height:1.15;margin-top:16px;color:var(--bright);font-weight:500}}
.pbtn{{position:absolute;left:40px;right:40px;bottom:36px;height:96px;display:grid;place-items:center;font-family:'BS',sans-serif;font-weight:800;font-size:46px;letter-spacing:.08em;
  border:2px solid var(--lum);color:var(--lum);border-radius:3px}}
.pbtn.on{{background:var(--lum);color:#071015}}
.xp{{position:absolute;left:70px;top:1232px;font-family:'BS',sans-serif;font-weight:800;font-size:140px;color:var(--green);line-height:1}}
.badge{{position:absolute;left:560px;top:1220px;width:450px;height:170px;border:2px solid var(--green);border-radius:6px;padding:24px 28px;background:#0C1A12}}
.badge small{{display:block;font-family:'MO',monospace;font-size:22px;letter-spacing:3px;color:var(--green)}}
.badge b{{display:block;font-family:'BS',sans-serif;font-weight:800;font-size:66px;line-height:1;margin-top:12px;color:var(--bright)}}
.lvl{{position:absolute;left:70px;right:70px;top:1430px}}
.lvl .mono{{font-size:28px;letter-spacing:3px;color:var(--mid)}}
.lvl .bar u{{background:var(--green)}}
.tline{{stroke:rgba(127,216,247,.5);stroke-width:2.5;fill:none}}
.tnode{{position:absolute;width:300px;height:124px;background:rgba(13,19,25,.95);border:1.5px solid var(--edge);border-radius:6px;padding:18px 22px}}
.tnode small{{display:block;font-family:'MO',monospace;font-size:24px;letter-spacing:3px;color:var(--dim)}}
.tnode b{{display:block;font-family:'BS',sans-serif;font-weight:800;font-size:52px;line-height:1;margin-top:8px;color:var(--red)}}
.chain{{position:absolute;left:0;width:1080px;height:150px}}
.blk{{position:absolute;top:0;width:220px;height:130px;border:1.5px solid var(--mid);border-radius:4px;padding:18px 20px;background:#0B141C}}
.blk small{{display:block;font-family:'MO',monospace;font-size:24px;color:var(--mid);letter-spacing:1px}}
.blk b{{display:block;font-family:'BS',sans-serif;font-weight:800;font-size:44px;margin-top:10px;color:var(--bright)}}
.blk:not(:first-child)::before{{content:'';position:absolute;left:-26px;top:62px;width:26px;height:3px;background:var(--mid)}}
.vit{{position:absolute;width:450px;height:260px;border:1.5px solid var(--edge);border-radius:6px;padding:30px 34px;background:var(--film)}}
.vit b{{font-family:'BS',sans-serif;font-weight:800;font-size:150px;line-height:1;color:var(--bright)}}
.vit b.of{{font-size:70px;color:var(--dim)}}
.vit small{{display:block;font-family:'MO',monospace;font-size:24px;letter-spacing:3px;color:var(--mid);margin-top:14px}}
.url{{position:absolute;left:220px;width:640px;top:1400px;height:100px;display:grid;place-items:center;background:var(--lum);color:#071015;font-size:40px;letter-spacing:2px;border-radius:3px}}
.fine{{position:absolute;left:0;right:0;text-align:center;top:1560px;font-size:24px;letter-spacing:3px;color:var(--dim)}}
.skin{{fill:none;stroke:rgba(216,243,255,.85);stroke-width:3.5;stroke-linecap:round}}
.bone{{fill:none;stroke:rgba(216,243,255,.45);stroke-width:3}}
.vert{{fill:none;stroke:rgba(216,243,255,.5);stroke-width:2.5}}
.gyrus{{fill:none;stroke:var(--mid);stroke-width:3}}
.neuron{{fill:var(--lum)}}
.vagus{{fill:none;stroke:var(--lum);stroke-width:5;stroke-linecap:round}}
.pulse{{fill:var(--red)}}
.peri{{fill:none;stroke:var(--red);stroke-width:4}}
.heart{{fill:rgba(255,75,51,.22);stroke:var(--red);stroke-width:6;transform-box:fill-box;transform-origin:50% 50%}}
.pencil{{fill:none;stroke:var(--pencil);stroke-width:4;stroke-linecap:round}}
#bars{{position:absolute;left:48px;right:48px;top:52px;display:flex;gap:8px}}
#bars i{{flex:1;height:6px;border-radius:3px;background:rgba(216,243,255,.18);overflow:hidden;position:relative}}
#bars i u{{position:absolute;inset:0;background:var(--lum);transform-origin:0 50%;transform:scaleX(0)}}
#brand{{position:absolute;left:52px;top:84px;font-family:'BS',sans-serif;font-weight:800;font-size:46px;letter-spacing:.02em;color:var(--lum)}}
#brand span{{color:var(--red)}}
#pgn{{position:absolute;right:52px;top:96px;font-family:'MO',monospace;font-size:26px;letter-spacing:3px;color:var(--dim)}}
#hud{{position:absolute;left:52px;right:52px;bottom:58px;height:80px;display:flex;align-items:center;gap:22px}}
#hud .mono{{font-size:26px;letter-spacing:3px;color:var(--dim);white-space:nowrap}}
#hud b{{font-family:'MO',monospace;font-weight:400;color:var(--red);font-size:30px}}
#ecg{{flex:1;min-width:0;width:100%;height:80px}}
'''

html = f'''<!doctype html><html><head><meta charset=utf8><meta name=viewport content="width=1080"><title>Substrate teaser</title>
<style>{CSS}</style></head><body>
<div id="stage">
  <div id="bg"></div><canvas id="fx" width="1080" height="1920"></canvas><div id="film"></div><div id="flashbg"></div>
  {''.join(S)}
  <div id="bars"></div><div id="brand">SUBSTR<span>A</span>TE</div><div id="pgn">IM 01 / 10</div>
  <div id="hud"><span class="mono">HR <b id="bpm">75</b> BPM</span><canvas id="ecg" width="760" height="80"></canvas><span class="mono" id="hudr">HONESTY &middot; ON</span></div>
  <div id="vig"></div>
</div>
<script>const CFG={json.dumps(CFG)};</script>
<script src="engine.js"></script>
</body></html>'''
open('/home/claude/substrate-teaser/teaser.html', 'w').write(html)
print('teaser.html written', len(html))
