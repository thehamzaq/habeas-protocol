# Habeas Protocol

A measurement framework + open-source rule library for the *computational legitimacy* of commercial courts that already handle digital and cross-border disputes. Built on three working tribunals: the **DIFC Courts** in Dubai, the **ADGM Courts** in Abu Dhabi, and the **Singapore International Commercial Court (SICC)**.

## In plain English

When a deal goes wrong online — a smart-contract exit gone sideways, a SaaS dispute across three continents, a digital-asset hack — courts struggle to keep up. The usual response is to invent a brand-new "Web3 tribunal." This project takes the opposite view.

**The tribunals already exist; what's missing is the software.** DIFC, ADGM, and SICC are real common-law courts inside special economic zones. They publish their judgments, cite specific rules, and produce orders enforceable in 170+ countries under the New York Convention.[^nyc] What they don't yet have is a way for software to *replay their reasoning* — to take a fact pattern, run it through the rule the court applied, and surface the same answer.

This repo does four things:

1. **Measures.** It scores 188 real judgments from the three tribunals against six "per-ruling primitives" a digital court must satisfy (Are the parties identified? Is the evidence dated? Is the rule cited with version? etc.) plus two architectural properties (separation of powers, appeal path).
2. **Falsifies.** It scores a 30-instrument falsification set — sealed arbitral awards, on-chain DAO "tribunals," regulator notices, platform adjudicators, UDRP panels — to demonstrate the rubric *can* fail and to identify the cells that actually distinguish a court from a non-court. Includes a positive-control class (UDRP panels) the rubric correctly does NOT mark down.
3. **Encodes.** It rewrites 12 of the corpus rules into Catala source plus a pure-Python reference evaluator (`{catala, py, conformance}` triples for all 12). Seven case traces run end-to-end and reproduce the court's arithmetic to the cent. Each rule module pins a specific version of its source instrument; CI checks for drift against the live URL.
4. **Bounds.** It is explicit about what does NOT compile: causation beyond simple but-for, ambiguous contractual construction, witness credibility, expert-quantum, public-policy refusal, sanction discretion, constitutional review. The protocol is a calculator for the deterministic parts and an auditor for the rest — not a substitute for substantive judicial reasoning.

The headline finding: **the rubric saturates on three serious commercial courts AND discriminates against five non-court instrument classes that share some, but not all, of the procedural form of a court ruling.** The computational layer is buildable today for the arithmetic-and-Boolean parts of court decision-making, on top of the legal substrate that already exists.

## Thesis in one paragraph (academic version)

Most "Web3 dispute resolution" proposals try to invent a tribunal from scratch. The thesis here is the inverse: **the tribunals already exist; what is missing is the computational layer.** DIFC and ADGM are common-law courts inside special economic zones in the United Arab Emirates; SICC is a division of the Singapore High Court staffed partly by international judges. All three operate with versioned rules, dated evidence, separation of powers, and rulings enforceable across borders under the New York Convention. This repository codes 188 judgments from the three tribunals against six per-ruling primitives a digital tribunal must satisfy, compiles **twelve rules from the corpus into executable Catala predicates and seven full case traces that reproduce the courts' arithmetic**, and exposes the deterministic predicate cores as a reusable rule library plus a public dashboard, a Postgres-backed read-only API, a schema-driven rule playground, and first-party Python + TypeScript clients.

## What's inside

### Empirical (n=188)

188 judgments scored against the v0.2 primitives. 39 form a hand-coded **gold set**; the other 149 are AI-triaged or AI-graded against the same rubric, with provenance recorded per-entry in the `coding.coder` field.

| Primitive | DIFC (n=32) | ADGM (n=76) | SICC (n=80) | Combined | What it tests |
|---|---:|---:|---:|---:|---|
| **PR1 Identity** | 1.81 | 1.97 | 1.82 | 1.88 | parties unambiguous, counsel of record |
| **PR2 Evidence log** | 1.78 | **2.00** | **2.00** | 1.96 | dated submissions, attributable record |
| **PR3 Rule bind** | 1.69 | 1.93 | 1.96 | 1.90 | specific clause + version cited |
| **PR4 Procedure** | 1.75 | **2.00** | 1.55 | 1.77 | notice + hearing + decision documented |
| **PR5 Ruling** | 1.88 | 1.96 | 1.96 | 1.95 | operative outcome unambiguous |
| **PR6 Enforcement bridge** | 1.44 | 1.62 | 1.81 | 1.67 | path to compulsion outside tribunal |
| **Overall** | **1.72** | **1.91** | **1.85** | **1.86** | |

