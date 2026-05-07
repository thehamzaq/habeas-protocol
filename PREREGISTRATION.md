# Pre-registration — Habeas Protocol v0.2 corpus analyses

**Pre-registration date:** 2026-05-07
**Author:** Hamza Qureshi (Maxim Labs)
**Repository:** https://github.com/thehamzaq/habeas-protocol
**Last committed SHA before pre-registration:** `6a77bdb` (`fix CI: deterministic rule schemas + drop decks`). The commit immediately following this file's addition pins the pre-registration to a specific repo state; any subsequent changes to the analysis pipeline must be appended to §6 (Amendments) below with a date and rationale rather than edited into §1–§5 in place.

This document records the analysis pipeline and stop rules committed
*before* the §4.6–§4.12 robustness checks of `paper.md` are run.
The intent is to make the empirical claims confirmatory rather than
exploratory: any result that fails its pre-registered stop rule is
reported in `paper.md` §11 (Negative results) as a failure of that
stop rule, not omitted.

A reviewer comparing this document to the eventual results should be
able to verify that:
1. The hypotheses were stated before the data was collected.
2. The stop rules were specified with concrete numerical thresholds
   that could not be moved post-hoc.
3. Any post-pre-registration changes to the analysis are themselves
   logged in this document with a date and rationale.

## 1. Hypotheses

### H1 — Grader-type stability within ADGM
**Claim:** Within ADGM (the only tribunal where both LLM and regex
grader types are represented), the per-tribunal mean is stable across
grader types to within 0.20 on the overall mean and to within 0.30 on
any single primitive.

**Stop rule (S1):** If the LLM-graded ADGM mean (n=7) and the regex
heuristic-graded ADGM mean (n=53) differ by more than 0.20 on the
overall, or by more than 0.30 on any single primitive, the difference
is reported as a grader-type effect and the headline ADGM mean is
re-reported per grader type rather than pooled.

**Power caveat:** n=7 LLM-graded entries against n=53 regex-graded
entries is structurally underpowered to detect small grader-type
effects; the 0.30 per-primitive threshold is generous. The
comparison is reported as evidence consistent with grader-type
stability, not as proof of it. A more demanding test would re-grade
a stratified subset of the n=53 regex-graded entries with the LLM
grader (or vice versa) under matched conditions; this is open work.

### H2 — Test-retest stability of the LLM grader
**Claim:** The LLM grader produces stable scores under repeated
invocation: per-primitive exact-match agreement ≥ 80% and
weighted Cohen's κ ≥ 0.6 between original and re-run scores.

**Stop rule (S2):** If exact-match agreement is below 80% on any
primitive, that primitive is reported as unstable and excluded from
the headline mean. If weighted κ is below 0.6 on any primitive, that
primitive is flagged for additional disclosure.

### H3 — Tribunal-blind robustness
**Claim:** The LLM grader produces stable scores when tribunal
identifiers (tribunal name, neutral citation, judge, caption) are
stripped from the input.

**Stop rule (S3):** If grading with tribunal identity stripped
produces a > 0.20 mean shift on any tribunal mean, the headline is
re-reported as identity-sensitive and the tribunal-blind result
becomes the headline.

### H4 — Model-size robustness
**Claim:** Per-primitive scores are stable across Claude model sizes
(Opus, Sonnet, Haiku) under identical prompt.

**Stop rule (S4):** If model-size perturbation produces a > 0.30 mean
shift on any primitive (Opus minus Haiku), that primitive is flagged
as model-dependent.

### H5 — Prompt-rephrase robustness
**Claim:** Per-primitive scores are stable when the rubric prompt is
rewritten with different ordering and examples but the same criteria.

**Stop rule (S5):** If the rephrased prompt produces a > 0.20 mean
shift on any primitive, that primitive is flagged as
prompt-sensitive.

### H6 — Internal robustness (within-design)
**Claim:** The headline DIFC < SICC < ADGM ordering is preserved
under (a) any single-primitive drop (LOPO), (b) ordinal collapse
1→0 or 1→2 (threshold sensitivity), and (c) within-tribunal
falsification baselines (LOTO).

**Stop rule (S6):** If the ordering reverses or collapses to a tie
under any of (a), (b), (c), that result is reported in §4.7 with
the implicated robustness check named.

