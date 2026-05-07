# Zenodo deposit runbook (item 23)

This document is the runbook for depositing the Habeas Protocol
structured-metadata snapshot to Zenodo for an immutable, citable DOI.
Run on every paper version bump.

## Why Zenodo

- Free for academic / research deposits.
- Issues a DOI per deposit version that survives even if the GitHub
  repository moves.
- Mirrors the structured metadata so a future reader can replicate
  against the exact snapshot used in the paper.
- The raw scraped judgments under `data/raw/` are NOT deposited
  (gitignored on ToS grounds — see `data/tos_audit.md` and
  `TAKEDOWN.md`); the structured metadata in `data/judgments.json`
  etc. is what we redistribute.

## What to deposit

A tarball of the structured-metadata layer plus the rule library and
the predicate evaluators:

```bash
make zenodo-tarball
# produces dist/habeas-protocol-snapshot-YYYYMMDD.tar.gz containing:
#   - data/judgments.json
#   - data/falsification_set.json
#   - data/comparison_set.json
#   - data/primitives.json
#   - data/schema.json
#   - data/sources.md
#   - data/PROVENANCE.md
#   - data/bootstrap_ci.json
#   - data/robustness/             (all derived analysis files)
#   - rules/                       (all 12 modules, sources, schemas)
#   - spike/trace-*/               (predicate + events + output + discrepancy per trace)
#   - paper.md, README.md, GRADING_SPEC.md, PREREGISTRATION.md
#   - LICENSE, LICENSES/, CONTRIBUTING.md, SECURITY.md, TRADEMARK.md, TAKEDOWN.md
```

(See `Makefile` target `zenodo-tarball`.)

## Procedure

1. Bump the version stamp:
   ```bash
   echo "v0.2-$(date -u +%Y%m%d)" > VERSION
   ```
2. Verify all robustness analyses are current:
   ```bash
   python3 scripts/analyse_robustness.py
   python3 scripts/check_grading_provenance.py
   make test  # all CI green
   ```
3. Build the tarball:
   ```bash
   make zenodo-tarball
   ```
4. Log in to https://zenodo.org with an institutional or ORCID account.
5. **First deposit only:** Create a new upload. Title:
   `Habeas Protocol — empirical study + executable rule library
   (snapshot YYYYMMDD)`. Description: copy the abstract from
   `paper.md`. Communities: tag at least `legal-tech` and
   `computational-law`. Authors: list `Qureshi, Hamza` with ORCID
   if available.
6. **Subsequent deposits:** Open the existing record, click "New
   version", upload the new tarball. Zenodo issues a per-version DOI;
   the concept DOI is the persistent identifier across all versions.
7. License: select `MIT` for code and `Other (non-commercial)` for
   structured-metadata data, citing `LICENSES/HABEAS-METADATA.txt`.
8. Click "Publish". The DOI is live within a few minutes.
9. Update `paper.md` Citation block with the new DOI:
   ```
   Maxim Labs, "Habeas Protocol: ...", v0.2-YYYYMMDD (Month YYYY).
   doi: 10.5281/zenodo.<NNNNNNN>
   ```
10. Commit the DOI update; tag the git commit `v0.2-YYYYMMDD`.

## Triggers

Re-deposit on every:
- Paper version bump.
- Rubric version bump (`data/primitives.json` v0.3, etc.).
- Re-grading of the corpus under a new model snapshot.
- After any Phase-1 stop rule fires that changes the headline
  numbers.

## What if Zenodo is down

Backup deposit options (in order of preference):
1. Software Heritage (https://archive.softwareheritage.org/) — free,
   accepts any GitHub commit hash; produces an SWHID identifier.
2. OSF (https://osf.io/) — free, similar service to Zenodo, accepts
   tarballs, issues DOIs.
3. arXiv ancillary data (only if the paper itself is being arxived
   — bundle the snapshot tarball as ancillary).

The DOI itself is what matters; whichever service issues it is
secondary.

## Concept DOI vs version DOI

Zenodo issues one DOI per uploaded version *and* one "concept DOI"
that always resolves to the latest version. Cite the concept DOI in
running text ("see the live snapshot at doi:10.5281/zenodo.<concept>"),
and the version DOI in the bibliography ("Maxim Labs, ..., v0.2-
YYYYMMDD, doi:10.5281/zenodo.<version>").
