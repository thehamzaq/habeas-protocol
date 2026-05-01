// Habeas Protocol — dashboard renderer.
// Vanilla JS, hand-rolled SVG. No build step, no dependencies.

// Try the local read-only API first (api/server.py — Postgres-backed).
// If it isn't running, fall back to the static JSON file. The static fallback
// is what the public GitHub Pages build uses, since it can't run a server.
const JUDGMENTS_URLS = [
  'http://127.0.0.1:5544/api/judgments',
  '/api/judgments',
  '../data/judgments.json',
  'data/judgments.json',
  '/data/judgments.json',
];
const PRIMITIVES_URLS = ['../data/primitives.json', 'data/primitives.json', '/data/primitives.json'];

let dataSource = 'unknown';

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
    outputs: [
      { label: 'professional_time_aed', computed: '6,000.00', court: '6,000.00', match: true },
      { label: 'disbursements_aed',     computed: '1,121.75', court: '1,121.75', match: true },
      { label: 'total_aed (computed)',  computed: '7,121.75', court: '7,121.75', match: true, note: 'matches Schedule of Reasons total' },
      { label: 'operative paragraph',   computed: '7,121.75', court: '7,127.75', match: false, note: '6 AED clerical gap surfaced — predicate ≠ operative',
        divergence: {
          kind: 'clerical',
          delta_label: 'AED 6.00',
          delta_signed: 6.00,
          delta_pct: 0.084,
          interpretation: 'Schedule of Reasons sums to AED 7,121.75; operative paragraph reads AED 7,127.75. The two figures appear in the same judgment — a transcription drift the predicate flags mechanically.',
        } },
    ],
    catala_cmd: 'catala interpret --no-stdlib --scope=TestDhawan rule.catala_en',
    catala_run: `┌─[RESULT]─ TestDhawan ─
│ award =
│   CostsAward {
│     -- professional_time_aed: 6,000.0
│     -- disbursements_aed: 1,121.75
│     -- total_aed: 7,121.75
│   }
└─`,
  },
  {
    n: 2,
    title: 'Deferred conditional',
    case_no: 'ARB 008/2026 — Oberlin v Ovidiu',
    rule: 'RDC 38.40 + Practice Direction No. 4 of 2017: 14-day payment window, 9% p.a. interest if missed, computed retroactively from the date of the order.',
    result: 'Five scenarios pass — on-time, at-deadline, 1 / 61 / 92 days late. Unpaid 92 days → <strong>AED 78,527.69</strong> owed.',
    finding: 'The 80% discretion + 14-day deadline + 9% interest structure recurs verbatim across adjacent DIFC arbitration costs orders. The protocol codifies the near-formula once.',
    path: '../spike/trace-02/',
    outputs: [
      { label: 'paid on time (08-Apr-2026)',     computed: 'in_breach=false, owed=76,785.81',     court: 'no interest accrued', match: true },
      { label: 'at deadline (09-Apr-2026)',      computed: 'in_breach=false, owed=76,785.81',     court: 'no interest accrued', match: true },
      { label: 'unpaid 1 day (10-Apr-2026)',     computed: 'in_breach=true, days=15, owed=77,069.74',  court: '15 days × 9% p.a.', match: true },
      { label: 'unpaid 61 days (26-May-2026)',   computed: 'in_breach=true, days=61, owed=77,940.75',  court: '61 days × 9% p.a.', match: true },
      { label: 'unpaid 92 days (26-Jun-2026)',   computed: 'in_breach=true, days=92, owed=78,527.69',  court: '92 days × 9% p.a.', match: true },
    ],
    catala_cmd: 'catala interpret --no-stdlib --scope=TestOberlinPaidOnTime rule.catala_en\ncatala interpret --no-stdlib --scope=TestOberlinUnpaid61Days rule.catala_en',
    catala_run: `┌─[RESULT]─ TestOberlinPaidOnTime ─
│ owed =
│   AmountOwed {
│     -- deadline: 2026-04-09
│     -- in_breach: false
│     -- days_accrued: 0.0
│     -- interest_accrued_aed: 0.0
│     -- total_owed_aed: 76,785.81
│   }
└─

┌─[RESULT]─ TestOberlinUnpaid61Days ─
│ owed =
│   AmountOwed {
│     -- deadline: 2026-04-09
│     -- in_breach: true
│     -- days_accrued: 61.0
│     -- interest_accrued_aed: 1,154.942,731,232,876,712,3…
│     -- total_owed_aed: 77,940.752,731,232,876,712…
│   }
└─`,
  },
  {
    n: 3,
    title: 'Bounded discretion',
    case_no: 'ENF 271/2025 — Taylor v Yao Affi',
    rule: 'Indemnity-basis costs review (Cooke J., §2): only reasonableness, no proportionality.',
    result: 'Predicate triages each objection: 1 mechanically disposed, 1 held to zero on evidence, 1 surfaced as bounded-discretion residue.',
    finding: 'The court reduced AED 128,914.80 → AED 120,000. The <strong>AED 8,914.80 (~6.92%)</strong> reduction is the structured-discretion residue. The protocol bounds, but does not eliminate, that residue.',
    path: '../spike/trace-03/',
    outputs: [
      { label: 'objection 1 (claimant did work himself)',          computed: 'mechanically disposed — non-specific',     court: 'rejected (Cooke J., §4)', match: true },
      { label: 'objection 2 (double counsel for hearing)',         computed: 'held to zero on evidence',                  court: 'rejected (Cooke J., §3)', match: true },
      { label: 'objection 3 (excess senior associate time)',       computed: 'flagged: requires_human_judgment',          court: 'reduction applied (Cooke J., §5)', match: true, note: 'protocol flags but cannot quantify' },
      { label: 'deterministic_reductions_aed',                     computed: '0.00',                                      court: 'no rule-derivable reduction',  match: true },
      { label: 'discretion residue (claim − awarded)',             computed: 'AED 8,914.80 (≈6.92%)',                     court: 'AED 8,914.80',                 match: true, note: 'the irreducible human-judgment residue' },
    ],
    catala_cmd: 'catala interpret --no-stdlib --scope=TestTaylor rule.catala_en',
    catala_run: `┌─[RESULT]─ TestTaylor ─
│ review =
│   ReviewOutcome {
│     -- mechanically_disposed_aed: 0.0
│     -- deterministic_reductions_aed: 0.0
│     -- residual_discretion_lower_aed: 0.0
│     -- residual_discretion_upper_aed: 128,914.8
│     -- requires_human_judgment: true
│   }
└─`,
  },
  {
    n: 4,
    title: 'Composition over findings',
    case_no: 'ADGMCFI-2024-320 — Projeco v Ideacrate',
    rule: 'Substantive contract dispute. UAE Civil Transactions Law Art. 390 (LDs cap) + ADGM CPR r.42 (admissions) + ADGM Civil Evidence Regs §§181-182 (set-off). Rule arithmetically composes multiple substantive findings.',
    result: 'Predicate takes human findings (97 days delay, items proven, scope determinations) as inputs; composes LDs cap → counterclaim set-off → net principal → pre-judgment interest. Net principal <strong>AED 10,500.96</strong> matches the court exactly.',
    finding: 'Pre-judgment interest at calendar 609 days = AED 876.04; court used inclusive-endpoint 610 days = AED 877.48 (delta AED 1.44). Protocol surfaces the daycount convention question, parallel to Trace #1\'s clerical error finding. Substantive contract dispute decomposes cleanly into human-judgment inputs and deterministic arithmetic composition.',
    path: '../spike/trace-04/',
    outputs: [
      { label: 'ld_was_capped',          computed: 'true',         court: 'true (10% cap applied)',     match: true },
      { label: 'ld_awarded_aed',         computed: '608,521.19',   court: '608,521.19',                 match: true },
      { label: 'counterclaim_sum_aed',   computed: '755,786.19',   court: '755,786.19',                 match: true },
      { label: 'net_to_claimant_aed',    computed: '10,500.96',    court: '10,500.96',                  match: true, note: 'principal matches court exactly' },
      { label: 'pre-judgment interest',  computed: 'AED 876.04 (609 calendar days)', court: 'AED 877.48 (610 inclusive-endpoint days)', match: false, note: 'daycount convention surfaced — protocol vs court',
        divergence: {
          kind: 'daycount',
          delta_label: 'AED 1.44',
          delta_signed: 1.44,
          delta_pct: 0.164,
          interpretation: 'Predicate uses calendar days (filing → judgment exclusive of endpoints); court used inclusive-endpoint count adding one day. Identical methodology, different convention — surfacing it makes the convention itself a contestable parameter rather than an unstated assumption.',
        } },
    ],
    catala_cmd: 'catala interpret --no-stdlib --scope=TestProjeco rule.catala_en',
    catala_run: `┌─[RESULT]─ TestProjeco ─
│ disposition =
│   Disposition {
│     -- ld_uncapped_aed: 9,700,000.0
│     -- ld_cap_aed: 608,521.19
│     -- ld_awarded_aed: 608,521.19
│     -- ld_was_capped: true
│     -- counterclaim_sum_aed: 755,786.19
│     -- net_to_claimant_aed: 10,500.96
│     -- days_to_judgment: 609.0
│     -- interest_aed: 876.038,991,780,821,917,80…
│     -- total_judgment_aed: 11,376.998,991,780,821,917…
│   }
└─`,
  },
  {
    n: 5,
    title: 'Conjunctive logical composition',
    case_no: 'ADGMCFI-2024-158 — Xetech v Pulsar',
    rule: 'Software-development contract dispute. English contractual interpretation (Wood v Capita / Rainy Sky / Arnold v Britton) + Ladd v Marshall 3-prong admissibility test + Assignment Agreement clauses 2(b), 7, 10. Rule is structurally Boolean, not arithmetic.',
    result: 'Predicate composes three conjunctive tests: clause alignment (3/3 point to payment-before-transfer), named-witness preponderance (6:2, both dissenters lacked DevOps access), Ladd v Marshall (fails on prong (a) — short-circuits). Judgment Sum <strong>GBP 409,870</strong>, costs <strong>USD 125,483.84</strong>, counterclaim dismissed — all match exactly.',
    finding: 'First trace whose rule is conjunctive Boolean composition rather than arithmetic. The protocol does not replace contractual interpretation, witness credibility, or document availability — it makes the *logical structure* of those determinations auditable. Even contract-interpretation reasoning has a verifiable structural skeleton.',
    path: '../spike/trace-05/',
    outputs: [
      { label: 'clauses_aligned (2(b), 7, 10)',  computed: 'true (3/3 point to payment-first)',  court: 'true (paras 59-60)',  match: true },
      { label: 'completion_proven',              computed: 'true (6 supporters vs 2 dissenters)', court: 'true (para 92)',     match: true, note: 'both dissenters lacked DevOps access' },
      { label: 'new_evidence_admissible',        computed: 'false — fails prong (a)',             court: 'false (para 49)',    match: true, note: 'Ladd v Marshall short-circuits on diligence' },
      { label: 'judgment_sum_gbp',               computed: '409,870.00',                          court: '409,870.00',         match: true },
      { label: 'costs_usd',                      computed: '125,483.84',                          court: '125,483.84',         match: true },
      { label: 'counterclaim_dismissed',         computed: 'true',                                court: 'true (paras 96, 99)', match: true },
    ],
    catala_cmd: 'catala interpret --no-stdlib --scope=TestXetech rule.catala_en',
    catala_run: `┌─[RESULT]─ TestXetech ─
│ disposition =
│   Disposition {
│     -- clauses_aligned: true
│     -- interpretation_holding: XetechEntitledBeforeTransfer
│     -- completion_proven: true
│     -- supporters_count: 6
│     -- dissenters_count: 2
│     -- new_evidence_admissible: false
│     -- judgment_sum_gbp: 409,870.0
│     -- costs_usd: 125,483.84
│     -- counterclaim_dismissed: true
│   }
└─`,
  },
  {
    n: 6,
    title: 'Partial statutory refusal (cross-tribunal)',
    case_no: 'SIC/OA 9/2025 — GNC Holdings v ONI Global',
    rule: 'NY Convention recognition of a foreign arbitral award under Singapore IAA s 31. Four enumerated grounds for refusing enforcement (s 31(2)(c) natural justice, s 31(2)(d) outside scope, s 31(4)(b) public policy), plus the DKT v DKU four-condition framework for "infra petita" natural-justice challenges. Rule is Boolean disjunction over the grounds, with a per-paragraph excision list for the partial-refusal case.',
    result: 'Predicate evaluates each of the four pleaded grounds, then computes the application disposition and which sub-paragraphs of the Tribunal\'s Order 3 are excised. Disposition <strong>ApplicationAllowedInPart</strong>; three of nine paragraphs of Order 3 not enforced — exactly matches para 185(a)-(c).',
    finding: 'First SICC trace and first to express a *partial* refusal of enforcement. Excises Order 3(d)(ii), Order 3(d)(iii), Order 3(f) — the sub-paragraphs the Tribunal did not put to the parties for submission on their specific terms (paras 103-105). The protocol crosses legal-family boundaries: the rule of decision is Singapore IAA + NY Convention, methodologically distinct from the English-law-via-statute reasoning of the DIFC/ADGM traces.',
    path: '../spike/trace-06/',
    outputs: [
      { label: 'n_grounds_pleaded',         computed: '4',                          court: '4',                          match: true },
      { label: 'n_grounds_dismissed',       computed: '3 (G1, G2, G3)',             court: '3',                          match: true, note: 'public policy, natural justice, outside-scope (damages)' },
      { label: 'n_grounds_partial',         computed: '1 (G4)',                     court: '1 — para 107',               match: true, note: 'Order 3 sub-paragraphs not put to parties' },
      { label: 'application_disposition',   computed: 'ApplicationAllowedInPart',   court: 'allowed in part — para 185(a)', match: true },
      { label: 'paragraphs_excised',        computed: '3: (d)(ii), (d)(iii), (f)',  court: '3 — para 185(b)',            match: true, note: 'natural-justice excision under DKT v DKU framework' },
      { label: 'award_enforced (varied)',   computed: 'true',                       court: 'true — para 185(c)',         match: true },
    ],
    catala_cmd: 'catala interpret --no-stdlib spike/trace-06/rule.catala_en',
    catala_run: `┌─[RESULT]─ TestGNCHoldings ─
│ disposition =
│   Disposition {
│     -- n_grounds_pleaded: 4
│     -- n_grounds_dismissed: 3
│     -- n_grounds_partial: 1
│     -- n_grounds_full: 0
│     -- application_disposition: ApplicationAllowedInPart
│     -- award_enforced: true
│     -- n_paras_excised: 3
│   }
│ enforced_paras = [Para_a; Para_b; Para_c; Para_d_i; Para_e; Para_g]
│ excised_paras = [Para_d_ii; Para_d_iii; Para_f]
└─`,
  },
  {
    n: 7,
    title: 'Third-party-jurisdiction gate (DIFC Digital Economy Court)',
    case_no: 'DEC 001/2025 — Techteryx v IG (and others)',
    rule: 'Norwich Pharmacal + Bankers Trust + RDC 28.52 third-party disclosure. The Court extends its jurisdiction to a non-party financial institution to compel production of account statements and onward-transaction records, exercising the powers in DIFC Courts Law Articles 15(1) + 24(D), DIFC Damages Law Article 36, and RDC 25.1(10) / 28.51-52. Three independent conjunctive jurisdictional gates — all must be made out.',
    result: 'Predicate evaluates each of three gates over their conjunctive elements: Norwich Pharmacal (4/4 elements), Bankers Trust (3/3 elements), RDC 28.52 (2/2 conditions). All gates satisfied → <strong>order granted in full</strong> against four IG respondents, with an agreed 14-day window for confirmations and 21-day window for document production — exactly matching Black KC\'s order at para 24.',
    finding: 'First trace in DIFC\'s <em>Digital Economy Court</em> and the first to encode a third-party-jurisdiction gate over a digital-asset dispute (USD 456 million in stablecoin reserves, allegedly misappropriated; USD 46 million traced onward to IG Accounts). Methodologically distinct from earlier traces because the predicate is not the substantive merits — it\'s the structural conditions for the Court to reach over to a non-party. On-thesis: the tribunal already exists; the rule of decision is auditable.',
    path: '../spike/trace-07/',
    outputs: [
      { label: 'nph_made_out (4/4 elements)',          computed: 'true',  court: 'true — para 23',     match: true,  note: 'wrong + mixed-up + possesses-info + necessary-in-interests-of-justice' },
      { label: 'bankers_trust_made_out (3/3)',         computed: 'true',  court: 'true — para 23',     match: true,  note: 'tracing claim asserted; IG holds traceable proceeds; disclosure necessary' },
      { label: 'rdc_2852_made_out (2/2)',              computed: 'true',  court: 'true — para 22',     match: true,  note: 'documents likely to support; production necessary to dispose / save costs' },
      { label: 'all_gates_satisfied',                  computed: 'true',  court: 'true — para 24',     match: true,  note: 'three gates conjunctive — granted only if all satisfied' },
      { label: 'order_granted',                        computed: 'true',  court: 'true — para 24',     match: true },
      { label: 'n_respondents',                        computed: '4',     court: '4',                  match: true,  note: 'IG Limited + IG Markets + IG Index + IG Trading and Investments' },
      { label: 'n_respondents_opposing_substance',     computed: '0',     court: '0 — Fisher WS',      match: true,  note: '"IG Respondents do not oppose the substance" — only confidentiality concerns absent a Court Order' },
      { label: 'information_window_days',              computed: '14',    court: '14 — para 24(1)',    match: true },
      { label: 'documents_window_days',                computed: '21',    court: '21 — para 24(2)',    match: true,  note: 'extended from initial 14d to 21d for transaction-volume reasons; modification agreed at para 19' },
    ],
    catala_cmd: 'catala interpret --no-stdlib spike/trace-07/rule.catala_en',
    catala_run: `┌─[RESULT]─ TestTechteryxVIG ─
│ order =
│   DisclosureOrder {
│     -- nph_made_out: true
│     -- bankers_trust_made_out: true
│     -- rdc_2852_made_out: true
│     -- all_gates_satisfied: true
│     -- order_granted: true
│     -- n_respondents: 4
│     -- n_respondents_opposing_substance: 0
│     -- information_window_days: 14.0
│     -- documents_window_days: 21.0
│   }
└─`,
  },
];

