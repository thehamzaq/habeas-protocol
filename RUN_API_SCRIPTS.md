# Running the API-dependent perturbation + recode scripts

This document is the runbook for the six API-dependent robustness
analyses. The static + non-API analyses have already been run:

- `scripts/analyse_robustness.py` — done; outputs in `data/robustness/`
- `scripts/external_correlate.py` — **done**; result at
  `data/robustness/external_correlate.json` (H8 passes, ρ=0.32 on
  was_appealed)
- `scripts/relabel_coding_provenance.py` — idempotent; already applied
- `scripts/clean_legacy_notes.py` — idempotent; already applied
- `scripts/check_grading_provenance.py` — clean (188 / 30 / 90)

The six scripts below require the Anthropic API and are staged for
you to run. The `anthropic` Python package is already installed
(`anthropic-0.100.0`).

## Prerequisites

Export your Anthropic API key:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

Sanity-check that it's set:

```bash
python3 -c "import os; print('OK' if os.environ.get('ANTHROPIC_API_KEY') else 'NOT SET')"
```

## Estimated cost

Per Anthropic pricing (Sonnet 4.5: $3/M input + $15/M output, October
2025 pricing). Each grading call is ~5K input tokens + ~500 output
tokens. The full suite costs roughly:

| Script | Calls | Tokens (in/out) | Cost (USD) |
|---|---:|---:|---:|
| `perturbation_test_retest.py` (n=30) | 30 | 150K / 15K | $0.68 |
| `perturbation_tribunal_blind.py` (n=30) | 30 | 150K / 15K | $0.68 |
| `perturbation_model_size.py` (n=15 × 3 models) | 45 | 225K / 22K | $1.01 |
| `perturbation_prompt_rephrase.py` (n=30 × 2) | 60 | 300K / 30K | $1.35 |
| `recode_sicc_pr4_claude.py` (n=80) | 80 | 400K / 40K | $1.80 |
| `sub_rubric_alternative.py` (1 + 30) | 31 | 155K / 15K | $0.69 |
| **Total** | **276** | **~1.4M / 137K** | **~$6.20** |

Actual costs may differ ±50% depending on judgment text length.

## Run order (recommended)

The scripts are independent of each other — order is preference, not
dependency. Recommended order (Phase-1 risk probes first):

```bash
# Phase 1 — highest-stakes probes (run first; if these fail, the
# rest tells you something more interesting)
python3 scripts/perturbation_tribunal_blind.py    # H3 (the single highest-stakes)
python3 scripts/perturbation_test_retest.py       # H2
python3 scripts/recode_sicc_pr4_claude.py         # corrects SICC PR4

# Phase 2 — model-family + prompt brittleness probes
python3 scripts/perturbation_model_size.py        # H4 (slowest — 3 models)
python3 scripts/perturbation_prompt_rephrase.py   # H5

# Phase 3 — coherence check
python3 scripts/sub_rubric_alternative.py         # H7
```

Total wall-clock with default n: roughly 30–60 minutes (rate-limited
sequential calls; could be parallelised by editing the loops).

## Expected outputs

Each script writes one or two files under `data/robustness/`:

| Script | Output(s) |
|---|---|
| `perturbation_test_retest.py` | `test_retest.json`, `test_retest_summary.json` |
| `perturbation_tribunal_blind.py` | `tribunal_blind.json`, `tribunal_blind_summary.json` |
| `perturbation_model_size.py` | `model_size.json`, `model_size_summary.json` |
| `perturbation_prompt_rephrase.py` | `prompt_rephrase.json`, `prompt_rephrase_summary.json` |
| `recode_sicc_pr4_claude.py` | `data/sicc_pr4_recoded.json`, `data/robustness/sicc_pr4_summary.json`, `data/robustness/sicc_pr4_regex.json` (snapshot of pre-recode regex scores) |
| `sub_rubric_alternative.py` | `sub_rubric_proposed.json`, `sub_rubric_scores.json`, `sub_rubric_summary.json` |

## Dry-run smoke tests (already verified by audit)

Each script supports `--dry-run` which exercises the sampling +
matching pipeline without making API calls. All six dry-runs succeeded
on 2026-05-07. To re-verify before a real run:

```bash
python3 scripts/perturbation_test_retest.py --dry-run --n-per-tribunal 5
python3 scripts/perturbation_tribunal_blind.py --dry-run --n-per-tribunal 5
python3 scripts/perturbation_model_size.py --dry-run --n-per-tribunal 3
python3 scripts/perturbation_prompt_rephrase.py --dry-run --n-per-tribunal 3
python3 scripts/recode_sicc_pr4_claude.py --dry-run --limit 3
python3 scripts/sub_rubric_alternative.py --dry-run
```

## Stop rules

Each script's output JSON includes a `stop_rule_violation: true|false`
field on each per-primitive or per-tribunal record. After running,
check the summary file for any stop-rule violation. The pre-registered
stop rules are documented in `PREREGISTRATION.md` §1 and listed
verbatim in `paper.md` §12.

## Reporting after running

After all six scripts complete, regenerate the paper-side numbers:

```bash
python3 scripts/check_grading_provenance.py    # confirms metadata still pinned
make conformance                               # confirms rule library still green
make property-tests                            # confirms 1930 invariants pass
```

Then update `paper.md` §4.6–§4.11 with the actual stop-rule outcomes
(replace "when run" / "to be reported" placeholders with the real
numbers from the `_summary.json` files). The §4.12 external-correlate
section is already populated.

## What changes in the headline

Once the six scripts run, the following claims in `paper.md` either
strengthen, weaken, or flip:

- **§4.10 Claude perturbation suite.** "When run with API access" →
  actual ρ + κ + shift numbers per axis. Stop-rule outcomes per axis.
- **§4.9 SICC PR4.** Headline SICC mean of 1.85 currently uses the
  regex value (1.55). After `recode_sicc_pr4_claude.py` runs, the
  Claude-corrected PR4 replaces it; the headline SICC mean updates
  in `paper.md` §4.1 + Appendix A. Update both with the new number.
- **§4.11 Sub-rubric coherence.** "When run" → actual headline
  ordering under the Claude-proposed alternative rubric. If the
  ordering reverses, S7 fires and the sub-rubric mean becomes a
  parallel headline (§11 negative results gets a new entry).

## Failure modes to watch for

- **Rate-limiting.** Anthropic enforces per-minute and per-hour token
  limits. If you hit one, the script raises and exits. Re-run; the
  test-retest script writes incremental output so re-running picks up
  where it left off only for the entries marked `error`. The other
  scripts are not incremental (they overwrite); if you need to
  resume, edit the script to skip already-graded entries.
- **API cost overrun.** If you want to bound cost, reduce
  `--n-per-tribunal` (default 10 for test-retest / tribunal-blind /
  prompt-rephrase; 5 for model-size; full corpus for SICC PR4 recode
  via `--limit`).
- **Network errors.** Wrap each script in a retry loop or run inside
  `tmux` / `screen` and inspect on completion.

## After all six scripts have run

1. Regenerate the Zenodo tarball: `make zenodo-tarball`.
2. Tag the git commit: `git tag v0.2-$(date -u +%Y%m%d)`.
3. Optional: deposit to Zenodo per `ZENODO.md` runbook.
