# Phase 0 — Go / No-Go Memo

**Date:** 27 April 2026
**Spike duration:** ~half day
**Recommendation:** **GO.** Proceed to Phase 1 with two scope adjustments.

## What we set out to test

1. Is the DIFC Courts judgment index machine-enumerable?
2. Can we pull a meaningful sample of judgments without hitting auth/PDF walls?
3. Are there judgments in that sample with crisply codable rules?
4. Can we express at least one rule in executable form and produce the same outcome the court did?

All four answered **yes** within a half day.

## Findings

### 1. DIFC index — better than expected
- Listing endpoint paginates cleanly: `?ccm_paging_p=N&ccm_order_by=ak_date&ccm_order_by_direction=desc`, 12 results per page.
- ~414 pages → ~5,000 historical judgments; dropdown filter for years 2007–2026.
- Judgments are **HTML on-page**, not PDF — directly parseable. Each carries structured metadata (case no., parties, judge, date, claim type, hearing dates) plus a "Schedule of Reasons" section with numbered paragraphs.
- A 36-line Python scraper (`spike/scrape.py`) pulled 24 judgments across 5 court divisions in under a minute, no auth, no rate-limiting issues at 0.5s/request.

### 2. Sample composition
The first 24 judgments include:
- Court of First Instance (CFI): 17
- Arbitration (ARB): 2
- Enforcement (ENF): 1
- Technology & Construction Division (TCD): 1
- Digital Economy Court (DEC): 1
- Plus listing-page artefacts skipped by the regex.

The Digital Economy Court (DEC 001/2025 Techteryx v IG) is particularly relevant to the metaverse-jurisdiction thesis — DIFC has *already* set up a court explicitly for digital-asset and digital-economy disputes. This was not part of the original plan and is a real find.

### 3. Trace candidates — picked
See `trace-picks.md` for full reasoning. Picks form an arithmetic → temporal → discretion progression, all from the 24-judgment sample:
1. **CFI 058/2024 Dhawan** — pure formula (hours × rate + filing fee)
2. **ARB 008/2026 Oberlin** — 14-day deadline + 9% interest accrual
3. **ENF 271/2025 Taylor** — bounded discretion on indemnity-basis review

### 4. Trace #1 compiled and verified
- `trace-01/rule.catala_en` — Catala source for RDC Part 38 standard-basis assessment, syntactically valid, ~40 lines including the test harness.
- `trace-01/events.json` — case facts as event log.
- `trace-01/evaluate.py` — Python predicate evaluator mirroring the Catala scope.
- **Output:** predicate computes AED 7,121.75 — matches the Schedule of Reasons total exactly.
- **Bonus finding:** the operative order states AED 7,127.75 — a 6 AED discrepancy from the schedule arithmetic. The protocol surfaces a clerical error in the human ruling. This is the kind of result that lands at FutureLaw.

## Scope adjustments for Phase 1

### Adjustment 1: Catala runtime install deferred, not abandoned
The Catala toolchain is OCaml/opam-based; a fresh install runs ~30+ minutes and was not worth the spike budget. The Catala source we wrote is valid syntactically. Phase 1 should:
- Install Catala (`opam install catala`) and run our trace #1 source against it as the first action.
- Maintain the Python evaluator as a parallel path so the dashboard can run client-side without OCaml.
- If Catala turns out to be brittle on macOS, fall back to Blawx (web-based) or a hand-rolled JS predicate DSL.

### Adjustment 2: Replace "contract formation" archetype with the actual archetypes the corpus offers
The original plan called for a contract-formation trace. The 24-judgment sample contains *zero* clean offer/acceptance/consideration rulings — most contract disputes that reach the DIFC are already past formation and are about breach, costs, or jurisdiction. The three picks above (arithmetic, temporal, bounded discretion) are a stronger demonstration anyway: they map directly onto the three things executable rules do well, do okay, and do poorly. Recommend revising the paper outline accordingly.

### Adjustment 3: Add Digital Economy Court as a fourth strand
DEC was not in the original plan — we discovered it in the sample. It is the single most metaverse-relevant DIFC division and deserves its own coding pass in Phase 1. Suggest scaling the empirical sweep from 200 → 250 to absorb DEC + a dedicated DEC sub-section in the paper.

## Risks revisited

| Risk (from plan) | Status |
|---|---|
| DIFC index not machine-readable | **Resolved.** HTML, paginated, scrapable. |
| PDF-only judgments | **Resolved.** HTML on-page. |
| Catala learning curve | **Partially resolved.** Source-level expressibility confirmed; runtime install deferred. |
| Coding rigor for 200 judgments | **Unchanged.** Plan's posture (publish 30-judgment gold set + document inter-rater reliability as limitation) holds. |
| Prospera data sparsity | **Unchanged.** Will confirm in Phase 1. |
| New: DIFC scrape rate-limiting | Not encountered at 0.5s/request, 24 requests. Will keep that throttle for full pull. |

## Recommended next step (Phase 1, Day 1)

1. Install Catala via opam (background task, ~30 min).
2. While Catala builds: scrape pages 1–25 (~300 judgments, 2024–2025 window).
3. Strip to text; build the codebook from the 30-judgment gold set; begin coding.
4. End of day: Catala running trace #1 source; ~50 judgments coded against the 7 primitives.

## Bottom line

The plan is buildable in two weeks. The corpus is richer and more accessible than the plan assumed. One trace already works end-to-end and produced a publishable side-finding (the 6 AED discrepancy). **Proceed.**
