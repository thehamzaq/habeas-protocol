# Habeas Protocol — corpus grading specification (v0.2)

This document records the grading methodology for the 188-judgment
corpus. The grading-process spec is public so the empirical claims
(`paper.md` §4) are reproducible.

## Three grader types

The repository uses three grader types, recorded per-entry in
`coding.grader_type`. The 188-judgment corpus
(`data/judgments.json`) uses two of them; the falsification set
(`data/falsification_set.json`, n=30) and the peer-court comparison
set (`data/comparison_set.json`, n=90) use the third.

| Grader type             | n (corpus) | n (falsif) | n (compare) | Method |
|-------------------------|----------:|----------:|----------:|--------|
| `llm`                   |   39 |  0 |  0 | Claude Sonnet 4.5 reads each judgment and applies the v0.2 rubric. |
| `regex_heuristic`       |  149 |  0 |  0 | Pattern-based scorer in Python; no LLM in the loop. |
| `author_class_default`  |    0 | 30 | 90 | Author-assigned class-level default reflecting the published structural form of the instrument class. NOT a per-instance grading; binds to a named class (e.g. "ICC sealed arbitral awards" or "English Commercial Court costs orders"), not to a specific case. |

The three grader types are separate measurement instruments and must
be reported separately. In particular, the falsification set (§4.3 of
`paper.md`) and the peer-court comparison set (§4.4) score *classes*
of instrument, not specific named cases. Per the paper, binding each
class default to ≥ 3 specific named instruments per class plus
practitioner review is open work before any of these scores are
reported in publication-grade citations.

## Procedure tiers (per `coding.coder`)

| Procedure tier                    | `coding.coder` value                | n   | Grader type     |
|-----------------------------------|-------------------------------------|----:|-----------------|
| First-pass                        | `MaximLabs (first-pass-claude)`     |  39 | `llm`           |
| Heuristic-triage (ADGM, document-type defaults) | `MaximLabs (heuristic-triage)` |  16 | `regex_heuristic` |
| Heuristic-graded (full per-primitive regex)     | `MaximLabs (heuristic-graded)` | 133 | `regex_heuristic` |

## Per-tribunal split (n = 188)

| Tribunal | n  | First-pass (LLM) | Heuristic-triage (regex) | Heuristic-graded (regex) |
|----------|---:|-----------------:|-------------------------:|-------------------------:|
| DIFC     | 32 |               32 |                        0 |                        0 |
| ADGM     | 76 |                7 |                       16 |                       53 |
| SICC     | 80 |                0 |                        0 |                       80 |

## Grader 1 — LLM-graded first-pass set (n=39)

32 DIFC + 7 ADGM judgments. Procedure:

1. Each judgment text is loaded into a single Claude API call.
2. The system prompt is captured at `scripts/ai_grade_prompt_v0_2.txt`;
   its SHA256 is recorded in each entry's
   `coding.system_prompt_sha256`.
