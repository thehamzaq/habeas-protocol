#!/usr/bin/env python3
"""Build a structured digest of each borderline ADGM judgment.

Reads data/adgm_triage.json, takes every entry classified "borderline",
and emits a per-file digest at data/adgm_borderline_digests.json. Each
digest summarises just enough of the judgment to apply the rubric in
data/primitives.json without needing to read the entire 1000-2000 line
judgment.

Digest fields:
  case_no, file, byte_size, judgment_kind ("summary" | "full"),
  parties_guess, judge_guess, date_guess, division_guess,
  catchwords (if structured), legislation_block, key_specific_cites,
  enforcement_bridge_terms_found, outcome_phrases_found,
  first_lines, last_lines, claim_type_guess, operative_amount_guess
"""
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
TRIAGE = os.path.join(HERE, "..", "data", "adgm_triage.json")
TXT_DIR = os.path.join(HERE, "..", "data", "raw", "adgm", "text")
OUT = os.path.join(HERE, "..", "data", "adgm_borderline_digests.json")

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

SPECIFIC_CITE_PATTERNS = [
    re.compile(r"\b(?:Rule|Section|Article|Clause|Regulation|Schedule)\s+\d+(?:\.\d+|\([\dA-Za-z]+\))?", re.IGNORECASE),
    re.compile(r"\bs\s*\.\s*\d+", re.IGNORECASE),
    re.compile(r"\bArt\s*\.\s*\d+", re.IGNORECASE),
]

OUTCOME_PHRASES = [
    "application is dismissed", "application dismissed",
    "application is granted", "application granted",
    "application is allowed", "application allowed",
    "application is refused", "application refused",
    "appeal is dismissed", "appeal dismissed",
    "appeal is allowed", "appeal allowed",
    "judgment for the claimant",
    "judgment for the defendant",
    "claim is dismissed", "claim dismissed",
    "order that the", "ordered that",
    "set aside",
    "permission to appeal",
    "judgment is given",
    "i declare", "the court declares",
    "costs of the application",
    "costs reserved",
]

DATE_PATTERN = re.compile(
    r"\b\d{1,2}\s+(?:January|February|March|April|May|June|July|August|"
    r"September|October|November|December)\s+\d{4}\b"
)

AED_PATTERN = re.compile(r"AED\s*[\d,]+(?:\.\d+)?", re.IGNORECASE)
USD_PATTERN = re.compile(r"(?:US\$|USD)\s*[\d,]+(?:\.\d+)?(?:\s*(?:million|billion))?", re.IGNORECASE)
GBP_PATTERN = re.compile(r"(?:£|GBP)\s*[\d,]+(?:\.\d+)?", re.IGNORECASE)

JUDGE_FROM_FILENAME = re.compile(
    r"Justice[_\s](?:Sir[_\s])?([A-Z][a-z]+(?:[_\s][A-Z][a-z]+)*)",
)


def load_text(path):
    with open(path) as f:
        return f.read()


def get_division(case_no, text, fn):
    if "ADGMCA" in (case_no or "") or "ADGMCA" in fn:
        return "Court of Appeal"
    if "APP" in (case_no or "") or "_APP_" in fn:
        return "Court of Appeal"
    if "ADGMCFI" in (case_no or "") or "ADGMCFI" in fn:
        return "Court of First Instance"
    return None


def get_judge(text, fn, fields_judge=None):
    if fields_judge:
        return re.sub(r"\s+", " ", fields_judge[:200]).strip()
    # Try the body — judgments commonly start "Judgment of Justice X" or
    # contain "BEFORE JUSTICE X"
    m = re.search(r"(?:Judgment\s+of|BEFORE)\s+(?:H\.?E\.?\s+)?(?:JUSTICE|Justice|Lord|Lady|MR\.?\s+JUSTICE)\s+(?:Sir\s+)?([A-Z][\w-]+(?:\s+[A-Z][\w-]+){0,4})", text)
    if m:
        return m.group(0).strip()
    # filename fallback
    m = JUDGE_FROM_FILENAME.search(fn)
    if m:
        return f"Justice {m.group(1).replace('_', ' ')}"
    return None


def get_parties(text, fields_name=None, fn=""):
    if fields_name:
        return re.sub(r"\s+", " ", fields_name[:240]).strip()
    # Body pattern: "X v Y" or "BETWEEN X and Y"
    m = re.search(r"BETWEEN\s+(.+?)\s+(?:Claimant|Plaintiff|Applicant)\s+(?:and\s+)?(.+?)\s+(?:Defendant|Respondent)", text, re.IGNORECASE | re.DOTALL)
    if m:
        c = re.sub(r"\s+", " ", m.group(1)).strip()[:120]
        d = re.sub(r"\s+", " ", m.group(2)).strip()[:120]
        return f"{c} v {d}"
    # filename: "X_v_Y" or "A_v_B"
    m = re.search(r"([A-Z][A-Za-z]+(?:_[A-Za-z]+)*)_v_?([A-Z][A-Za-z]+(?:_[A-Za-z]+)*)", fn)
    if m:
        return f"{m.group(1).replace('_', ' ')} v {m.group(2).replace('_', ' ')}"
    return None


