# Contributing to Habeas Protocol

Thanks for your interest. This project codes commercial-court rules into
executable predicates and exposes them through a public corpus, an API, and
a rule library. Contributions are welcome at every layer — corpus coding,
rule modules, API features, dashboard UX, documentation, and the
certification process itself.

## Open audit and replication invitation

Anyone who wishes to re-grade the corpus under their own rubric, or to
replicate the AI-coding pipeline with a different procedure, is invited
to do so. Open a GitHub issue using the `replication-attempt` template
(see `.github/ISSUE_TEMPLATE/replication-attempt.md`).

The Docker image at the repository root runs the full corpus through
`make test` in one command. Reproducibility scripts live under
`scripts/`. The pre-registered analysis pipeline is in
`PREREGISTRATION.md`.

The author will accept co-authorship offers on the next paper revision
from any independent party who replicates the procedure end-to-end and
publishes their results, whether their findings agree with or contradict
the published numbers.

## Practitioner review of rule modules

All 12 rule modules under `rules/` ship at state `draft` per
`rules/_certification.yaml`. Movement to `submitted` → `reviewed` →
`certified` requires named admitted-lawyer review in the relevant
jurisdiction. If you are an admitted UAE / Singapore / English-law
practitioner willing to review one or more rule modules, please open
an issue tagged `practitioner-review` describing which module(s) you
can review.

The interpretive choices made during the original encoding are
documented at `rules/ENCODING_DECISIONS.md`; that file is the starting
point for review.

## Ways to contribute

1. **File an issue** — bug reports, corpus errors, miscoded judgments,
   missing primitives, dashboard glitches, broken API responses, doc fixes.
2. **Improve the corpus** — re-code a judgment with a better primitive
   score, add provenance, attach a missing source URL. Each entry in
   `data/judgments.json` carries a `coding.coder` field; please update it
   when you change a score.
3. **Submit a rule module** — a new entry under `rules/` that codes a
   real legal rule from a real tribunal in Catala, with a metadata file
   and at least one trace under `spike/`. See "Submitting a rule" below.
4. **Improve the API or dashboard** — endpoints under `api/`, pages under
   `dashboard/`. Keep the dashboard stdlib-only (no build step) and the
   Python client stdlib-only (no third-party deps).
5. **Improve clients or tooling** — Python and TypeScript first-party
   clients live under `clients/`. Property tests live under `tests/`.

## Before you start

- Read [`README.md`](README.md) for the project thesis and corpus
  methodology.
- Read [`paper.md`](paper.md) for the v0.2 primitive rubric and the
  empirical results.
- Read [`rules/_certification.yaml`](rules/_certification.yaml) — this is
  the spec for how rules move from `draft` → `submitted` → `reviewed` →
  `certified`. Contributing a rule means engaging with this lifecycle.
- Run the existing tests: `bash scripts/run_tests.sh` (catala typecheck +
  trace evaluators + property tests + drift checks).

## Submitting a rule

Rules are the highest-value contribution. Each rule module needs:

1. **`rules/<rule_id>.catala_en`** — the Catala source. The rule must
   typecheck (`catala typecheck`) and interpret (`catala interpret`)
   without errors.
2. **`rules/<rule_id>_metadata.json`** — declares jurisdiction, claim
   types, source citation (with stable URL), state (`draft` initially),
   author, and review history. See any existing metadata file as a
   template.
3. **`rules/<rule_id>.schema.json`** — generated from the Catala source
   (`scripts/gen_rule_schemas.py`). Do not hand-edit.
4. **At least one trace** — `spike/trace-NN/` containing `rule.catala_en`,
   `events.json`, `evaluate.py`, and `output.json`. The trace must
   reproduce a known judgment's arithmetic.
5. **Tests** — at least one property in `tests/property_tests.py`.

New rules enter at `state: draft`. To move to `submitted`, open a PR.
Review and certification follow the process in
[`rules/_certification.yaml`](rules/_certification.yaml).

## Coding conventions

- **Python**: stdlib-only for the API server and the Python client.
  Third-party libraries are allowed under `scripts/` for ingestion and
  migration only.
- **TypeScript**: zero-build; compiles in browsers and Node directly.
- **HTML/CSS**: stdlib-only dashboard, no bundler, no React.
- **SQL**: dollar-quoted literals; no ORMs in the API path.
- **Comments**: minimal — only when the *why* is non-obvious.

## Pull requests

- Branch from `main`.
- Keep PRs scoped — one rule, one fix, one feature.
- Run `bash scripts/run_tests.sh` locally before pushing.
- The CI workflow will re-run tests, typecheck Catala, evaluate every
  trace, and check schema drift. All must pass before merge.

## Licensing of contributions

By submitting a contribution, you agree that:

- Code contributions are licensed under the **MIT License**.
- Data contributions (under `data/`) are licensed under
  **CC-BY-4.0**.
- You have the right to submit the contribution under those terms.

## Getting help

Open a GitHub Discussion or an issue. For private matters (security,
trademark, certification authority), email **thehamzaq@gmail.com**.
