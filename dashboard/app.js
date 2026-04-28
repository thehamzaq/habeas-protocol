// Habeas Protocol — dashboard renderer.
// Vanilla JS, hand-rolled SVG. No build step, no dependencies.

const JUDGMENTS_URLS = ['../data/judgments.json', 'data/judgments.json', '/data/judgments.json'];
const PRIMITIVES_URLS = ['../data/primitives.json', 'data/primitives.json', '/data/primitives.json'];

const PRIMITIVES = ['PR1', 'PR2', 'PR3', 'PR4', 'PR5', 'PR6'];

const PRIMITIVE_SHORT = {
  PR1: 'Identity',
  PR2: 'Evidence log',
  PR3: 'Rule bind',
  PR4: 'Procedure',
  PR5: 'Ruling',
  PR6: 'Enforcement bridge',
};

const TRIBUNALS = ['DIFC Courts', 'ADGM Courts', 'Singapore International Commercial Court'];

const TRIBUNAL_SHORT = {
  'DIFC Courts': 'DIFC',
  'ADGM Courts': 'ADGM',
  'Singapore International Commercial Court': 'SICC',
};

const TRACES = [
  {
    n: 1,
    title: 'Pure formula',
    case_no: 'CFI 058/2024 — Atul Dhawan v Ramzi El Jaouhari',
    rule: 'RDC Part 38 standard-basis costs assessment: hours × rate + filing fee.',
    result: 'Predicate computes <strong>AED 7,121.75</strong>, matches the Schedule of Reasons exactly.',
    finding: 'The operative paragraph states AED 7,127.75 — a 6 AED gap. The protocol mechanically surfaces a clerical error a human reader would skim past.',
    path: '../spike/trace-01/',
  },
  {
    n: 2,
    title: 'Deferred conditional',
    case_no: 'ARB 008/2026 — Oberlin v Ovidiu',
    rule: 'RDC 38.40 + Practice Direction No. 4 of 2017: 14-day payment window, 9% p.a. interest if missed, computed retroactively from the date of the order.',
    result: 'Five scenarios pass — on-time, at-deadline, 1 / 61 / 92 days late. Unpaid 92 days → <strong>AED 78,527.69</strong> owed.',
    finding: 'The 80% discretion + 14-day deadline + 9% interest structure recurs verbatim across adjacent DIFC arbitration costs orders. The protocol codifies the near-formula once.',
    path: '../spike/trace-02/',
  },
  {
    n: 3,
    title: 'Bounded discretion',
    case_no: 'ENF 271/2025 — Taylor v Yao Affi',
    rule: 'Indemnity-basis costs review (Cooke J., §2): only reasonableness, no proportionality.',
    result: 'Predicate triages each objection: 1 mechanically disposed, 1 held to zero on evidence, 1 surfaced as bounded-discretion residue.',
    finding: 'The court reduced AED 128,914.80 → AED 120,000. The <strong>AED 8,914.80 (~6.92%)</strong> reduction is the structured-discretion residue. The protocol bounds, but does not eliminate, that residue.',
    path: '../spike/trace-03/',
  },
  {
    n: 4,
    title: 'Composition over findings',
    case_no: 'ADGMCFI-2024-320 — Projeco v Ideacrate',
    rule: 'Substantive contract dispute. UAE Civil Transactions Law Art. 390 (LDs cap) + ADGM CPR r.42 (admissions) + ADGM Civil Evidence Regs §§181-182 (set-off). Rule arithmetically composes multiple substantive findings.',
    result: 'Predicate takes human findings (97 days delay, items proven, scope determinations) as inputs; composes LDs cap → counterclaim set-off → net principal → pre-judgment interest. Net principal <strong>AED 10,500.96</strong> matches the court exactly.',
    finding: 'Pre-judgment interest at calendar 609 days = AED 876.04; court used inclusive-endpoint 610 days = AED 877.48 (delta AED 1.44). Protocol surfaces the daycount convention question, parallel to Trace #1\'s clerical error finding. Substantive contract dispute decomposes cleanly into human-judgment inputs and deterministic arithmetic composition.',
    path: '../spike/trace-04/',
  },
];

let judgments = [];
let primitives = null;

async function fetchFirst(urls) {
  for (const url of urls) {
    try {
      const r = await fetch(url);
      if (r.ok) return r.json();
    } catch (e) { /* try next */ }
  }
  return null;
}

