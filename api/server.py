#!/usr/bin/env python3
"""Read-only JSON API over the habeas-protocol Postgres corpus.

Stdlib only — no Flask, no FastAPI, no psycopg. Shells out to `psql` and
returns whatever it prints. The migration script does the same; this keeps
the project install-free beyond the Postgres binaries themselves.

Endpoints
---------
GET /api/health
GET /api/judgments?tribunal=ADGM&limit=50
GET /api/rules?limit=20
GET /api/search?q=indemnity+basis+costs&limit=10
GET /api/tribunal_means          (paper headlines)

Run
---
    eval $(./scripts/postgres_local.sh env)
    python3 api/server.py            # listens on 127.0.0.1:5544

CORS is open (`*`) since this is local-dev only.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

PGHOST = os.environ.get("PGHOST", "localhost")
PGPORT = os.environ.get("PGPORT", "5433")
PGUSER = os.environ.get("PGUSER", os.environ.get("USER", "postgres"))
PGDATABASE = os.environ.get("PGDATABASE", "habeas")

API_HOST = os.environ.get("HABEAS_API_HOST", "127.0.0.1")
API_PORT = int(os.environ.get("HABEAS_API_PORT", "5544"))

REPO_ROOT = os.path.abspath(os.path.dirname(__file__) + "/..")
RULES_DIR = REPO_ROOT + "/rules"


def _find_catala() -> str | None:
    """Locate the catala binary even when the API is launched without
    opam env sourced. Defers any error to the request that needs it."""
    import shutil
    on_path = shutil.which("catala")
    if on_path:
        return on_path
    candidate = os.path.expanduser("~/.opam/catala/bin/catala")
    return candidate if os.path.exists(candidate) else None


CATALA_BIN = _find_catala()


def psql_json(sql: str) -> object:
    """Run a `SELECT json_agg(...)`-shaped query, return parsed JSON.

    The SQL is piped over stdin (NOT `-c`), because psql's `:'var'`
    substitution silently skips `-c` strings. Callers must validate any
    user-derived values themselves before splicing them into `sql`.
    """
    cmd = [
        "psql",
        "-h", PGHOST, "-p", PGPORT, "-U", PGUSER, "-d", PGDATABASE,
        "-At", "--no-psqlrc",
        "-v", "ON_ERROR_STOP=1",
    ]
    out = subprocess.run(cmd, input=sql, capture_output=True, text=True, timeout=15)
    if out.returncode != 0:
        raise RuntimeError(f"psql failed: {out.stderr.strip()}")
    raw = out.stdout.strip()
    if not raw or raw == "":
        return []
    return json.loads(raw)


def _clamp_int(value: str | None, default: int, lo: int, hi: int) -> int:
    try:
        n = int(value) if value is not None else default
    except (TypeError, ValueError):
        n = default
    return max(lo, min(hi, n))


def _safe_tribunal(value: str | None) -> str | None:
    if value is None:
        return None
    v = value.strip().upper()
    return v if v in {"DIFC", "ADGM", "SICC"} else None


# ---------- handlers ----------

def handle_health(_qs):
    rows = psql_json("SELECT json_build_object('ok', true, 'judgments', (SELECT count(*) FROM judgments));")
    return {"status": rows}


def handle_judgments(qs):
    """Return judgments in the same shape as data/judgments.json.

    `raw_json` was preserved verbatim during migration, so the dashboard
    can swap fetch('data/judgments.json') for fetch('/api/judgments') and
    every existing key (parties.claimant, primitive_scores_v02, coding
    notes, etc.) still resolves.
    """
    limit = _clamp_int(qs.get("limit", [None])[0], 500, 1, 1000)
    tribunal = _safe_tribunal(qs.get("tribunal", [None])[0])
    where = f"WHERE tribunal_code = '{tribunal}'" if tribunal else ""
    return psql_json(f"""
        SELECT coalesce(json_agg(raw_json ORDER BY date_issued DESC NULLS LAST, case_no), '[]')
        FROM (
          SELECT raw_json, date_issued, case_no
          FROM judgments
          {where}
          ORDER BY date_issued DESC NULLS LAST, case_no
          LIMIT {limit}
        ) j;
    """)


def handle_rules(qs):
    limit = _clamp_int(qs.get("limit", [None])[0], 20, 1, 200)
    return psql_json(f"""
        SELECT coalesce(json_agg(t), '[]') FROM (
          SELECT instrument, n_judgments, n_difc, n_adgm, n_sicc
          FROM rule_frequency
          ORDER BY n_judgments DESC, instrument
          LIMIT {limit}
        ) t;
    """)


def handle_tribunal_means(_qs):
    return psql_json("""
        SELECT coalesce(json_agg(t), '[]') FROM (
          SELECT tribunal_code, n_judgments,
                 round(mean_pr_score::numeric, 2) AS mean_pr,
                 round(mean_sp_score::numeric, 2) AS mean_sp
          FROM tribunal_means_v02
          ORDER BY mean_pr DESC NULLS LAST
        ) t;
    """)


def handle_search(qs):
    q_raw = (qs.get("q", [""])[0] or "").strip()
    if not q_raw:
        return []
    # Cap query length and strip newlines/quotes — psql -v substitution
    # pastes the value into the SQL text, so we both restrict the alphabet
    # AND wrap it in plainto_tsquery (which is grammar-safe by definition).
    q = "".join(c for c in q_raw if c.isalnum() or c in " -._/").strip()[:200]
    if not q:
        return []
    # alphabet is restricted above, but defence-in-depth: SQL-quote escape
    q_lit = "'" + q.replace("'", "''") + "'"
    limit = _clamp_int(qs.get("limit", [None])[0], 10, 1, 50)
    # LEFT JOIN keeps unlinked-but-searchable raw docs in the result set.
    # `case_no` falls back to the document's inferred case number, so
    # callers can tell coded-and-linked rows from raw-only rows by the
    # presence of `gold_set` / `is_coded`.
    return psql_json(f"""
        SELECT coalesce(json_agg(t), '[]') FROM (
          SELECT
            coalesce(j.case_no, d.case_no_inferred, '(unknown)') AS case_no,
            d.tribunal_code,
            j.date_issued,
            d.filename,
            (j.id IS NOT NULL) AS is_coded,
            j.gold_set,
            ts_rank(to_tsvector('english', d.text_extracted),
                    plainto_tsquery('english', {q_lit})) AS rank,
            ts_headline('english', d.text_extracted,
                        plainto_tsquery('english', {q_lit}),
                        'StartSel=<<,StopSel=>>,MaxFragments=2,MaxWords=18,MinWords=6') AS snippet
          FROM documents d
          LEFT JOIN judgments j ON j.id = d.judgment_id
          WHERE to_tsvector('english', coalesce(d.text_extracted, ''))
                @@ plainto_tsquery('english', {q_lit})
          ORDER BY rank DESC
          LIMIT {limit}
        ) t;
    """)


def handle_rule_modules(_qs):
    """List all rule modules + their schema-extracted scopes."""
    idx_path = f"{RULES_DIR}/_index.json"
    if not os.path.exists(idx_path):
        return []
    with open(idx_path) as f:
        return json.load(f)


def handle_claims(_qs):
    """Claim-type registry — drives the simulator's rule routing."""
    path = f"{RULES_DIR}/_claims.json"
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        return json.load(f)


