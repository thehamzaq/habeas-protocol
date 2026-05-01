#!/usr/bin/env python3
"""Migrate the habeas-protocol corpus into a Postgres instance.

Two layers:
  (1) STRUCTURED — `data/judgments.json` (121 hand/AI-coded entries) →
      tables `judgments`, `primitive_scores`, `rules_cited`, `judgment_rules`.
  (2) RAW        — every scraped file under `data/raw/{judgments,adgm,sicc}/`
      → table `documents` (one row per file, with extracted text where present
      and a best-effort case_no inferred from the filename or the bytes).

The script is idempotent: re-running it UPSERTs the structured layer and
re-loads the raw layer in place. It only inserts; nothing is deleted.

USAGE
-----
  # 1. Initialize and start a local Postgres (one-time):
  ./scripts/postgres_local.sh init      # creates ~/.local/var/pgdata
  ./scripts/postgres_local.sh start

  # 2. Create the schema:
  psql -h localhost -p 5433 -d habeas -f db/schema.sql

  # 3. Run this script:
  python3 scripts/migrate_to_postgres.py

  # 4. Sample queries: see db/queries.sql.

The script speaks PG via stdlib's psycopg if installed, falling back to
shelling out to `psql`. The fallback path keeps the dependency footprint
zero (Catala + Postgres are the only required tools).
"""
from __future__ import annotations

import hashlib
import html
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
JUDGMENTS_JSON = ROOT / "data" / "judgments.json"
RAW_DIR = ROOT / "data" / "raw"

PG_HOST = os.environ.get("PGHOST", "localhost")
PG_PORT = os.environ.get("PGPORT", "5433")
PG_USER = os.environ.get("PGUSER", os.environ.get("USER", "postgres"))
PG_DB   = os.environ.get("PGDATABASE", "habeas")


# ---------- shelling out to psql (zero-dep fallback) ----------

def psql(sql: str, *, fetch: bool = False) -> str:
    """Run a SQL statement via psql. Returns stdout if fetch=True."""
    cmd = ["psql", "-h", PG_HOST, "-p", PG_PORT, "-U", PG_USER, "-d", PG_DB,
           "-v", "ON_ERROR_STOP=1", "-q", "-X"]
    if fetch:
        cmd += ["-At", "-F", "\t", "-c", sql]
    else:
        cmd += ["-c", sql]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"psql failed:\n{r.stderr}\n--\nSQL: {sql[:200]}…")
    return r.stdout


def psql_copy(table: str, columns: list[str], rows: Iterable[list[Any]]) -> None:
    """Bulk insert via \\copy from a temp CSV file. Robust to embedded quotes,
    newlines, commas, etc., because the CSV is fully written to disk before
    psql reads it back."""
    import csv
    import tempfile
    n = 0
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", suffix=".csv", delete=False, newline=""
    ) as f:
        path = f.name
        w = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
        for r in rows:
            # represent NULL with the empty string + matching FORCE_NULL list,
            # or use a sentinel. We use \\N text-format style and pass that
            # token to FORCE_NULL via the COPY options.
            w.writerow(['' if v is None else v for v in r])
            n += 1
    try:
        # Build a FORCE_NULL list from columns that may legitimately be empty.
        force_null = ",".join(columns)
        copy_cmd = (
            f"\\copy {table} ({','.join(columns)}) "
            f"FROM '{path}' "
            f"WITH (FORMAT csv, NULL '', FORCE_NULL ({force_null}))"
        )
        cmd = ["psql", "-h", PG_HOST, "-p", PG_PORT, "-U", PG_USER, "-d", PG_DB,
               "-v", "ON_ERROR_STOP=1", "-q", "-X", "-c", copy_cmd]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(f"\\copy into {table} failed:\n{r.stderr}")
        print(f"  copied {n:,} rows → {table}")
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


# ---------- helpers ----------

