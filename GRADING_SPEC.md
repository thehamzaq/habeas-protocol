# Habeas Protocol — corpus grading specification (v0.2)

This document records the grading methodology for the 188-judgment corpus.
Per the audit, the grading-process spec must be public for the empirical
claim ("ADGM 1.91, SICC 1.85, DIFC 1.72") to be reproducible.

## Coder population

| Code | Coder | Role |
|---|---|---|
| `Hamza` | Hamza Qureshi | Hand coder. The 39-judgment gold set. Trained on the v0.2 rubric (`data/primitives.json`). |
| `MaximLabs` | Heuristic + AI | The 149 non-gold entries. Provenance recorded in each judgment's `coding.coder` field. Subdivided below. |

## Per-tribunal split (n = 188)

| Tribunal | n | Hand-coded (`Hamza`) | Heuristic-triaged | AI-graded |
|---|---:|---:|---:|---:|
| DIFC | 32 | 32 | 0 | 0 |
| ADGM | 76 | 7 | 16 | 53 |
| SICC | 80 | 13 | 0 | 67 |

## Heuristic triage (ADGM only)

`scripts/triage_adgm.py` matches a fixed regex set against the raw judgment
text and assigns one of two default vectors:

- **Saturating "Judgment Summary" template** → `(2, 2, 2, 2, 2, 2)` and
  `(2, 2)` for SP1/SP2.
- **Case-management order** → `(2, 2, 2, 2, 2, 1)` (PR6 floor reflects the
  intra-jurisdictional nature of CMS orders).

These are **structural defaults derived from the document type**, not
grades against the rubric. They are recorded with `coding.coder =
"MaximLabs (triaged)"` so a downstream user can filter them out.

## AI grading (ADGM 53 + SICC 67)

The 120 AI-graded entries used the following spec:

- **Model:** Claude Sonnet 4.5 (`claude-sonnet-4-5-20250929`).
- **Provider:** Anthropic API.
- **Temperature:** 0.0 (deterministic).
- **Top-p:** unset (default 1.0).
- **Max output tokens:** 1024.
- **System prompt:** literal copy of `data/primitives.json` v0.2 plus a
  one-paragraph instruction: *"You are a hostile legal-procedure auditor.
  Score each per-ruling primitive PR1–PR6 and each system property
  SP1–SP2 on the 0/1/2 scale defined above. Return strict JSON: {pr1:
  …, pr6: …, sp1: …, sp2: …, notes: …}. If a primitive is not
  determinable, return -1. Do NOT speculate."*
- **Run dates:** ADGM 53 graded 2026-04-12; SICC 67 graded 2026-04-29
  (recorded in each judgment's `coding.run_date` field).
- **Prompt versioning:** the literal prompt text is captured in
  `scripts/ai_grade_prompt_v0_2.txt`; that file is read at run time.

## Validation gates (open work — flagged in §9 of the paper)

1. **Inter-rater reliability (Coder B).** `data/irr/` ships a 20-judgment
   stratified gold sample (`sample.json`), Coder A's grades
   (`coder_a.json`), and a template for Coder B (`coder_b.template.json`).
   The Coder-B slot **requires a qualified independent human reviewer**;
   LLM-as-Coder-B is excluded by design. Cohen's κ per primitive will be
   reported once Coder B completes the sample, via
   `scripts/score_irr.py`. Until that is done, the rubric's stability
   should be regarded as **unverified**.
2. **PR4 SICC heuristic validation.** SICC PR4 = 1.55 reflects a
   measurement-instrument limitation (regex-based marker detection in
   narrative grounds-of-decision documents), not a tribunal-quality
   regression. A stratified hand-validation of 20 SICC entries from the
   n=67 expansion is on the open-work list (`data/sicc_stratification_plan.md`).
3. **Confidence intervals.** Tribunal means in `paper.md` §4.1 are
   currently reported as point estimates. Bootstrap 95% CIs on each
   tribunal's mean and tests of significance for inter-tribunal
   differences are pending.

## Reproducibility

`scripts/grade_borderline.py` is the canonical AI-grading entry point;
it reads `scripts/ai_grade_prompt_v0_2.txt` and writes one row per
judgment. The system prompt, model id, and temperature are pinned in
that script; do not change them without bumping `data/primitives.json`
to v0.3 and re-grading the whole corpus.

## Provenance fields on every judgment

Every entry in `data/judgments.json` carries:

```json
"coding": {
  "coder": "Hamza" | "MaximLabs (triaged)" | "MaximLabs (ai-graded)",
  "run_date": "YYYY-MM-DD",
  "notes": "free-form coder note"
}
```

A future revision will add `model_version` and `prompt_sha256` at the
per-row level so the prompt change history is auditable independent of
this document.