System properties (architectural, scored once per institution):

| | DIFC | ADGM | SICC | VARA | Próspera | Kleros |
|---|---|---|---|---|---|---|
| **SP1 Separation of powers** | 2 | 2 | 2 | 1 | 2 | 0 |
| **SP2 Appeal path** | 2 | 2 | 2 | 1 | 1 | 0 |

**Headline.** All three operating tribunals score at or near ceiling on every per-ruling primitive. The saturation pattern is robust to one expansion test and qualified by a second:

- **ADGM expansion (passes):** 1.93 at n=7 hand-coded → 1.91 at n=76 (hand + AI). The pattern survives the 10× sample expansion essentially unchanged.
- **SICC expansion (qualified):** 1.95 at n=13 → **1.85 at n=80**. The 6× expansion drops the mean by ≈0.10, driven mainly by PR4 (1.55 — `triage_sicc.py` looks for four procedural markers (hearing date, decision date, named panel/coram, and a "reasons / judgment / GROUNDS OF DECISION" header) and requires ≥3 to score PR4=2; SICC's narrative-style grounds-of-decision often defeat the regex-based extraction of one or more of these markers, so the heuristic outputs PR4=1 or PR4=0 even when the document is procedurally regular). The expansion exposed a heuristic-coding limitation, not a tribunal-quality regression. PR3 actually *rises* from 1.92 to 1.96 on the larger sample; PR6 falls slightly from 1.85 to 1.81 (within noise).

All three tribunals score 2/2 on both system properties. **Three operating commercial tribunals, all implementing the full protocol at near-ceiling, available to plug in today** — with the SICC expansion finding documented honestly rather than smoothed away.

### Constructive: seven executable traces

Each trace lifts a rule from the corpus into [Catala][^catala] source plus a Python predicate evaluator and runs it against an event log of the case facts. The seven traces span the rule-shape spectrum and cross legal-family boundaries (DIFC + ADGM English-law-via-statute + Singapore IAA + NY Convention):

- **Trace #1 — pure formula.** [`spike/trace-01/`](./spike/trace-01/). DIFC RDC[^rdc] Part 38 standard-basis costs, applied to *Atul Dhawan v Ramzi El Jaouhari* (CFI 058/2024). Predicate computes **AED 7,121.75** matching the Schedule of Reasons exactly. The operative paragraph states AED 7,127.75 — **a 6 AED clerical-error gap** the protocol mechanically surfaces.

- **Trace #2 — deferred conditional.** [`spike/trace-02/`](./spike/trace-02/). RDC 38.40 + Practice Direction 4/2017 from *Oberlin v Ovidiu* (ARB 008/2026): a 14-day payment window, 9% per annum interest if missed, computed retroactively from the date of the order rather than from the deadline. Five scenarios pass — on-time, at-deadline, 1 / 61 / 92 days late. The 80% discretion + 14-day deadline + 9% interest structure recurs verbatim across adjacent DIFC arbitration costs orders; the corpus has converged on a near-formula.

- **Trace #3 — bounded discretion.** [`spike/trace-03/`](./spike/trace-03/). Indemnity-basis costs review from *Taylor v Yao Affi* (ENF 271/2025). In English costs law, the *standard basis* allows the court to disallow disproportionate costs even if reasonably incurred; the *indemnity basis* strips proportionality and leaves only reasonableness, which is not formulaic. The predicate triages each defendant objection into one of four buckets: mechanically disposed (no specific line item named), held to zero on evidence, deterministic reduction with named amount, or requires human judgment. Court reduced AED 128,914.80 → AED 120,000 — the **AED 8,914.80, ≈6.92% of the claim**, is the structured-discretion residue. **The honest case for what executable rules cannot fully decide.**

- **Trace #4 — composition over substantive findings.** [`spike/trace-04/`](./spike/trace-04/). Substantive contract dispute from *Projeco v Ideacrate* (ADGMCFI-2024-320, Justice Heath KC). UAE Civil Transactions Law Article 390 (liquidated-damages cap)[^uae-civil] + ADGM CPR Rule 42 (admissions)[^adgm-cpr] + ADGM Civil Evidence Regulations §§ 181–182 (set-off). Predicate takes human substantive findings as inputs (97 days of critical delay, smoke management within scope, repair counterclaim not proven) and composes them deterministically: liquidated-damages cap → counterclaim set-off → net principal → pre-judgment interest. **Net principal AED 10,500.96 reproduces the court exactly.** Pre-judgment interest at 609 calendar days computes AED 876.04; court's stated AED 877.48 corresponds to 610 days — protocol surfaces the daycount convention.

- **Trace #5 — conjunctive logical composition.** [`spike/trace-05/`](./spike/trace-05/). Software-development contract dispute from *Xetech v Pulsar* (ADGMCFI-2024-158, Justice Heath KC, [2026] ADGMCFI 0006). English contractual interpretation (*Wood v Capita Insurance Services* applying *Rainy Sky*) + *Ladd v Marshall* three-prong fresh-evidence test + Assignment Agreement clauses 2(b), 7, 10. The first trace whose rule is **structurally Boolean** rather than arithmetic. Predicate composes three conjunctive tests: clause alignment (3/3 point to payment-before-transfer), named-witness preponderance (6:2; both dissenters lacked DevOps access), Ladd v Marshall (fails on prong (a) — short-circuits). **Judgment Sum GBP 409,870, costs USD 125,483.84, counterclaim dismissed — all match.** The protocol does not replace contractual interpretation; it makes the *logical structure* of that interpretation auditable.

- **Trace #6 — partial statutory refusal (cross-tribunal).** [`spike/trace-06/`](./spike/trace-06/). NY Convention recognition under Singapore IAA s 31 from *GNC Holdings v ONI Global Pte Ltd* (SIC/OA 9/2025, [2025] SGHC(I) 25; Chua Lee Ming J, Simon Thorley IJ, James Allsop IJ). The first SICC trace and the first to express a *partial* refusal of enforcement: of four pleaded grounds, three dismissed in full, one allowed in part — with three named sub-paragraphs of the Tribunal's Order 3 excised because the parties were not afforded an opportunity to be heard on their specific terms. Disposition reproduces para 185(a)–(c) exactly: application allowed in part; Order 3(d)(ii), (d)(iii), (f) not enforced; the rest enforced. **Demonstrates the protocol crosses legal-family boundaries** (Singapore IAA + NY Convention vs DIFC/ADGM English-law-via-statute).

- **Trace #7 — third-party-jurisdiction gate.** [`spike/trace-07/`](./spike/trace-07/). *Norwich Pharmacal* + *Bankers Trust* + DIFC RDC 28.52, applied to a digital-asset tracing dispute (DEC 001/2025) before DIFC's *Digital Economy Court*. The first trace to combine a constructive-trust threshold, an innocent-mixed-up-party gate, and the DIFC's third-party disclosure rule into one decision tree. **Demonstrates protocol coverage of the FinTech/digital-asset vertical** the courts increasingly handle.

### Rule library — twelve reusable Catala modules

[`rules/`](./rules/) factors the deterministic computational cores out of the traces into reusable Catala modules — the seed of the Stage-2 dispute simulator. Each module ships with a Clerk-compatible test suite (`#[test]` scopes, both the canonical case and contrary-branch demonstrations), a generated JSON schema (input/output shapes for tooling), and is wired into CI alongside the traces.

> **Sibling stack.** Catala[^catala] (judgment-side, statute-and-tribunal logic) is complemented in Singapore by the L4 DSL[^l4-deontics] (contract-side, deontic-and-temporal logic) developed by Legalese with the SMU Centre for Computational Law. The two are the natural left-and-right hand of an end-to-end computational-law stack. The SICC trace in this repo (`spike/trace-06/`) — Singapore IAA s 31 + the *DKT v DKU* four-condition framework — is the kind of judgment-side gate against which an L4-encoded contract could in principle be checked for bisimilarity.

| Module | Source | Used in |
|---|---|---|
| `difc_rdc_part_38` | DIFC RDC Part 38 standard-basis costs assessment | Trace #1 |
| `difc_practice_direction_4_2017` | DIFC PD 4/2017 (Interest on Judgments) + RDC 38.40 (14-day deadline) + 80% practice convention | Trace #2 |
| `difc_rdc_38_19_indemnity` | DIFC RDC 38.17 + 38.19 — indemnity-basis costs (proportionality stripped) | Trace #3 |
| `uae_civil_code_art_390` | UAE Civil Transactions Law Art 390(2) — liquidated-damages cap | Trace #4 |
| `adgm_cpr_admissions` | ADGM Court Procedure Rules 2016 — admissions and set-off arithmetic | Trace #4 |
| `english_contract_interpretation` | *Wood v Capita* / *Rainy Sky* contractual-interpretation test | Trace #5 |
| `ladd_v_marshall` | *Ladd v Marshall* [1954] 1 WLR 1489 fresh-evidence three-prong test | Trace #5 |
| `sg_iaa_s_31` | Singapore IAA s 31 (NY Convention Article V grounds) + DKT v DKU four-condition framework | Trace #6 |
| `difc_third_party_disclosure` | *Norwich Pharmacal* + *Bankers Trust* + RDC 28.52 third-party gate | Trace #7 |
| `adgm_cpr_summary_judgment` | ADGM CPR summary-judgment threshold | reusable |
| `adgm_arbitration_regulations_2015` | ADGM Arbitration Regulations 2015 — set-aside and recognition | reusable |
| `caparo_three_stage_test` | *Caparo v Dickman* [1990] duty-of-care three-stage test | reusable |

## Why these three tribunals

| | DIFC Courts | ADGM Courts | SICC |
|---|---|---|---|
| Founded | 2004 | 2013 | 2015 |
| Law system | Common-law (own statutes + Practice Directions) | Common-law (English law applied wholesale via the *Application of English Law Regulations 2015*[^adgm-aelr]) | Common-law (Singapore law; international judges may apply foreign law) |
| Digital court | Digital Economy Court (2025) | Full eCourts platform from 2018 | Cross-border commercial cases since 2015 |
| Judgment publication | HTML on-page, 5,000+ since 2007 | PDF with structured Judgment Summary, full neutral citations | HTML via elitigation.sg, structured judgments |
| Cross-border enforcement | New York Convention + UAE federal recognition | New York Convention + UAE Cabinet Resolution + Federal Law | New York Convention + Singapore *Reciprocal Enforcement of Commonwealth Judgments Act* |

ADGM's *Application of English Law Regulations 2015* is itself a constitutional artefact: a single instrument making the entire body of English common law the binding rule-of-decision. Every ADGM judgment in the gold set cites English House of Lords and Court of Appeal cases — *Caparo*,[^caparo] *Hedley Byrne*,[^hedley] *Murphy v Brentwood DC*, *Arnold v Britton*[^arnold] — directly, alongside a growing internal ADGMCFI line. ADGM has the cleanest "PR3 Rule bind" implementation we have seen in any tribunal anywhere.

## v0.2 framework

The six per-ruling primitives + two system properties replaced v0.1's seven primitives, which mixed constitutional values (separation of powers) with technical features (executable predicates) and an upstream-prevention category that does not belong on a tribunal. v0.2 separates the per-ruling layer from the architectural layer and aligns with Fuller's eight desiderata of legality[^fuller] and Hart's primary/secondary rule distinction.[^hart]

See [`data/primitives.json`](./data/primitives.json) for full definitions and the v0.1 → v0.2 mapping.

## Infrastructure

### Local Postgres + read-only API

The whole corpus also lives in a local Postgres instance (188 judgments + 978 raw documents, 355 auto-linked) so it can be queried beyond what `judgments.json` exposes:

- [`db/schema.sql`](./db/schema.sql) — 8 tables, 3 views, FTS index on extracted text
- [`scripts/postgres_local.sh`](./scripts/postgres_local.sh) — install-free control script (initdb / start / psql / schema / reset / nuke). Runs without sudo or Homebrew under `~/.local/`.
- [`scripts/migrate_to_postgres.py`](./scripts/migrate_to_postgres.py) — loads structured judgments, scrapes raw documents, infers case_no per tribunal, links raw → structured.
- [`api/server.py`](./api/server.py) — stdlib-only read-only JSON API on `127.0.0.1:5544`. Endpoints: `/api/health`, `/api/judgments`, `/api/rules`, `/api/tribunal_means`, `/api/search?q=…` (FTS), `/api/rule_modules`, `POST /api/rule_run`. The dashboard tries the API first and silently falls back to the static JSON when the server isn't running, so the public Pages build keeps working unchanged.

### Rule playground

[`dashboard/playground.html`](./dashboard/playground.html) is a schema-driven UI: pick any of the twelve rule modules, enter inputs through an auto-generated form (forms come from `catala json-schema` per module), and the predicate runs server-side via `catala interpret -F json`. The first concrete piece of the Stage-2 dispute simulator.

## Layout

```
habeas-protocol/
├── README.md                       # this file
├── paper.md                        # full working paper (~5000 words)
├── data/
│   ├── primitives.json             # v0.2 rubric + scoring + v0.1 mapping
│   ├── schema.json                 # JSON Schema (v0.1 + v0.2 supported)
│   ├── judgments.json              # 188 coded judgments
│   ├── sources.md                  # corpus provenance
│   ├── adgm_triage.json            # AI-triage classifications
│   ├── adgm_borderline_digests.json
│   ├── adgm_graded.json            # AI-graded scores + rationale
│   └── raw/
│       ├── judgments/              # 294 DIFC HTML pulls
│       ├── text/                   # DIFC stripped to plain text
│       ├── adgm/{pdfs,text,pages}/ # 175 ADGM PDFs + extracted text + page HTMLs
│       └── sicc/{html,text}/       # SICC raw + extracted
├── rules/
│   ├── clerk.toml                  # Clerk project for the rule library
│   ├── *.catala_en                 # twelve reusable rule modules
│   ├── *.schema.json               # generated JSON schemas (input + output shapes)
│   └── _index.json                 # module/scope catalogue, consumed by playground
├── db/
│   ├── schema.sql                  # 8 tables + 3 views + FTS index
│   └── queries.sql                 # 15 sample queries reproducing paper headlines
├── api/
│   └── server.py                   # stdlib-only read-only JSON API + rule runner
├── scripts/
│   ├── fetch_difc.py               # DIFC scraper
│   ├── fetch_adgm_pages.py         # ADGM scraper (plain HTTP, no API key)
│   ├── fetch_adgm_firecrawl.py     # ADGM scraper (Firecrawl fallback)
│   ├── strip_html.py               # HTML → text
│   ├── migrate_v02.py              # v0.1 → v0.2 schema migration
│   ├── migrate_to_postgres.py      # corpus → Postgres
│   ├── postgres_local.sh           # local Postgres control
│   ├── build_trace_outputs.sh      # regenerate spike/trace-*/output.json
│   ├── build_rule_schemas.sh       # regenerate rules/*.schema.json + _index.json
│   ├── triage_adgm.py              # AI three-bucket classifier
│   ├── build_digests.py            # per-case digest extractor
│   ├── grade_borderline.py         # rubric-applying grader
│   └── merge_adgm_codings.py       # merger into judgments.json
├── spike/
│   └── trace-0{1,2,3,4,5,6,7}/     # Catala rule + events.json + evaluate.py + output.json
├── dashboard/                      # interactive view (vanilla JS, hand-rolled SVG)
│   ├── index.html  app.js  styles.css
│   └── playground.html             # schema-driven rule playground
└── .github/workflows/
    └── test.yml                    # CI: typecheck + interpret 7 traces + 12 rule modules,
                                    # run 7 evaluate.py, regenerate output/schema files,
                                    # fail on drift
```

## Reproduce

> **First time?** Copy `.env.example` to `.env` and source it (`set -a; . ./.env; set +a`).
> The grading methodology — model, temperature, system prompt, run dates, and the
> open IRR / SICC PR4 validation work — is documented in `GRADING_SPEC.md`.
>
> **Prefer not to install opam / Catala / Postgres locally?** A `Dockerfile` and
> a `.devcontainer/` ship with the repo:
> ```bash
> docker build -t habeas .
> docker run --rm habeas       # runs `make test`
> ```

```bash
# Corpus pull (incremental — skips files already on disk)
python3 scripts/fetch_difc.py 25
python3 scripts/strip_html.py
python3 scripts/fetch_adgm_pages.py    # plain HTTP, no API key required

# AI codings
python3 scripts/triage_adgm.py
python3 scripts/build_digests.py
python3 scripts/grade_borderline.py
python3 scripts/merge_adgm_codings.py

# Catala traces — typecheck, interpret, and Python evaluator (7 traces)
eval $(opam env --switch=catala)       # if installed via opam
for d in spike/trace-*/; do
  catala typecheck --no-stdlib "$d/rule.catala_en"
  catala interpret --no-stdlib "$d/rule.catala_en"
  python3 "$d/evaluate.py"
done

# Rule library
for f in rules/*.catala_en; do
  catala typecheck --no-stdlib "$f"
  catala interpret --no-stdlib "$f"
done

# Local Postgres + corpus migration (~15 sec)
./scripts/postgres_local.sh init
./scripts/postgres_local.sh start
./scripts/postgres_local.sh schema
python3 scripts/migrate_to_postgres.py

# Read-only API + dashboard
eval $(./scripts/postgres_local.sh env)
python3 api/server.py &              # 127.0.0.1:5544
python3 -m http.server 8001 &        # serves dashboard at 127.0.0.1:8001/dashboard/
```

## Phase status

- **Phase 0–2** done.
- **Phase 3 (current)** done: Catala 1.1.0 toolchain installed; all seven traces compile and interpret under `catala interpret --no-stdlib`; rule library extracted as twelve reusable modules with auto-generated JSON schemas; corpus migrated to local Postgres (188 judgments, 978 raw documents, 355 linked); 18-endpoint read-only API + schema-driven rule playground + first-party Python and TypeScript clients shipped; CI exercises the full matrix on every push.
- **Open**: hand-validation of a stratified subset of the 67 newly-graded SICC entries (specifically to refine the PR4 heuristic against narrative-style grounds-of-decision); IRR exercise with an independent human Coder B against `data/irr/` (LLM-as-Coder-B explicitly excluded); further FinTech-vertical traces; permission letters to the three court registries.

## License

Code: MIT. Structured metadata under `data/`: Habeas Protocol Structured-Metadata Licence v1 (non-commercial research; takedown-respecting). Source judgments under `data/raw/` are NOT redistributed by this project (`.gitignore`'d on ToS grounds — see [`data/tos_audit.md`](./data/tos_audit.md) and [`TAKEDOWN.md`](./TAKEDOWN.md)). Full licence texts in [`LICENSE`](./LICENSE) and [`LICENSES/`](./LICENSES/).

## Project policies

- [`CONTRIBUTING.md`](./CONTRIBUTING.md) — how to file issues, submit rule modules, and engage with the certification lifecycle.
- [`SECURITY.md`](./SECURITY.md) — vulnerability disclosure (private email, coordinated release).
- [`TRADEMARK.md`](./TRADEMARK.md) — informal policy on the *Habeas Protocol* and *Maxim Labs* names; the open licences cover code and data, not the brand.
- [`rules/_certification.yaml`](./rules/_certification.yaml) — the spec for how rules move from `draft` → `submitted` → `reviewed` → `certified`.

## Citation

```
Maxim Labs, "Habeas Protocol: An Empirical Analysis of DIFC, ADGM, and Singapore
SICC as Working Prototypes for Constitutional Digital Tribunals," v0.2 (May 2026).
```

## References

[^catala]: Merigoux, Chataing, Protzenko, "Catala: A Programming Language for the Law," *PACMPL* 5, ICFP (2021). https://catala-lang.org

[^l4-deontics]: Hsu, Lim, Wong, Chun et al., "Deontics and Time in Contracts: An Executable Semantics for the L4 DSL," in *Legal Knowledge and Information Systems (JURIX 2023)*, IOS Press. The L4 DSL — developed by Legalese (`legalese.com`) with the SMU Centre for Computational Law (`cclaw.smu.edu.sg`) — is the contract-side counterpart to Catala's judgment-side encoding of statute and tribunal doctrine.

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