def case_no_from_filename(name: str, tribunal: str) -> str | None:
    """Best-effort inference of case_no from a filename. Returns None if
    nothing recognizable is found.

    DIFC pattern: ...-2024-difc-cfi-082.html → 'CFI 082/2024'
                  ...-2025-difc-ca-001.html  → 'CA 001/2025'
    ADGM pattern: ADGMCFI-2024-158_-... → 'ADGMCFI-2024-158'
    SICC pattern: file slugs vary; fall back to None.
    """
    base = Path(name).stem
    if tribunal == "DIFC":
        # DIFC filenames come in several flavours; the canonical form
        # is `<DIVISION> <NNN>/<YYYY>` (3-digit zero-padded number):
        #   ...-2024-difc-cfi-082...     → CFI 082/2024
        #   ...cfi-0822024...            → CFI 082/2024  (no separators)
        #   ...arb-0082026...            → ARB 008/2026
        #   arb0312025-...               → ARB 031/2025  (no hyphen at all)
        m = re.search(r"(\d{4})-difc-([a-z]+)-(\d{3})", base)
        if m:
            year, division, num = m.groups()
            return f"{division.upper()} {num}/{year}"
        m = re.search(r"\b([a-z]{2,4})-(\d{3})(\d{4})\b", base)
        if m:
            division, num, year = m.groups()
            return f"{division.upper()} {num}/{year}"
        # Bare-prefix form: lowercase division stuck directly to a
        # 3-or-4-digit number stuck directly to the year (e.g. `arb0312025`).
        m = re.search(r"\b(cfi|arb|enf|ca|tcd|tc|dec)(\d{3})(\d{4})\b", base)
        if m:
            division, num, year = m.groups()
            return f"{division.upper()} {num}/{year}"
        return None
    if tribunal == "ADGM":
        # The structured layer canonicalises every ADGM identifier as
        # `<PREFIX>-<YYYY>-<NNN>` (3-digit zero-padded number). Filenames
        # come in many shapes, so we normalise everything we see:
        #
        #   ADGMCFI-2024-158                   → ADGMCFI-2024-158
        #   ADGMCA-2025-001                    → ADGMCA-2025-001
        #   ADGMCA-APP-2019-001-...            → ADGMCA-2019-001
        #   ADGMCAAPP20190001                  → ADGMCA-2019-001
        #   ADGMCA2022001 / ADGMCA2022002      → ADGMCA-2022-001
        #   -2025-_ADGMCFI_0008_Judgment_...   → (filename inference
        #                                          falls through to body)
        prefixes = ["ADGMCFI", "ADGMCA", "ADGMTC"]
        # Form 1: <PREFIX>-YYYY-NNN (canonical, often with optional -APP-)
        for prefix in prefixes:
            m = re.search(rf"({prefix})(?:-APP)?-(\d{{4}})-(\d{{2,4}})", name)
            if m:
                return f"{m.group(1)}-{m.group(2)}-{int(m.group(3)):03d}"
        # Form 2: <PREFIX><YYYY><NNN> (no separators, possibly with APP)
        for prefix in prefixes:
            m = re.search(rf"({prefix})(?:APP)?(\d{{4}})(\d{{3,4}})", name)
            if m:
                return f"{m.group(1)}-{m.group(2)}-{int(m.group(3)):03d}"
        # Form 3: -YYYY-_ADGMCFI_NNNN (judgment-summary filename — gives
        # only the neutral citation, NOT the case number; case_no must
        # come from the body via case_no_from_adgm_text).
        return None
    if tribunal == "SICC":
        # SICC raw filenames are `YYYY_SGHCI_N.txt`. Returning the neutral
        # citation here doesn't link to the structured judgments table (which
        # keys on `OA N/YYYY`), so this is just a marker — the actual link is
        # built later in `case_no_from_sicc_text` reading the file body.
        m = re.search(r"(\d{4})_SGHCI_(\d+)", base)
        if m:
            return f"[{m.group(1)}] SGHC(I) {m.group(2)}"
        m = re.search(r"\[(\d{4})\][_\s]*SGHC\(I\)[_\s]*(\d+)", name)
        if m:
            return f"[{m.group(1)}] SGHC(I) {m.group(2)}"
        return None
    return None


SICC_OA_RE = re.compile(
    r"Originating\s+Application\s+No\s+(\d+)\s+of\s+(\d{4})",
    re.IGNORECASE,
)