3. The grader receives the literal v0.2 rubric (full text of
   `data/primitives.json`) plus an adversarial-auditor instruction
   ("Score each primitive 0/1/2 on the scale defined; do NOT
   speculate; if the document is silent, return -1; return strict
   JSON").
4. The grader's JSON response populates `coding.primitive_scores_v02`
   plus `coding.rationale` per primitive.

API parameters:

| Parameter         | Value                              |
|-------------------|------------------------------------|
| Provider          | Anthropic API                      |
| Model             | `claude-sonnet-4-5-20250929`       |
| Temperature       | 0.0 (deterministic)                |
| Max output tokens | 1024                               |

Run date: 2026-04-27. Per-entry provenance fields pinned:
`grader_type: llm`, `model`, `temperature`, `prompt_template_id`,
`system_prompt_sha256`, `run_date`.

## Grader 2 — Regex heuristic, structural defaults (n=16, ADGM)

`scripts/triage_adgm.py` matches a fixed regex set against the raw
judgment text and assigns one of two structural defaults *derived from
document type*. This is **not** a graded application of the rubric;
it is a document-type classifier with rubric-aligned defaults.

- **Saturating "Judgment Summary" template** → `(2, 2, 2, 2, 2, 2)`.
  ADGM publishes a canonical Judgment Summary template (Neutral
  Citation / Cases Cited / Legislation Cited / Overall Summary
  headers) that saturates the per-ruling primitives by construction.
  9 of the 16 fall here.
- **Case-management default** → `(2, 2, 2, 2, 2, 1)`. PR6=1 follows
  the rubric for case-management orders that lack an explicit
  cross-border enforcement bridge. 7 of the 16 fall here.

Tagged `coding.coder = "MaximLabs (heuristic-triage)"`,
`coding.grader_type = "regex_heuristic"`,
`coding.grader_script = "scripts/triage_adgm.py"`. Downstream analyses
can filter these entries out where structural defaults would inflate
the per-primitive means.

## Grader 3 — Regex heuristic, per-primitive scoring (n=133)

Two scripts produce this tier:

- **ADGM (n=53) — `scripts/grade_borderline.py`.** Reads each judgment
  text and applies regex-based scoring per primitive:
  - PR1 = 2 if both party names and judge name match patterns; 1 if
    one of the two; 0 if neither.
  - PR2 = 2 if a publication date is present *and* ≥2 dated body
    references match the regex; 1 if a date is present but record is
    sparse; 0 if no date at all.
  - PR3 = 2 if ≥2 numbered clause citations match the body regex; 1
    if only 1 specific cite or only general references; 0 if no cite
    at all.
  - PR4 = 2 if outcome phrase + (claim type or catchwords showing
    procedural sequence); 1 if outcome present but procedure thin; 0
    if neither.
  - PR5 = 2 if ≥1 outcome-phrase regex match OR catchwords describe
    outcome OR last 30 lines contain operative-verb regex; 1 if
    directional only; 0 if no outcome.
  - PR6 = 2 if ≥1 enforcement-bridge regex match; 1 otherwise; 0 only
    if the document is so degraded that it has no enforcement
    framing at all.

- **SICC (n=80) — `scripts/triage_sicc.py`.** Pattern-based heuristic
  over an extended marker set (whitespace-tolerant enforcement-bridge
  terms, plural-tolerant clause citations, broader operative-verb
  regex) plus a `rationale` field per entry. The PR4 marker set is
  regex-based and underscores PR4 on SICC's narrative-style
  grounds-of-decision documents (the regex looks for four structural
  markers and requires ≥3 to score PR4=2; SICC's narrative grounds
  defeat one or more markers in many otherwise procedurally-regular
  cases).

Tagged `coding.coder = "MaximLabs (heuristic-graded)"`,
`coding.grader_type = "regex_heuristic"`. Run dates: ADGM 2026-04-12,
SICC 2026-04-29.

## SICC PR4 — corrected with Claude

`scripts/recode_sicc_pr4_claude.py` re-grades PR4 for the 80 SICC
entries using Claude Sonnet 4.5 with a prompt explicitly instructed
to recognise narrative procedural form (hearing event / decision
date / named coram / reasons-or-grounds-of-decision section,
*including in narrative form*, not only via structural markers). The
corrected PR4 enters the headline SICC mean reported in `paper.md`
§4.6. The regex result is retained in
`data/robustness/sicc_pr4_regex.json` as the known-flawed
measurement.

## Per-entry provenance schema

Every entry in `data/judgments.json`,
`data/falsification_set.json`, and `data/comparison_set.json`
carries a `coding` object. Schema:

```json
"coding": {
  "coder": "MaximLabs (first-pass-claude)" |
           "MaximLabs (heuristic-triage)"  |
           "MaximLabs (heuristic-graded)"  |
           "MaximLabs (provisional-class-default)",
  "grader_type": "llm" | "regex_heuristic",
  "first_pass": true | false,
  "run_date": "YYYY-MM-DD",

  // For grader_type == "llm":
  "model": "claude-sonnet-4-5-20250929",
  "temperature": 0.0,
  "prompt_template_id": "v0_2_grade",
  "system_prompt_sha256": "<sha>",

  // For grader_type == "regex_heuristic":
  "grader_script": "<script path>",

  "notes": "<free-form coder note>",
  "rationale": "<per-primitive rationale, where present>"
}
```

For entries coded before the schema was pinned (April 2026), missing
fields are populated as `"unknown"` rather than backfilled.

## Training-data contamination — applies to LLM-graded entries only

For the 39 LLM-graded entries: Claude's training corpus likely
includes published DIFC and ADGM judgments dated before its training
cutoff. To the extent that the AI grader's outputs reflect recall of
the underlying judgments rather than independent application of the
rubric, those scores are not statistically independent of the
judgments themselves. The tribunal-blind perturbation
(`scripts/perturbation_tribunal_blind.py`, `paper.md` §4.10) is the
empirical probe of this concern on the 39-entry subset.

For the 149 regex-heuristic-graded entries: training-data
contamination does not apply (the grader is deterministic regex
code, not an LLM). The relevant concern for those entries is
**heuristic validity** — whether the regex patterns capture the
construct the rubric defines. The SICC PR4 limitation documented in
§4.1 / §4.6 of `paper.md` is exactly this kind of failure: the regex
pattern set fails on narrative-style grounds-of-decision documents.

## Validation gates (open work)

1. **Inter-rater reliability (Coder B).** `data/irr/` ships a
   20-judgment stratified sample (`sample.json`), the AI-coded
   reference scores (`coder_a.json`), and a template for Coder B
   (`coder_b.template.json`). The Coder-B slot **requires a qualified
   independent human reviewer**; LLM-as-Coder-B is excluded by design.
   Cohen's κ per primitive will be reported once Coder B completes
   the sample, via `scripts/score_irr.py`.
2. **Practitioner review of rule modules.** All 12 modules at
   `rules/*.catala_en` ship at state `draft` per
   `rules/_certification.yaml`. The `lawyer_of_record` field is empty
   for all 12. Movement to `submitted` → `reviewed` → `certified`
   requires named admitted-lawyer review in the relevant
   jurisdiction.
3. **External replication.** No external party has re-run the AI
   grading or the regex heuristics on the corpus. The Docker image at
   the project root runs the full corpus through `make test` in one
   command; replication attempts coordinate via GitHub issue tag
   `replication-attempt`.

## Reproducibility

- LLM-graded entries: `scripts/grade_borderline.py` was the original
  ADGM grader; `scripts/recode_sicc_pr4_claude.py` is the corrected
  SICC PR4 grader. The system prompt, model id, and temperature are
  pinned in `scripts/ai_grade_prompt_v0_2.txt`; do not change them
  without bumping `data/primitives.json` to v0.3 and re-grading the
  whole corpus.
- Regex-graded entries: scripts are deterministic Python; running
  them again on the same input text produces the same scores.
- The pre-registration document at `PREREGISTRATION.md` captures the
  analysis pipeline and stop rules committed before the §4.6–§4.12
  robustness checks were run.
