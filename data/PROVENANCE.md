# Corpus provenance

Per-source documentation for the structured metadata in `data/judgments.json`.
For the underlying ToS analysis and required actions, see `data/tos_audit.md`.

The `data/raw/` directory is **not** in this repository. Researchers
rebuild raw bytes locally via `scripts/fetch_*.py` under their own
personal-research fair-dealing posture. The structured metadata below
is what the project redistributes (under `LICENSES/HABEAS-METADATA.txt`).

---

## DIFC Courts

- **Source URL pattern:** https://www.difccourts.ae/rules-decisions/judgments-orders
- **Scraper:** `scripts/fetch_difc.py` (raw HTTP, no API key)
- **Stripper:** `scripts/strip_html.py`
- **Last pull:** April 2026 — 294 HTML pages spanning recent DIFC output
  across the Court of First Instance (CFI), Court of Appeal (CA), Arbitration
  Division (ARB), and Enforcement Division (ENF).
- **Coded n:** 32 (first-pass-claude; AI-coded with Claude Sonnet 4.5).
- **ToS at pull time:** https://www.difccourts.ae/terms-of-use, asserting
  copyright and prohibiting electronic storage / redistribution of website
  content. See `data/tos_audit.md` §1 for verbatim clauses.
- **Intended use:** non-commercial academic research; criticism and review;
  procedural-form rubric scoring.
- **Anonymisation posture:** none applied at our end — DIFC publishes party
  names directly, and where the court anonymised (e.g. arbitration parties
  designated by reference codes), we preserve the court's anonymisation.
- **Known biases:** sample is balanced toward costs and case-management
  orders, which dominate DIFC published output. Substantive matters are
  under-represented. PR6 (enforcement bridge) consequently shows a floor
  of 1.44 driven by intra-jurisdictional CMS orders that score PR6=1 by
  rubric design.
- **Takedown contact:** see `TAKEDOWN.md`.

---

## ADGM Courts

- **Source URL pattern:** https://www.adgm.com/adgm-courts/judgments and
  asset PDFs at https://assets.adgm.com/download/assets/...
- **Scrapers:**
  - `scripts/fetch_adgm_pages.py` (raw HTTP, no API key)
  - `scripts/fetch_adgm_firecrawl.py` (Firecrawl fallback for JS-rendered
    listing pages)
- **Stripper:** `scripts/strip_html.py` (HTML); native PDF text extraction
  for `data/raw/adgm/pdfs/`.
- **Last pull:** April 2026 — 174 ADGM PDFs spanning 2017–2026.
- **Coded n:** 76 (7 first-pass-claude + 16 heuristic-triage + 53 heuristic-graded).
- **ToS at pull time:** https://www.adgm.com/information/terms-and-conditions,
  asserting copyright and prohibiting reproduction or storage on another
  website / public retrieval system. See `data/tos_audit.md` §2 for
  verbatim clauses.
- **Intended use:** non-commercial academic research; criticism and review.
- **Anonymisation posture:** ADGM publishes Judgment Summary templates with
  full party identification; we preserve as published.
- **Known biases:** ADGM PR2 = 2.00 by construction in the heuristic-triage
  tier (Judgment Summary template scores PR2 ceiling automatically).
  Reported in §3 of `paper.md` as a methodological caveat. Procedure-tier
  per-primitive comparison (`paper.md` §4.6, `data/robustness/adgm_procedure_comparison.json`)
  shows the three procedure tiers (first-pass, heuristic-triage, heuristic-graded)
  produce overall means within ±0.02 of each other on ADGM.
- **Takedown contact:** see `TAKEDOWN.md`.

---

## Singapore International Commercial Court (SICC)

- **Source URL pattern:** https://www.elitigation.sg/gd/sic/<slug> via the
  paginated SICC listing at
  https://www.elitigation.sg/gd/Home/Index?Filter=SICC&...
- **Scrapers:**
  - `scripts/fetch_sicc.py` (initial Firecrawl-based pull, n=13, April 2026)
  - `scripts/fetch_sicc_more.py` (Firecrawl page-2 expansion)
  - `scripts/fetch_sicc_direct.py` (no-Firecrawl direct fetcher, May 2026,
    pulled the additional 67 entries that took SICC to n=80)
- **Stripper:** `scripts/strip_html.py` style markup-stripping; native to the
  direct fetcher.