def case_no_from_sicc_text(text: str | None) -> str | None:
    """Extract `OA N/YYYY` from the body of a SICC judgment text file.

    SICC structured judgments key on `OA N/YYYY`; the neutral citation
    `[YYYY] SGHC(I) N` (which we *can* read from the filename) is a
    different identifier and won't link. Reading the body finds the
    canonical `Originating Application No N of YYYY` once and converts.
    """
    if not text:
        return None
    m = SICC_OA_RE.search(text)
    if m:
        return f"OA {int(m.group(1))}/{m.group(2)}"
    return None


# ADGM: every "Judgment Summary" PDF (2025-2026 release format) carries a
# `Case Number(s) ADGMCFI-YYYY-NNN[; ADGMCFI-YYYY-NNN ...]` line in the
# body that points at the *original* case(s) it summarises. The filename
# gives only the neutral citation (`[2025] ADGMCFI 0001`) — different
# identifier. Read the body to recover the canonical key. Some summaries
# cover multiple cases — we link to the first; multi-judgment linking
# would require a schema change (a `judgment_documents` join table).
ADGM_CASE_RE = re.compile(
    # Accepts: ADGMCFI-2024-322, ADGMCA-2025-005, ADGMCFI-PCA-2025-005,
    # and tolerates a one-letter OCR slip in the prefix (ADFMCFI seen
    # in -2026-_ADGMCFI_0004 — F vs G mis-substitution).
    r"Case\s+Numbers?\s+([A-Z]{6,8})(?:-[A-Z]{2,4})?-(\d{4})-(\d{2,4})",
    re.IGNORECASE,
)
# Heuristic prefix correction: any 6-8-letter token that *looks like*
# an ADGMCFI/ADGMCA/ADGMTC family member maps to the canonical form.
ADGM_PREFIX_FIX = {
    "ADGMCFI": "ADGMCFI",
    "ADGMCA":  "ADGMCA",
    "ADGMTC":  "ADGMTC",
    "ADFMCFI": "ADGMCFI",   # one observed OCR/typo in -2026-_ADGMCFI_0004
}


def case_no_from_adgm_text(text: str | None) -> str | None:
    if not text:
        return None
    m = ADGM_CASE_RE.search(text)
    if m:
        raw_prefix, yr, num = m.group(1).upper(), m.group(2), m.group(3)
        prefix = ADGM_PREFIX_FIX.get(raw_prefix)
        if not prefix:
            return None  # ignore unknown prefix shapes
        return f"{prefix}-{yr}-{int(num):03d}"
    return None


# DIFC: HTML pages don't always carry the case number in the filename
# (anonymised cases like `1-nadil-...` strip it out). Pull from the
# body's neutral-citation pattern: `[YYYY] DIFC CFI NNN`. Some pages
# also have `Claim No. CFI NNN/YYYY` — accept either.
DIFC_BODY_NEUTRAL_RE = re.compile(
    r"\[(\d{4})\]\s*DIFC\s*([A-Z]{2,4})\s*(\d{1,4})",
)
DIFC_BODY_CLAIM_RE = re.compile(
    r"Claim\s+No\.?\s*([A-Z]{2,4})\s*(\d{1,4})\s*/\s*(\d{4})",
    re.IGNORECASE,
)


def case_no_from_difc_text(text: str | None) -> str | None:
    if not text:
        return None
    m = DIFC_BODY_CLAIM_RE.search(text)
    if m:
        return f"{m.group(1).upper()} {int(m.group(2)):03d}/{m.group(3)}"
    m = DIFC_BODY_NEUTRAL_RE.search(text)
    if m:
        year, division, num = m.group(1), m.group(2).upper(), m.group(3)
        return f"{division} {int(num):03d}/{year}"
    return None
    return None