def handle_jurisdictions(_qs):
    """Multi-jurisdiction routing data: per-tribunal posture, per-rule
    primary jurisdiction + applies_in list, plus the cross-border path
    catalogue. Drives both the conflict-of-laws resolver and the
    cross-border dashboard view."""
    path = f"{RULES_DIR}/_jurisdictions.json"
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        return json.load(f)


def handle_certification_states(_qs):
    """Aggregate the per-module certification state. Returns a
    {module → metadata} dict, with state defaulting to 'draft' when no
    metadata file exists. The spec (lifecycle, transitions, checklist)
    lives at rules/_certification.yaml — served at /api/certification_spec."""
    out = {}
    if not os.path.exists(RULES_DIR):
        return out
    for fn in os.listdir(RULES_DIR):
        if not fn.endswith("_metadata.json"):
            continue
        try:
            with open(f"{RULES_DIR}/{fn}") as f:
                meta = json.load(f)
            module = meta.get("module_name") or fn[:-len("_metadata.json")]
            out[module] = meta
        except (OSError, json.JSONDecodeError):
            continue
    return out


def handle_certification_spec(_qs):
    """Serve the certification spec YAML as plain text for clients that
    want to consume the human-readable form. (For programmatic use,
    /api/certification_states is enough.)"""
    path = f"{RULES_DIR}/_certification.yaml"
    if not os.path.exists(path):
        return {"error": "no certification spec on disk"}
    with open(path) as f:
        return {"yaml": f.read()}


def _load_json(path: str, default):
    if not os.path.exists(path):
        return default
    with open(path) as f:
        return json.load(f)


_TRIBUNAL_CODES = {"DIFC", "ADGM", "SICC", "FOREIGN_ARBITRAL_TRIBUNAL", "HONG_KONG_HIGH_COURT", "ANY"}


