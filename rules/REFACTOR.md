# Rule module refactor — `{catala, py, conformance}` triples

Each rule module is now a triple plus a version pin:

```
rules/<module>.catala_en              # spec — Catala source (authoritative)
rules/<module>_eval.py                # impl — pure-Python reference evaluator
rules/<module>_conformance.py         # cross-check — asserts spec ≡ impl
rules/<module>_source.yaml            # version pin — official source URL + sha256
rules/<module>_metadata.json          # human label + certification state (existing)
rules/<module>__<scope>.schema.json   # I/O JSON Schema (existing, generated)
```

Catala remains the spec. The Python evaluator is the runtime — it lets a
user run the rule without installing opam, which matters for both casual
users and CI in environments where opam is heavy.

## Why both?

- **Catala** is the legal-readable spec. It is the document that a lawyer
  reviewing the rule will read. It compiles to a typechecked DSL; the
  `#[test]` scopes in the file run on every push.
- **Python** is the operational runtime. It is what most consumers of the
  module will actually invoke. It must agree with Catala, byte for byte,
  on canonical inputs.
- **Conformance** is the gate. CI fails if Python and Catala disagree.

## Status (2026-05-03)

All 12 modules now have catala + eval.py + conformance.py + source.yaml.
All 12 conformance tests pass under `python3` (Catala cross-check is
skipped locally where opam is not installed; CI exercises the Catala
side via `catala interpret --no-stdlib`).

| Module                              | catala | eval.py | conformance | source.yaml | drift |
|-------------------------------------|:------:|:-------:|:-----------:|:-----------:|:-----:|
| difc_rdc_part_38                    |   ✓    |   ✓     |     ✓       |     ✓       | http_get |
| difc_practice_direction_4_2017      |   ✓    |   ✓     |     ✓       |     ✓       | http_get |
| difc_rdc_38_19_indemnity             |   ✓    |   ✓     |     ✓       |     ✓       | http_get |
| difc_third_party_disclosure         |   ✓    |   ✓     |     ✓       |     ✓       | http_get |
| uae_civil_code_art_390              |   ✓    |   ✓     |     ✓       |     ✓       | http_get (MoJ index page) |
| adgm_cpr_admissions                 |   ✓    |   ✓     |     ✓       |     ✓       | http_get (PDF, binary sha256) |
| adgm_cpr_summary_judgment           |   ✓    |   ✓     |     ✓       |     ✓       | http_get (PDF, binary sha256) |
| adgm_arbitration_regulations_2015   |   ✓    |   ✓     |     ✓       |     ✓       | http_get |
| english_contract_interpretation     |   ✓    |   ✓     |     ✓       |     ✓       | manual (doctrine) |
| ladd_v_marshall                     |   ✓    |   ✓     |     ✓       |     ✓       | manual (doctrine) |
| sg_iaa_s_31                         |   ✓    |   ✓     |     ✓       |     ✓       | http_get |
| caparo_three_stage_test             |   ✓    |   ✓     |     ✓       |     ✓       | manual (doctrine) |

Drift coverage: **9 of 12 modules** under active `http_get` drift detection
(6 HTML + 2 PDF + 1 MoJ-roster index). The 3 `manual` modules are
common-law doctrines where drift = higher-court overrule, not text
amendment — `manual` is the correct method, not a gap.

## How to add a new module's `eval.py` + conformance

1. Read the corresponding `.catala_en` to find the scope name(s) and the
   input/output structures.
2. Copy the relevant function out of `spike/trace-NN/evaluate.py`.
3. Convert it to a pure function: `(input dict) → output dict` — drop
   any event-log handling. Use `decimal.Decimal(str(x))` for numerics.
4. Write `<module>_conformance.py` with at least:
   - One synthetic case from the `.catala_en` `#[test]` scope.
   - One real case from the trace that uses the module.
5. Run `python3 rules/<module>_conformance.py` locally — must pass.
6. Push; CI runs all `*_conformance.py` and `--soft` drift check.

## Drift checking

`scripts/check_rule_drift.py` fetches the pinned URL for each module,
canonicalises the HTML (strip markup, collapse whitespace, lowercase),
sha256s it, and compares against the `retrieved_sha256` in
`<module>_source.yaml`.

- `--bootstrap` populates `retrieved_sha256` where currently null.
- `--check` (default) exits non-zero on drift or unpinned modules.
- `--soft` exits zero (CI-friendly while URL coverage matures).

For doctrines (Caparo, Ladd v Marshall, Wood v Capita), drift detection
is `manual` — drift means a higher court overrules the doctrine, not a
text amendment. The drift checker prints a "MANUAL" line with the URL
to inspect on each run as a reminder.

For UAE Civil Transactions Law and ADGM CPR rule books, the official
URLs are either subscription-walled (Thomson Reuters mirror) or
intermittently slow; those are also tagged `manual` until a stable
free authoritative URL is identified. See `drift_block_reason` in
each affected `_source.yaml`.

## Source-version pinning

Each `<module>_source.yaml` records:

- `version_id`: the in-force version of the source instrument the rule
  is encoded against
- `source_authority.url`: the canonical URL
- `source_authority.retrieved_sha256`: hash of the canonicalised text
  at retrieval; populated by `--bootstrap`
- `amendment_window`: in-force-from / in-force-until dates
- `expiry.{reminder_at, hard_expiry_at}`: dates after which the module
  must not be relied on without re-pinning

This is the audit trail. If anyone ever asks "which version of RDC 38
is this rule encoded against?", the source.yaml is the answer.
