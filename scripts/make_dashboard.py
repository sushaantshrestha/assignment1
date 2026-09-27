"""Generate a single self-contained dashboard from one or more run JSONs.

Usage:
  python3 scripts/make_dashboard.py \
      --runs "Imbalanced 2-class=output/classify_2class_imbalanced.json;Balanced 3-class=output/classify_3class_balanced.json" \
      --out dashboard/index.html

The HTML embeds the run data as JSON and renders entirely client-side, so it
works offline with no server or network. Charts are hand-drawn SVG/CSS - no
external libraries. The theme lives in CSS custom properties so a host can
recolour the whole product by editing :root.
"""
import argparse, json, os, html, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import NRC_EMOTIONS

TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
:root {{
  /* THEME - recolour the whole product here */
  --bg: #0f1216;
  --surface: #181d24;
  --surface-2: #1f2630;
  --border: #2a333f;
  --text: #edf1f6;
  --muted: #9aa6b5;
  --accent: #6ea8fe;
  --accent-2: #9758ff;
  --good: #4cd08d;
  --warn: #f2c14e;
  --bad: #f06a6a;
  --pos: #4cd08d;
  --neu: #f2c14e;
  --neg: #f06a6a;
  --radius: 14px;
  --shadow: 0 10px 30px rgba(0,0,0,.35);
}}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
html,body {{ background: var(--bg); color: var(--text);
  font-family: "Inter",-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  line-height: 1.5; }}
.wrap {{ max-width: 1180px; margin: 0 auto; padding: 28px 24px 60px; }}
a {{ color: var(--accent); }}
.small {{ font-size: .82rem; color: var(--muted); }}

/* Header */
header {{ display:flex; flex-wrap:wrap; gap:16px; align-items:flex-end;
  justify-content:space-between; padding-bottom:20px; margin-bottom:8px;
  border-bottom:1px solid var(--border); }}
h1 {{ font-size:1.7rem; font-weight:700; letter-spacing:-.02em; }}
h1 .dot {{ color: var(--accent); }}
.sub {{ color:var(--muted); margin-top:6px; font-size:.92rem; max-width:640px; }}
.run-tabs {{ display:flex; gap:6px; flex-wrap:wrap; }}
.run-tab {{ padding:8px 14px; border:1px solid var(--border); border-radius:999px;
  background:var(--surface); color:var(--muted); cursor:pointer; font-size:.85rem; font-weight:600;}}
.run-tab.active {{ background:var(--accent); color:#0b0e13; border-color:var(--accent); }}

/* Theme switch */
.themes {{ display:flex; gap:6px; align-items:center; margin-left:auto; }}
.theme-btn {{ width:22px; height:22px; border-radius:50%; border:2px solid var(--border);
  cursor:pointer; }}
.theme-btn:hover {{ transform:scale(1.12); }}

/* KPI cards */
.kpis {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr));
  gap:14px; margin:22px 0; }}
.kpi {{ background:var(--surface); border:1px solid var(--border); border-radius:var(--radius);
  padding:18px; box-shadow:var(--shadow); }}
.kpi .label {{ font-size:.78rem; text-transform:uppercase; letter-spacing:.06em; color:var(--muted); }}
.kpi .value {{ font-size:1.9rem; font-weight:800; margin-top:6px; letter-spacing:-.02em; }}
.kpi .hint {{ font-size:.78rem; color:var(--muted); margin-top:4px; }}
.val-good {{ color:var(--good); }} .val-warn {{ color:var(--warn); }} .val-bad {{ color:var(--bad); }}

/* Sections */
section {{ background:var(--surface); border:1px solid var(--border); border-radius:var(--radius);
  padding:22px; margin-top:18px; box-shadow:var(--shadow); }}
section h2 {{ font-size:1.05rem; margin-bottom:4px; letter-spacing:-.01em; }}
section .desc {{ color:var(--muted); font-size:.86rem; margin-bottom:16px; }}
.cols {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(320px,1fr)); gap:22px; }}

