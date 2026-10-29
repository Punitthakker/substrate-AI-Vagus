(function(){
const W=1080,HH=1920,D=80,BEAT=0.8;
const $=id=>document.getElementById(id),Q=(s,r=document)=>[...r.querySelectorAll(s)];
const cl=(x,a=0,b=1)=>Math.min(b,Math.max(a,x)),P=(t,a,b)=>cl((t-a)/(b-a)),L=(a,b,k)=>a+(b-a)*k;
const eo=x=>1-Math.pow(1-x,3),eio=x=>x<.5?4*x*x*x:1-Math.pow(-2*x+2,3)/2;
const back=x=>{const c1=1.7,c3=c1+1;return 1+c3*Math.pow(x-1,3)+c1*Math.pow(x-1,2)};
let seed=7;const rnd=()=>{seed=(seed*16807)%2147483647;return seed/2147483647};

const SC=[[0,8],[8,16],[16,24],[24,33.6],[33.6,44],[44,52],[52,60],[60,68],[68,73.6],[73.6,80.01]];
const FADE=[[0,.35],[.35,.35],[.35,.35],[.35,0],[0,.35],[.35,.35],[.35,.35],[.35,.35],[.35,0],[0,0]];
const S=SC.map((_,i)=>$('s'+(i+1)));
const bars=$('bars');SC.forEach(()=>{const i=document.createElement('i');i.innerHTML='<u></u>';bars.appendChild(i)});const barU=Q('#bars u');
const num=s=>s==null?null:parseFloat(s),nums=s=>s?s.split(/[ ,]+/).map(parseFloat):null;

// heartbeat envelope: 1 at each lub, small second bump for dub
const beatOn=t=>{ if(t<0)return false; if(t>=73.6) return [76.0,76.8,77.6,78.4].some(b=>t>=b&&t<b+.8); return true; };
function hb(t){ if(!beatOn(t))return 0; let ph=((t%BEAT)+BEAT)%BEAT; if(t>=73.6){const bs=[76.0,76.8,77.6,78.4];const b=bs.filter(x=>t>=x).pop();ph=t-b;}
  return Math.exp(-ph*14)+.55*Math.exp(-Math.max(0,ph-.2)*16)*(ph>=.2?1:0); }

// ---------- declarative animation items
const items=S.map(()=>[]);
Q('#stage [data-in],#stage [data-draw],#stage [data-dot],#stage [data-on],#stage [data-count],#stage [data-w],#stage [data-text],#stage [data-flip],#stage [data-sweep],#stage [data-pulses],#stage [data-shake],#stage [data-out]').forEach(el=>{
 const sc=el.closest('.sc');const si=S.indexOf(sc);if(si<0)return;const d=el.dataset;
 const a={el,svg:el instanceof SVGElement,in:num(d.in),type:d.anim||'up',dur:num(d.dur)||.45,dy:num(d.dy)??60,dx:num(d.dx)??300,out:num(d.out),
  sh:nums(d.shake),pus:nums(d.pulses),flip:nums(d.flip),w:nums(d.w),sw:nums(d.sweep),on:num(d.on),off:num(d.off),cnt:d.count?d.count.split(','):null,
  txt:d.text?d.text.split('|').map(x=>{const i=x.indexOf(':');return [parseFloat(x.slice(0,i)),x.slice(i+1)]}):null,draw:nums(d.draw),dot:d.dot?d.dot.split(','):null};
 if(a.draw){a.len=el.getTotalLength();el.style.strokeDasharray=a.len;el.style.strokeDashoffset=a.len;}
 items[si].push(a);});
const FMT={int:v=>Math.round(v).toLocaleString('en-US'),aed:v=>'AED '+Math.round(v).toLocaleString('en-US'),pct:v=>Math.round(v)+'%'};
const cval=(c,t)=>{const to=+c[0],a=+c[1],b=+c[2],f=c[3]||'int',fr=c[4]!=null?+c[4]:0;return FMT[f](L(fr,to,eo(P(t,a,b))))};
function anim(a,t){const el=a.el;let o=1,tx=0,ty=0,sc=1,ry=0,sx=1;
 if(a.in!=null){const k=P(t,a.in,a.in+a.dur),e=eo(k);
  switch(a.type){case 'up':o=e;ty=(1-e)*a.dy;break;case 'down':o=e;ty=-(1-e)*a.dy;break;case 'left':o=e;tx=-(1-e)*a.dx;break;case 'right':o=e;tx=(1-e)*a.dx;break;
   case 'pop':o=cl(k*3);sc=k>0?back(k):.6;break;case 'zoom':o=e;sc=L(1.5,1,e);break;default:o=e;}}
 if(a.out!=null)o*=1-P(t,a.out,a.out+.3);
 if(a.sh&&t>a.sh[0]&&t<a.sh[1])tx+=Math.sin(t*90)*12*(1-P(t,a.sh[0],a.sh[1]));
 if(a.pus)a.pus.forEach(p=>{sc*=1+.05*Math.sin(P(t,p,p+.3)*Math.PI)});
 if(a.flip)ry=(1-eio(P(t,a.flip[0],a.flip[1])))*180;
 if(a.w)sx=eio(P(t,a.w[0],a.w[1]));
 if(a.sw)tx+=L(0,a.sw[2],eio(P(t,a.sw[0],a.sw[1])));
 if(a.on!=null)el.classList.toggle('on',t>=a.on&&!(a.off!=null&&t>=a.off));
 if(a.cnt)el.textContent=cval(a.cnt,t);
 if(a.txt){let s=a.txt[0][1];a.txt.forEach(([tt,v])=>{if(t>=tt)s=v});if(el._t!==s){el.innerHTML=s;el._t=s;}}
 if(a.draw)el.style.strokeDashoffset=a.len*(1-eio(P(t,a.draw[0],a.draw[1])));
 if(a.dot){const p=$(a.dot[0]),t0=+a.dot[1],t1=+a.dot[2];const k=P(t,t0,t1);if(!p._len)p._len=p.getTotalLength();
  if(k>0&&k<1){const q=p.getPointAtLength(p._len*eio(k));el.setAttribute('cx',q.x);el.setAttribute('cy',q.y);el.setAttribute('opacity',1);}else el.setAttribute('opacity',0);return;}
 el.style.opacity=o;
 if(a.w){el.style.transform=`scaleX(${sx})`;return;}
 if(!a.svg)el.style.transform=`translate(${tx}px,${ty}px) perspective(900px) rotateY(${ry}deg) scale(${sc})`;
}

// ---------- canvas FX: drifting cells, scan sweeps, rings, bursts
const fx=$('fx'),cx=fx.getContext('2d');
const cells=[];seed=5;for(let i=0;i<70;i++)cells.push({x:rnd()*W,y:rnd()*HH,s:14+rnd()*40,ph:rnd()*6.28,r:3+rnd()*7,red:rnd()<.45,a:.12+rnd()*.25});
const SWEEPS=[8,16,24,44,52,60,68];
const RINGS=[[30.0,566,968],[33.6,540,880],[41.2,540,960],[60,540,888],[68,540,960],[73.6,540,520]];
const BURSTS=[];seed=11;[[56.25,250,1300,70],[73.65,540,520,110],[33.62,540,800,90]].forEach(([t0,x,y,n])=>{for(let i=0;i<n;i++){const a=rnd()*6.283,v=420+rnd()*1000;BURSTS.push({t0,x,y,vx:Math.cos(a)*v,vy:Math.sin(a)*v-260,r:2+rnd()*5,life:.9+rnd()*.9,red:rnd()<.5});}});
function drawFX(t){cx.clearRect(0,0,W,HH);
 const k=hb(t),drive=t>=33.6&&t<73.6?1:.55;
 cells.forEach(p=>{const y=((p.y-t*p.s*drive)%HH+HH)%HH,x=p.x+Math.sin(t*.6+p.ph)*24;const r=p.r*(1+.25*k);
  cx.beginPath();cx.ellipse(x,y,r,r*.7,p.ph,0,6.283);cx.strokeStyle=p.red?`rgba(255,75,51,${p.a*(.7+.6*k)})`:`rgba(127,216,247,${p.a*.8})`;cx.lineWidth=2;cx.stroke();});
 SWEEPS.forEach(b=>{const q=P(t,b-.3,b+.35);if(q<=0||q>=1)return;const y=L(-80,2000,eio(q));
  const g=cx.createLinearGradient(0,y-110,0,y+20);g.addColorStop(0,'rgba(216,243,255,0)');g.addColorStop(.85,'rgba(216,243,255,.22)');g.addColorStop(1,'rgba(216,243,255,.0)');
  cx.fillStyle=g;cx.fillRect(0,y-110,W,130);cx.fillStyle='rgba(216,243,255,.7)';cx.fillRect(0,y,W,3);});
 RINGS.forEach(([t0,x,y])=>{const d=t-t0;if(d<0||d>1)return;const q=d;cx.beginPath();cx.arc(x,y,60+eo(q)*820,0,6.283);cx.strokeStyle=`rgba(255,75,51,${.5*(1-q)})`;cx.lineWidth=6*(1-q)+1;cx.stroke();});
 BURSTS.forEach(b=>{const d=t-b.t0;if(d<0||d>b.life)return;const q=d/b.life,x=b.x+b.vx*d,y=b.y+b.vy*d+800*d*d;cx.beginPath();cx.arc(x,y,b.r*(1-q*.5),0,6.283);cx.fillStyle=b.red?`rgba(255,75,51,${1-q})`:`rgba(216,243,255,${1-q})`;cx.fill();});
}

// ---------- HUD ECG
const ec=$('ecg'),ex=ec.getContext('2d');
function ecgV(tau){ if(tau<0)return 0; let v=0;
 const near=Math.round(tau/BEAT);for(let k=near-1;k<=near+1;k++){const b=k*BEAT;if(b<0||!beatOn(b+.001))continue;
  if(b>=73.6&&![76.0,76.8,77.6,78.4].some(x=>Math.abs(x-b)<.01))continue;
  const d=tau-b; v+=.12*Math.exp(-Math.pow((d+.14)/.03,2)) - .15*Math.exp(-Math.pow((d+.02)/.008,2)) + 1*Math.exp(-Math.pow(d/.011,2)) - .28*Math.exp(-Math.pow((d-.025)/.012,2)) + .22*Math.exp(-Math.pow((d-.2)/.045,2));}
 return v;}
function drawECG(t){ex.clearRect(0,0,760,80);ex.beginPath();const win=3.2;
 for(let i=0;i<=760;i+=2){const tau=t-win+win*i/760;const y=56-ecgV(tau)*44;i?ex.lineTo(i,y):ex.moveTo(i,y);}
 ex.strokeStyle=t>=33.6&&t<73.6?'#FF4B33':'#7FD8F7';ex.lineWidth=3;ex.stroke();
 ex.beginPath();ex.arc(758,56-ecgV(t)*44,5,0,6.283);ex.fillStyle='#E4F5FD';ex.fill();}
const BPMS=[[0,72],[16,96],[24,80],[33.6,75],[44,75],[52,68],[60,75],[73.6,64]];

// ---------- kinetic open
const KT=[.8,1.6,2.4,3.2,4.0,4.8],flash=$('flash');
const HEARTS=[['hgrp',566,975],['h8',540,888],['h10',540,520]].map(([id,x,y])=>[$(id),x,y]);
function render(t){
 SC.forEach(([a,b],i)=>{const [fi,fo]=FADE[i];let o=(t>=a&&t<b)?1:0;if(o){if(fi)o*=P(t,a,a+fi);if(fo)o*=1-P(t,b-fo,b);}
  S[i].style.opacity=o;S[i].style.visibility=o>0.001?'visible':'hidden';
  if(o>0){const pr=P(t,a,b),zin=fi?(1-eo(P(t,a,a+fi)))*.05:0,zout=fo?eio(P(t,b-fo,b))*.05:0;
   S[i].style.transform=`scale(${1+.025*pr-zin+zout})`;S[i].style.filter=(zin+zout)>.002?`blur(${(zin+zout)*110}px)`:'none';
   items[i].forEach(x=>anim(x,t));}
  barU[i].style.transform=`scaleX(${P(t,a,b)})`;});
 const si=SC.findIndex(([a,b])=>t>=a&&t<b);$('pgn').textContent='IM '+String(si+1).padStart(2,'0')+' / 10';
 const chrome=t<73.4?1:1-P(t,73.4,73.7);['bars','pgn','brand'].forEach(id=>$(id).style.opacity=chrome*(t<.4?P(t,0,.4):1));
 let bp=72;BPMS.forEach(([tt,v])=>{if(t>=tt)bp=v});$('bpm').textContent=bp;$('hudr').innerHTML=t<33.6?'HONESTY &middot; <span style="color:#FF4B33">MISSING</span>':'HONESTY &middot; <span style="color:#9EF0B0">ON</span>';
 let fl=0;[[33.6,.55],[73.6,.45],[30.0,.18],[41.2,.15],[60,.2],[68,.18]].forEach(([f,v])=>{if(t>=f)fl+=v*(1-P(t,f,f+.4))});$('flashbg').style.opacity=fl;
 const k=hb(t);HEARTS.forEach(([g,x,y])=>{if(g)g.setAttribute('transform',`translate(${x} ${y}) scale(${1+.09*k}) translate(${-x} ${-y})`)});
 drawFX(t);drawECG(t);
 if(t<5.8){let ci=-1;KT.forEach((kk,i)=>{if(t>=kk)ci=i});
  if(ci>=0){const w=CFG.kin[ci],q=P(t,KT[ci],KT[ci]+.16);const fs=w.length<=3?330:w.length<=7?250:190;
   flash.innerHTML=w;flash.style.fontSize=fs+'px';flash.style.top=(960-fs*.5)+'px';flash.style.opacity=1-P(t,5.45,5.6);
   flash.style.transform=`scale(${L(1.35,1,eo(q))})`;flash.style.color=w==='AGREE'?'#FF4B33':'#E4F5FD';}else flash.style.opacity=0;}
 else flash.style.opacity=0;
}

// ---------- audio: a score built on the heart
let AC,OUT,REV,NOISE;const mf=n=>440*Math.pow(2,(n-69)/12);
function initAudio(ctx){AC=ctx;const comp=AC.createDynamicsCompressor();comp.threshold.value=-16;comp.ratio.value=4;comp.connect(AC.destination);
 OUT=AC.createGain();OUT.gain.value=.9;OUT.connect(comp);const conv=AC.createConvolver();const len=AC.sampleRate*2.6,ir=AC.createBuffer(2,len,AC.sampleRate);
 for(let c=0;c<2;c++){const d=ir.getChannelData(c);for(let i=0;i<len;i++)d[i]=(Math.random()*2-1)*Math.pow(1-i/len,3)}conv.buffer=ir;
 REV=AC.createGain();REV.gain.value=.34;REV.connect(conv);conv.connect(OUT);
 NOISE=AC.createBuffer(1,AC.sampleRate*2,AC.sampleRate);const nd=NOISE.getChannelData(0);for(let i=0;i<nd.length;i++)nd[i]=Math.random()*2-1;}
function gain(w,a,peak,d,dest=OUT,rev=0){const g=AC.createGain();g.gain.setValueAtTime(.0001,w);g.gain.exponentialRampToValueAtTime(peak,w+a);g.gain.exponentialRampToValueAtTime(.0001,w+a+d);g.connect(dest);if(rev){const r=AC.createGain();r.gain.value=rev;g.connect(r);r.connect(REV);}return g}
function osc(type,f,w,dur,dest){const o=AC.createOscillator();o.type=type;o.frequency.setValueAtTime(f,w);o.connect(dest);o.start(w);o.stop(w+dur+.05);return o}
function noise(w,dur,dest){const s=AC.createBufferSource();s.buffer=NOISE;s.connect(dest);s.start(w,Math.random());s.stop(w+dur+.05);return s}
function filt(type,f,qv,dest){const b=AC.createBiquadFilter();b.type=type;b.frequency.value=f;if(qv)b.Q.value=qv;b.connect(dest);return b}
const half=dest=>{const h=AC.createGain();h.gain.value=.3;h.connect(dest);return h};
const I={
 lub(w,v=.9){const g=gain(w,.004,v,.3);const o=osc('sine',62,w,.36,g);o.frequency.exponentialRampToValueAtTime(38,w+.18);
  const t=gain(w,.002,v*.25,.08);noise(w,.1,filt('lowpass',180,1,t));},
 dub(w,v=.55){const g=gain(w,.004,v,.2);const o=osc('sine',84,w,.24,g);o.frequency.exponentialRampToValueAtTime(52,w+.12);},
 beep(w,v=.045){const g=gain(w,.002,v,.12,OUT,.2);osc('sine',1046,w,.14,g);},
 breath(w,dur,v=.05){const g=AC.createGain();g.gain.setValueAtTime(.0001,w);g.gain.linearRampToValueAtTime(v,w+dur*.45);g.gain.linearRampToValueAtTime(.0001,w+dur);g.connect(OUT);
  const bp=filt('bandpass',500,.8,g);bp.frequency.setValueAtTime(380,w);bp.frequency.linearRampToValueAtTime(900,w+dur*.45);bp.frequency.linearRampToValueAtTime(320,w+dur);noise(w,dur,bp);},
 drone(w,f,dur,v=.05){const g=AC.createGain();g.gain.setValueAtTime(.0001,w);g.gain.linearRampToValueAtTime(v,w+dur*.6);g.gain.linearRampToValueAtTime(.0001,w+dur);g.connect(OUT);
  const lp=filt('lowpass',300,1,g);[-5,5].forEach(dt=>{const o=osc('sawtooth',f,w,dur,lp);o.detune.value=dt;});osc('sine',f/2,w,dur,g);},
 clap(w,v=.24){const g=gain(w,.002,v,.16,OUT,.35);noise(w,.2,filt('bandpass',1600,.9,g));},
 hat(w,v=.04,open=false){const g=gain(w,.001,v,open?.15:.03);noise(w,.2,filt('highpass',8000,0,g));},
 bass(w,f,v=.16,d=.32){const g=gain(w,.006,v,d);const lp=filt('lowpass',480,1,g);osc('triangle',f,w,d+.05,lp);osc('sine',f/2,w,d+.05,lp);},
 pluck(w,f,v=.05){const g=gain(w,.003,v,.5,OUT,.4);const lp=filt('lowpass',3200,2,g);lp.frequency.setValueAtTime(3200,w);lp.frequency.exponentialRampToValueAtTime(650,w+.28);osc('triangle',f,w,.55,lp);osc('square',f*1.004,w,.55,half(lp));},
 pad(w,notes,dur,v=.032){const g=AC.createGain();g.gain.setValueAtTime(.0001,w);g.gain.linearRampToValueAtTime(v,w+.6);g.gain.setValueAtTime(v,w+dur);g.gain.linearRampToValueAtTime(.0001,w+dur+.8);g.connect(OUT);const r=AC.createGain();r.gain.value=.55;g.connect(r);r.connect(REV);
  const lp=filt('lowpass',1100,.7,g);notes.forEach(n=>{[-7,7].forEach(dt=>{const o=osc('sawtooth',mf(n),w,dur+.9,lp);o.detune.value=dt;})});},
 stab(w,notes,v=.06){const g=gain(w,.004,v,.6,OUT,.45);const lp=filt('lowpass',2400,.8,g);notes.forEach(n=>{[-6,6].forEach(dt=>{const o=osc('sawtooth',mf(n+12),w,.75,lp);o.detune.value=dt;})});},
 tick(w,f=1500,v=.08){const g=gain(w,.001,v,.07);const o=osc('sine',f,w,.1,g);o.frequency.exponentialRampToValueAtTime(f*.55,w+.06);},
 whoosh(w,dur=.5,v=.18,rev=false){const g=AC.createGain();g.gain.setValueAtTime(.0001,w);g.gain.linearRampToValueAtTime(v,w+dur*(rev?.85:.45));g.gain.linearRampToValueAtTime(.0001,w+dur);g.connect(OUT);
  const r=AC.createGain();r.gain.value=.4;g.connect(r);r.connect(REV);const bp=filt('bandpass',rev?4000:300,1.3,g);bp.frequency.setValueAtTime(rev?4000:300,w);bp.frequency.exponentialRampToValueAtTime(rev?300:4200,w+dur);noise(w,dur,bp);},
 riser(w,dur,v=.12){const g=AC.createGain();g.gain.setValueAtTime(.0001,w);g.gain.exponentialRampToValueAtTime(v,w+dur);g.gain.linearRampToValueAtTime(.0001,w+dur+.03);g.connect(OUT);
  const hp=filt('highpass',300,1,g);hp.frequency.setValueAtTime(300,w);hp.frequency.exponentialRampToValueAtTime(6000,w+dur);noise(w,dur,hp);
  const lp=filt('lowpass',600,4,g);lp.frequency.setValueAtTime(600,w);lp.frequency.exponentialRampToValueAtTime(5000,w+dur);const h=AC.createGain();h.gain.value=.35;h.connect(lp);const o=osc('sawtooth',110,w,dur,h);o.frequency.exponentialRampToValueAtTime(880,w+dur);},
 decline(w){[[311,0],[233,.14],[175,.3]].forEach(([f,o])=>{const g=gain(w+o,.004,.09,.22);osc('square',f,w+o,.26,filt('lowpass',1300,0,g));});},
 chime(w,notes,v=.07,step=.07){notes.forEach((n,i)=>{const g=gain(w+i*step,.003,v,1.2,OUT,.55);osc('sine',mf(n),w+i*step,1.3,g);osc('triangle',mf(n+12),w+i*step,1.3,half(g));});},
 coin(w,v=.05){[[2093,0],[2637,.055],[3136,.11]].forEach(([f,o])=>{const g=gain(w+o,.002,v,.3,OUT,.3);osc('square',f,w+o,.32,filt('lowpass',5000,0,g));});},
 boom(w,v=.8){const g=gain(w,.01,v,1.7);const o=osc('sine',72,w,1.8,g);o.frequency.exponentialRampToValueAtTime(29,w+1.5);const c=gain(w,.005,.1,1.9,OUT,.6);noise(w,2,filt('highpass',5200,0,c));},
 glitch(w,v=.05){const g=gain(w,.001,v,.09);const f=1800+Math.random()*2400;const o=osc('square',f,w,.1,filt('bandpass',f,6,g));o.frequency.setValueAtTime(f*.5,w+.04);},
};
const PAT=[0,2,4,1,3,4,2,1];
function buildCues(){const CH=CFG.prog,ROOT=CFG.root,c=[];const add=(t,f)=>c.push([t,f]);
 const chordAt=t=>Math.floor(t/3.2)%4;
 // the heart: lub-dub on every beat
 for(let k=0;k<92;k++){const t=k*BEAT;const groove=t>=33.6;const v=t<8?L(.45,.7,t/8):(groove?.95:.72);
  const gap=[51.2,59.2,67.2,72.8].some(g=>Math.abs(g-t)<.01);if(gap)continue;
  add(t,w=>I.lub(w,v));add(t+.2,w=>I.dub(w,v*.6));if(t<24)add(t+.02,w=>I.beep(w,t<8?.04:.03));}
 [[76.0,.8],[76.8,.6],[77.6,.42],[78.4,.26]].forEach(([t,v])=>{add(t,w=>I.lub(w,v));add(t+.2,w=>I.dub(w,v*.6));add(t+.02,w=>I.beep(w,.03*v));});
 // breath + drone in the dark
 add(0,w=>I.breath(w,3.2,.035));add(3.2,w=>I.breath(w,3.2,.04));add(6.4,w=>I.breath(w,1.6,.03));
 add(.5,w=>I.drone(w,mf(38),7.6,.045));
 // kinetic stabs
 KT.forEach((t,i)=>add(t,w=>{I.stab(w,CH[0],.045+i*.004);I.tick(w,900+i*160,.05)}));
 add(5.6,w=>I.whoosh(w,.6,.12));add(6.4,w=>I.riser(w,1.6,.1));
 // pads from 8s, until the end card
 for(let t=8;t<73.6;t+=3.2){const ci=chordAt(t);const v=t<24?.026:(t<33.6?.03:.024);add(t,w=>I.pad(w,CH[ci],3.25,v));}
 // sycophancy glitches + loss
 for(let t=9.5;t<11.6;t+=.25)add(t,w=>I.glitch(w,.045));add(12.2,w=>I.whoosh(w,.4,.14,true));
 for(let t=17.1;t<17.9;t+=.11)add(t,w=>I.tick(w,2100,.025));
 add(19.5,w=>I.decline(w));add(16.8,w=>I.drone(w,mf(33),6.6,.05));
 add(14.4,w=>I.riser(w,1.6,.1));add(22.4,w=>I.riser(w,1.6,.11));
 // the x-ray: slow arpeggio, heart ignites
 for(let t=24;t<33.6;t+=.4){const ci=chordAt(t),st=Math.round((t%3.2)/.4);const notes=CH[ci].map(n=>n+12).sort((a,b)=>a-b);add(t,w=>I.pluck(w,mf(notes[PAT[st%8]%notes.length]),.04));}
 add(24,w=>I.whoosh(w,1.2,.12));add(29.2,w=>I.riser(w,.8,.09));
 add(30.0,w=>{I.boom(w,.7);I.chime(w,[74,77,81,86],.06,.06)});
 add(31.2,w=>I.riser(w,2.4,.13));for(let t=32.8;t<33.6;t+=.1)add(t,(tt=>w=>I.clap(w,.05+.3*(tt-32.8)))(t));add(33.2,w=>I.whoosh(w,.4,.18,true));
 // THE DROP: 33.6 - 73.6 groove on the heartbeat
 add(33.6,w=>{I.boom(w);I.stab(w,CH[0],.08);I.chime(w,[CH[0][0]+24,CH[0][2]+24,CH[0][3]+24,CH[0][4]+24],.06,.05)});
 for(let t=33.6;t<73.2;t+=.2){const k=Math.round((t-33.6)/.2);const gap=[51.2,59.2,67.2,72.8].some(g=>t>=g&&t<g+.8);
  if(k%2===0)add(t+.1,w=>I.hat(w,.04,k%4===2));else add(t,w=>I.hat(w,.018));
  const ci=chordAt(t),st=k%16;const notes=CH[ci].map(n=>n+12).sort((a,b)=>a-b);if(!gap)add(t,w=>I.pluck(w,mf(notes[PAT[st%8]%notes.length]),st%4===0?.05:.035));
  if(k%4===2&&!gap)add(t,w=>I.bass(w,mf(ROOT[ci]+(k%8===2?0:12))));
  if(k%8===4&&!gap)add(t,w=>I.clap(w,.2));}
 [[51.2,52],[59.2,60],[67.2,68]].forEach(([a,b])=>{add(a-.8,w=>I.riser(w,1.6,.12));for(let t=a;t<b;t+=.1)add(t,(tt=>w=>I.clap(w,.05+.32*(tt-a)))(t));add(b-.4,w=>I.whoosh(w,.4,.18,true));});
 add(52,w=>I.boom(w,.55));add(60,w=>I.boom(w));add(68,w=>I.boom(w,.65));add(44,w=>I.whoosh(w,.5,.16));
 // gameplay sfx
 add(41.2,w=>{I.boom(w,.6);I.clap(w,.35);I.stab(w,[38,45,50],.08)});
 add(53.3,w=>{I.tick(w,1200,.09);I.chime(w,[81,86],.05,.08)});add(54.4,w=>I.whoosh(w,.5,.14));
 add(56.2,w=>I.coin(w,.06));add(56.6,w=>I.chime(w,[86,89,93,98],.065,.07));add(57.0,w=>I.riser(w,1,.06));
 add(71.8,w=>{I.boom(w,.5);I.chime(w,[86,93,98],.06,.06)});add(72.0,w=>I.riser(w,1.6,.13));
 // auto ticks on pops
 let pi=0;items.forEach((arr,si)=>{if(si===9)return;arr.forEach(a=>{if(a.type==='pop'&&a.in!=null&&a.in>8){const f=900+(pi++%8)*130;add(a.in,w=>I.tick(w,f,.045));}});});
 for(let i=0;i<8;i++)add(44.8+i*.68,w=>I.tick(w,1300+i*90,.06));
 // end card
 add(73.6,w=>{I.boom(w);I.lub(w,.9);I.stab(w,CH[0],.08);I.pad(w,CH[0],5.4,.04);I.bass(w,mf(ROOT[0]),.18,2.4)});
 add(74.4,w=>I.chime(w,[CH[0][0]+24,CH[0][1]+24,CH[0][2]+24,CH[0][3]+24,CH[0][4]+24],.065,.1));add(76.0,w=>I.chime(w,[CH[0][2]+36,CH[0][4]+36],.035,.18));
 return c.sort((a,b)=>a[0]-b[0]);}

window.__reel={D,seek(t){render(t)},
 async audio(){const sr=44100,oc=new OfflineAudioContext(2,Math.ceil(sr*(D+.5)),sr);initAudio(oc);buildCues().forEach(([ct,fn])=>{try{fn(ct)}catch(e){console.error(e)}});
  const b=await oc.startRendering(),n=b.length,L0=b.getChannelData(0),R0=b.getChannelData(1),buf=new DataView(new ArrayBuffer(44+n*4));
  const ws=(o,s)=>{for(let i=0;i<s.length;i++)buf.setUint8(o+i,s.charCodeAt(i))};
  ws(0,'RIFF');buf.setUint32(4,36+n*4,true);ws(8,'WAVEfmt ');buf.setUint32(16,16,true);buf.setUint16(20,1,true);buf.setUint16(22,2,true);buf.setUint32(24,sr,true);buf.setUint32(28,sr*4,true);buf.setUint16(32,4,true);buf.setUint16(34,16,true);ws(36,'data');buf.setUint32(40,n*4,true);
  for(let i=0;i<n;i++){buf.setInt16(44+i*4,cl(L0[i],-1,1)*32767,true);buf.setInt16(46+i*4,cl(R0[i],-1,1)*32767,true);}
  const u=new Uint8Array(buf.buffer);let s='';for(let i=0;i<u.length;i+=32768)s+=String.fromCharCode.apply(null,u.subarray(i,i+32768));return btoa(s);}};
render(0);
})();