async function load() {
  judgments = await fetchFirst(JUDGMENTS_URLS);
  primitives = await fetchFirst(PRIMITIVES_URLS);
  if (!judgments || !primitives) {
    document.body.insertAdjacentHTML('afterbegin',
      '<div style="padding:20px;background:#fee;border:1px solid #c33;color:#900;font-family:sans-serif">' +
      '<strong>Could not load data files.</strong> Run <code>python3 -m http.server</code> from the <code>habeas-protocol/</code> directory (not from inside <code>dashboard/</code>).' +
      '</div>');
    return;
  }
  renderStats();
  renderPrimitivesTable();
  renderHeatmaps();
  renderMeanComparison();
  renderSystemProps();
  renderRules();
  renderTraces();
  renderJudgmentsTable();
}

function set(id, v) { document.getElementById(id).textContent = v; }

function meanScore(j) {
  const s = j.primitive_scores_v02;
  let total = 0;
  PRIMITIVES.forEach(p => { total += s[p]; });
  return total / PRIMITIVES.length;
}

function tribunalMean(t, p) {
  const slice = judgments.filter(j => j.tribunal === t);
  return slice.reduce((sum, j) => sum + j.primitive_scores_v02[p], 0) / slice.length;
}

function renderStats() {
  const difc = judgments.filter(j => j.tribunal === 'DIFC Courts');
  const adgm = judgments.filter(j => j.tribunal === 'ADGM Courts');
  const sicc = judgments.filter(j => j.tribunal === 'Singapore International Commercial Court');
  const gold = judgments.filter(j => j.coding && j.coding.gold_set);
  set('totalJudgments', judgments.length);
  set('goldSet', gold.length);
  set('difcCount', difc.length);
  set('adgmCount', adgm.length);
  set('siccCount', sicc.length);
  const flat = (rows) => rows.flatMap(j => PRIMITIVES.map(p => j.primitive_scores_v02[p]));
  const meanOf = (arr) => arr.length ? (arr.reduce((a,b)=>a+b,0) / arr.length).toFixed(2) : '—';
  set('difcMean', meanOf(flat(difc)));
  set('adgmMean', meanOf(flat(adgm)));
  set('siccMean', meanOf(flat(sicc)));
}

function renderPrimitivesTable() {
  const tbody = document.querySelector('#primitivesTable tbody');
  tbody.innerHTML = '';
  primitives.per_ruling_primitives.forEach(p => {
    const tr = document.createElement('tr');
    tr.innerHTML = `<td><strong>${p.id}</strong></td><td>${escape(p.name)}</td><td>${escape(p.definition)}</td>`;
    tbody.appendChild(tr);
  });
}

function heatColor(v) {
  if (v === 2) return 'var(--heat-2)';
  if (v === 1) return 'var(--heat-1)';
  return 'var(--heat-0)';
}

function renderHeatmaps() {
  const difc = judgments.filter(j => j.tribunal === 'DIFC Courts');
  const adgm = judgments.filter(j => j.tribunal === 'ADGM Courts');
  const sicc = judgments.filter(j => j.tribunal === 'Singapore International Commercial Court');
  drawHeatmap('heatmapDIFC', difc, `DIFC Courts (n=${difc.length})`);
  drawHeatmap('heatmapADGM', adgm, `ADGM Courts (n=${adgm.length})`);
  drawHeatmap('heatmapSICC', sicc, `Singapore International Commercial Court (n=${sicc.length})`);
}

function drawHeatmap(id, rows, panelTitle) {
  const target = document.getElementById(id);
  target.innerHTML = '';
  const labelW = 220;
  const colW = 70;
  const cellH = 18;
  const headerH = 50;
  const w = labelW + colW * PRIMITIVES.length + 24;
  const h = headerH + rows.length * cellH + 12;

  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('viewBox', `0 0 ${w} ${h}`);
  svg.setAttribute('preserveAspectRatio', 'xMinYMin meet');

  // panel title
  const pt = document.createElementNS('http://www.w3.org/2000/svg', 'text');
  pt.setAttribute('x', 0); pt.setAttribute('y', 14); pt.setAttribute('class', 'panel-title');
  pt.textContent = panelTitle;
  svg.appendChild(pt);

  // column headers
  PRIMITIVES.forEach((p, i) => {
    const x = labelW + i * colW + colW / 2;
    const t = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    t.setAttribute('x', x); t.setAttribute('y', headerH - 22);
    t.setAttribute('text-anchor', 'middle');
    t.setAttribute('class', 'heat-label-col');
    t.textContent = p;
    svg.appendChild(t);
    const sub = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    sub.setAttribute('x', x); sub.setAttribute('y', headerH - 8);
    sub.setAttribute('text-anchor', 'middle');
    sub.setAttribute('class', 'heat-label-row');
    sub.textContent = PRIMITIVE_SHORT[p];
    svg.appendChild(sub);
  });

  // rows
  rows.forEach((j, i) => {
    const y = headerH + i * cellH;
    const lbl = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    lbl.setAttribute('x', labelW - 10);
    lbl.setAttribute('y', y + cellH / 2);
    lbl.setAttribute('dominant-baseline', 'central');
    lbl.setAttribute('class', 'heat-label-row');
    lbl.textContent = j.case_no;
    svg.appendChild(lbl);

    PRIMITIVES.forEach((p, c) => {
      const v = j.primitive_scores_v02[p];
      const x = labelW + c * colW;
      const r = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
      r.setAttribute('x', x + 1);
      r.setAttribute('y', y + 1);
      r.setAttribute('width', colW - 2);
      r.setAttribute('height', cellH - 2);
      r.setAttribute('class', 'heat-cell');
      r.setAttribute('fill', heatColor(v));
      svg.appendChild(r);
    });
  });

  target.appendChild(svg);
}

