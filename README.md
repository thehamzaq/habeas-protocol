# Habeas Protocol

A constitutional reframing of the "Legal Operating System for Digital Worlds" thesis, grounded in empirical analysis of three operating special-jurisdiction commercial courts: the **DIFC Courts** in Dubai, the **ADGM Courts** in Abu Dhabi, and the **Singapore International Commercial Court (SICC)**.

## Thesis in one paragraph

Most "Web3 dispute resolution" proposals try to invent a tribunal from scratch. The thesis here is the inverse: **the tribunals already exist; what is missing is the computational layer.** DIFC and ADGM are common-law courts inside special economic zones in the United Arab Emirates; SICC is a division of the Singapore High Court staffed partly by international judges. All three operate with versioned rules, dated evidence, separation of powers, and rulings enforceable across borders under the New York Convention.[^nyc] This repository codes 121 judgments from the three tribunals against six per-ruling primitives a digital tribunal must satisfy, and compiles four rules from the corpus into executable predicates that reproduce the courts' arithmetic.

## What's inside

### Empirical (n=121)

121 judgments scored against the v0.2 primitives. 39 form a hand-coded **gold set**; the other 82 are AI-triaged or AI-graded against the same rubric, with provenance recorded per-entry in the `coding.coder` field.

| Primitive | DIFC (n=32) | ADGM (n=76) | SICC (n=13) | Combined | What it tests |
|---|---:|---:|---:|---:|---|
| **PR1 Identity** | 1.81 | 1.97 | **2.00** | 1.93 | parties unambiguous, counsel of record |
| **PR2 Evidence log** | 1.78 | **2.00** | **2.00** | 1.94 | dated submissions, attributable record |
| **PR3 Rule bind** | 1.69 | 1.93 | 1.92 | 1.87 | specific clause + version cited |
| **PR4 Procedure** | 1.75 | **2.00** | **2.00** | 1.93 | notice + hearing + decision documented |
| **PR5 Ruling** | 1.88 | 1.96 | 1.92 | 1.93 | operative outcome unambiguous |
| **PR6 Enforcement bridge** | 1.44 | 1.62 | **1.85** | 1.60 | path to compulsion outside tribunal |
| **Overall** | **1.72** | **1.91** | **1.95** | **1.87** | |

System properties (architectural, scored once per institution):

| | DIFC | ADGM | SICC | VARA | Próspera | Kleros |
|---|---|---|---|---|---|---|
| **SP1 Separation of powers** | 2 | 2 | 2 | 1 | 2 | 0 |
| **SP2 Appeal path** | 2 | 2 | 2 | 1 | 1 | 0 |

**Headline.** All three operating tribunals score at or near ceiling on every per-ruling primitive. The saturation pattern survived two stress tests during this work: a 10× expansion of the ADGM sample (1.93 at n=7 hand-coded → 1.91 at n=76 hand+AI), and a replication on a third tribunal in a different legal family (SICC at 1.95). All three score 2/2 on both system properties. **Three operating commercial tribunals, all implementing the full protocol at near-ceiling, available to plug in today.**

### Constructive: four executable traces

Each trace lifts a rule from the corpus into [Catala][^catala] source plus a Python predicate evaluator and runs it against an event log of the case facts. The four traces span the rule-shape spectrum:

- **Trace #1 — pure formula.** [`spike/trace-01/`](./spike/trace-01/). DIFC RDC[^rdc] Part 38 standard-basis costs, applied to *Atul Dhawan v Ramzi El Jaouhari* (CFI 058/2024). Predicate computes **AED 7,121.75** matching the Schedule of Reasons exactly. The operative paragraph states AED 7,127.75 — **a 6 AED clerical-error gap** the protocol mechanically surfaces.

- **Trace #2 — deferred conditional.** [`spike/trace-02/`](./spike/trace-02/). RDC 38.40 + Practice Direction 4/2017 from *Oberlin v Ovidiu* (ARB 008/2026): a 14-day payment window, 9% per annum interest if missed, computed retroactively from the date of the order rather than from the deadline. Five scenarios pass — on-time, at-deadline, 1 / 61 / 92 days late. The 80% discretion + 14-day deadline + 9% interest structure recurs verbatim across adjacent DIFC arbitration costs orders; the corpus has converged on a near-formula.

