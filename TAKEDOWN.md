# Takedown notice

If you are a court registrar, a rightsholder of source content, or a
named individual identified in this repository's metadata and you wish
disputed material removed, please email:

> **thehamzaq@gmail.com** (with subject line beginning `[habeas-protocol takedown]`)

We commit to:

1. **Acknowledge** receipt of the takedown notice within 2 business days.
2. **Verify** the request — confirm the requester's standing (e.g. Court
   Registry, named party, named counsel of record) and the disputed
   material's location in the repository.
3. **Remove** verified disputed material from the public repository
   within **7 calendar days** of acknowledgment. Local clones held by
   prior users of the repository are outside our control; we will note
   the removal in the project changelog so downstream users can mirror
   the change.

Material in scope:

- Any field of `data/judgments.json` (including `parties`, `judge`,
  `coding.notes`, `coding.rationale`).
- Any entry in `data/falsification_set.json` or
  `data/comparison_set.json`.
- Any other file under `data/` that identifies a person or institution.

Out of scope:

- Source judgment text under `data/raw/` is NOT in the repository
  (`.gitignore` excludes it). If you have located such material in a
  redistributed copy of this project, please direct the takedown to the
  redistributor and notify us so we can update our governance policy.

What we will NOT do without a court order:

- Identify by IP, name, or organization any prior reader of the
  repository.
- Modify the historical commit graph (squash / rebase / force-push). We
  will instead remove disputed material in a new commit and tag the
  prior state for legal record.

For ToS-related concerns specifically, see `data/tos_audit.md` and the
underlying source ToS clauses cited there.
