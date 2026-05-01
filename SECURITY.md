# Security Policy

## Reporting a vulnerability

If you discover a security issue in Habeas Protocol — anything from a
data leak in the API, an injection vector in the dashboard, a Catala
evaluation that bypasses a certified rule's intended semantics, an issue
in the migration scripts, a credential accidentally committed to history,
or a supply-chain concern in the clients — please report it privately.

**Email:** **thehamzaq@gmail.com**

Subject line suggestion: `[Habeas Security] <short description>`.

Please **do not** open a public GitHub issue for security matters until a
fix is available.

## What to include

A useful report typically contains:

- A description of the issue and its impact.
- The component affected (`api/`, `dashboard/`, `clients/`, `rules/`,
  `scripts/`, `db/`, etc.) and the file(s) or endpoint(s) involved.
- Steps to reproduce, or a minimal proof-of-concept.
- The version, commit SHA, or release tag you tested against.
- Your assessment of severity (low / medium / high / critical), if you
  have one.
- Whether you would like to be credited in the fix advisory, and under
  what name.

## What to expect

This project is currently maintained by a small team (initially solo).
Response targets are best-effort:

- **Acknowledgement**: within **3 working days** of receipt.
- **Initial triage and severity assessment**: within **7 working days**.
- **Fix or mitigation timeline**: communicated after triage. Critical
  issues are prioritized; lower-severity issues may be batched into the
  next release.
- **Disclosure**: coordinated. Reporters are credited in the release
  notes unless they request otherwise.

## Scope

In scope:

- The Habeas Protocol code in this repository.
- The reference API server (`api/server.py`) and its endpoints.
- The first-party Python and TypeScript clients (`clients/`).
- The dashboard (`dashboard/`).
- The migration and ingestion scripts (`scripts/`) — particularly any
  path that reads or writes user-supplied content.
- The Catala rule modules (`rules/`) — semantic bypasses or rules whose
  encoding contradicts the cited source are in scope as well.

Out of scope:

- The 121-judgment dataset under `data/judgments.json`. This is sourced
  from public court records; factual errors should be reported as
  regular GitHub issues, not as security reports.
- Third-party services referenced but not operated by this project
  (court websites, Firecrawl, Postgres itself, OCaml/Catala upstream).
- Issues in unsupported, modified, or fork distributions.

## Hardening notes for self-hosters

If you run your own instance:

- The reference API server is **read-only by design**. Do not expose
  write endpoints (rule authoring, ingestion) to untrusted clients.
- Keep the Postgres instance behind a firewall; the API server expects
  to be the only client.
- Do not commit `data/raw/` or any database dumps to public forks —
  the structured `data/judgments.json` is the publishable artefact.
- Rotate any local API tokens you add on top of the reference
  implementation.

## Acknowledgements

A list of reporters credited for past disclosures will be maintained
here once the project has its first acknowledged report.