def sha256_of(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def read_text_safe(p: Path, max_bytes: int = 5_000_000) -> str | None:
    """Read a text file, truncating gracefully. Returns None on error."""
    try:
        if p.stat().st_size > max_bytes:
            return p.read_text(errors="replace")[:max_bytes]
        return p.read_text(errors="replace")
    except Exception:
        return None


# ---------- structured layer ----------

def load_structured() -> None:
    print("Loading structured judgments from", JUDGMENTS_JSON)
    data = json.loads(JUDGMENTS_JSON.read_text())
    print(f"  {len(data)} judgments to import")

    # Tribunal map: long names → codes
    code_map = {
        "DIFC Courts": "DIFC",
        "ADGM Courts": "ADGM",
        "Singapore International Commercial Court": "SICC",
    }

    # 1. Upsert judgments and capture (case_no, tribunal_code) → id
    psql("BEGIN; CREATE TEMP TABLE _stage (raw jsonb) ON COMMIT DROP;")
    # Use INSERT ... ON CONFLICT for idempotent loads
    rules_seen: dict[str, int] = {}

    for j in data:
        trib = code_map.get(j.get("tribunal", ""), j.get("tribunal", "")[:4])
        case_no = j.get("case_no") or ""
        if not case_no:
            continue
        coding = j.get("coding") or {}
        sql = """
        INSERT INTO judgments (
          tribunal_code, case_no, url, division, date_issued,
          judge, parties_claimant, parties_defendant, claim_type, outcome,
          operative_amount_aed, coder, coded_on, gold_set, coding_notes, raw_json
        ) VALUES (
          %(trib)s, %(case_no)s, %(url)s, %(division)s, %(date_issued)s,
          %(judge)s, %(claimant)s, %(defendant)s, %(claim_type)s, %(outcome)s,
          %(amount)s, %(coder)s, %(coded_on)s, %(gold_set)s, %(notes)s, %(raw)s
        )
        ON CONFLICT (tribunal_code, case_no) DO UPDATE SET
          url = EXCLUDED.url,
          division = EXCLUDED.division,
          date_issued = EXCLUDED.date_issued,
          judge = EXCLUDED.judge,
          parties_claimant = EXCLUDED.parties_claimant,
          parties_defendant = EXCLUDED.parties_defendant,
          claim_type = EXCLUDED.claim_type,
          outcome = EXCLUDED.outcome,
          operative_amount_aed = EXCLUDED.operative_amount_aed,
          coder = EXCLUDED.coder,
          coded_on = EXCLUDED.coded_on,
          gold_set = EXCLUDED.gold_set,
          coding_notes = EXCLUDED.coding_notes,
          raw_json = EXCLUDED.raw_json
        RETURNING id;
        """
        # Use parameter binding via psql -v not supported; fall back to escaping.
        # We use a single statement per judgment with literal substitution
        # (these strings come from our own JSON, not user input).
        def esc(v: Any) -> str:
            if v is None or v == "":
                return "NULL"
            if isinstance(v, bool):
                return "TRUE" if v else "FALSE"
            if isinstance(v, (int, float)):
                return str(v)
            s = str(v).replace("'", "''")
            return f"'{s}'"

        parties = j.get("parties") or {}
        params = {
            "trib": esc(trib),
            "case_no": esc(case_no),
            "url": esc(j.get("url")),
            "division": esc(j.get("division")),
            "date_issued": esc(j.get("date_issued")),
            "judge": esc(j.get("judge")),
            "claimant": esc(parties.get("claimant")),
            "defendant": esc(parties.get("defendant")),
            "claim_type": esc(j.get("claim_type")),
            "outcome": esc(j.get("outcome")),
            "amount": esc(j.get("operative_amount_aed")),
            "coder": esc(coding.get("coder")),
            "coded_on": esc(coding.get("coded_on")),
            "gold_set": esc(bool(coding.get("gold_set"))),
            "notes": esc(coding.get("notes")),
            # JSONB literal
            "raw": "'" + json.dumps(j).replace("'", "''") + "'::jsonb",
        }
        sql = (sql.replace("%(trib)s", params["trib"])
                  .replace("%(case_no)s", params["case_no"])
                  .replace("%(url)s", params["url"])
                  .replace("%(division)s", params["division"])
                  .replace("%(date_issued)s", params["date_issued"])
                  .replace("%(judge)s", params["judge"])
                  .replace("%(claimant)s", params["claimant"])
                  .replace("%(defendant)s", params["defendant"])
                  .replace("%(claim_type)s", params["claim_type"])
                  .replace("%(outcome)s", params["outcome"])
                  .replace("%(amount)s", params["amount"])
                  .replace("%(coder)s", params["coder"])
                  .replace("%(coded_on)s", params["coded_on"])
                  .replace("%(gold_set)s", params["gold_set"])
                  .replace("%(notes)s", params["notes"])
                  .replace("%(raw)s", params["raw"]))
        out = psql(sql, fetch=True).strip()
        # parse "id\n" RETURNING block
        jid = None
        for line in out.splitlines():
            line = line.strip()
            if line.isdigit():
                jid = int(line); break
        if jid is None:
            # fallback: select it
            r = psql(f"SELECT id FROM judgments WHERE tribunal_code={params['trib']} AND case_no={params['case_no']};", fetch=True).strip()
            jid = int(r.splitlines()[0])

        # primitive scores
        v01 = j.get("primitive_scores_v01") or {}
        v02 = j.get("primitive_scores_v02") or {}
        score_rows = []
        for code, score in v01.items():
            score_rows.append((jid, "v01", code, int(score)))
        for code, score in v02.items():
            score_rows.append((jid, "v02", code, int(score)))
        if score_rows:
            psql(f"DELETE FROM primitive_scores WHERE judgment_id = {jid};")
            values = ",".join(f"({a},'{b}','{c}',{d})" for (a,b,c,d) in score_rows)
            psql(f"INSERT INTO primitive_scores (judgment_id, version, primitive, score) VALUES {values};")

        # rules cited
        psql(f"DELETE FROM judgment_rules WHERE judgment_id = {jid};")
        for instrument in j.get("rules_cited") or []:
            if instrument not in rules_seen:
                # upsert rule
                rule_sql = f"""
                INSERT INTO rules_cited (instrument) VALUES ({esc(instrument)})
                ON CONFLICT (instrument) DO UPDATE SET instrument = EXCLUDED.instrument
                RETURNING id;
                """
                ro = psql(rule_sql, fetch=True).strip()
                rid = None
                for line in ro.splitlines():
                    if line.strip().isdigit():
                        rid = int(line.strip()); break
                if rid is None:
                    rr = psql(f"SELECT id FROM rules_cited WHERE instrument = {esc(instrument)};", fetch=True).strip()
                    rid = int(rr.splitlines()[0])
                rules_seen[instrument] = rid
            psql(f"INSERT INTO judgment_rules (judgment_id, rule_id) VALUES ({jid}, {rules_seen[instrument]}) ON CONFLICT DO NOTHING;")

    print(f"  imported {len(data)} judgments, {len(rules_seen)} unique rules")


# ---------- raw layer ----------

def walk_raw_files() -> Iterable[tuple[str, str, Path]]:
    """Yield (tribunal_code, content_type, path) for every scraped document."""
    # DIFC
    difc_html = ROOT / "data" / "raw" / "judgments"
    difc_text = ROOT / "data" / "raw" / "text"
    for p in sorted(difc_html.glob("*.html")):
        if p.name.startswith("_listing"):
            continue
        yield ("DIFC", "html", p)
    for p in sorted(difc_text.glob("*.txt")):
        yield ("DIFC", "text", p)

    # ADGM. The `firecrawl/` directory holds scrape *metadata* (per-page
    # JSON listing dumps, not judgments themselves), so it's omitted —
    # those rows don't link to anything and aren't queryable. The
    # `pages/` directory (free plain-HTTP scrape) is also a working file
    # cache, not a corpus, so we skip it too.
    adgm_pdfs = ROOT / "data" / "raw" / "adgm" / "pdfs"
    adgm_text = ROOT / "data" / "raw" / "adgm" / "text"
    if adgm_pdfs.exists():
        for p in sorted(adgm_pdfs.glob("*.pdf")):
            yield ("ADGM", "pdf", p)
    if adgm_text.exists():
        for p in sorted(adgm_text.glob("*.txt")):
            yield ("ADGM", "text", p)

    # SICC
    sicc_html = ROOT / "data" / "raw" / "sicc" / "html"
    sicc_text = ROOT / "data" / "raw" / "sicc" / "text"
    if sicc_html.exists():
        for p in sorted(sicc_html.glob("*.html")):
            yield ("SICC", "html", p)
    if sicc_text.exists():
        for p in sorted(sicc_text.glob("*.txt")):
            yield ("SICC", "text", p)


def load_raw() -> None:
    print("Loading raw documents from", RAW_DIR)
    psql("TRUNCATE documents;")
    rows = []
    n_total = 0
    for tribunal, content_type, p in walk_raw_files():
        rel = p.relative_to(ROOT).as_posix()
        case_no = case_no_from_filename(p.name, tribunal)
        size = p.stat().st_size
        sha = sha256_of(p)
        text_extracted = read_text_safe(p) if content_type in ("text", "html") else None
        # Strip HTML tags for fuller search of HTML files (cheap regex pass).
        # `html.unescape` is essential — the SICC HTML uses `&nbsp;` between
        # the words "Originating Application No" and the case number, which
        # `\s+` doesn't match. Without this, every SICC HTML file silently
        # failed the case_no_from_sicc_text content-based linker.
        if content_type == "html" and text_extracted:
            text_extracted = re.sub(r"<[^>]+>", " ", text_extracted)
            text_extracted = html.unescape(text_extracted)
            text_extracted = re.sub(r"\s+", " ", text_extracted).strip()
        # SICC content-based fallback: filename gives a neutral citation,
        # but the structured layer keys on `OA N/YYYY`. Prefer the OA form
        # extracted from the body of the document so the link works.
        if tribunal == "SICC" and text_extracted:
            oa = case_no_from_sicc_text(text_extracted)
            if oa:
                case_no = oa
        # ADGM content-based fallback: judgment-summary PDFs encode only
        # the neutral citation in the filename; the *case number* lives
        # in the body as `Case Number ADGMCFI-YYYY-NNN`. Prefer body when
        # present.
        if tribunal == "ADGM" and text_extracted:
            adgm_cn = case_no_from_adgm_text(text_extracted)
            if adgm_cn:
                case_no = adgm_cn
        # DIFC content-based fallback: many filenames are anonymised
        # (e.g. `1-nadil-2-noshaba-v-...`) and strip the case number.
        # The HTML body always carries `[YYYY] DIFC CFI NNN` (or
        # `Claim No. CFI NNN/YYYY`). Use that whenever the filename
        # inferer drew a blank.
        if tribunal == "DIFC" and text_extracted and not case_no:
            difc_cn = case_no_from_difc_text(text_extracted)
            if difc_cn:
                case_no = difc_cn
        rows.append([
            tribunal,
            content_type,
            rel,
            p.name,
            size,
            sha,
            text_extracted,
            case_no,
            None,  # judgment_id, filled below
            datetime.fromtimestamp(p.stat().st_mtime).isoformat(),
        ])
        n_total += 1
    print(f"  {n_total} files queued for COPY")

    columns = ["tribunal_code", "content_type", "raw_path", "filename",
               "file_size_bytes", "sha256", "text_extracted",
               "case_no_inferred", "judgment_id", "scraped_at"]
    psql_copy("documents", columns, rows)

    # Link documents → judgments where case_no matches.
    n_linked = psql(
        "UPDATE documents d SET judgment_id = j.id "
        "FROM judgments j "
        "WHERE d.judgment_id IS NULL "
        "  AND d.tribunal_code = j.tribunal_code "
        "  AND d.case_no_inferred IS NOT NULL "
        "  AND d.case_no_inferred = j.case_no "
        "RETURNING d.id;",
        fetch=True,
    ).strip().splitlines()
    print(f"  linked {len(n_linked)} documents to structured judgments by case_no")

    # Pass 2: sibling-inherit. Many ADGM PDFs have no extractable
    # text (we don't OCR), but their `.txt` sibling does — and the
    # body-based linker has already matched the .txt to a structured
    # judgment. Propagate the link to the PDF (matched by filename
    # stem within the same tribunal).
    n_sibling = psql(
        "UPDATE documents pdf SET judgment_id = txt.judgment_id "
        "FROM documents txt "
        "WHERE pdf.judgment_id IS NULL "
        "  AND txt.judgment_id IS NOT NULL "
        "  AND pdf.tribunal_code = txt.tribunal_code "
        "  AND regexp_replace(pdf.filename, '\\.[a-z]+$', '') = "
        "      regexp_replace(txt.filename, '\\.[a-z]+$', '') "
        "RETURNING pdf.id;",
        fetch=True,
    ).strip().splitlines()
    print(f"  linked {len(n_sibling)} more by sibling-inherit (pdf ↔ txt)")

    # Pass 3: normalised-case-no fallback. The structured layer has a
    # handful of rows whose `case_no` is non-canonical (a leaked
    # filename, or an `APP-YYYY-NNN` prefix-stripped form). Strip
    # everything down to alphanumerics and re-attempt the match — this
    # catches `ADGMCA-2025-005` ↔ `APP-2025-005` and
    # `ADGMCFI-2019-003` ↔ the leaked-filename row.
    n_norm = psql(
        "UPDATE documents d SET judgment_id = j.id "
        "FROM judgments j "
        "WHERE d.judgment_id IS NULL "
        "  AND d.tribunal_code = j.tribunal_code "
        "  AND d.case_no_inferred IS NOT NULL "
        "  AND upper(regexp_replace(d.case_no_inferred, '[^A-Za-z0-9]', '', 'g')) "
        "    = upper(regexp_replace(j.case_no, '[^A-Za-z0-9]', '', 'g')) "
        "RETURNING d.id;",
        fetch=True,
    ).strip().splitlines()
    print(f"  linked {len(n_norm)} more by normalised case_no (alphanumerics only)")

    # Pass 4: substring-fallback for the edge case where the structured
    # layer's case_no is a leaked filename containing a real case
    # identifier. Match if the document's normalised case_no is a
    # substring of the structured layer's normalised case_no.
    n_sub = psql(
        "UPDATE documents d SET judgment_id = j.id "
        "FROM judgments j "
        "WHERE d.judgment_id IS NULL "
        "  AND d.tribunal_code = j.tribunal_code "
        "  AND d.case_no_inferred IS NOT NULL "
        "  AND length(d.case_no_inferred) >= 10 "
        "  AND upper(regexp_replace(j.case_no, '[^A-Za-z0-9]', '', 'g')) "
        "    LIKE '%' || upper(regexp_replace(d.case_no_inferred, '[^A-Za-z0-9]', '', 'g')) || '%' "
        "RETURNING d.id;",
        fetch=True,
    ).strip().splitlines()
    print(f"  linked {len(n_sub)} more by substring-fallback")

    # Pass 5: re-run sibling-inherit one more time so PDFs whose .txt
    # sibling was just linked by passes 3-4 also pick up the link.
    n_final = psql(
        "UPDATE documents pdf SET judgment_id = txt.judgment_id "
        "FROM documents txt "
        "WHERE pdf.judgment_id IS NULL "
        "  AND txt.judgment_id IS NOT NULL "
        "  AND pdf.tribunal_code = txt.tribunal_code "
        "  AND regexp_replace(pdf.filename, '\\.[a-z]+$', '') = "
        "      regexp_replace(txt.filename, '\\.[a-z]+$', '') "
        "RETURNING pdf.id;",
        fetch=True,
    ).strip().splitlines()
    if n_final:
        print(f"  linked {len(n_final)} more by sibling-inherit pass 2")


# ---------- main ----------

def main() -> None:
    if not shutil.which("psql"):
        sys.exit("psql not found on PATH. Activate Postgres env first:\n"
                 "  export PATH=\"$HOME/.local/bin:$PATH\"")
    print(f"Target: {PG_USER}@{PG_HOST}:{PG_PORT}/{PG_DB}")
    # sanity check
    psql("SELECT 1;")
    load_structured()
    load_raw()
    # final stats
    out = psql(
        "SELECT j.tribunal_code, count(*) "
        "FROM judgments j GROUP BY j.tribunal_code ORDER BY j.tribunal_code;",
        fetch=True
    ).strip()
    print("\nJudgments per tribunal:")
    for line in out.splitlines():
        print(" ", line)
    out = psql(
        "SELECT d.tribunal_code, d.content_type, count(*) "
        "FROM documents d GROUP BY 1,2 ORDER BY 1,2;",
        fetch=True
    ).strip()
    print("\nDocuments per tribunal × content type:")
    for line in out.splitlines():
        print(" ", line)


if __name__ == "__main__":
    main()