def get_date(text, fields_date=None, fn=""):
    if fields_date:
        return fields_date.strip()[:30]
    # Look in first 200 lines and last 50 lines
    for chunk in (text[:8000], text[-3000:]):
        m = DATE_PATTERN.search(chunk)
        if m:
            return m.group(0)
    # filename like _15112022_, _SEALED_30032023, etc.
    m = re.search(r"(\d{2})(\d{2})(\d{4})", fn)
    if m:
        return f"{m.group(1)}/{m.group(2)}/{m.group(3)}"
    return None


def find_specific_cites(text):
    hits = set()
    # Cap to avoid blowing up
    for p in SPECIFIC_CITE_PATTERNS:
        for m in p.finditer(text):
            hits.add(m.group(0).strip())
            if len(hits) >= 25:
                break
    return sorted(hits)[:25]


def find_bridges(text):
    return [t for t in ENFORCEMENT_BRIDGE_TERMS if t.lower() in text.lower()]


def find_outcome_phrases(text):
    body = text.lower()
    return [p for p in OUTCOME_PHRASES if p in body]


def find_amounts(text):
    return (
        AED_PATTERN.findall(text)[:3]
        + USD_PATTERN.findall(text)[:3]
        + GBP_PATTERN.findall(text)[:3]
    )


def guess_claim_type(text, catchwords):
    t = (catchwords or "")[:600] + " " + text[:1500]
    tl = t.lower()
    rules = [
        ("arbitration_recognition", ["recognition and enforcement", "recognise and enforce"]),
        ("arbitration_enforcement", ["enforce", "enforcement of arbitral"]),
        ("costs_assessment", ["costs assessment", "assessment of costs", "summary assessment"]),
        ("permission_to_appeal", ["permission to appeal"]),
        ("jurisdictional_challenge", ["jurisdiction", "challeng"]),
        ("default_judgment", ["default judgment"]),
        ("interim_relief", ["freezing order", "injunction", "interim", "preservation"]),
        ("summary_judgment", ["summary judgment"]),
        ("substantive_breach", ["breach of contract", "duty of care"]),
        ("real_property", ["mortgage", "real property", "land"]),
        ("fraud", ["fraud"]),
        ("insolvency", ["insolvency", "winding up", "liquidation", "administration"]),
        ("case_management", ["case management", "directions", "service of"]),
    ]
    for label, kws in rules:
        if any(k in tl for k in kws):
            return label
    return "other"


def main():
    triage = json.load(open(TRIAGE))
    borderline = [r for r in triage["results"] if r["classification"] == "borderline"]
    print(f"Building digests for {len(borderline)} borderline cases...")

    digests = []
    for r in borderline:
        path = os.path.join(TXT_DIR, r["file"])
        text = load_text(path)
        catchwords = (r.get("catchwords") or "").strip() or None
        # Deeper field extraction (re-parse since triage parser was conservative)
        from triage_adgm import parse_header
        fields = parse_header(text)

        case_no = r.get("case_no") or ""
        if not case_no:
            from triage_adgm import extract_case_no_from_filename
            case_no = extract_case_no_from_filename(r["file"]) or ""

        is_summary = "Judgment_Summary" in r["file"]

        digest = {
            "case_no": case_no,
            "file": r["file"],
            "byte_size": len(text),
            "judgment_kind": "summary" if is_summary else "full",
            "division_guess": get_division(case_no, text, r["file"]),
            "judge_guess": get_judge(text, r["file"], fields.get("Judge")),
            "parties_guess": get_parties(text, fields.get("Name of Case"), r["file"]),
            "date_guess": get_date(text, fields.get("Date Issued"), r["file"]),
            "catchwords": catchwords or fields.get("Catchwords", "") or None,
            "legislation_block": (fields.get("Legislation and Authorities Cited") or "")[:1200] or None,
            "specific_cites_in_body": find_specific_cites(text),
            "enforcement_bridges_found": find_bridges(text),
            "outcome_phrases_found": find_outcome_phrases(text),
            "amounts_found": find_amounts(text),
            "claim_type_guess": guess_claim_type(text, catchwords),
            "scores_heuristic": r["scores_heuristic"],
            "first_lines": "\n".join(text.splitlines()[:30])[:1500],
            "last_lines": "\n".join(text.splitlines()[-30:])[:1500],
        }
        digests.append(digest)

    with open(OUT, "w") as f:
        json.dump({"n": len(digests), "digests": digests}, f, indent=2)
    print(f"Wrote {OUT}")
    print(f"  cases: {len(digests)}")
    print(f"  summary kind: {sum(1 for d in digests if d['judgment_kind'] == 'summary')}")
    print(f"  full kind:    {sum(1 for d in digests if d['judgment_kind'] == 'full')}")


if __name__ == "__main__":
    main()