- **Last pull:** May 2026 — 80 HTML grounds-of-decision documents spanning
  SICC and SICC-CA judgments from 2023 through April 2026.
- **Coded n:** 80 (all heuristic-graded via `scripts/triage_sicc.py`; PR4 recoded with Claude via `scripts/recode_sicc_pr4_claude.py` — see §4.9 of `paper.md`).
- **ToS at pull time:** https://www.judiciary.gov.sg/terms-of-use, asserting
  IP rights and prohibiting commercial reproduction. Singapore Copyright Act
  2021 ss 190–196 (fair dealing for research / criticism / review) is the
  carve-out under which we operate. See `data/tos_audit.md` §3 for verbatim
  clauses.
- **Intended use:** non-commercial academic research; criticism and review.
- **Anonymisation posture:** SICC publishes anonymised codes (e.g. "DVA v
  DVC", "DNZ v DOA") for sensitive matters; we preserve as published.
- **Known biases:**
  - **PR4 heuristic limitation.** SICC writes integrated-narrative grounds-
    of-decision rather than the canonical "notice → hearing → decision"
    structural triplet that `scripts/triage_sicc.py` looks for. The regex
    produces PR4 = 1.55 on the n=80 corpus. The Claude-recoded PR4
    (`scripts/recode_sicc_pr4_claude.py`, prompt explicitly instructed to
    recognise narrative procedural form) is the corrected measurement and
    enters the headline SICC mean. The regex result is retained in
    `data/robustness/sicc_pr4_regex.json` as the known-flawed measurement.
    Reported in `paper.md` §4.1 and §4.9.
  - **Time bias.** Sample is concentrated 2024–2026; pre-2023 SICC output
    under-represented.
- **Pipeline notes:**
  - `triage_sicc.py` recognises both SGHC(I) (Singapore International
    Commercial Court) and SGCA(I) (Singapore Court of Appeal,
    International) citation patterns, with SGCA(I) preferred when both
    appear (an SGCA(I) appellate decision repeatedly cites the
    appealed-from SGHC(I) ruling in its body). SGCA(I) entries use
    `CA N/YYYY` format for `case_no`, distinct from SICC's `OA N/YYYY`,
    so the two never collide on the structured-metadata key.
  - The Postgres schema's unique key on the `judgments` table is
    `(tribunal_code, case_no, neutral_citation)` — accommodating the
    legitimate case where one Originating Application produces multiple
    distinct judgments (e.g. interim ruling + substantive ruling +
    costs order, each with its own neutral citation).
- **Takedown contact:** see `TAKEDOWN.md`.

---

## Falsification set instruments

- **File:** `data/falsification_set.json` (n=30 across 5 classes).
- **Provenance:** `coder: MaximLabs (provisional-class-default)`. Each entry
  is a **class-level** scoring of the instrument *type* (e.g. "ICC Court of
  Arbitration as a class") rather than a named case. Hand-validation against
  ≥3 specific instruments per class is required before any of these scores
  are reported in publication.
- **No source-content redistribution.** Entries reference public institutional
  URLs (https://iccwbo.org/, https://kleros.io/, https://www.fca.org.uk/, etc.)
  but do not store or redistribute scraped content.
- **Built by:** `scripts/build_falsification_set.py`.

## Peer-court comparison set

- **File:** `data/comparison_set.json` (n=90 across 3 courts × 30 case-type slots).
- **Provenance:** `coder: MaximLabs (provisional-class-default)`. Slots are
  `case_no: null` placeholders awaiting binding to named citations.
- **No source-content redistribution.** Entries reference public institutional
  URLs (BAILII, courts.delaware.gov, ICCP-CA Paris) but do not store scraped
  content.
- **Built by:** `scripts/build_comparison_set.py`.

---

## Re-deriving the corpus

Anyone can rebuild `data/raw/` locally:

```bash
python3 scripts/fetch_difc.py 25
python3 scripts/strip_html.py
python3 scripts/fetch_adgm_pages.py        # plain HTTP
python3 scripts/fetch_adgm_firecrawl.py    # if FIRECRAWL_KEY set
python3 scripts/fetch_sicc_direct.py --target-n 80
```

This places raw bytes under `data/raw/` (gitignored). Operating under your
own jurisdiction's research-fair-dealing rules is your responsibility.
The structured metadata in `data/judgments.json` is regenerated from the
raw via the `triage_*` and `merge_*` scripts.
