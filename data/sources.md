# Sources

## Sampling frame and bias direction (read first)

The 188-judgment corpus is a **convenience sample**, not a random
draw from any defined population. Per tribunal:

- **DIFC** (n=32): the first 32 judgments returned by
  `scripts/fetch_difc.py` from the difccourts.ae listing endpoint
  (paginated April 2026). The full scrape returned ~294 unique
  judgments saved as HTML; the 32 coded entries are the first
  page-by-page fetched, not a stratified or random sample of the
  ~5,000+ judgments in the historical DIFC index.
- **ADGM** (n=76): the 76 PDFs returned by
  `scripts/fetch_adgm_pages.py` and `scripts/fetch_adgm_firecrawl.py`
  from the adgm.com listing pages (April 2026), spanning 2017–2026.
- **SICC** (n=80): the 80 HTML grounds-of-decision documents
  returned by `scripts/fetch_sicc_direct.py` from elitigation.sg
  (April–May 2026), spanning 2023–2026.

**Bias direction:** the sample is biased toward judgments that are
**findable** (indexed in the public listing), **recent** (the date
ranges above), **well-formatted** (parseable by the scrapers
without manual recovery), and **English-language**. It is
specifically *not* a random draw, and it is *not* claimed to be
representative of the population of all rulings each tribunal has
ever issued.

The pre-registration (`PREREGISTRATION.md` §2) states the same
sampling frame for any future analysis run on this corpus.

---

## Primary corpus — DIFC Courts

- **Index:** https://www.difccourts.ae/rules-decisions/judgments-orders
- **Pagination:** `?ccm_paging_p=N&ccm_order_by=ak_date&ccm_order_by_direction=desc`, 12 per page, ~414 total pages.
- **Phase 1 pull:** pages 1–25, retrieved 27 April 2026, 294 unique judgments saved as HTML in `data/raw/judgments/` and stripped to text in `data/raw/text/`.
- **Format:** HTML on-page, structured with case number, parties, judge, date, "Schedule of Reasons" body.
- **Rules instruments cited across the corpus:**
  - Rules of the DIFC Courts (RDC), various Parts
  - DIFC Court Law No. 2 of 2025
  - Various Practice Directions (e.g. Practice Direction No. 4 of 2017 on Interest on Judgments)

## Co-primary corpus — ADGM Courts

- **Index:** https://www.adgm.com/adgm-courts/judgments
- **Format:** PDF behind asset URLs at `assets.adgm.com/download/assets/...`. Two artefact types per case:
  - **Judgment Summary** — fixed-template ~5KB PDF with neutral citation, parties, judge, catchwords, legislation cited, cases cited, executive summary
  - **Full Judgment** — sealed PDF, ranges from ~25KB to 300KB
- **Phase 1.5 pull:** landing-page (page 1, ~15 PDFs), retrieved 27 April 2026, in `data/raw/adgm/pdfs/` + extracted text in `data/raw/adgm/text/`.
- **Pagination:** JS-rendered. Static fetch yields ~15 PDFs (covering ~11 distinct cases). Deeper pull requires headless browser pass — deferred to Phase 2.
- **Rules instruments cited across the corpus:**
  - ADGM Court Procedure Rules 2016
  - ADGM Application of English Law Regulations 2015
  - ADGM Financial Services and Markets Regulations 2015
  - ADGM Real Property Regulations 2024
  - ADGM Insolvency Regulations 2015 / 2022
  - ADGM Practice Directions (e.g. PD 7, PD 8)
  - UAE Federal Law No. 2 of 2015 (Commercial Companies)
  - UAE Federal Law No. 5 of 1985 (Civil Transactions)
  - Cabinet Resolutions (e.g. No. 41 of 2023 — Al Reem Island incorporation into ADGM)
- **Notable:** the **Application of English Law Regulations 2015** is the constitutional move that makes ADGM uniquely "habeas-clean" on Rule Bind (PR3) — it explicitly imports English common law as the rule of decision, so every ADGM judgment cites English HL/CA precedent directly.

## Secondary corpus — Dubai VARA

- **Index:** https://www.vara.ae/en/regulations/regulatory-notices/
- **Format:** Press-release-style notices, not structured judgments. Five notices identified for 2024–2025 plus an Aug-2024-to-Aug-2025 enforcement summary covering 36 firms.
- **Penalty range:** AED 50,000 to AED 600,000; statutory maximum AED 10M.
- **Phase 1 status:** structure documented; per-notice scraping deferred to Phase 2 — would add a meaningful ~5 first-pass items (not 30, as the plan assumed).
- **Rules instrument:** VARA Rulebook (versioned, public, available at https://rulebooks.vara.ae/).

## Tertiary corpus — Próspera Arbitration Center (PAC)

- **Status:** No published PAC awards located via public web search (27 April 2026).
- **What does exist:** PAC is the default arbitration body for the Próspera ZEDE under the Organic Law; awards are internationally enforceable via NY/Panama Conventions. The center's structure and rules are public, but individual awards are not published.
- **Adjacent case:** *Honduras Próspera Inc. et al. v. Republic of Honduras* (ICSID Case No. ARB/23/2). This is an investor-state arbitration *about* the ZEDE's destruction by the Honduran state, not a PAC award. Decision on Preliminary Objections issued 26 February 2025.
- **Phase 1 status:** Próspera relegated to *design-only comparator* as the Phase 0 memo anticipated. The comparison strand becomes "DIFC (operating tribunal) vs. VARA (operating regulator) vs. Próspera (designed-but-empirically-dark)." That's actually a useful three-axis comparison — Próspera shows what a tribunal *plan* without a public record looks like, which is itself informative for the protocol thesis.

## Citation form for the dataset

When citing a coded judgment, use the case number plus the canonical URL. When citing a primitive score, use the form `CFI-058-2024 / P1=2 / RDC 38.7 cited`.
