# Terms-of-Service audit — primary corpus sources

**Audit date:** 2026-05-03
**Auditor:** Maxim Labs (initial pass; legal-counsel review pending)
**Scope:** the three sources from which `data/raw/` content was pulled
(DIFC Courts, ADGM Courts, eLitigation.sg / Singapore Courts).

> **Headline.** All three sources prohibit, in some form, the bulk storage
> and/or redistribution of website content that the current `data/raw/`
> directory and the `CC-BY-4.0` dataset licence assume. **Action is required
> before the next public release.**

---

## 1. DIFC Courts — `difccourts.ae`

**Source of terms:** https://www.difccourts.ae/terms-of-use
(linked from footer of https://www.difccourts.ae/)

**What the project does:** `scripts/fetch_difc.py` pulls 294 judgment HTML
pages into `data/raw/judgments/`; `scripts/strip_html.py` produces
`data/raw/text/`; both are committed and served under `CC-BY-4.0`.

**Relevant ToS clauses (verbatim):**

> "You shall not store electronically any portion of the Website Content.
> You may not copy, store, redistribute or publish any Website Content
> without the express written permission of DIFC Courts."

> "[restricted to] personal, non-commercial purposes [...] you cannot sell,
> modify or delete the Website Content or reproduce, display, publicly
> perform, distribute or otherwise use the Website Content in any way for
> any public or commercial purpose."

> "DIFC Courts owns or is an approved licensee to the copyright and all
> other intellectual property contained in the Website and the Website
> Content, including but not limited to all text, images or links."

**Disclaimer (relevant to the project's reliance disclaimers):**

> "[content is] for information purposes only [...] not intended to,
> constitute legal advice."

**Compliance assessment:**
- ❌ **Storage:** `data/raw/judgments/` and `data/raw/text/` violate
  "shall not store electronically any portion".
- ❌ **Redistribution:** committing scraped HTML/text to a public GitHub
  repo and licensing it under `CC-BY-4.0` violates the no-redistribute /
  no-republish clauses.
- ❌ **Commercial use:** any plan to charge for products built directly on
  the scraped corpus runs into "personal, non-commercial purposes only".
- ⚠ **IP:** the corpus encodes structured fields (case_no, parties, judge,
  date, primitive scores). The structured fields themselves are facts
  (likely copyright-thin in most jurisdictions); the scraped text is
  copyrighted by DIFC Courts.

**Required actions:**
1. Remove `data/raw/judgments/` (HTML) and `data/raw/text/` (stripped) from
   the public repo *or* obtain written permission from the DIFC Courts
   Registrar before the next public release.
2. Re-licence `data/judgments.json` to retain only fields that are factual
   metadata (case_no, citation, parties as published, date, claim_type,
   primitive scores, rationale) — drop any verbatim text excerpts beyond
   short quotation for criticism / review fair-dealing.
3. Replace bulk redistribution with on-demand pull: ship a scraper that
   the user runs locally; do not commit scraped content to the repo.
4. Write to the DIFC Courts Registrar (registry@difccourts.ae) requesting
   written permission for academic / research use, citing the project's
   research aim. Note that DIFC may grant a research licence given the
   project's nature; the request is the appropriate path.

---

## 2. ADGM Courts — `adgm.com` and `assets.adgm.com`

**Source of terms:** https://www.adgm.com/information/terms-and-conditions
(linked from footer of https://www.adgm.com/)

**What the project does:** `scripts/fetch_adgm_pages.py` and
`scripts/fetch_adgm_firecrawl.py` pull 175 ADGM judgment PDFs into
`data/raw/adgm/pdfs/`; extracted text in `data/raw/adgm/text/`; committed
and served under `CC-BY-4.0`.

**Relevant ToS clauses (verbatim):**

> "You must not reproduce or store any part of this site on any other
> website or include it in any public or private electronic retrieval
> system or service, without our prior written permission."

> "[material downloaded may only be used for] personal or internal
> organizational viewing. Distribution to third parties or commercial
> circulation is prohibited, except that extracts (of no more than a few
> relevant provisions) are copied to individual third parties incidental
> to advice or other activities."

> "Unless otherwise stated, ADGM owns the copyright and any other rights
> in all material on this site."

**Compliance assessment:**
- ❌ **Storage on another site:** committing PDFs and extracted text to a
  public GitHub repo is a textbook violation of "must not reproduce or
  store any part of this site on any other website or include it in any
  public or private electronic retrieval system."
- ❌ **Redistribution:** the `CC-BY-4.0` dataset licence purports to allow
  the public to redistribute and even commercialize the material — ADGM's
  ToS forbids both.
- ⚠ **Fair-extract carve-out:** the ToS allows quoting "a few relevant
  provisions [...] incidental to advice or other activities." A research
  paper quoting paragraphs of judgments under criticism/review is likely
  defensible; redistributing the full corpus is not.
- ⚠ **OFAC clause:** ADGM ToS notes that services are not provided to
  OFAC-sanctioned jurisdictions — relevant for any future commercial
  offering's geographic restrictions.

**Required actions:**
1. Remove `data/raw/adgm/pdfs/` and `data/raw/adgm/text/` from the public
   repo. Replace with a fetcher that downloads PDFs locally on demand.
2. Same `data/judgments.json` re-licensing as for DIFC: keep factual
   metadata + scores; remove verbatim long-form excerpts.
3. Write to ADGM Courts Registry (court.registry@adgm.com) requesting
   written permission for academic / research redistribution.

---

## 3. Singapore International Commercial Court — `elitigation.sg`

**Source of terms:** https://www.judiciary.gov.sg/terms-of-use
(eLitigation.sg is operated by the Singapore Courts; the Judiciary's
site-wide terms of use govern the corpus.)

**What the project does:** `scripts/fetch_sicc.py` and
`scripts/fetch_sicc_more.py` pull SICC HTML / extracted text into
`data/raw/sicc/{html,text}/`; committed and served under `CC-BY-4.0`.

**Relevant ToS clauses (verbatim):**

> "no part of The Website may be reproduced or reused for any commercial
> purposes whatsoever without our prior written permission"

> "The intellectual property rights in the materials is owned by or
> licensed to us. All rights reserved."

> "Apart from any fair dealings for the purposes of private study,
> research, criticism or review, as permitted in law..."

**Compliance assessment:**
- ✅ **Research fair-dealing:** Singapore Copyright Act 2021 ss 190–196
  permit fair dealing for "research or study" and for "criticism, review
  and reporting current events". A non-commercial research paper that
  quotes judgments and publishes derived scores is the canonical example
  of fair dealing.
- ❌ **Commercial use:** the project's stated commercial direction
  (Maxim Labs offering paid products) is incompatible without written
  permission. Singapore is the strictest of the three on commerce.
- ⚠ **Redistribution under `CC-BY-4.0`:** redistributing scraped Singapore
  judgment text under a licence that *expressly permits* commercial
  re-use is incompatible with the source's ToS. This is the case even if
  *Maxim Labs* itself is not commercial — `CC-BY-4.0` lets a downstream
  user be commercial, which the source forbids.
- ⚠ **Singapore Government Open Data:** Singapore operates `data.gov.sg`
  under the Singapore Open Data Licence (more permissive). SICC judgments
  are NOT on `data.gov.sg`; the Judiciary terms govern. Verify with each
  pull.

**Required actions:**
1. Limit SICC redistribution to fair-dealing-compliant excerpts (short
   quotations within criticism / review). Remove `data/raw/sicc/{html,text}`
   bulk content from the public repo.
2. Drop `CC-BY-4.0` for the SICC subset; replace with a custom data licence
   that mirrors fair dealing — i.e., research-only, non-commercial,
   takedown on request.
3. Write to the Singapore Courts (`siccs@judiciary.gov.sg` or the
   eLitigation helpdesk) requesting written permission for any
   commercial-tier redistribution, or operate strictly under fair dealing
   without redistribution.

---

## 4. Repository-wide changes required

### 4.1 Remove or gate raw content

The following directories contain content the source ToS prohibit
redistributing:

```
data/raw/judgments/        # 294 DIFC HTML files          (gitignored ✓)
data/raw/text/             # DIFC stripped text           (gitignored ✓)
data/raw/adgm/pdfs/        # 175 ADGM PDFs                (gitignored ✓)
data/raw/adgm/text/        # ADGM extracted text          (gitignored ✓)
data/raw/adgm/pages/       # ADGM HTML pages              (gitignored ✓)
data/raw/sicc/html/        # SICC HTML                    (gitignored ✓)
data/raw/sicc/text/        # SICC extracted text          (gitignored ✓)
spike/judgments/*.html     # Phase 0 spike DIFC HTML      (gitignored ✓; 26 files still tracked — needs `git rm --cached`)
spike/text/*.txt           # Phase 0 spike stripped text  (gitignored ✓; needs `git rm --cached`)
```

**Status (2026-05-03):** all eight paths are now gitignored. The
`tos-guard` CI job at `.github/workflows/test.yml` enforces the policy
on every push: builds fail if any `.html`, `.txt`, or `.pdf` file is
tracked under `data/raw/`, `spike/judgments/`, or `spike/text/`. The
fetcher scripts remain so each researcher rebuilds locally.

**Outstanding cleanup:** the 26 spike HTML files + spike text files
were already tracked at the time `.gitignore` and the CI guard were
added. Run the following to untrack them (preserves working-tree
copies for local research):

```bash
git rm --cached spike/judgments/*.html spike/judgments/_listing*.html
git rm --cached spike/text/*.txt
git commit -m "tos: untrack spike-phase raw DIFC HTML per data/tos_audit.md"
```

For full historical scrubbing (removing the files from prior commits),
a `git filter-repo` or `bfg-repo-cleaner` pass is required. That is a
destructive history-rewriting operation; the repository owner should
run it after coordinating with any collaborators or downstream forks.

### 4.2 Re-licence `data/judgments.json`

Current header (implicit `CC-BY-4.0`):
- ❌ unsafe given DIFC + ADGM ToS prohibit reproduction.

Replace with **factual-metadata-only** content (case_no, citation,
parties as published in caption, date, claim_type, scores, rationale —
no verbatim long-form excerpts) under a custom licence:

> "Habeas Protocol structured-metadata licence v1: factual metadata may
> be reused for non-commercial research with attribution. Any verbatim
> quotation of source judgments retained in this file is reproduced under
> the fair-dealing exception in the source jurisdiction (Singapore
> Copyright Act 2021 ss 190–196 / equivalent UAE provisions / standard
> common-law criticism-and-review)."

### 4.3 Update `LICENSE` and `LICENSES/`

- Keep MIT for `code` (scripts, evaluators, dashboard JS).
- Replace `CC-BY-4.0` for `data` with the structured-metadata licence
  above. State explicitly that the licence does NOT extend to source
  judgment text, which remains the property of the issuing court.
- Add `LICENSES/THIRD-PARTY-RIGHTS.md` summarising this audit.

### 4.4 Add a `data/PROVENANCE.md` per source

Per the data-sheet recommendation in the previous review, document for
each source: collection date, scraper version, ToS at time of pull,
known biases, intended use, and contact for takedown.

### 4.5 Takedown procedure

Add to `SECURITY.md` (or a new `TAKEDOWN.md`):

> "If you are a court registrar or rightsholder and identify content in
> this repository that you wish removed, email <takedown contact>. We
> will remove disputed material within 7 days pending verification."

### 4.6 Permission-request letters

Draft three letters (one each to DIFC, ADGM, Singapore Courts) requesting
written permission for academic / research redistribution. Even if denied,
the request itself documents good faith. Templates to be added under
`docs/permission_request_template.md`.

---

## 5. Practical roadmap

| Priority | Action                                                               | Owner          | Target      |
|---------:|----------------------------------------------------------------------|----------------|-------------|
| P0       | Remove `data/raw/**` from `main`; add to `.gitignore`               | repo owner     | this week   |
| P0       | Replace `CC-BY-4.0` data licence with structured-metadata licence   | repo owner     | this week   |
| P0       | Add `TAKEDOWN.md` + takedown contact                                | repo owner     | this week   |
| P1       | Send permission-request letters to all three registrars             | repo owner     | this month  |
| P1       | Add `data/PROVENANCE.md` per source                                 | repo owner     | this month  |
| P1       | Update CI to skip steps requiring raw content if not present       | repo owner     | this month  |
| P2       | Counsel review of UAE / Singapore re-distribution exposure          | UAE counsel    | within 60d  |

---

## 6. Self-criticism

This audit was conducted by reading the public ToS pages without legal
counsel. A qualified lawyer (UAE-licensed for DIFC + ADGM, Singapore-
licensed for SICC) should review the conclusions before any action that
depends on them — particularly the fair-dealing assessment for Singapore
and the IP scope question for the structured metadata.

The audit also does not cover: (a) UAE federal copyright law (Federal
Decree-Law No. 38 of 2021); (b) ADGM's own intellectual property
regulations; (c) DIFC Law No. 8 of 2004 (Data Protection); (d) any
implicit Crown / Government Copyright claim on Singapore judgments under
Singapore's Government Information Notice. These all require licensed
counsel.

The recommended path of "permission-request letters" is the
conservative, documentable route. A more aggressive position — that
factual judicial output is in some sense res publica, and that
research-tier redistribution falls within copyright limitations — is
defensible but must be backed by counsel willing to sign opinion letters.
The project should not adopt the aggressive position without that
backing.