/* Charts */
.chart-title {{ font-size:.82rem; color:var(--muted); margin-bottom:10px; font-weight:600;
  text-transform:uppercase; letter-spacing:.05em; }}
.hbar-row {{ display:grid; grid-template-columns:118px 1fr 52px; gap:10px; align-items:center;
  margin:7px 0; font-size:.86rem; }}
.hbar-row .lbl {{ color:var(--text); font-weight:600; }}
.hbar-track {{ background:var(--surface-2); border-radius:6px; height:18px; overflow:hidden; }}
.hbar-fill {{ height:100%; border-radius:6px; transition:width .5s ease; }}
.hbar-row .num {{ text-align:right; color:var(--muted); font-variant-numeric:tabular-nums; }}

/* Confusion matrix */
.confusion {{ display:grid; grid-template-columns:auto auto; gap:0; justify-content:start; }}
.conf-row {{ display:contents; }}
.conf-cell {{ min-width:86px; text-align:center; padding:14px 10px; font-weight:700;
  border:1px solid var(--surface); position:relative; }}
.conf-cell .n {{ font-size:1.05rem; }}
.conf-cell .pct {{ font-size:.72rem; color:rgba(0,0,0,.55); font-weight:600; }}
.conf-head-row, .conf-head-col {{ color:var(--muted); font-size:.74rem; text-transform:uppercase;
  letter-spacing:.05em; font-weight:700; }}
.conf-corner {{ }}
.conf-head-col {{ transform:rotate(180deg); writing-mode:vertical-rl; align-self:center;
  justify-self:center; }}
.legend {{ display:flex; gap:10px; align-items:center; font-size:.75rem; color:var(--muted); margin-top:10px;}}
.legend .swatch {{ width:12px; height:12px; border-radius:3px; display:inline-block; }}

/* Emotion bars */
.emo-grid {{ display:grid; grid-template-columns:1fr 1fr; gap:24px; }}
.emo-bars {{ }}
@media (max-width:760px){{ .emo-grid {{ grid-template-columns:1fr; }} }}
.vbar-track {{ background:var(--surface-2); border-radius:6px; height:210px; display:flex;
  align-items:flex-end; gap:6px; padding:8px; }}
.vbar {{ flex:1; border-radius:5px 5px 2px 2px; background:var(--accent); min-width:0;
  position:relative; transition:height .5s ease; }}
.vbar:hover {{ filter:brightness(1.2); }}
.vbar-none {{ border-left:1px dashed var(--border); border-top-left-radius:0;
  border-bottom-left-radius:0; }}
.vbar .tl {{ position:absolute; top:-18px; width:100%; text-align:center; font-size:.7rem;
  color:var(--muted); }}
.vbar-ticks {{ display:flex; gap:6px; padding:4px 8px 0; }}
.vbar-ticks span {{ flex:1; min-width:0; text-align:center; font-size:.56rem;
  letter-spacing:-.02em; color:var(--muted); overflow:hidden; white-space:nowrap;
  text-overflow:ellipsis; }}

/* Metric pills */
.pill-row {{ display:flex; flex-wrap:wrap; gap:10px; }}
.pill {{ background:var(--surface-2); border:1px solid var(--border); border-radius:999px;
  padding:6px 12px; font-size:.82rem; color:var(--text); }}

/* Reviews table */
.controls {{ display:flex; flex-wrap:wrap; gap:10px; align-items:center; margin-bottom:14px; }}
.seg {{ display:inline-flex; border:1px solid var(--border); border-radius:999px; overflow:hidden; }}
.seg button {{ padding:7px 14px; background:var(--surface); color:var(--muted); border:none;
  cursor:pointer; font-size:.83rem; font-weight:600; }}