let judgments = [];
let primitives = null;

async function fetchFirst(urls) {
  for (const url of urls) {
    try {
      const r = await fetch(url);
      if (r.ok) {
        const data = await r.json();
        return { data, url };
      }
    } catch (e) { /* try next */ }
  }
  return { data: null, url: null };
}

function classifySource(url) {
  if (!url) return 'none';
  if (url.includes('/api/judgments')) return 'api';
  return 'static';
}

async function load() {
  const j = await fetchFirst(JUDGMENTS_URLS);
  const p = await fetchFirst(PRIMITIVES_URLS);
  judgments = j.data;
  primitives = p.data;
  dataSource = classifySource(j.url);
  document.body.dataset.source = dataSource;
  const badge = document.getElementById('sourceBadge');
  if (badge) {
    if (dataSource === 'api') {
      badge.textContent = '· live (Postgres)';
      badge.title = `Loaded ${(judgments || []).length} judgments from ${j.url}`;
    } else if (dataSource === 'static') {
      badge.textContent = '· static';
      badge.title = `Loaded ${(judgments || []).length} judgments from ${j.url}`;
    }
  }
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
  renderTraceViewer();
  renderConventionDivergences();
  renderAuditPanel();
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
  if (!document.getElementById('heatmapDIFC')) return;
  const difc = judgments.filter(j => j.tribunal === 'DIFC Courts');
  const adgm = judgments.filter(j => j.tribunal === 'ADGM Courts');
  const sicc = judgments.filter(j => j.tribunal === 'Singapore International Commercial Court');
  drawHeatmap('heatmapDIFC', difc, `DIFC Courts (n=${difc.length})`);
  drawHeatmap('heatmapADGM', adgm, `ADGM Courts (n=${adgm.length})`);
  drawHeatmap('heatmapSICC', sicc, `Singapore International Commercial Court (n=${sicc.length})`);
}