- **Trace #3 — bounded discretion.** [`spike/trace-03/`](./spike/trace-03/). Indemnity-basis costs review from *Taylor v Yao Affi* (ENF 271/2025). In English costs law, the *standard basis* allows the court to disallow disproportionate costs even if reasonably incurred; the *indemnity basis* strips proportionality and leaves only reasonableness, which is not formulaic. The predicate triages each defendant objection into one of four buckets: mechanically disposed (no specific line item named), held to zero on evidence, deterministic reduction with named amount, or requires human judgment. Court reduced AED 128,914.80 → AED 120,000 — the **AED 8,914.80, ≈6.92% of the claim**, is the structured-discretion residue. **The honest case for what executable rules cannot fully decide.**

- **Trace #4 — composition over substantive findings.** [`spike/trace-04/`](./spike/trace-04/). Substantive contract dispute from *Projeco v Ideacrate* (ADGMCFI-2024-320, Justice Heath KC). UAE Civil Transactions Law Article 390 (liquidated-damages cap)[^uae-civil] + ADGM CPR Rule 42 (admissions)[^adgm-cpr] + ADGM Civil Evidence Regulations §§ 181–182 (set-off). Predicate takes human substantive findings as inputs (97 days of critical delay, smoke management within scope, repair counterclaim not proven) and composes them deterministically: liquidated-damages cap → counterclaim set-off → net principal → pre-judgment interest. **Net principal AED 10,500.96 reproduces the court exactly.** Pre-judgment interest at 609 calendar days computes AED 876.04; court's stated AED 877.48 corresponds to 610 days — protocol surfaces the daycount convention.

## Why these three tribunals

| | DIFC Courts | ADGM Courts | SICC |
|---|---|---|---|
| Founded | 2004 | 2013 | 2015 |
| Law system | Common-law (own statutes + Practice Directions) | Common-law (English law applied wholesale via the *Application of English Law Regulations 2015*[^adgm-aelr]) | Common-law (Singapore law; international judges may apply foreign law) |
| Digital court | Digital Economy Court (2025) | Full eCourts platform from 2018 | Cross-border commercial cases since 2015 |
| Judgment publication | HTML on-page, 5,000+ since 2007 | PDF with structured Judgment Summary, full neutral citations | HTML via elitigation.sg, structured judgments |
| Cross-border enforcement | New York Convention + UAE federal recognition | New York Convention + UAE Cabinet Resolution + Federal Law | New York Convention + Singapore *Reciprocal Enforcement of Commonwealth Judgments Act* |

ADGM's *Application of English Law Regulations 2015* is itself a constitutional artefact: a single instrument making the entire body of English common law the binding rule-of-decision. Every ADGM judgment in the gold set cites English House of Lords and Court of Appeal cases — *Caparo*,[^caparo] *Hedley Byrne*,[^hedley] *Murphy*, *Arnold v Britton*[^arnold] — directly, alongside a growing internal ADGMCFI line. ADGM has the cleanest "PR3 Rule bind" implementation we have seen in any tribunal anywhere.

## v0.2 framework

The six per-ruling primitives + two system properties replaced v0.1's seven primitives, which mixed constitutional values (separation of powers) with technical features (executable predicates) and an upstream-prevention category that does not belong on a tribunal. v0.2 separates the per-ruling layer from the architectural layer and aligns with Fuller's eight desiderata of legality[^fuller] and Hart's primary/secondary rule distinction.[^hart]

See [`data/primitives.json`](./data/primitives.json) for full definitions and the v0.1 → v0.2 mapping.

## Layout