function renderMeanComparison() {
  const target = document.getElementById('meanComparison');
  target.innerHTML = '';
  const w = 800;
  const labelW = 200;
  const valW = 60;
  const rowH = 60;
  const groupGap = 3;
  const max = 2.0;
  const h = PRIMITIVES.length * rowH + 24;

  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('viewBox', `0 0 ${w} ${h}`);
  svg.setAttribute('preserveAspectRatio', 'xMinYMid meet');
  const barAreaW = w - labelW - valW - 32;

  const tribClasses = ['bar-difc', 'bar-adgm', 'bar-sicc'];

  PRIMITIVES.forEach((p, i) => {
    const y = i * rowH + 10;
    const t = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    t.setAttribute('x', labelW - 10);
    t.setAttribute('y', y + rowH / 2);
    t.setAttribute('text-anchor', 'end');
    t.setAttribute('dominant-baseline', 'central');
    t.setAttribute('class', 'bar-label');
    t.textContent = `${p} ${PRIMITIVE_SHORT[p]}`;
    svg.appendChild(t);

    const barH = (rowH - 8 - groupGap * 2) / TRIBUNALS.length;
    TRIBUNALS.forEach((trib, ti) => {
      const m = tribunalMean(trib, p);
      const by = y + 4 + ti * (barH + groupGap);
      const r = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
      r.setAttribute('x', labelW); r.setAttribute('y', by);
      r.setAttribute('width', Math.max((m / max) * barAreaW, 1));
      r.setAttribute('height', barH);
      r.setAttribute('class', tribClasses[ti]);
      svg.appendChild(r);
      const v = document.createElementNS('http://www.w3.org/2000/svg', 'text');
      v.setAttribute('x', labelW + (m / max) * barAreaW + 6);
      v.setAttribute('y', by + barH / 2);
      v.setAttribute('dominant-baseline', 'central');
      v.setAttribute('class', 'bar-value');
      v.textContent = m.toFixed(2);
      svg.appendChild(v);
    });
  });

  target.appendChild(svg);

  const legend = document.createElement('div');
  legend.className = 'legend-row';
  legend.innerHTML = `
    <span><span class="legend-swatch" style="background:var(--bar-difc)"></span>DIFC Courts</span>
    <span><span class="legend-swatch" style="background:var(--bar-adgm)"></span>ADGM Courts</span>
    <span><span class="legend-swatch" style="background:var(--bar-sicc)"></span>SICC</span>
  `;
  target.appendChild(legend);
}

function renderSystemProps() {
  const tbody = document.querySelector('#systemPropsTable tbody');
  tbody.innerHTML = '';
  const tribs = ['DIFC Courts', 'ADGM Courts', 'Singapore International Commercial Court', 'VARA', 'Próspera Arbitration Center', 'ad-hoc Web3 arbitration (Kleros)'];
  const sp1 = primitives.system_properties[0].tribunal_score;
  const sp2 = primitives.system_properties[1].tribunal_score;
  tribs.forEach(t => {
    const tr = document.createElement('tr');
    tr.innerHTML = `<td>${escape(t)}</td><td class="num">${sp1[t] ?? '—'}</td><td class="num">${sp2[t] ?? '—'}</td>`;
    tbody.appendChild(tr);
  });
}

function renderRules() {
  const counts = {};
  judgments.forEach(j => (j.rules_cited || []).forEach(r => { counts[r] = (counts[r] || 0) + 1; }));
  const data = Object.entries(counts).sort((a, b) => b[1] - a[1]).slice(0, 14);
  drawHBar('rulesChart', data, { maxValue: Math.max(...data.map(d => d[1])) });
}