def handle_conflict_route(_qs, body: bytes):
    """POST /api/conflict_route — multi-jurisdiction routing.

    Inputs:  {forum, originating_forum?, claim_type, governing_law?}
    Output:  {forum_posture, applicable_rules, recognition_chain,
              public_policy_overrides, narrative}

    The resolver walks three layers:
      1. The local forum's posture (default governing law, recognition
         path, public-policy authority).
      2. Rules whose `applies_in` list includes the forum AND whose
         primary jurisdiction matches the governing law (or fall back
         to the forum's default).
      3. If `originating_forum` is set, append the cross-border-path
         catalogue's recognition chain — these are the gates that must
         be cleared *before* the substantive rules in (2) bind.
    """
    try:
        req = json.loads(body or b"{}")
    except json.JSONDecodeError as e:
        raise RuntimeError(f"bad JSON request: {e}")
    forum = str(req.get("forum", "")).upper()
    originating_forum = (req.get("originating_forum") or None)
    if originating_forum:
        originating_forum = str(originating_forum).upper()
    claim_type = str(req.get("claim_type", "")).strip()
    governing_law = (req.get("governing_law") or None)
    if governing_law:
        governing_law = str(governing_law).upper()

    if forum not in _TRIBUNAL_CODES:
        raise RuntimeError(f"unknown forum: {forum!r}")
    if originating_forum and originating_forum not in _TRIBUNAL_CODES:
        raise RuntimeError(f"unknown originating_forum: {originating_forum!r}")

    juris = _load_json(f"{RULES_DIR}/_jurisdictions.json", {"tribunals": [], "rule_jurisdictions": [], "cross_border_paths": []})
    claims = _load_json(f"{RULES_DIR}/_claims.json", {"claim_types": []})

    forum_posture = next((t for t in juris.get("tribunals", []) if t["code"] == forum), None)

    # Layer (3): cross-border recognition chain (must clear before substantive rules)
    recognition_chain: list[dict] = []
    cb_match = None
    if originating_forum:
        for path in juris.get("cross_border_paths", []):
            if path["local_forum"] != forum:
                continue
            if path.get("originating_forum") != originating_forum:
                continue
            if claim_type and path.get("claim_type") != claim_type:
                continue
            cb_match = path
            break
        if cb_match:
            for mod_name in cb_match.get("recognition_chain", []):
                rule = next((r for r in juris.get("rule_jurisdictions", []) if r["module"] == mod_name), None)
                if rule:
                    recognition_chain.append({**rule, "reason": f"recognition gate for {originating_forum} → {forum}"})

    # Layer (2): substantive rules from the claim registry, filtered by forum + governing law
    applicable_rules: list[dict] = []
    if claim_type:
        ct = next((c for c in claims.get("claim_types", []) if c["claim_type"] == claim_type), None)
        if ct:
            for r in ct.get("applicable_rules", []):
                if r.get("tribunal") == forum:
                    rj = next((rr for rr in juris.get("rule_jurisdictions", [])
                               if rr["module"] == r["module"] and rr["scope"] == r["scope"]), None)
                    merged = {**r, **(rj or {})}
                    applicable_rules.append(merged)

    # If governing_law was supplied and differs from forum, lift any English-law-via-statute
    # interpretation rules that apply in this forum even though they're not registered for the
    # specific claim_type — typical of cross-border substantive claims under ADGM AELR.
    if governing_law and governing_law != forum:
        for rj in juris.get("rule_jurisdictions", []):
            if forum in (rj.get("applies_in") or []) and rj.get("primary_jurisdiction") == governing_law:
                already = any(a.get("module") == rj["module"] and a.get("scope") == rj["scope"] for a in applicable_rules)
                if not already and rj.get("role_class") in ("interpretation", "gate"):
                    applicable_rules.append({**rj, "tribunal": forum,
                                             "when": f"Imported into {forum} as {governing_law} rule of decision",
                                             "role": rj.get("role_class")})

    public_policy_overrides = [
        r for r in (recognition_chain + applicable_rules)
        if r.get("public_policy_gate")
    ]

    narrative_lines = []
    if forum_posture:
        narrative_lines.append(f"Local forum: {forum_posture['label']}.")
        narrative_lines.append(f"Default rule of decision: {forum_posture['default_governing_law']}.")
        if forum_posture.get("english_law_via_statute"):
            narrative_lines.append("English common law applies wholesale via statute (the AELR pathway).")
        narrative_lines.append(f"Recognition path: {forum_posture['recognition_path']}.")
        narrative_lines.append(f"Public-policy authority: {forum_posture['public_policy_authority']}.")
    if cb_match:
        narrative_lines.append("")
        narrative_lines.append(f"Cross-border path matched: \"{cb_match['name']}\".")
        narrative_lines.append(cb_match.get("note", ""))
    if governing_law and governing_law != forum:
        narrative_lines.append("")
        narrative_lines.append(f"Governing law ({governing_law}) differs from forum ({forum}); cross-border substantive interpretation rules lifted in.")

    return {
        "forum": forum,
        "originating_forum": originating_forum,
        "claim_type": claim_type,
        "governing_law": governing_law,
        "forum_posture": forum_posture,
        "cross_border_path": cb_match,
        "recognition_chain": recognition_chain,
        "applicable_rules": applicable_rules,
        "public_policy_overrides": public_policy_overrides,
        "narrative": narrative_lines,
    }