### H7 — Sub-rubric coherence (within-Claude)
**Claim:** A Claude-proposed alternative rubric saturates the same
three tribunals to within 0.20 on the overall mean and preserves the
DIFC < SICC < ADGM ordering.

**Stop rule (S7):** If the Claude-proposed rubric (i) produces a
different headline tribunal-mean ordering, OR (ii) shifts any
tribunal mean by more than 0.20, that divergence is reported as a
model-author rubric instability and the alternative-rubric scores
become a parallel headline rather than a coherence note.

### H8 — External correlate (single-direction)
**Claim:** The per-judgment v0.2 mean correlates positively with at
least one external metric extractable from the same court sites
(subsequent-citation count, was-appealed status, days-to-judgment).

**Stop rule (S8):** If all three external correlations are null
(|ρ| ≤ 0.10) AND none reach |ρ| ≥ 0.20 in either direction, the
rubric's external validity is reported as not established by this
analysis. A null correlate is not a refutation — the rubric measures
procedural form, not citation centrality — but the failure to find a
positive correlate is disclosed in §4.12. The bar for satisfying H8
is intentionally low: a single ρ ≥ 0.10 in the predicted direction
on any of the three metrics passes.

## 2. Sampling frame

The 188-judgment corpus is a convenience sample assembled by:
- DIFC: first 32 results returned by `scripts/fetch_difc.py` from the
  difccourts.ae listing endpoint, paginated April 2026.
- ADGM: 76 PDFs returned by `scripts/fetch_adgm_pages.py` and
  `scripts/fetch_adgm_firecrawl.py` from the adgm.com listing pages,
  April 2026.
- SICC: 80 HTML grounds-of-decision documents returned by
  `scripts/fetch_sicc_direct.py` from elitigation.sg, April–May 2026.

Bias direction: the sample is biased toward findable, recent,
well-formatted, English-language judgments. It is not a random draw
from any defined population.

The 30-judgment perturbation sample (§4.10, §4.11) is stratified
(10 per tribunal) drawn under seed `20260507`. The stratification
script is `perturbation_test_retest.stratified_sample()`; reusing
the same seed reproduces the same sample.

## 3. Pre-committed analysis pipeline

1. Run `scripts/relabel_coding_provenance.py` to ensure all entries
   have grader-type and provenance metadata pinned.
2. Run `scripts/analyse_robustness.py` to produce the static
   robustness analyses (LOPO, LOTO, threshold sensitivity, procedure
   split, adversarial sample). These tests evaluate H1, H6.
3. Run the LLM perturbation suite. Test H2 → H5:
   - `scripts/perturbation_test_retest.py`
   - `scripts/perturbation_tribunal_blind.py`
   - `scripts/perturbation_model_size.py`
   - `scripts/perturbation_prompt_rephrase.py`
4. Run `scripts/recode_sicc_pr4_claude.py` to obtain the corrected
   SICC PR4 measurement. The corrected mean enters the headline; the
   regex result remains as the known-flawed measurement.
5. Run `scripts/sub_rubric_alternative.py` to test H7.
6. Run `scripts/external_correlate.py` to test H8.

## 4. Going-forward encoding pipeline (item 17)

For each *new* rule encoded into the rule library after the
pre-registration date, the encoding pipeline is:

1. Commit the verbatim source text excerpt (statute / rule / case
   passage) into a new entry in `rules/ENCODING_DECISIONS.md`.
2. Commit the interpretive choices made and the rationale for each.
3. Commit the intended test scenarios (input vectors and expected
   dispositions).
4. Only after steps 1–3 are committed, write the Catala predicate.
5. After the predicate compiles, run the test scenarios and update
   `ENCODING_DECISIONS.md` with the actual dispositions.

Encoding-pipeline retrospective entries for the 12 existing rule
modules are in `rules/ENCODING_DECISIONS.md`.

## 5. Open audit

Anyone who wishes to re-grade the corpus under their own rubric, or
to replicate the AI-coding pipeline with a different procedure, is
invited to do so. The Docker image at the repository root runs the
full corpus through `make test` in one command; reproducibility scripts
live under `scripts/`. Open a GitHub issue tagged `replication-attempt`
to coordinate. The author will accept co-authorship offers from any
independent party who replicates the procedure end-to-end and
publishes their results.

## 6. Amendments to this pre-registration

Every change to this document after the initial commit must be
appended to this section with a date and rationale. The original
hypotheses and stop rules above must not be edited in place.

(none yet)
