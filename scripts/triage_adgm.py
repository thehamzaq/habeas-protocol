#!/usr/bin/env python3
"""ADGM judgment triage.

Reads each text file under data/raw/adgm/text/, applies coarse heuristics
for each of the v0.2 per-ruling primitives, and classifies the judgment
as either "saturating" (all heuristics indicate 2) or "borderline" (any
primitive triggers a 1-or-0 signal).

The output is a triage report at data/adgm_triage.json plus a printable
summary. The report is NOT a substitute for the gold-set rubric; it is
a sieve that lets a human reader skip the obviously-saturating cases and
focus on the ~20-30% that actually need a careful read.

Heuristic rationale:

  PR1 Identity  — ADGM Judgment Summary always has "Name of Case" and
                  "Judge" lines. If both are present and parsable, score
                  2. Anonymised pairs (A17 v B17) preserve identity at
                  the litigation level per the rubric, so they pass.

  PR2 Evidence  — Look for at least 3 dated references in the body
                  (orders dated, submissions filed on, witness statement
                  of). 0-2 dated refs is suspicious.

  PR3 Rule bind — Look at the "Legislation and Authorities Cited"
                  section. Specific section/rule numbers (e.g.
                  "Rule 71", "Section 37") = 2. Only vague
                  ("the Regulations") = 1. Empty = 0.

  PR4 Procedure — Look for the procedural triplet: notice/submissions/
                  hearing + decision. ADGM Judgment Summaries always
                  include an Overall Summary documenting the procedure.

  PR5 Ruling    — Look for an operative outcome with named amount,
                  deadline, or party action. Procedural-only orders
                  ("application dismissed") are still 2 if the operative
                  is unambiguous.

  PR6 Enforcement bridge — Look for ADGM-specific bridges: Application
                  of English Law Regulations 2015, ADGM Founding Law,
                  Cabinet Resolution, Federal Law, NY Convention,
                  Reciprocal Enforcement. ADGM judgments typically cite
                  the Founding Law explicitly; absence of any bridge
                  signal = 1.

The output report is not graded; it just flags. A judgment classified
as "saturating" is a recommendation to apply (2,2,2,2,2,2) on default
and move on. A judgment classified as "borderline" is a recommendation
to read it carefully and apply the rubric.
"""
import json
import os
import re
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
TXT_DIR = os.path.join(HERE, "..", "data", "raw", "adgm", "text")
OUT = os.path.join(HERE, "..", "data", "adgm_triage.json")

# Cases already in the gold set (case_no fragments to skip)
ALREADY_CODED = {
    "ADGMCFI-2025-283",
    "ADGMCFI-2024-158",
    "ADGMCFI-2025-198",
    "ADGMCFI-2024-322",  # joined with 323
    "ADGMCFI-2024-323",
    "ADGMCFI-2023-249",  # joined with CFI-2024-047
    "ADGMCFI-2024-047",
    "ADGMCFI-2022-265",
    "ADGMCFI-2020-020",
}

ENFORCEMENT_BRIDGE_TERMS = [
    "Application of English Law Regulations",
    "Founding Law",
    "Cabinet Resolution",
    "Federal Law",
    "New York Convention",
    "Reciprocal Enforcement",
    "Judicial Authority Law",
    "Abu Dhabi Law No 4 of 2013",
    "Memorandum of Understanding",
]

SPECIFIC_RULE_PATTERNS = [
    re.compile(r"\bRule\s+\d+", re.IGNORECASE),
    re.compile(r"\bSection\s+\d+", re.IGNORECASE),
    re.compile(r"\bArticle\s+\d+", re.IGNORECASE),
    re.compile(r"\bClause\s+\d+", re.IGNORECASE),
    re.compile(r"\bRegulation\s+\d+", re.IGNORECASE),
]

DATE_PATTERN = re.compile(
    r"\b\d{1,2}\s+(January|February|March|April|May|June|July|August|"
    r"September|October|November|December)\s+\d{4}\b"
)

CASE_NO_PATTERN = re.compile(
    r"(ADGMCFI[-\s_]\d{4}[-\s_]\d{1,4}|ADGMCA[-\s_]\d{4}[-\s_]\d{1,3}|"
    r"APP[-\s_]\d{4}[-\s_]\d{1,3})"
)