_MODULE_RE = re.compile(r"^[a-z][a-z0-9_]+$")
_SCOPE_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")


def handle_rule_validate(_qs, body: bytes):
    """POST /api/rule_validate — runs `catala typecheck` against the
    supplied source and returns {ok, errors?, output?}. The source is
    written to a tempfile (so error line numbers stay legible) and
    discarded immediately. Does not touch the rules/ directory."""
    if CATALA_BIN is None:
        raise RuntimeError("catala binary not found")
    try:
        req = json.loads(body or b"{}")
    except json.JSONDecodeError as e:
        raise RuntimeError(f"bad JSON request: {e}")
    source = req.get("source")
    if not isinstance(source, str) or len(source) > 200_000:
        raise RuntimeError("source must be a string under 200KB")

    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".catala_en", delete=False) as f:
        f.write(source)
        tmp_path = f.name
    try:
        tc = subprocess.run(
            [CATALA_BIN, "typecheck", "--no-stdlib", tmp_path],
            capture_output=True, text=True, timeout=15,
        )
        if tc.returncode != 0:
            return {"ok": False, "stage": "typecheck", "errors": tc.stderr.strip() or tc.stdout.strip()}
        # also run interpret for #[test] scopes if any
        run = subprocess.run(
            [CATALA_BIN, "interpret", "--no-stdlib", tmp_path],
            capture_output=True, text=True, timeout=15,
        )
        if run.returncode != 0:
            return {"ok": False, "stage": "interpret", "errors": run.stderr.strip() or run.stdout.strip()}
        return {"ok": True, "interpret_output": run.stdout.strip()}
    finally:
        try: os.unlink(tmp_path)
        except OSError: pass


_FILENAME_RE = re.compile(r"^[a-z][a-z0-9_]+\.catala_en$")


def handle_rule_save(_qs, body: bytes):
    """POST /api/rule_save — admin-mode only. Writes a validated rule
    module to rules/<filename>. Refuses unless HABEAS_ADMIN_MODE=1.
    Filename whitelisted to `^[a-z][a-z0-9_]+\\.catala_en$`."""
    if os.environ.get("HABEAS_ADMIN_MODE") != "1":
        raise RuntimeError("save-back is disabled. Start the API with HABEAS_ADMIN_MODE=1 to enable.")
    if CATALA_BIN is None:
        raise RuntimeError("catala binary not found")
    try:
        req = json.loads(body or b"{}")
    except json.JSONDecodeError as e:
        raise RuntimeError(f"bad JSON request: {e}")
    filename = str(req.get("filename", ""))
    source = req.get("source")
    if not _FILENAME_RE.match(filename):
        raise RuntimeError(f"bad filename: must match {_FILENAME_RE.pattern}")
    if not isinstance(source, str) or len(source) > 200_000:
        raise RuntimeError("source must be a string under 200KB")

    # Validate first; refuse to save anything that does not typecheck.
    res = handle_rule_validate(_qs, body)
    if not res.get("ok"):
        return {"saved": False, "validation": res}

    dest = f"{RULES_DIR}/{filename}"
    overwrote = os.path.exists(dest)
    with open(dest, "w") as f:
        f.write(source)
    return {"saved": True, "path": f"rules/{filename}", "overwrote_existing": overwrote}


def _audit_log(module: str, scope: str, inputs: dict,
               output: dict | None, success: bool, error: str | None,
               duration_ms: int, source_label: str | None) -> None:
    """Insert an audit row for a single /api/rule_run call. Soft-fail —
    if Postgres is unreachable the run still returns successfully; the
    log is best-effort, not a gate.

    Strategy: pack the row as a single JSON document, send to psql, and
    let `jsonb_populate_record` do the typing. Avoids the brittle psql
    `\\set` quoting path (which choked on box-drawing characters in
    catala's error messages).
    """
    try:
        canonical_inputs = json.dumps(inputs, sort_keys=True, separators=(",", ":"))
        sha = hashlib.sha256(canonical_inputs.encode("utf-8")).hexdigest()
        row = {
            "module": module,
            "scope": scope,
            "inputs": inputs,
            "output": output,
            "success": success,
            "error": (error or "")[:4000] if error else None,
            "duration_ms": int(duration_ms),
            "inputs_sha256": sha,
            "source_label": (source_label or "")[:64] if source_label else None,
        }
        cmd = [
            "psql",
            "-h", PGHOST, "-p", PGPORT, "-U", PGUSER, "-d", PGDATABASE,
            "-At", "--no-psqlrc",
            "-v", "ON_ERROR_STOP=1",
        ]
        # Pass the JSON payload as a dollar-quoted string so embedded
        # quotes, newlines, and backslashes (e.g. \uXXXX inside
        # catala's box-drawing error messages) round-trip cleanly. The
        # `$j$` tag is unique to this code path; we just sanity-check
        # the payload doesn't contain it (it never legitimately would).
        json_line = json.dumps(row, separators=(",", ":"))
        if "$j$" in json_line:
            json_line = json_line.replace("$j$", "")  # paranoia
        sql = (
            "INSERT INTO rule_runs\n"
            "  (module, scope, inputs, output, success, error,\n"
            "   duration_ms, inputs_sha256, source_label)\n"
            "SELECT j->>'module', j->>'scope', j->'inputs', j->'output',\n"
            "       (j->>'success')::boolean, j->>'error',\n"
            "       (j->>'duration_ms')::integer, j->>'inputs_sha256',\n"
            "       j->>'source_label'\n"
            f"FROM (SELECT $j${json_line}$j$::jsonb AS j) t;\n"
        )
        subprocess.run(cmd, input=sql, capture_output=True, text=True, timeout=5)
    except Exception:
        # Audit logging is best-effort. Never let an audit failure
        # surface to the caller.
        pass


