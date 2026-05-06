# Inter-rater reliability (IRR) exercise

The audit recommended a Cohen's κ check on a stratified subsample of the
hand-coded gold set, with an independent human as the second coder.

## Files

| File                          | Role                                                    |
|-------------------------------|---------------------------------------------------------|
| `sample.json`                 | 20 case_no's selected (stratified, seed=42)             |
| `coder_a.json`                | Coder A scores, lifted from `data/judgments.json`       |
| `coder_b.template.json`       | Blank template for Coder B (independent human reviewer) |
| `coder_b.json`                | (TO BE PROVIDED) Coder B's completed scoring            |
| `results.md`                  | (generated) per-primitive κ + 95% CI + interpretation   |

## Protocol

1. **Select.** `python3 scripts/select_irr_sample.py` — already run; 20
   judgments stratified across (tribunal, claim_type) with seed=42.
2. **Brief Coder B.** Independent reviewer reads `data/primitives.json`
   (the v0.2 rubric) and the 20 judgments at the URLs in
   `coder_b.template.json`. Reviewer records scores and rationale per
   primitive. Reviewer must be:
   - independent of Maxim Labs (no involvement in v0.1 / v0.2 design)
   - qualified in the relevant law (UAE counsel for DIFC/ADGM judgments;
     SG counsel or common-law academic for SICC)
   - **NOT an LLM** — LLM-as-second-coder is not valid IRR (training-data
     overlap with Coder A's reasoning, lack of accountability).
3. **Score.** `python3 scripts/score_irr.py` reads `coder_b.json`,
   computes per-primitive Cohen's κ + bootstrap 95% CI, writes
   `results.md`.
4. **Adjudicate disagreements.** Where κ < 0.7 or specific cells differ
   by ≥ 1, hold a brief adjudication call between coders. Record the
   adjudicated resolution in `data/irr/adjudication.md`. The
   adjudication notes are themselves part of the protocol; they show
   where the rubric is ambiguous.

## Audit-recommended target

κ ≥ 0.7 per primitive (substantial agreement). Cells below 0.7 indicate
rubric ambiguity that must be addressed before publication. PR3
(rule-bind: specific clause + version) and PR6 (enforcement bridge) are
the cells most likely to show disagreement, given the inherent
judgement involved.

## Why a single LLM coder is insufficient

A single LLM (the system that drafted v0.2 of this audit) re-coding the
sample would produce κ ≈ Coder A by construction — same statistical
priors, same training data, same prompt-induced framing. The κ would
look high but would not measure what the reviewer cares about: whether
*humans*, applying the rubric in good faith, agree.

If hiring a qualified counsel is impractical in the near term, an
acceptable (weaker) alternative is:

- a published-academic with common-law commercial-court expertise but
  no project relationship; or
- a paralegal or trainee at a DIFC/ADGM firm under named partner
  supervision.

In either case the coder's identity and credentials must appear in
`results.md` for transparency.