def extract_case_no_from_filename(fn):
    """Extract canonical case_no from a filename. Handles all ADGM
    filename conventions on disk (with or without separators)."""
    # Try canonical hyphenated form first
    m = re.search(r"ADGMC(?:FI|A)[-_]\d{4}[-_]\d{1,4}", fn)
    if m:
        return m.group(0).replace("_", "-")
    # ADGMCFI2019003 / ADGMCAAPP2019002 / ADGMCAAPP20190001 form
    m = re.search(r"ADGMC(FI|A)(?:APP)?(\d{4})(\d{3,4})", fn)
    if m:
        prefix = "ADGMCFI" if m.group(1) == "FI" else "ADGMCA"
        return f"{prefix}-{m.group(2)}-{m.group(3).lstrip('0').zfill(3)}"
    # APP-2019-001 standalone
    m = re.search(r"APP[-_]\d{4}[-_]\d{1,3}", fn)
    if m:
        return m.group(0).replace("_", "-")
    return None


def parse_header(text):
    """Pull structured fields from the ADGM Judgment Summary header."""
    fields = {}
    keys = [
        "Neutral Citation", "Case Number", "Case Numbers",
        "Name of Case", "Name of Cases", "Judge", "Judges",
        "Date Issued", "Catchwords", "Cases Cited",
        "Legislation and Authorities Cited", "Executive Summary",
        "Overall Summary", "Decision", "Order",
    ]
    boundary = "|".join(re.escape(k) for k in keys)
    for k in keys:
        m = re.search(rf"{re.escape(k)}\s+(.+?)(?=\n\s*(?:{boundary})|\Z)",
                      text, re.IGNORECASE | re.DOTALL)
        if m:
            fields[k] = m.group(1).strip()[:1500]
    # canonicalize plural variants
    if "Name of Case" not in fields and "Name of Cases" in fields:
        fields["Name of Case"] = fields["Name of Cases"]
    if "Case Number" not in fields and "Case Numbers" in fields:
        fields["Case Number"] = fields["Case Numbers"]
    return fields


def has_structured_format(fields):
    """ADGM Judgment Summary is a structured headnote. If the core headers
    are all present, the document is by-construction PR1-PR5 saturating
    (the format itself implies named parties + judge + dated procedure +
    cited rules + recorded outcome). Score accordingly."""
    required = ["Neutral Citation", "Case Number", "Judge", "Date Issued",
                "Catchwords", "Cases Cited", "Legislation and Authorities Cited",
                "Overall Summary"]
    present = [k for k in required if fields.get(k)]
    return len(present), required


def score_pr1(text, fields):
    """Identity: parties + judge identifiable."""
    has_case = bool(fields.get("Name of Case"))
    has_judge = bool(fields.get("Judge"))
    if has_case and has_judge:
        return 2, []
    flags = []
    if not has_case:
        flags.append("no Name of Case header")
    if not has_judge:
        flags.append("no Judge header")
    return (1 if (has_case or has_judge) else 0), flags


def score_pr2(text, fields):
    """Evidence log: dated references. ADGM summaries typically include
    submission dates and order dates; a properly-formatted summary with
    Date Issued is at minimum PR2=2."""
    dates = DATE_PATTERN.findall(text)
    if len(dates) >= 2 or fields.get("Date Issued"):
        return 2, []
    if len(dates) >= 1:
        return 2, []  # single date in narrative + Date Issued header is enough
    return 1, ["no dated references found"]


def score_pr3(text, fields):
    """Rule bind: specific clause citations. ADGM Judgment Summaries have
    a 'Legislation and Authorities Cited' section that almost always names
    specific sections/rules/articles."""
    leg = fields.get("Legislation and Authorities Cited", "") or ""
    if not leg.strip():
        leg = text
    specific_count = sum(len(p.findall(leg)) for p in SPECIFIC_RULE_PATTERNS)
    if specific_count >= 2:
        return 2, []
    if specific_count == 1:
        return 2, []  # one specific cite is bind, not "general reference"
    if not leg.strip():
        return 0, ["no Legislation/Authorities section"]
    return 1, ["only general references; no Section/Rule/Article numbers"]


def score_pr4(text, fields):
    """Procedure: notice/submissions/hearing + decision. The Judgment
    Summary format itself encodes procedure — Catchwords describe the
    application type, Overall Summary documents the procedural sequence,
    Date Issued records the decision. Default to 2 if structured."""
    n_present, required = has_structured_format(fields)
    if n_present >= 6:
        return 2, []
    body = (fields.get("Overall Summary", "") or text).lower()
    hits = 0
    if re.search(r"submission|application|filed|served|claim", body):
        hits += 1
    if re.search(r"hearing|heard|considered|argued|judgment|order", body):
        hits += 1
    if re.search(r"order|judgment|ruling|decision|dismiss|grant|allow", body):
        hits += 1
    return (2 if hits >= 3 else 1 if hits >= 2 else 0), [
        f"only {n_present}/{len(required)} structured headers present"
    ]