def handle_rule_run(_qs, body: bytes):
    """POST /api/rule_run — runs `catala interpret -F json` against
    a rule module's named scope, with JSON inputs piped over stdin.
    Logs every call (success or failure) to the audit table."""
    if CATALA_BIN is None:
        raise RuntimeError(
            "catala binary not found. Activate the opam switch or install "
            "catala at ~/.opam/catala/bin/catala."
        )
    try:
        req = json.loads(body or b"{}")
    except json.JSONDecodeError as e:
        raise RuntimeError(f"bad JSON request: {e}")
    module = str(req.get("module", ""))
    scope = str(req.get("scope", ""))
    inputs = req.get("inputs", {})
    source_label = str(req.get("source_label", "")) or None
    if not _MODULE_RE.match(module):
        raise RuntimeError(f"bad module name: {module!r}")
    if not _SCOPE_RE.match(scope):
        raise RuntimeError(f"bad scope name: {scope!r}")
    rule_file = f"{RULES_DIR}/{module}.catala_en"
    if not os.path.exists(rule_file):
        raise RuntimeError(f"unknown rule module: {module}")
    cmd = [
        CATALA_BIN, "interpret",
        "-F", "json",
        "--no-stdlib",
        f"--scope={scope}",
        "--input=-",
        rule_file,
    ]
    t0 = time.time()
    out = subprocess.run(
        cmd,
        input=json.dumps(inputs),
        capture_output=True, text=True, timeout=15,
    )
    duration_ms = int((time.time() - t0) * 1000)
    if out.returncode != 0:
        err = out.stderr.strip() or "catala failed"
        _audit_log(module, scope, inputs, None, False, err, duration_ms, source_label)
        raise RuntimeError(err)
    raw = out.stdout.strip()
    if not raw:
        _audit_log(module, scope, inputs, {}, True, None, duration_ms, source_label)
        return {}
    try:
        result = json.loads(raw)
    except json.JSONDecodeError as e:
        _audit_log(module, scope, inputs, None, False, f"parse: {e}", duration_ms, source_label)
        raise RuntimeError(f"could not parse catala output: {e}\n{raw}")
    _audit_log(module, scope, inputs, result, True, None, duration_ms, source_label)
    return result