```
habeas-protocol/
├── README.md                       # this file
├── paper.md                        # full working paper (~5000 words)
├── data/
│   ├── primitives.json             # v0.2 rubric + scoring + v0.1 mapping
│   ├── schema.json                 # JSON Schema (v0.1 + v0.2 supported)
│   ├── judgments.json              # 121 coded judgments
│   ├── sources.md                  # corpus provenance
│   ├── adgm_triage.json            # AI-triage classifications
│   ├── adgm_borderline_digests.json
│   ├── adgm_graded.json            # AI-graded scores + rationale
│   └── raw/
│       ├── judgments/              # 294 DIFC HTML pulls
│       ├── text/                   # DIFC stripped to plain text
│       ├── adgm/{pdfs,text}/       # 172 ADGM PDFs + extracted text
│       └── sicc/{html,text}/       # SICC raw + extracted
├── scripts/
│   ├── fetch_difc.py               # DIFC scraper
│   ├── fetch_adgm_firecrawl.py     # ADGM full-corpus scraper
│   ├── strip_html.py               # HTML → text
│   ├── migrate_v02.py              # v0.1 → v0.2 schema migration
│   ├── triage_adgm.py              # AI three-bucket classifier
│   ├── build_digests.py            # per-case digest extractor
│   ├── grade_borderline.py         # rubric-applying grader
│   └── merge_adgm_codings.py       # merger into judgments.json
├── spike/
│   ├── trace-01/   trace-02/       # Catala source + Python evaluator
│   └── trace-03/   trace-04/       #   per trace
└── dashboard/                      # interactive view (vanilla JS, hand-rolled SVG)
```

## Reproduce

```bash
# Corpus pull
python3 scripts/fetch_difc.py 25
python3 scripts/strip_html.py
python3 scripts/fetch_adgm_firecrawl.py    # uses Firecrawl API; plain ?page=N also works

# AI codings
python3 scripts/triage_adgm.py
python3 scripts/build_digests.py
python3 scripts/grade_borderline.py
python3 scripts/merge_adgm_codings.py

# Run all four traces
python3 spike/trace-01/evaluate.py
python3 spike/trace-02/evaluate.py
python3 spike/trace-03/evaluate.py
python3 spike/trace-04/evaluate.py

# Local dashboard
python3 -m http.server 8001
# open http://127.0.0.1:8001/dashboard/
```

## Phase status

- **Phase 0–1.5** done: DIFC scraping, 39-judgment hand-coded gold set, v0.1 → v0.2 framework refactor, all 32 DIFC re-scored under v0.2, 7 ADGM coded.
- **Phase 2** done: all four traces compiled and passing; deeper ADGM pull (172 PDFs); 76 ADGM cases coded (7 hand + 16 AI-triaged + 53 AI-graded); SICC sample (13 cases) added; saturation pattern survives the 10× ADGM expansion and replicates on SICC; dashboard and paper updated.
- **Open (optional)**: Catala runtime install + bisimilarity check; stratified hand-validation of ~30 AI-coded entries to harden methodological provenance; larger SICC pull.

## License

Code: MIT. Dataset: CC-BY-4.0.

## Citation

```
Maxim Labs, "Habeas Protocol: An Empirical Analysis of DIFC, ADGM, and Singapore
SICC as Working Prototypes for Constitutional Digital Tribunals," v0.2 (April 2026).
```

## References

[^catala]: Merigoux, Chataing, Protzenko, "Catala: A Programming Language for the Law," *PACMPL* 5, ICFP (2021). https://catala-lang.org

[^rdc]: Dubai International Financial Centre Courts, *Rules of the DIFC Courts (RDC)* (as amended). https://www.difccourts.ae

[^adgm-aelr]: Abu Dhabi Global Market, *Application of English Law Regulations 2015*. https://www.adgm.com

[^adgm-cpr]: Abu Dhabi Global Market Courts, *Court Procedure Rules 2016* (as amended).

[^uae-civil]: United Arab Emirates *Civil Transactions Law*, Federal Law No. 5 of 1985 (as amended), Article 390.

[^nyc]: *Convention on the Recognition and Enforcement of Foreign Arbitral Awards* (New York Convention), 330 UNTS 3 (1958), 172 contracting states.

[^fuller]: Fuller, Lon L. *The Morality of Law* (rev. ed., Yale University Press, 1969).

[^hart]: Hart, H.L.A. *The Concept of Law* (Clarendon Press, 1961; 2nd ed. 1994).

[^caparo]: *Caparo Industries plc v Dickman* [1990] UKHL 2, [1990] 2 AC 605.

[^hedley]: *Hedley Byrne & Co Ltd v Heller & Partners Ltd* [1963] UKHL 4, [1964] AC 465.

[^arnold]: *Arnold v Britton* [2015] UKSC 36, [2015] AC 1619.