function drawHBar(targetId, data, opts = {}) {
  const target = document.getElementById(targetId);
  target.innerHTML = '';
  const rowH = 26;
  const labelW = 320;
  const valueW = 50;
  const w = 800;
  const barAreaW = w - labelW - valueW - 24;
  const h = data.length * rowH + 16;
  const max = opts.maxValue || Math.max(...data.map(d => d[1]));
  const formatValue = opts.formatValue || (v => Math.round(v).toString());

  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('viewBox', `0 0 ${w} ${h}`);
  svg.setAttribute('preserveAspectRatio', 'xMinYMid meet');

  data.forEach(([label, val], i) => {
    const y = i * rowH + 8;
    const barW = (val / max) * barAreaW;

    const t = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    t.setAttribute('x', labelW - 10);
    t.setAttribute('y', y + rowH / 2);
    t.setAttribute('text-anchor', 'end');
    t.setAttribute('dominant-baseline', 'central');
    t.setAttribute('class', 'bar-label');
    t.textContent = label;
    svg.appendChild(t);

    const r = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
    r.setAttribute('x', labelW);
    r.setAttribute('y', y + 4);
    r.setAttribute('width', Math.max(barW, 1));
    r.setAttribute('height', rowH - 12);
    r.setAttribute('class', opts.accentTop && i === 0 ? 'bar-accent' : 'bar');
    svg.appendChild(r);

    const v = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    v.setAttribute('x', labelW + barW + 6);
    v.setAttribute('y', y + rowH / 2);
    v.setAttribute('dominant-baseline', 'central');
    v.setAttribute('class', 'bar-value');
    v.textContent = formatValue(val);
    svg.appendChild(v);
  });

  target.appendChild(svg);
}

function renderTraces() {
  const grid = document.getElementById('tracesGrid');
  grid.innerHTML = '';
  TRACES.forEach(t => {
    const div = document.createElement('div');
    div.className = 'trace';
    div.innerHTML = `
      <div class="trace-num">Trace #${t.n} · ${escape(t.title)}</div>
      <div class="trace-title">${escape(t.title)}</div>
      <div class="trace-case">${escape(t.case_no)}</div>
      <div class="trace-rule">${escape(t.rule)}</div>
      <div class="trace-result">${t.result}</div>
      <div class="trace-finding">${t.finding}</div>
    `;
    grid.appendChild(div);
  });
}

function renderJudgmentsTable() {
  const claimSet = new Set(judgments.map(j => j.claim_type).filter(Boolean));
  const claimSel = document.getElementById('claimFilter');
  Array.from(claimSet).sort().forEach(c => {
    const o = document.createElement('option'); o.value = c; o.textContent = c.replace(/_/g, ' ');
    claimSel.appendChild(o);
  });

  const draw = () => {
    const q = document.getElementById('searchBox').value.toLowerCase();
    const trib = document.getElementById('tribunalFilter').value;
    const claim = claimSel.value;
    const tbody = document.querySelector('#judgmentsTable tbody');
    tbody.innerHTML = '';

    judgments
      .slice()
      .sort((a, b) => (b.date_issued || '').localeCompare(a.date_issued || ''))
      .filter(j => {
        if (trib && j.tribunal !== trib) return false;
        if (claim && j.claim_type !== claim) return false;
        if (q) {
          const blob = `${j.case_no} ${j.tribunal} ${j.judge || ''} ${(j.parties && j.parties.claimant) || ''} ${(j.parties && j.parties.defendant) || ''} ${(j.rules_cited || []).join(' ')}`.toLowerCase();
          if (!blob.includes(q)) return false;
        }
        return true;
      })
      .forEach(j => {
        const m = meanScore(j);
        const s = j.primitive_scores_v02;
        const cells = PRIMITIVES.map(p => `<td class="num">${s[p]}</td>`).join('');
        const tribClass =
          j.tribunal === 'DIFC Courts' ? 'tag-difc' :
          j.tribunal === 'ADGM Courts' ? 'tag-adgm' : 'tag-sicc';
        const tribShort = TRIBUNAL_SHORT[j.tribunal] || j.tribunal;
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td><strong>${escape(j.case_no)}</strong><br><span class="muted" style="font-size:12px">${escape((j.parties && j.parties.claimant) || '')} v ${escape((j.parties && j.parties.defendant) || '')}</span></td>
          <td><span class="tag ${tribClass}">${tribShort}</span></td>
          <td>${escape(j.date_issued || '—')}</td>
          <td>${escape(j.judge || '—')}</td>
          <td class="num">${m.toFixed(2)}</td>
          ${cells}
        `;
        tbody.appendChild(tr);
      });
  };

  document.getElementById('searchBox').addEventListener('input', draw);
  document.getElementById('tribunalFilter').addEventListener('change', draw);
  claimSel.addEventListener('change', draw);
  draw();
}

function escape(s) {
  return String(s ?? '').replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
}

load();