function drawHeatmap(id, rows, panelTitle) {
  const target = document.getElementById(id);
  if (!target) return;
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
  if (!target) return;
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
  if (!document.getElementById('rulesChart')) return;
  const counts = {};
  judgments.forEach(j => (j.rules_cited || []).forEach(r => { counts[r] = (counts[r] || 0) + 1; }));
  const data = Object.entries(counts).sort((a, b) => b[1] - a[1]).slice(0, 14);
  drawHBar('rulesChart', data, { maxValue: Math.max(...data.map(d => d[1])) });
}

function drawHBar(targetId, data, opts = {}) {
  const target = document.getElementById(targetId);
  if (!target) return;
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

// ---------- Trace viewer (rule | events | output, side by side) ----------

const TRACE_FETCH_CACHE = {};

async function fetchTraceFile(path, name) {
  const key = path + name;
  if (TRACE_FETCH_CACHE[key] !== undefined) return TRACE_FETCH_CACHE[key];
  // Try a few plausible URLs depending on whether the dashboard is served from
  // habeas-protocol/ or from inside dashboard/.
  const candidates = [
    path + name,
    path.replace('../', '') + name,
    '../' + path + name,
  ];
  for (const url of candidates) {
    try {
      const r = await fetch(url);
      if (r.ok) {
        const t = await r.text();
        TRACE_FETCH_CACHE[key] = t;
        return t;
      }
    } catch (e) { /* try next */ }
  }
  TRACE_FETCH_CACHE[key] = null;
  return null;
}

// Court-convention divergences: every trace row where the predicate's
// reading differs from the court's operative figure, classified by
// kind. Promotes the per-trace footnotes to a corpus-level finding —
// the discrepancies are the protocol's machine-checkable contribution,
// not a per-case curiosity.
const DIVERGENCE_KIND_LABEL = {
  clerical:    { label: 'Clerical',    blurb: 'A transcription gap inside the same judgment.' },
  daycount:    { label: 'Daycount',    blurb: 'A counting-convention difference (inclusive vs exclusive endpoints, calendar vs business days).' },
  rounding:    { label: 'Rounding',    blurb: 'A rounding policy that compounds at scale (e.g., per-line vs total).' },
  substantive: { label: 'Substantive', blurb: 'A finding the predicate reads differently from the court.' },
};

function collectDivergences() {
  const out = [];
  TRACES.forEach(t => {
    if (!Array.isArray(t.outputs)) return;
    t.outputs.forEach(o => {
      if (o.match === false && o.divergence) {
        out.push({
          n: t.n,
          case_no: t.case_no,
          label: o.label,
          predicate: o.computed,
          court: o.court,
          kind: o.divergence.kind || 'substantive',
          delta_label: o.divergence.delta_label || '',
          delta_pct: o.divergence.delta_pct,
          interpretation: o.divergence.interpretation || o.note || '',
        });
      }
    });
  });
  return out;
}

function renderConventionDivergences() {
  const root = document.getElementById('conventionDivergences');
  if (!root) return;
  const items = collectDivergences();
  if (items.length === 0) {
    root.innerHTML = '<p class="muted">No surfaced divergences in the current trace set.</p>';
    return;
  }
  const byKind = items.reduce((acc, x) => {
    (acc[x.kind] = acc[x.kind] || []).push(x); return acc;
  }, {});
  const order = ['clerical', 'daycount', 'rounding', 'substantive'];
  let html = `
    <p>Each row is a place where the predicate's mechanical reading diverged from the court's operative figure. The protocol's contribution is structural: the divergence is named, classified, and quantified — turning an unstated convention into a contestable parameter. ${items.length} surfaced ${items.length === 1 ? 'divergence' : 'divergences'} across the trace set, by kind:</p>
  `;
  html += '<div class="cd-grid">';
  order.forEach(kind => {
    const rows = byKind[kind];
    if (!rows || !rows.length) return;
    const meta = DIVERGENCE_KIND_LABEL[kind] || { label: kind, blurb: '' };
    html += `<div class="cd-kind"><div class="cd-kind-h">${escape(meta.label)}<span class="cd-kind-n">${rows.length}</span></div>`;
    html += `<div class="cd-kind-blurb">${escape(meta.blurb)}</div>`;
    rows.forEach(r => {
      const pct = (typeof r.delta_pct === 'number') ? `${r.delta_pct.toFixed(2)}%` : '';
      html += `
        <div class="cd-row">
          <div class="cd-row-h"><span class="cd-trace">Trace #${r.n}</span><span class="cd-case">${escape(r.case_no)}</span></div>
          <div class="cd-label">${escape(r.label)}</div>
          <div class="cd-vals">
            <span class="cd-pred"><span class="cd-vk">predicate</span> ${escape(r.predicate)}</span>
            <span class="cd-court"><span class="cd-vk">court</span> ${escape(r.court)}</span>
            <span class="cd-delta"><span class="cd-vk">Δ</span> ${escape(r.delta_label)}${pct ? ' · ' + pct + ' of court value' : ''}</span>
          </div>
          <div class="cd-interp">${escape(r.interpretation)}</div>
        </div>
      `;
    });
    html += '</div>';
  });
  html += '</div>';
  root.innerHTML = html;
}

async function renderAuditPanel() {
  const root = document.getElementById('auditPanel');
  if (!root) return;
  // Same API discovery as the data-source loader. If we already loaded
  // judgments from the API, we know it's reachable; if we fell back to
  // static, the audit table just isn't available — the panel says so.
  if (dataSource !== 'api') {
    root.innerHTML = `<p class="muted" style="font-size:12.5px;">Audit log only renders in <strong>live</strong> mode (Postgres + API). Currently running on the static JSON fallback. Start the API with <code>python3 api/server.py</code> to populate.</p>`;
    return;
  }
  try {
    const [recent, stats] = await Promise.all([
      fetch('http://127.0.0.1:5544/api/runs/recent?limit=15').then(r => r.json()),
      fetch('http://127.0.0.1:5544/api/runs/stats').then(r => r.json()),
    ]);
    let html = '';

    // stats summary
    if (Array.isArray(stats) && stats.length) {
      const total = stats.reduce((a, s) => a + (s.runs || 0), 0);
      const ok = stats.reduce((a, s) => a + (s.successes || 0), 0);
      const successRate = total ? (100 * ok / total).toFixed(1) : '—';
      html += `<div class="audit-summary">
        <div class="audit-stat"><div class="audit-stat-num">${total}</div><div class="audit-stat-label">total runs</div></div>
        <div class="audit-stat"><div class="audit-stat-num">${ok}</div><div class="audit-stat-label">successes</div></div>
        <div class="audit-stat"><div class="audit-stat-num">${successRate}%</div><div class="audit-stat-label">success rate</div></div>
        <div class="audit-stat"><div class="audit-stat-num">${stats.length}</div><div class="audit-stat-label">distinct (module, scope)</div></div>
      </div>`;

      html += '<h3 class="audit-h3">By module</h3>';
      html += '<div class="audit-stats-grid">';
      stats.forEach(s => {
        const succRate = s.runs ? (100 * s.successes / s.runs).toFixed(0) : '—';
        html += `<div class="audit-stats-row">
          <span class="audit-mod">${escape(s.module)} · ${escape(s.scope)}</span>
          <span class="audit-stats-meta">${s.runs} run${s.runs === 1 ? '' : 's'} · ${succRate}% ok · ${s.median_ms || 0}ms median · last ${formatTs(s.last_ts)}</span>
        </div>`;
      });
      html += '</div>';
    }

    // recent runs
    if (Array.isArray(recent) && recent.length) {
      html += '<h3 class="audit-h3">Recent runs</h3>';
      html += '<div class="audit-runs">';
      recent.forEach(r => {
        const ok = r.success;
        const errSnip = (r.error || '').replace(/[┌-▀]+/g, '').replace(/\s+/g, ' ').trim().slice(0, 100);
        html += `<div class="audit-run ${ok ? 'audit-run-ok' : 'audit-run-err'}">
          <div class="audit-run-h">
            <span class="audit-run-id">#${r.id}</span>
            <span class="audit-mod">${escape(r.module)}</span>
            <span class="audit-stats-meta">${escape(r.scope)} · ${r.duration_ms}ms · ${formatTs(r.ts)}${r.source_label ? ' · ' + escape(r.source_label) : ''}</span>
            <span class="audit-run-tag ${ok ? 'audit-run-tag-ok' : 'audit-run-tag-err'}">${ok ? 'success' : 'failure'}</span>
          </div>
          <div class="audit-run-sha">sha256: ${escape((r.inputs_sha256 || '').slice(0, 16))}…</div>
          ${errSnip ? `<div class="audit-run-err-snip">${escape(errSnip)}</div>` : ''}
        </div>`;
      });
      html += '</div>';
    } else {
      html += '<p class="muted" style="font-size:12.5px;">No rule runs yet. Try the <a href="playground.html">rule playground</a> or the <a href="simulator.html">dispute simulator</a>; both write to this log.</p>';
    }

    root.innerHTML = html;
  } catch (e) {
    root.innerHTML = `<p class="muted" style="font-size:12.5px;">Audit log unavailable: ${escape(String(e))}</p>`;
  }
}

function formatTs(ts) {
  if (!ts) return '—';
  // The DB returns ISO-8601 with timezone — render a relative timestamp.
  const t = new Date(ts);
  if (isNaN(t.getTime())) return ts;
  const dt = (Date.now() - t.getTime()) / 1000;
  if (dt < 60) return `${Math.floor(dt)}s ago`;
  if (dt < 3600) return `${Math.floor(dt / 60)}m ago`;
  if (dt < 86400) return `${Math.floor(dt / 3600)}h ago`;
  return t.toISOString().slice(0, 16).replace('T', ' ');
}

function renderTraceViewer() {
  const tabs = document.getElementById('viewerTabs');
  if (!tabs) return;
  tabs.innerHTML = '';
  TRACES.forEach((t, i) => {
    const b = document.createElement('button');
    b.className = 'viewer-tab' + (i === 0 ? ' active' : '');
    b.dataset.idx = i;
    b.textContent = `#${t.n} · ${t.title}`;
    b.addEventListener('click', () => {
      tabs.querySelectorAll('.viewer-tab').forEach(x => x.classList.remove('active'));
      b.classList.add('active');
      loadViewerFor(t);
    });
    tabs.appendChild(b);
  });
  loadViewerFor(TRACES[0]);
}

async function loadViewerFor(trace) {
  const meta = document.getElementById('viewerMeta');
  const ruleEl = document.getElementById('viewerRule');
  const eventsEl = document.getElementById('viewerEvents');
  const outputEl = document.getElementById('viewerOutput');

  meta.innerHTML = `
    <div class="viewer-case">${escape(trace.case_no)}</div>
    <div class="viewer-rule-summary">${escape(trace.rule)}</div>
  `;

  ruleEl.textContent = 'loading…';
  eventsEl.textContent = 'loading…';
  outputEl.innerHTML = 'loading…';

  const [ruleSrc, eventsSrc] = await Promise.all([
    fetchTraceFile(trace.path, 'rule.catala_en'),
    fetchTraceFile(trace.path, 'events.json'),
  ]);

  // Rule column: raw Catala source.
  if (ruleSrc) {
    ruleEl.textContent = ruleSrc;
  } else {
    ruleEl.textContent = `(could not load ${trace.path}rule.catala_en — serve from habeas-protocol/ root)`;
  }

  // Events column: events timeline + human findings + facts summary.
  if (eventsSrc) {
    try {
      const ev = JSON.parse(eventsSrc);
      eventsEl.innerHTML = renderEventsPanel(ev);
    } catch (e) {
      eventsEl.textContent = '(failed to parse events.json: ' + e.message + ')';
    }
  } else {
    eventsEl.textContent = `(could not load ${trace.path}events.json)`;
  }

  // Output column: predicate-vs-court rows from the trace config.
  outputEl.innerHTML = renderOutputPanel(trace);
  outputEl.querySelectorAll('[data-action="toggle-catala"]').forEach(btn => {
    btn.addEventListener('click', () => {
      const block = btn.closest('.viewer-catala');
      const out = block.querySelector('.viewer-runout');
      const showing = !out.hasAttribute('hidden');
      if (showing) {
        out.setAttribute('hidden', '');
        btn.innerHTML = 'Run <code>catala interpret</code>';
      } else {
        out.removeAttribute('hidden');
        btn.textContent = 'Hide text output';
      }
    });
  });
  outputEl.querySelectorAll('[data-action="toggle-json"]').forEach(btn => {
    btn.addEventListener('click', async () => {
      const block = btn.closest('.viewer-catala');
      const panel = block.querySelector('.viewer-jsonout');
      const showing = !panel.hasAttribute('hidden');
      if (showing) {
        panel.setAttribute('hidden', '');
        btn.innerHTML = 'Run <code>catala interpret -F json</code>';
        return;
      }
      panel.removeAttribute('hidden');
      btn.textContent = 'Hide JSON output';
      const body = panel.querySelector('.viewer-jsonbody');
      if (body.dataset.loaded === '1') return;
      const path = panel.dataset.tracePath;
      const data = await fetchTraceFile(path, 'output.json');
      if (!data) {
        body.innerHTML = `<span class="viewer-jsonerror">Could not load <code>output.json</code>. Run <code>scripts/build_trace_outputs.sh</code> to regenerate.</span>`;
        return;
      }
      try {
        const parsed = JSON.parse(data);
        body.innerHTML = renderCatalaJson(parsed, trace);
        body.dataset.loaded = '1';
      } catch (e) {
        body.innerHTML = `<span class="viewer-jsonerror">Failed to parse output.json: ${escape(e.message)}</span>`;
      }
    });
  });
}

// Map a JSON leaf field name to a predicate-vs-court row, when one exists.
// Returns 'ok' (match), 'warn' (mismatch), or null (no row registered).
function classifyField(fieldName, trace) {
  if (!trace || !Array.isArray(trace.outputs)) return null;
  const norm = String(fieldName).toLowerCase().replace(/[^a-z0-9]/g, '');
  for (const o of trace.outputs) {
    const oNorm = String(o.label).toLowerCase().replace(/[^a-z0-9]/g, '');
    // Either label includes field, or field includes label — accept either
    // direction since the dashboard's labels are sometimes prose forms of
    // the JSON field names ("net_to_claimant_aed" vs "net principal").
    if (oNorm.includes(norm) || norm.includes(oNorm)) {
      return o.match ? 'ok' : 'warn';
    }
  }
  return null;
}

function renderCatalaJson(value, trace, depth) {
  depth = depth || 0;
  if (Array.isArray(value)) {
    if (value.length === 0) return '<span class="viewer-jsempty">[]</span>';
    const isPrimList = value.every(v => typeof v !== 'object' || v === null);
    if (isPrimList) {
      return '<span class="viewer-jsbracket">[</span>' +
        value.map(v => `<span class="viewer-jsstr">${escape(JSON.stringify(v))}</span>`).join(', ') +
        '<span class="viewer-jsbracket">]</span>';
    }
    return '<div class="viewer-jslist">' +
      value.map((v, i) => `<div class="viewer-jsitem"><span class="viewer-jsindex">[${i}]</span> ${renderCatalaJson(v, trace, depth + 1)}</div>`).join('') +
      '</div>';
  }
  if (value && typeof value === 'object') {
    let html = '<div class="viewer-jsobj">';
    for (const [k, v] of Object.entries(value)) {
      const cls = classifyField(k, trace);
      const cellCls = cls === 'ok' ? 'viewer-jsfield viewer-jsfield-ok'
                  : cls === 'warn' ? 'viewer-jsfield viewer-jsfield-warn'
                  : 'viewer-jsfield';
      const isLeaf = (typeof v !== 'object') || v === null;
      const status = cls === 'ok' ? '<span class="viewer-jstag viewer-jstag-ok">match</span>'
                  : cls === 'warn' ? '<span class="viewer-jstag viewer-jstag-warn">surfaced</span>'
                  : '';
      if (isLeaf) {
        html += `<div class="${cellCls}"><span class="viewer-jsk">${escape(k)}</span><span class="viewer-jsv">${escape(formatJsLeaf(v))}</span>${status}</div>`;
      } else {
        html += `<div class="${cellCls}"><span class="viewer-jsk">${escape(k)}</span> ${renderCatalaJson(v, trace, depth + 1)}${status}</div>`;
      }
    }
    html += '</div>';
    return html;
  }
  return `<span class="viewer-jsv">${escape(formatJsLeaf(value))}</span>`;
}

function formatJsLeaf(v) {
  if (typeof v === 'number') {
    // Catala emits decimals as floats; trim noise tail beyond 6 dp.
    if (Number.isInteger(v)) return String(v);
    const s = v.toPrecision(12);
    return parseFloat(s).toString();
  }
  if (typeof v === 'string') return v;
  if (typeof v === 'boolean') return v ? 'true' : 'false';
  if (v === null) return 'null';
  return JSON.stringify(v);
}

function renderEventsPanel(ev) {
  let html = '';
  if (ev.judge || ev.decision_date || ev.neutral_citation) {
    html += '<div class="viewer-block"><div class="viewer-block-h">Decision</div>';
    if (ev.judge) html += `<div class="viewer-row"><span class="viewer-k">judge</span><span class="viewer-v">${escape(ev.judge)}</span></div>`;
    if (ev.decision_date) html += `<div class="viewer-row"><span class="viewer-k">date</span><span class="viewer-v">${escape(ev.decision_date)}</span></div>`;
    if (ev.neutral_citation) html += `<div class="viewer-row"><span class="viewer-k">citation</span><span class="viewer-v">${escape(ev.neutral_citation)}</span></div>`;
    html += '</div>';
  }
  if (Array.isArray(ev.events) && ev.events.length) {
    html += '<div class="viewer-block"><div class="viewer-block-h">Event log</div>';
    ev.events.forEach(e => {
      const t = e.t || '';
      const type = e.type || '';
      const extras = Object.entries(e)
        .filter(([k]) => !['t', 'type'].includes(k))
        .map(([k, v]) => `${k}=${typeof v === 'object' ? JSON.stringify(v) : v}`)
        .join(' · ');
      html += `<div class="viewer-event"><span class="viewer-event-t">${escape(t)}</span><span class="viewer-event-type">${escape(type)}</span>${extras ? `<span class="viewer-event-extra">${escape(extras)}</span>` : ''}</div>`;
    });
    html += '</div>';
  }
  if (Array.isArray(ev.human_findings_required) && ev.human_findings_required.length) {
    html += '<div class="viewer-block"><div class="viewer-block-h">Human findings (inputs to predicate)</div>';
    ev.human_findings_required.forEach(f => {
      html += `<div class="viewer-finding">· ${escape(f)}</div>`;
    });
    html += '</div>';
  }
  if (ev.facts) {
    html += '<div class="viewer-block"><div class="viewer-block-h">Facts</div>';
    Object.entries(ev.facts).forEach(([k, v]) => {
      let valStr;
      if (Array.isArray(v)) {
        valStr = v.length + ' item' + (v.length === 1 ? '' : 's');
      } else if (typeof v === 'object' && v !== null) {
        valStr = '{…}';
      } else {
        valStr = String(v);
      }
      html += `<div class="viewer-row"><span class="viewer-k">${escape(k)}</span><span class="viewer-v">${escape(valStr)}</span></div>`;
    });
    html += '</div>';
  }
  return html || '<div class="muted">(no event data)</div>';
}

function renderOutputPanel(trace) {
  if (!Array.isArray(trace.outputs) || trace.outputs.length === 0) {
    return '<div class="muted">(no output config)</div>';
  }
  let html = '<div class="viewer-block"><div class="viewer-block-h">Predicate output ↔ court</div>';
  let allMatch = true;
  trace.outputs.forEach(o => {
    if (!o.match) allMatch = false;
    const mark = o.match ? '✓' : '⚠';
    const cls = o.match ? 'viewer-ok' : 'viewer-warn';
    html += `<div class="viewer-out ${cls}">
      <div class="viewer-out-h"><span class="viewer-out-mark">${mark}</span><span class="viewer-out-label">${escape(o.label)}</span></div>
      <div class="viewer-out-row"><span class="viewer-out-side">predicate</span><span class="viewer-out-val">${escape(o.computed)}</span></div>
      <div class="viewer-out-row"><span class="viewer-out-side">court</span><span class="viewer-out-val">${escape(o.court)}</span></div>
      ${o.note ? `<div class="viewer-out-note">${escape(o.note)}</div>` : ''}
    </div>`;
  });
  html += '</div>';
  const summaryCls = allMatch ? 'viewer-summary-ok' : 'viewer-summary-warn';
  const summaryText = allMatch
    ? `PASS — predicate reproduces every line of the court's ruling.`
    : `Predicate matches the court's substantive findings; surfaces a discrepancy on flagged rows above.`;
  html += `<div class="viewer-summary ${summaryCls}">${summaryText}</div>`;

  if (trace.catala_run) {
    const cmd = trace.catala_cmd || `catala interpret --no-stdlib --scope=… rule.catala_en`;
    const jsonCmd = `catala interpret -F json --no-stdlib rule.catala_en`;
    html += `
      <div class="viewer-block viewer-catala">
        <div class="viewer-block-h">Catala 1.1.0 interpreter</div>
        <div class="viewer-runbtns">
          <button class="viewer-runbtn" data-action="toggle-catala">Run <code>catala interpret</code></button>
          <button class="viewer-runbtn" data-action="toggle-json">Run <code>catala interpret -F json</code></button>
        </div>
        <div class="viewer-runout" hidden>
          <div class="viewer-runout-cmd">$ ${escape(cmd)}</div>
          <pre class="viewer-runout-pre">${escape(trace.catala_run)}</pre>
          <div class="viewer-runout-note">Output is from the Catala 1.1.0 interpreter run against <code>rule.catala_en</code>. Every <code>assertion</code> in the test scope passed; the result struct above is the predicate's reading of the case.</div>
        </div>
        <div class="viewer-jsonout" hidden data-trace-path="${escape(trace.path)}">
          <div class="viewer-runout-cmd">$ ${escape(jsonCmd)}</div>
          <div class="viewer-jsonbody"><span class="viewer-jsonloading">Loading…</span></div>
          <div class="viewer-runout-note">JSON-mode output is the structural reading of the trace's predicate scopes. Fields shaded green match an entry in the predicate-vs-court table above; amber rows correspond to surfaced discrepancies. Regenerated by <code>scripts/build_trace_outputs.sh</code> on every push (CI checks for drift).</div>
        </div>
      </div>
    `;
  }
  return html;
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