_DATE_RES = [
    # 5 March 2026 / 5th March 2026 / March 5 2026 / 5-Mar-2026
    re.compile(r"(\d{1,2})(?:st|nd|rd|th)?\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})", re.IGNORECASE),
    re.compile(r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(\d{4})", re.IGNORECASE),
    re.compile(r"(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\.?\s+(\d{4})", re.IGNORECASE),
    re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b"),
    re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b"),
    re.compile(r"\b(\d{1,2})\.(\d{1,2})\.(\d{4})\b"),
]
_MONTHS = {m: i for i, m in enumerate(
    ["January","February","March","April","May","June","July","August","September","October","November","December"], start=1)}
_MONTHS_SHORT = {m[:3].lower(): i for m, i in _MONTHS.items()}
# Currency / amount: AED 12,345.67 / USD 1,000 / GBP 12.5 million / £150,000
_AMOUNT_RE = re.compile(
    r"(AED|USD|GBP|EUR|SGD|HKD|US\$|£|\$|€|S\$)\s*([\d]{1,3}(?:[,]\d{3})*(?:\.\d{1,4})?(?:\s*(?:million|billion|m|bn))?)\b",
    re.IGNORECASE,
)
# Citation: [2025] SGHC(I) 25 / [2026] ADGMCFI 0006 / [1990] UKHL 2 / CFI 058/2024
_CITATION_RES = [
    re.compile(r"\[(\d{4})\]\s*(SGHC\(I\)|ADGMCFI|UKHL|UKSC|EWCA(?:\s*(?:Civ|Crim))?|EWHC|AC|WLR|SLR|QB|KB)\s*(\d{1,4})"),
    re.compile(r"\b(CFI|ARB|ENF|DEC|CA|TC)\s+(\d{2,5})\s*/\s*(\d{4})\b", re.IGNORECASE),
    re.compile(r"\b(ADGMCFI)-(\d{4})-(\d{2,4})\b"),
    re.compile(r"\b(SIC/OA|OA)\s+(\d{1,3})\s*/\s*(\d{4})\b", re.IGNORECASE),
]
# Parties: capitalised name(s) before/after ` v `. Allows `(1) Foo Ltd
# (2) Bar PJSC ...` enumerated defendants and tolerates trailing
# punctuation. Greedy enough to catch full corporate names but bounded
# at common terminators.
_PARTIES_RE = re.compile(
    r"([A-Z][A-Za-z0-9&.,\-' ]{2,120}?)"
    r"\s+(?:v|vs\.?|versus)\.?\s+"
    r"((?:\(\d+\)\s*)?[A-Z][A-Za-z0-9&.,\-'() ]{2,200}?)"
    r"(?=\s+(?:and|in|where|on|of|claim|order|judgment|application|appeal|the court|para)\b|[\.,\n\[]|$)",
    re.IGNORECASE,
)
# Statutes / RDC / etc.
_INSTRUMENT_RES = [
    re.compile(r"\b(?:RDC|DIFC RDC)\s*(?:Part\s*)?\d{1,3}(?:\.\d{1,3})*"),
    re.compile(r"\bADGM Court Procedure Rules(?: 20\d{2})?\b"),
    re.compile(r"\bADGM (?:Application of English Law Regulations|Arbitration Regulations|Companies Regulations|Real Property Regulations)(?: 20\d{2})?\b"),
    re.compile(r"\bInternational Arbitration Act(?: 1994(?: \(2020 Rev Ed\))?)?\b"),
    re.compile(r"\bNew York Convention\b"),
    re.compile(r"\bs(?:ection)?\s*\d{1,3}(?:\([a-z\d]\))?(?:\([a-z\d]\))?\b", re.IGNORECASE),
    re.compile(r"\bArticle\s*\d{1,4}\b", re.IGNORECASE),
    re.compile(r"\bPractice Direction(?: No\.\s*\d+(?: of \d{4})?)?\b"),
]


def _parse_date_match(m) -> str | None:
    g = m.groups()
    try:
        if len(g) == 3:
            # Determine ordering
            if g[0].isalpha():  # "March 5 2026"
                month = _MONTHS.get(g[0].title()) or _MONTHS_SHORT.get(g[0][:3].lower())
                day, year = int(g[1]), int(g[2])
            elif g[1].isalpha():  # "5 March 2026" / "5 Mar 2026"
                day = int(g[0])
                month = _MONTHS.get(g[1].title()) or _MONTHS_SHORT.get(g[1][:3].lower())
                year = int(g[2])
            elif len(g[0]) == 4:  # "2026-03-05"
                year, month, day = int(g[0]), int(g[1]), int(g[2])
            else:                 # "5/3/2026" or "5.3.2026" — assume DMY
                day, month, year = int(g[0]), int(g[1]), int(g[2])
            if not month or not (1 <= month <= 12) or not (1 <= day <= 31) or not (1900 <= year <= 2100):
                return None
            return f"{year:04d}-{month:02d}-{day:02d}"
    except (ValueError, AttributeError):
        return None
    return None


def handle_ingest(_qs, body: bytes):
    """POST /api/ingest — heuristic regex sweep over pasted plain text
    or HTML. Returns an `events.json`-shaped skeleton: detected dates,
    parties, monetary amounts, citations, and instruments. The sweep is
    deliberately additive (records every match) and lossy (no dedup at
    this layer beyond exact string equality); the human author edits
    the result before saving alongside a Catala rule."""
    try:
        req = json.loads(body or b"{}")
    except json.JSONDecodeError as e:
        raise RuntimeError(f"bad JSON request: {e}")
    text = req.get("text", "")
    if not isinstance(text, str) or len(text) > 1_000_000:
        raise RuntimeError("text must be a string under 1MB")

    # Strip HTML tags if it looks like HTML.
    if "<" in text and ">" in text and ("<html" in text.lower() or "<p" in text.lower() or "<div" in text.lower()):
        text = re.sub(r"<script[^>]*>.*?</script>", " ", text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"&nbsp;", " ", text)
        text = re.sub(r"&amp;", "&", text)
        text = re.sub(r"&[a-z]+;", " ", text)

    text = re.sub(r"[ \t]+", " ", text).strip()

    # Dates
    dates: list[str] = []
    for r in _DATE_RES:
        for m in r.finditer(text):
            iso = _parse_date_match(m)
            if iso and iso not in dates:
                dates.append(iso)

    # Citations
    citations: list[str] = []
    for r in _CITATION_RES:
        for m in r.finditer(text):
            full = m.group(0).strip()
            if full not in citations:
                citations.append(full)

    # Amounts
    amounts: list[dict] = []
    for m in _AMOUNT_RE.finditer(text):
        cur = m.group(1).upper().replace("US$", "USD").replace("£", "GBP").replace("€", "EUR").replace("S$", "SGD")
        if cur == "$":
            cur = "USD"
        raw = m.group(2)
        normalized_str = raw.replace(",", "").lower().strip()
        multiplier = 1
        if normalized_str.endswith("billion") or normalized_str.endswith("bn"):
            multiplier = 1_000_000_000
            normalized_str = normalized_str.replace("billion", "").replace("bn", "").strip()
        elif normalized_str.endswith("million") or normalized_str.endswith("m"):
            multiplier = 1_000_000
            normalized_str = normalized_str.replace("million", "").replace("m", "").strip()
        try:
            value = float(normalized_str) * multiplier
        except ValueError:
            continue
        amounts.append({
            "currency": cur,
            "value": value,
            "raw": m.group(0),
        })

    # Parties (the V vs. pattern)
    parties: list[dict] = []
    seen_pairs = set()
    for m in _PARTIES_RE.finditer(text):
        c = m.group(1).strip().rstrip(",.; ")
        d = m.group(2).strip().rstrip(",.; ")
        # Filter out obvious non-party matches: short noun phrases, all-cap roles
        if len(c.split()) > 12 or len(d.split()) > 12:
            continue
        if c.lower() in {"either", "neither", "both", "the parties"} or d.lower() in {"either", "neither", "both"}:
            continue
        key = (c.lower()[:60], d.lower()[:60])
        if key in seen_pairs:
            continue
        seen_pairs.add(key)
        parties.append({"claimant": c, "defendant": d})

    # Instruments / rules cited
    instruments: list[str] = []
    for r in _INSTRUMENT_RES:
        for m in r.finditer(text):
            v = m.group(0).strip()
            if v not in instruments and len(v) >= 3:
                instruments.append(v)

    # Tribunal hint
    tribunal = None
    if re.search(r"\bDIFC\b", text):
        tribunal = "DIFC Courts"
    elif re.search(r"\bADGM\b", text):
        tribunal = "ADGM Courts"
    elif re.search(r"\bSICC\b|\bSGHC\(I\)\b|Singapore International Commercial", text):
        tribunal = "Singapore International Commercial Court"

    # Build events.json skeleton (lifted from the existing trace events files)
    skeleton = {
        "case_no": citations[0] if citations else "",
        "neutral_citation": next((c for c in citations if c.startswith("[")), ""),
        "tribunal": tribunal or "",
        "judge": "",
        "decision_date": dates[-1] if dates else "",  # heuristic: last date is often decision
        "parties": parties[0] if parties else {"claimant": "", "defendant": ""},
        "all_parties": parties,
        "amounts": amounts,
        "all_dates": dates,
        "all_citations": citations,
        "instruments_cited": instruments,
        "fact_summary": "",
        "human_findings_required": [],
        "events": [],
        "_extraction": {
            "n_dates": len(dates),
            "n_citations": len(citations),
            "n_amounts": len(amounts),
            "n_parties_pairs": len(parties),
            "n_instruments": len(instruments),
            "input_chars": len(text),
        }
    }
    return skeleton


def handle_corpus_coverage(_qs):
    """Per-tribunal corpus coverage stats — coded judgments,
    raw-discovered-but-uncoded cases, link rate. Surfaces the
    structured-layer ceiling as an explicit metric."""
    return psql_json("""
        SELECT coalesce(json_agg(t ORDER BY t.tribunal_code), '[]') FROM (
          WITH per_trib AS (
            SELECT
              tribunals.code AS tribunal_code,
              tribunals.full_name AS tribunal_name,
              (SELECT count(*) FROM judgments WHERE tribunal_code = tribunals.code) AS coded_judgments,
              (SELECT count(*) FROM judgments WHERE tribunal_code = tribunals.code AND gold_set) AS gold_set,
              (SELECT count(*) FROM documents WHERE tribunal_code = tribunals.code) AS raw_docs,
              (SELECT count(*) FROM documents WHERE tribunal_code = tribunals.code AND judgment_id IS NOT NULL) AS linked_docs,
              (SELECT count(DISTINCT case_no_inferred) FROM documents
                 WHERE tribunal_code = tribunals.code AND case_no_inferred IS NOT NULL
                   AND case_no_inferred NOT IN (SELECT case_no FROM judgments WHERE tribunal_code = tribunals.code)
              ) AS discovered_uncoded_cases
            FROM tribunals
          )
          SELECT
            tribunal_code,
            tribunal_name,
            coded_judgments,
            gold_set,
            raw_docs,
            linked_docs,
            CASE WHEN raw_docs > 0 THEN round(100.0 * linked_docs / raw_docs, 1) ELSE NULL END AS link_pct,
            discovered_uncoded_cases,
            (coded_judgments + discovered_uncoded_cases) AS total_known_cases
          FROM per_trib
        ) t;
    """)


def handle_runs_recent(qs):
    """List the most recent rule_run rows (no input/output bodies — keeps
    the response small; details are loadable per-id via /api/runs/<id>
    if we add that later)."""
    limit = _clamp_int(qs.get("limit", [None])[0], 50, 1, 500)
    return psql_json(f"""
        SELECT coalesce(json_agg(t ORDER BY t.ts DESC), '[]') FROM (
          SELECT id, ts, module, scope, success, error, duration_ms,
                 source_label, inputs_sha256
          FROM rule_runs
          ORDER BY ts DESC
          LIMIT {limit}
        ) t;
    """)


def handle_runs_stats(_qs):
    """Aggregate audit-log stats: per-module run count, success rate,
    median duration. Drives the dashboard's provenance-trail panel."""
    return psql_json("""
        SELECT coalesce(json_agg(t ORDER BY t.runs DESC), '[]') FROM (
          SELECT module, scope,
                 count(*) AS runs,
                 count(*) FILTER (WHERE success) AS successes,
                 round(percentile_cont(0.5) WITHIN GROUP (ORDER BY duration_ms)::numeric, 0) AS median_ms,
                 max(ts) AS last_ts
          FROM rule_runs
          GROUP BY module, scope
        ) t;
    """)


ROUTES = {
    "/api/health":          handle_health,
    "/api/judgments":       handle_judgments,
    "/api/rules":           handle_rules,
    "/api/search":          handle_search,
    "/api/tribunal_means":  handle_tribunal_means,
    "/api/rule_modules":    handle_rule_modules,
    "/api/claims":          handle_claims,
    "/api/runs/recent":     handle_runs_recent,
    "/api/runs/stats":      handle_runs_stats,
    "/api/corpus/coverage": handle_corpus_coverage,
    "/api/jurisdictions":   handle_jurisdictions,
    "/api/certification_states":  handle_certification_states,
    "/api/certification_spec":    handle_certification_spec,
}

POST_ROUTES = {
    "/api/rule_run":        handle_rule_run,
    "/api/rule_validate":   handle_rule_validate,
    "/api/rule_save":       handle_rule_save,
    "/api/ingest":          handle_ingest,
    "/api/conflict_route":  handle_conflict_route,
}


class Handler(BaseHTTPRequestHandler):
    server_version = "habeas-api/0.1"

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _json(self, status, body):
        payload = json.dumps(body, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self._cors()
        self.end_headers()
        self.wfile.write(payload)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self._cors()
        self.end_headers()

    def do_GET(self):
        url = urlparse(self.path)
        handler = ROUTES.get(url.path)
        if handler is None:
            return self._json(404, {"error": "not found", "path": url.path,
                                    "routes": sorted(list(ROUTES.keys()) + list(POST_ROUTES.keys()))})
        try:
            data = handler(parse_qs(url.query))
            return self._json(200, data)
        except RuntimeError as e:
            return self._json(500, {"error": str(e)})
        except subprocess.TimeoutExpired:
            return self._json(504, {"error": "subprocess timed out"})

    def do_POST(self):
        url = urlparse(self.path)
        handler = POST_ROUTES.get(url.path)
        if handler is None:
            return self._json(404, {"error": "not found", "path": url.path,
                                    "post_routes": sorted(POST_ROUTES.keys())})
        n = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(n) if n > 0 else b""
        try:
            data = handler(parse_qs(url.query), body)
            return self._json(200, data)
        except RuntimeError as e:
            return self._json(500, {"error": str(e)})
        except subprocess.TimeoutExpired:
            return self._json(504, {"error": "subprocess timed out"})

    # quieter access log
    def log_message(self, fmt, *args):
        sys.stderr.write(f"[api] {self.log_date_time_string()} {fmt % args}\n")


def main():
    server = ThreadingHTTPServer((API_HOST, API_PORT), Handler)
    print(f"[api] listening on http://{API_HOST}:{API_PORT}")
    print(f"[api] db = postgres://{PGUSER}@{PGHOST}:{PGPORT}/{PGDATABASE}")
    print(f"[api] try: curl -s 'http://{API_HOST}:{API_PORT}/api/health'")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == "__main__":
    main()