.seg button.active {{ background:var(--accent); color:#0b0e13; }}
.controls input[type=search], .controls select {{
  padding:8px 12px; border-radius:10px; border:1px solid var(--border);
  background:var(--surface); color:var(--text); font-size:.85rem; outline:none; }}
.controls input[type=search]:focus, .controls select:focus {{ border-color:var(--accent); }}
.count-line {{ margin-left:auto; color:var(--muted); font-size:.84rem;
  font-variant-numeric:tabular-nums; }}
table {{ width:100%; border-collapse:collapse; font-size:.85rem; }}
th {{ text-align:left; color:var(--muted); text-transform:uppercase; font-size:.7rem;
  letter-spacing:.05em; padding:8px 10px; border-bottom:1px solid var(--border); cursor:pointer;
  user-select:none; white-space:nowrap; }}
td {{ padding:10px; border-bottom:1px solid var(--surface-2); vertical-align:top; }}
tr.row:hover {{ background:var(--surface-2); }}
.badge {{ display:inline-block; padding:2px 8px; border-radius:999px; font-size:.7rem;
  font-weight:700; }}
.b-pos {{ background:rgba(76,208,141,.16); color:var(--pos); }}
.b-neu {{ background:rgba(242,193,78,.16); color:var(--neu); }}
.b-neg {{ background:rgba(240,106,106,.16); color:var(--neg); }}
.correct {{ color:var(--good); }} .incorrect {{ color:var(--bad); font-weight:700; }}
.emo-tag {{ font-size:.76rem; padding:2px 6px; border-radius:6px; background:var(--surface-2);
  color:var(--muted); }}
.row-expand {{ font-size:.86rem; color:var(--muted); margin-top:6px; border-top:1px dashed var(--border);
  padding-top:6px; }}
.truncate {{ max-width:340px; }}
.grid-star {{ color:var(--warn); }}

footer {{ margin-top:30px; padding-top:16px; border-top:1px solid var(--border);
  color:var(--muted); font-size:.8rem; }}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <div>
      <h1>Amazon Gift-Card <span class="dot">Review</span> Classifier</h1>
      <div class="sub">LLM sentiment &amp; emotion classification of Amazon
        <strong>Reviews '23</strong> &ldquo;Gift Cards&rdquo; reviews, checked against star ratings.
        Self-contained, offline, recolorable.</div>
    </div>
    <div class="themes" title="Recolour the theme">
      <button class="theme-btn" data-var='dark' style="background:#0f1216" title="Dark"></button>
      <button class="theme-btn" data-var='light' style="background:#f7f8fa" title="Light"></button>
      <button class="theme-btn" data-var='sepia' style="background:#f4ead9" title="Sepia"></button>
    </div>
  </header>

  <div class="run-tabs" id="runTabs"></div>

  <div class="kpis" id="kpis"></div>

  <section>
    <h2>How well does the model classify?</h2>
    <div class="desc">Model predictions vs. the rating-based answer, plus the &ldquo;guess the majority class&rdquo;
      baseline, so the headline number is honest about the class imbalance.</div>
    <div class="cols">
      <div>
        <div class="chart-title">Agreement vs. majority-class baseline</div>
        <div class="hbar-row"><span class="lbl">Model</span>
          <div class="hbar-track"><div class="hbar-fill" id="b_model" style="background:var(--accent)"></div></div>
          <span class="num" id="n_model"></span></div>
        <div class="hbar-row"><span class="lbl">Baseline</span>
          <div class="hbar-track"><div class="hbar-fill" id="b_base" style="background:var(--accent-2)"></div></div>
          <span class="num" id="n_base"></span></div>
        <div class="small" style="margin-top:8px" id="baseline_note"></div>
      </div>
      <div>
        <div class="chart-title">Per-class accuracy (fraction each answer-class got right)</div>
        <div id="class_acc"></div>
      </div>
    </div>
  </section>

  <section>
    <h2>Where the model succeeds and fails</h2>
    <div class="desc">Confusion matrix &mdash; true answer on the top, what the model predicted on the side.
      Bright diagonal = correct. Off-diagonal cells show exactly which classes get confused with which.</div>
    <div class="cols">
      <div>
        <div id="confusion"></div>
        <div class="legend"><span class="swatch" id="lg-lo"></span> low count
          <span class="swatch" id="lg-hi"></span> high count</div>
      </div>
      <div>
        <div class="chart-title">Distribution of classes in this sample</div>
        <div id="dist"></div>
      </div>
    </div>
  </section>

  <section>
    <h2>Primary emotion: LLM vs. word list</h2>
    <div class="desc">Two independent takers on each review's primary emotion. The LLM reads context;
      the NRC word list just counts which emotion-words appear. Compare their distributions and agreement.</div>
    <div class="pill-row" style="margin-bottom:16px" id="emo_agree_pills"></div>
    <div class="emo-grid">
      <div>
        <div class="chart-title">LLM-detected emotions</div>
        <div class="vbar-track" id="emo_llm"></div>
        <div class="vbar-ticks" id="emo_llm_ticks"></div>
      </div>
      <div>
        <div class="chart-title">NRC word-list emotions</div>
        <div class="vbar-track" id="emo_nrc"></div>
        <div class="vbar-ticks" id="emo_nrc_ticks"></div>
      </div>
    </div>
  </section>

  <section>
    <h2>Every review</h2>
    <div class="desc">Filter the sample &mdash; all, correct, or mismatched &mdash; by class, or search the text.
      Rows show what the model said vs. the rating-based answer, plus both emotion takers.</div>
    <div class="controls">
      <div class="seg" id="segFilter">
        <button data-f="all" class="active">All</button>
        <button data-f="correct">Correct</button>
        <button data-f="mismatch">Mismatched</button>
      </div>
      <select id="classFilter"><option value="all">All classes</option></select>
      <select id="emoFilter"><option value="all">Any emotion</option></select>
      <input type="search" id="search" placeholder="Search text (e.g. 'terrible', 'gift')">
      <span class="count-line" id="countLine"></span>
    </div>
    <div style="overflow-x:auto">
      <table>
        <thead><tr>
          <th data-k="rating">★</th>
          <th data-k="correct">Answer</th>
          <th data-k="pred">Model</th>
          <th>Emotions (LLM / NRC)</th>
          <th data-k="conf">Confidence</th>
          <th>Title &amp; text</th>
          <th data-k="helpful">Helpful</th>
        </tr></thead>
        <tbody id="tbody"></tbody>
      </table>
    </div>
  </section>

  <footer id="footer"></footer>
</div>

<script>
const RUNS = __RUNS__;
let current = Object.keys(RUNS)[0];
let fCorrect='all', fClass='all', fEmo='all', fSearch='', sortK='rating', sortDir=-1;

const EMO = __EMO__;
const THEMES = {{
  dark:  {{ '--bg':'#0f1216','--surface':'#181d24','--surface-2':'#1f2630','--border':'#2a333f','--text':'#edf1f6','--muted':'#9aa6b5','--accent':'#6ea8fe','--accent-2':'#9758ff','--good':'#4cd08d','--warn':'#f2c14e','--bad':'#f06a6a','--pos':'#4cd08d','--neu':'#f2c14e','--neg':'#f06a6a' }},
  light: {{ '--bg':'#f7f8fa','--surface':'#ffffff','--surface-2':'#eef1f5','--border':'#e0e4ea','--text':'#17202a','--muted':'#5d6b7a','--accent':'#2563eb','--accent-2':'#7c3aed','--good':'#15803d','--warn':'#b45309','--bad':'#b91c1c','--pos':'#15803d','--neu':'#b45309','--neg':'#b91c1c' }},
  sepia: {{ '--bg':'#f4ead9','--surface':'#fbf5e8','--surface-2':'#efe3cf','--border':'#d8c7a3','--text':'#3b3020','--muted':'#7c6a4e','--accent':'#9a5b23','--accent-2':'#6d7f32','--good':'#3f7d3a','--warn':'#a8641c','--bad':'#a63c2b','--pos':'#3f7d3a','--neu':'#a8641c','--neg':'#a63c2b' }},
}};
function applyTheme(name){{
  const t=THEMES[name]; if(!t) return;
  const r=document.documentElement.style;
  for(const k in t) r.setProperty(k, t[k]);
}}
document.querySelectorAll('.theme-btn').forEach(b=>{{
  b.onclick=()=>{{
    applyTheme(b.dataset.var);
    document.querySelectorAll('.theme-btn').forEach(x=>x.style.borderColor='var(--border)');
    b.style.borderColor='var(--accent)';
  }};
}});

function run(){{ return RUNS[current]; }}
function classColor(c){{ return c==='POSITIVE'?'var(--pos)':(c==='NEGATIVE'?'var(--neg)':'var(--neu)'); }}

function renderTabs(){{
  const c=document.getElementById('runTabs'); c.innerHTML='';
  for(const k of Object.keys(RUNS)){{
    const b=document.createElement('button');
    b.className='run-tab'+(k===current?' active':''); b.textContent=k;
    b.onclick=()=>{{ current=k; document.querySelectorAll('.run-tab').forEach(x=>x.classList.remove('active'));
      b.classList.add('active'); renderAll(); }};
    c.appendChild(b);
  }}
}}

function renderKpis(){{
  const m=run().meta; const cls=run().rows.length;
  const agree=run().rows.filter(r=>r.pred===r.correct).length;
  const rate=agree/cls;
  const fails=run().rows.filter(r=>r.pred===null).length;
  // baseline = majority class share
  const cnt={{}}; run().rows.forEach(r=>cnt[r.correct]=(cnt[r.correct]||0)+1);
  const base=Math.max(...Object.values(cnt))/cls;
  const pc=String(Math.round(rate*1000)/10)+'%';
  const gain=(rate-base)*100;
  const g = (rate>base? 'val-good':(rate<base?'val-bad':'val-warn'));
  const kids=[
    ['Agreement vs rating', pc, m.agreement!==undefined?'matches saved output':'', g],
    ['Reviews scored', cls, m.sample||'', ''],
    ['vs majority baseline', '+'+(gain).toFixed(1)+' pts',
     (isTie(run())? 'guessing any single class = ' : 'always-pick-'+majorityLabel(run())+ ' = ')+Math.round(base*1000)/10+'%',
     gain>0?'val-warn':''],
    ['LLM failures', fails, fails? 'unable to produce a label':'clean run', fails? 'val-bad':'val-good'],
  ];
  document.getElementById('kpis').innerHTML = kids.map(k=>
    `<div class="kpi"><div class="label">${k[0]}</div><div class="value ${k[3]}">${k[1]}</div>`+
    `<div class="hint">${k[2]}</div></div>`).join('');
  document.getElementById('baseline_note').textContent =
    isTie(run())
    ? 'These classes are perfectly balanced in this sample (33.3% each), so guessing any single class every time already scores 33.3%.'
    : 'The data is heavily skewed: the majority answer-class is '+majorityLabel(run())+
      ' '+Math.round(base*1000)/10+'% of this sample. Guessing it every time already looks accurate.';
}}
function majorityLabel(run){{
  const cnt={{}}; run.rows.forEach(r=>cnt[r.correct]=(cnt[r.correct]||0)+1);
  const entries=Object.entries(cnt).sort((a,b)=>b[1]-a[1]);
  const top=entries[0][1];
  const tied=entries.filter(e=>e[1]===top).length;
  return tied>1 ? "any single class" : entries[0][0];
}}
function isTie(run){{
  const cnt={{}}; run.rows.forEach(r=>cnt[r.correct]=(cnt[r.correct]||0)+1);
  const entries=Object.entries(cnt).sort((a,b)=>b[1]-a[1]);
  return entries.filter(e=>e[1]===entries[0][1]).length>1;
}}

function renderClassAcc(){{
  const rows=run().rows, el=document.getElementById('class_acc'); el.innerHTML='';
  const classes=[...new Set(rows.map(r=>r.correct))];
  for(const c of ['POSITIVE','NEUTRAL','NEGATIVE'].filter(c=>classes.includes(c)) ){{
    const sub=rows.filter(r=>r.correct===c);
    const ok=sub.filter(r=>r.pred===c).length;
    const pct=sub.length? ok/sub.length:0;
    const row=document.createElement('div'); row.className='hbar-row';
    row.innerHTML=`<span class="lbl">${c}</span>
      <div class="hbar-track"><div class="hbar-fill" style="width:${pct*100}%;background:${classColor(c)}"></div></div>
      <span class="num">${ok}/${sub.length} = ${Math.round(pct*100)}%</span>`;
    el.appendChild(row);
  }}
}}

function renderConfusion(){{
  const rows=run().rows, el=document.getElementById('confusion');
  const classes=['POSITIVE','NEUTRAL','NEGATIVE'];
  const used=classes.filter(c=>rows.some(r=>r.correct===c||r.pred===c));
  // heat scale
  let maxn=0; const cell={{}};
  used.forEach(a=>used.forEach(b=>{{ const n=rows.filter(r=>r.correct===a&&r.pred===b).length;
    cell[a+'_'+b]=n; maxn=Math.max(maxn,n); }}));
  function bg(a,b){{
    const n=cell[a+'_'+b]||0; const t=n/maxn;
    // interp across accent ramp
    const lo=[31,42,56], hi=[110,168,254];
    const c=lo.map((v,i)=>Math.round(v+(hi[i]-v)*t));
    const txt = t>0.4 ? '#0b0e13':'#eef1f6';
    return `background:rgb(${c});color:${txt}`;
  }}
  let html=`<div class="confusion"><div class="conf-cell conf-corner"></div>`;
  used.forEach(b=>html+=`<div class="conf-cell conf-head-row">${b}</div>`);
  used.forEach(a=>{{
    html+=`<div class="conf-cell conf-head-col">${a}</div>`;
    used.forEach(b=>{{
      const n=cell[a+'_'+b]||0;
      html+=`<div class="conf-cell" style="${bg(a,b)}"><div class="n">${n}</div>`+
        `<div class="pct">${rows.length?Math.round(100*n/rows.length)+'% of sample':''}</div>`;
    }});
  }});
  html+=`</div>`;
  el.innerHTML=html;
  // legend swatches
  document.getElementById('lg-lo').style.background='rgb(31,42,56)';
  document.getElementById('lg-hi').style.background='rgb(110,168,254)';
}}

function renderDist(){{
  const el=document.getElementById('dist'); el.innerHTML='';
  const stars={{}}; run().rows.forEach(r=>stars[r.rating]=(stars[r.rating]||0)+1);
  const mx=Math.max(...Object.values(stars));
  for(const s of [1,2,3,4,5]){{
    const n=stars[s]||0;
    const row=document.createElement('div'); row.className='hbar-row';
    row.innerHTML=`<span class="lbl">${'★'.repeat(s)}</span>
      <div class="hbar-track"><div class="hbar-fill" style="width:${(n/mx)*100}%;background:var(--warn)"></div></div>
      <span class="num">${n}</span>`;
    el.appendChild(row);
  }}
}}

function renderEmotions(){{
  const rows=run().rows;
  const cnt=(key)=>{{ const o={{}}; rows.forEach(r=>{{ const v=r[key]||'none'; o[v]=(o[v]||0)+1; }}); return o; }};
  const l=cnt('llm_emotion'), n=cnt('nrc_emotion');
  const agree=rows.filter(r=>r.llm_emotion===r.nrc_emotion).length;
  const all=EMO.concat('none');
  function bars(o,parent,ticks){{
    const mx=Math.max(1,...all.map(e=>o[e]||0));
    parent.innerHTML='';
    ticks.innerHTML=all.map(e=>`<span title="${e}">${e}</span>`).join('');
    all.forEach(e=>{{
      const v=o[e]||0, b=document.createElement('div');
      b.className = e==='none' ? 'vbar vbar-none' : 'vbar';
      // zero-count columns get a faint stub so the axis is visible; real hits
      // get an accent bar whose height is proportional (min 6px so thin ones
      // never collapse to nothing).
      const h = v ? Math.max(v/mx*188, 6) : 6;
      b.style.height=h+'px';
      b.style.background = (e==='none' || v===0) ? 'var(--surface-2)' : 'var(--accent)';
      b.title=e+' · '+v;
      if(v) b.innerHTML=run().rows.length?`<span class="tl">${v}</span>`:'';
      parent.appendChild(b);
    }});
  }}
  bars(l, document.getElementById('emo_llm'), document.getElementById('emo_llm_ticks'));
  bars(n, document.getElementById('emo_nrc'), document.getElementById('emo_nrc_ticks'));
  const el=document.getElementById('emo_agree_pills');
  el.innerHTML=`<span class="pill">Both takers agree: ${agree}/${rows.length} (${Math.round(agree/rows.length*100)}%)</span>`+
    `<span class="pill">LLM chose "none": ${l.none||0}</span>`+
    `<span class="pill">Word list found no emotion words: ${n.none||0}</span>`;
}}

function esc(s){{ return (s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }}
function bad(c,p){{ return c===p; }}

function filteredRows(){{
  return run().rows.filter(r=>{{
    if(fCorrect==='correct' && !bad(r.correct,r.pred)) return false;
    if(fCorrect==='mismatch' && bad(r.correct,r.pred)) return false;
    if(fClass!=='all' && r.correct!==fClass) return false;
    if(fEmo!=='all' && r.llm_emotion!==fEmo && r.nrc_emotion!==fEmo) return false;
    if(fSearch && !((r.title||'')+' '+(r.text||'')).toLowerCase().includes(fSearch.toLowerCase())) return false;
    return true;
  }});
}}

function renderTable(){{
  let rows=filteredRows();
  rows.sort((a,b)=>{{
    let av=a[sortK], bv=b[sortK];
    if(sortK==='rating'||sortK==='conf'||sortK==='helpful'){{ av=av||0; bv=bv||0; return (av-bv)*sortDir; }}
    av=String(av||''); bv=String(bv||''); return av.localeCompare(bv)*sortDir;
  }});
  const tb=document.getElementById('tbody'); tb.innerHTML='';
  if(!rows.length){{ tb.innerHTML='<tr><td colspan="7" style="text-align:center;color:var(--muted)">No reviews match this filter.</td></tr>'; }}
  rows.forEach(r=>{{
    const ok=bad(r.correct,r.pred);
    const tr=document.createElement('tr'); tr.className='row';
    const stars='★'.repeat(Math.round(r.rating))||'';
    tr.innerHTML=`
      <td class="grid-star">${stars}</td>
      <td><span class="badge b-${r.correct[0].toLowerCase()}">${r.correct}</span></td>
      <td>${r.pred ? `<span class="badge b-${r.pred[0].toLowerCase()}">${r.pred}</span>` : '<span style="color:var(--muted)">—</span>'}</td>
      <td><span class="emo-tag">${esc(r.llm_emotion||'—')}</span> / <span class="emo-tag">${esc(r.nrc_emotion||'—')}</span></td>
      <td ${!ok?'class="incorrect"':''}>${r.conf!==null&&r.conf!==undefined?Math.round(r.conf*100)+'%':''}${ok?'':' ✗'}</td>
      <td><div class="truncate"><strong>${esc(r.title)}</strong></div>
          <div class="small truncate">${esc((r.text||'').slice(0,220))}${(r.text||'').length>220?'…':''}</div></td>
      <td>${r.helpful_vote||0}</td>`;
    tr.title='Click to expand/collapse full text';
    tr.style.cursor='pointer';
    tr.onclick=()=>{{
      const ex=tr.querySelector('.row-expand');
      if(ex) ex.remove();
      else {{ const d=document.createElement('div'); d.className='row-expand';
        d.textContent=(r.text||''); tr.querySelector('td:last-child').after?null:null;
        tr.querySelector('td:nth-child(6)').appendChild(d); }}
    }};
    tb.appendChild(tr);
  }});
  const total=run().rows.length;
  document.getElementById('countLine').textContent=`Showing ${rows.length} of ${total}`;
}}

function renderAll(){{ renderKpis(); renderClassAcc(); renderConfusion(); renderDist();
  renderEmotions(); renderTable(); }}

// populate emotion + class filter options once
EMO.forEach(e=>{{
  const o=document.createElement('option'); o.value=e; o.textContent=e; document.getElementById('emoFilter').appendChild(o);
}});
['POSITIVE','NEUTRAL','NEGATIVE'].forEach(c=>{{
  const o=document.createElement('option'); o.value=c; o.textContent=c; document.getElementById('classFilter').appendChild(o);
}});

// events
document.getElementById('segFilter').addEventListener('click',e=>{{
  const b=e.target.closest('button'); if(!b) return;
  fCorrect=b.dataset.f; document.querySelectorAll('#segFilter button').forEach(x=>x.classList.toggle('active',x===b));
  renderTable();
}});
document.getElementById('classFilter').onchange=e=>{{ fClass=e.target.value; renderTable(); }};
document.getElementById('emoFilter').onchange=e=>{{ fEmo=e.target.value; renderTable(); }};
document.getElementById('search').oninput=e=>{{ fSearch=e.target.value; renderTable(); }};
document.querySelectorAll('th').forEach(th=>{{
  th.onclick=()=>{{ const k=th.dataset.k; if(!k) return;
    if(sortK===k) sortDir*=-1; else {{ sortK=k; sortDir=-1; }} renderTable(); }};
}});

renderTabs(); renderAll();
</script>
</body>
</html>
"""


def build_runs_arg(args):
    """Turn --runs into {label: data}."""
    runs = {}
    for part in args.runs.split(";"):
        if not part.strip():
            continue
        label, path = part.split("=", 1)
        with open(path, "r", encoding="utf-8") as f:
            runs[label.strip()] = json.load(f)
    return runs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", required=True,
                    help="label=path;label=path for one or more saved run JSONs")
    ap.add_argument("--out", default="dashboard/index.html")
    args = ap.parse_args()

    runs = build_runs_arg(args)
    for label, data in runs.items():
        meta = data.get("meta", {})
        # guard: only include sentiment fields a two-class vs three-class run
        print(f"[{label}] classes={meta.get('labels')} rows={meta.get('n_rows')} "
              f"agreement={meta.get('agreement')}")

    run_json = json.dumps(runs, ensure_ascii=False).replace("</", "<\\/")
    title = "Amazon Review Classifier — Dashboard"
    # Fold doubled braces (the template body uses {{ }} because it is embedded
    # next to an f-string in this generator file) back to single braces first,
    # then substitute the JSON + title placeholders.
    html_page = TEMPLATE.replace("{{", "{").replace("}}", "}")
    html_page = (html_page
                 .replace("__RUNS__", run_json)
                 .replace("__EMO__", json.dumps(NRC_EMOTIONS))
                 .replace("{title}", title))
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(html_page)
    print(f"Wrote dashboard -> {args.out} ({len(html_page)/1024:.0f} KB)")


if __name__ == "__main__":
    main()