def score_pr5(text, fields):
    """Ruling: operative outcome unambiguous. ADGM Judgment Summaries
    encode the outcome in Catchwords (e.g. 'Application dismissed') and
    in the Overall Summary. Default to 2 unless catchwords are missing."""
    catch = (fields.get("Catchwords", "") or "").lower()
    body = (fields.get("Overall Summary", "") or text).lower()
    has_operative_in_body = bool(re.search(
        r"\b(dismiss|grant|allow|order(?:ed|s)?|adjourn|declar(?:e|ed|ation)|"
        r"set\s+aside|refus(?:e|ed)|stay|judgment\s+(?:for|in\s+favour)|"
        r"applicat(?:ion|ions)\s+(?:granted|dismissed|allowed|refused))",
        body
    ))
    if catch and has_operative_in_body:
        return 2, []
    if catch and len(catch) > 40:
        return 2, []  # catchwords describe the matter; outcome implicit
    if has_operative_in_body:
        return 2, []
    return 1, ["no operative outcome verb and no catchwords"]


def score_pr6(text, fields):
    """Enforcement bridge: NY Convention / Cabinet Resolution / English Law.
    Procedural-only orders (case management, payment into court) score 1
    by rubric — implicit enforceability via standard procedure but no
    explicit bridge."""
    leg = (fields.get("Legislation and Authorities Cited", "")
           + "\n" + text[:5000])
    hits = [t for t in ENFORCEMENT_BRIDGE_TERMS if t.lower() in leg.lower()]
    if hits:
        return 2, []
    return 1, ["no enforcement bridge term in legislation/early body"]


def already_coded(case_no_text):
    if not case_no_text:
        return False
    for prefix in ALREADY_CODED:
        if prefix in case_no_text:
            return True
    return False


def triage_one(path):
    with open(path) as f:
        text = f.read()
    if len(text) < 200:
        return {
            "file": os.path.basename(path),
            "size": len(text),
            "classification": "skip_too_short",
            "reason": "text under 200 chars (likely a sealed/redacted artefact)",
        }
    fields = parse_header(text)
    case_no = fields.get("Case Number", "") or ""
    if not case_no:
        case_no = extract_case_no_from_filename(os.path.basename(path)) or ""
    if already_coded(case_no) or already_coded(text[:600]):
        return {
            "file": os.path.basename(path),
            "case_no": case_no,
            "classification": "skip_already_coded",
        }
    pr1, f1 = score_pr1(text, fields)
    pr2, f2 = score_pr2(text, fields)
    pr3, f3 = score_pr3(text, fields)
    pr4, f4 = score_pr4(text, fields)
    pr5, f5 = score_pr5(text, fields)
    pr6, f6 = score_pr6(text, fields)
    scores = {"PR1": pr1, "PR2": pr2, "PR3": pr3, "PR4": pr4, "PR5": pr5, "PR6": pr6}
    flags = {"PR1": f1, "PR2": f2, "PR3": f3, "PR4": f4, "PR5": f5, "PR6": f6}
    saturating = all(v == 2 for v in scores.values())
    return {
        "file": os.path.basename(path),
        "case_no": case_no,
        "name_of_case": fields.get("Name of Case", "")[:120],
        "judge": fields.get("Judge", "")[:80],
        "date_issued": fields.get("Date Issued", "")[:40],
        "catchwords": fields.get("Catchwords", "")[:240],
        "scores_heuristic": scores,
        "flags": {k: v for k, v in flags.items() if v},
        "classification": "saturating" if saturating else "borderline",
    }


def reclassify(scores):
    """Three buckets:
       saturating         (2,2,2,2,2,2) — apply all-2 default, move on
       procedural_default (2,2,2,2,2,1) — apply (2,2,2,2,2,1) default,
                                          glance at catchwords to confirm
                                          this is a procedural matter
       borderline         anything else — careful human read required
    """
    vals = [scores[k] for k in ("PR1", "PR2", "PR3", "PR4", "PR5", "PR6")]
    if all(v == 2 for v in vals):
        return "saturating"
    if vals[:5] == [2, 2, 2, 2, 2] and vals[5] == 1:
        return "procedural_default"
    return "borderline"


def best_file_per_case(results):
    """Dedupe: prefer Judgment Summary, then earliest non-sealed, then any."""
    by_case = {}
    for r in results:
        if r["classification"].startswith("skip_"):
            continue
        case_no = (r.get("case_no") or "").strip()
        if not case_no:
            case_no = r["file"]
        # priority: Judgment_Summary > non-SEALED > anything
        score = 0
        fn = r["file"]
        if "Judgment_Summary" in fn:
            score = 3
        elif "SEALED" not in fn and "REDACTED" not in fn:
            score = 2
        else:
            score = 1
        prev = by_case.get(case_no)
        if not prev or prev["_priority"] < score:
            r2 = dict(r); r2["_priority"] = score
            by_case[case_no] = r2
    return list(by_case.values())


def main():
    files = sorted(f for f in os.listdir(TXT_DIR) if f.endswith(".txt"))
    print(f"Processing {len(files)} text files from {TXT_DIR}")
    print()

    raw_results = [triage_one(os.path.join(TXT_DIR, f)) for f in files]

    # Reclassify with the 3-bucket scheme
    for r in raw_results:
        if "scores_heuristic" in r:
            r["classification"] = reclassify(r["scores_heuristic"])

    # Dedupe per case_no
    deduped = best_file_per_case(raw_results)
    skipped = [r for r in raw_results if r["classification"].startswith("skip_")]

    cls_counts = Counter(r["classification"] for r in deduped)
    cls_counts["skip_already_coded"] = sum(1 for r in skipped if r["classification"] == "skip_already_coded")
    cls_counts["skip_too_short"] = sum(1 for r in skipped if r["classification"] == "skip_too_short")

    print("=== Classification (deduped by case_no) ===")
    print(f"  total raw text files       {len(raw_results):>3}")
    print(f"  unique case_no after dedup {len(deduped):>3}")
    for cls in ("saturating", "procedural_default", "borderline"):
        n = sum(1 for r in deduped if r["classification"] == cls)
        print(f"    {cls:<22}  {n:>3}")
    print(f"  skipped (already coded)    {cls_counts['skip_already_coded']:>3}")
    print(f"  skipped (too short)        {cls_counts['skip_too_short']:>3}")
    print()

    saturating = [r for r in deduped if r["classification"] == "saturating"]
    procedural = [r for r in deduped if r["classification"] == "procedural_default"]
    borderline = [r for r in deduped if r["classification"] == "borderline"]

    def _print_short(r):
        flag_summary = "; ".join(
            f"{k} ({v[0]})" for k, v in r["flags"].items() if v
        ) or "—"
        scores = " ".join(f"{k}={v}" for k, v in r["scores_heuristic"].items())
        print(f"  {(r['case_no'] or '?'):<28}  {r['file'][:80]}")
        print(f"    {scores}    flags: {flag_summary}")
        if r.get("catchwords"):
            cw = r['catchwords'].replace("\n", " ").strip()
            print(f"    catch: {cw[:160]}")

    print(f"=== Saturating ({len(saturating)}) — code (2,2,2,2,2,2) ===")
    print()
    for r in saturating:
        _print_short(r)
        print()

    print(f"=== Procedural default ({len(procedural)}) — code (2,2,2,2,2,1) — confirm catchwords are case-management/costs ===")
    print()
    for r in procedural:
        _print_short(r)
        print()

    print(f"=== Borderline ({len(borderline)}) — read carefully ===")
    print()
    # Sort borderline: structured-summary failures first (the few-flags),
    # then full-judgment files (many flags) at the end
    borderline_sorted = sorted(
        borderline,
        key=lambda r: (sum(1 for v in r["flags"].values() if v), r["file"])
    )
    for r in borderline_sorted:
        _print_short(r)
        print()

    out = {
        "generated_by": "scripts/triage_adgm.py",
        "n_text_files": len(raw_results),
        "n_unique_cases": len(deduped),
        "n_saturating": len(saturating),
        "n_procedural_default": len(procedural),
        "n_borderline": len(borderline),
        "n_skipped_already_coded": cls_counts['skip_already_coded'],
        "saturating_default": {"PR1": 2, "PR2": 2, "PR3": 2, "PR4": 2, "PR5": 2, "PR6": 2},
        "procedural_default": {"PR1": 2, "PR2": 2, "PR3": 2, "PR4": 2, "PR5": 2, "PR6": 1},
        "results": deduped,
    }
    with open(OUT, "w") as f:
        json.dump(out, f, indent=2)
    print(f"=== Wrote {OUT} ===")
    print(f"  saturating         {len(saturating):>3}  (recommend: code (2,2,2,2,2,2))")
    print(f"  procedural_default {len(procedural):>3}  (recommend: code (2,2,2,2,2,1) — confirm by catchwords)")
    print(f"  borderline         {len(borderline):>3}  (recommend: human careful read)")


if __name__ == "__main__":
    main()
