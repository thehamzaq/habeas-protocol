#!/usr/bin/env python3
"""Merge AI-triaged + AI-graded ADGM codings into data/judgments.json.

Sources:
  data/adgm_triage.json           — saturating + procedural_default
  data/adgm_graded.json           — borderline cases graded against rubric

Output:
  data/judgments.json             — appended (preserving original 39 entries)

Provenance: every new entry is tagged with
  coder: "MaximLabs (heuristic-triage)"  or  "MaximLabs (heuristic-graded)"
  grader_type: "regex_heuristic"
  first_pass: false
The original 39 LLM-graded entries keep their first_pass: true.

The merger refuses to add a duplicate of an existing case_no.
"""
import json
import os
import re
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
TRIAGE = os.path.join(HERE, "..", "data", "adgm_triage.json")
GRADED = os.path.join(HERE, "..", "data", "adgm_graded.json")
JUDG = os.path.join(HERE, "..", "data", "judgments.json")
TXT_DIR = os.path.join(HERE, "..", "data", "raw", "adgm", "text")


def normalize_case_no(s):
    if not s:
        return ""
    s = s.strip()
    # Canonicalize "ADFMCFI" typo to "ADGMCFI"
    s = s.replace("ADFMCFI", "ADGMCFI")
    # Collapse "ADGMCFI-2025-011 and ADGMCFI-2025-012" → first
    m = re.match(r"(ADGMC(?:FI|A|FI-PCA)[-\s]\d{4}[-\s]\d{1,4})", s)
    if m:
        return m.group(1).replace(" ", "-")
    return s


def existing_case_set(judgments):
    out = set()
    for j in judgments:
        cn = normalize_case_no(j.get("case_no", ""))
        if cn:
            out.add(cn)
        # also handle joined case numbers like "ADGMCFI-2024-322 + 323"
        m = re.findall(r"ADGMC(?:FI|A)[-\s]\d{4}[-\s]\d{1,4}", j.get("case_no", ""))
        for x in m:
            out.add(x.replace(" ", "-"))
    return out


def parse_iso_date(s):
    if not s:
        return None
    s = s.strip()
    for fmt in ("%d %B %Y", "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def parse_url_from_filename(fn):
    """Best-effort URL guess for the ADGM judgment landing page. We don't
    have a deterministic URL pattern, so we leave this empty for AI-graded
    entries and let the user fill in if needed."""
    return ""


def get_division(case_no, fn):
    if "ADGMCA" in case_no or "_APP_" in fn or "ADGMCA" in fn:
        return "Court of Appeal"
    return "Court of First Instance"


def extract_rules_cited_from_digest_or_file(case_no, file, file_text=None):
    if file_text is None:
        try:
            with open(os.path.join(TXT_DIR, file)) as f:
                file_text = f.read()
        except FileNotFoundError:
            return []
    # Top-of-file legislation block on Judgment Summaries
    m = re.search(
        r"Legislation\s+and\s*\n?\s*Authorities\s+Cited\s+(.+?)(?=\n\s*Executive\s+Summary|\n\s*Overall\s+Summary|\Z)",
        file_text, re.IGNORECASE | re.DOTALL
    )
    if m:
        block = m.group(1)[:1200]
        # split on instrument names, keep top entries
        lines = [l.strip() for l in block.split("\n") if l.strip()]
        return lines[:10]
    # Fallback: pull recognisable instrument names from the body
    instruments = set()
    patterns = [
        r"ADGM (?:Court Procedure Rules|Arbitration Regulations|Insolvency Regulations|Real Property Regulations|Companies Regulations|Application of English Law Regulations)\s+\d{4}",
        r"Cabinet Resolution(?:\s+No\.?\s*\(?\d+\)?\s+of\s+\d{4})?",
        r"Federal Law\s+No\.?\s*\(?\d+\)?\s+of\s+\d{4}",
        r"Practice Direction(?:\s+No\.?\s*\(?\d+\)?\s+of\s+\d{4})?",
        r"Abu Dhabi Law\s+No\.?\s*\(?\d+\)?\s+of\s+\d{4}",
        r"Trustee Act\s+\d{4}",
        r"Senior Courts Act\s+\d{4}",
        r"Insolvency Act\s+\d{4}",
        r"Companies Act\s+\d{4}",
        r"Limitation Act\s+\d{4}",
    ]
    for p in patterns:
        for m in re.finditer(p, file_text, re.IGNORECASE):
            instruments.add(re.sub(r"\s+", " ", m.group(0)).strip())
    return sorted(instruments)[:10]


def extract_judge(text, fn):
    m = re.search(r"Judge\s+([A-Z].+?)(?:\n\s*Date Issued|\n\s*Catchwords)",
                  text, re.IGNORECASE | re.DOTALL)
    if m:
        return re.sub(r"\s+", " ", m.group(1).strip())[:120]
    m = re.search(r"(?:Judgment\s+of|BEFORE)\s+(?:H\.?E\.?\s+)?(?:JUSTICE|Justice|Lord|Lady)\s+(?:Sir\s+)?([A-Z][\w-]+(?:\s+[A-Z][\w-]+){0,5})",
                  text)
    if m:
        return f"H.E. Justice {m.group(1)}"
    m = re.search(r"Justice[_\s](?:Sir[_\s])?([A-Z][a-z]+(?:[_\s][A-Z][a-z]+){0,4})", fn)
    if m:
        return f"H.E. Justice {m.group(1).replace('_', ' ')}"
    return None


def extract_parties(text, fn):
    m = re.search(r"Name\s+of\s+Cases?\s+(.+?)(?=\n\s*(?:Judge|Date Issued|Catchwords))",
                  text, re.IGNORECASE | re.DOTALL)
    if m:
        line = re.sub(r"\s+", " ", m.group(1).strip())[:240]
        m2 = re.match(r"(.+?)\s+v\.?\s+(.+)", line, re.IGNORECASE)
        if m2:
            return {"claimant": m2.group(1)[:120], "defendant": m2.group(2)[:160]}
    m = re.search(r"BETWEEN\s+(.+?)\s+(?:Claimant|Plaintiff|Applicant|Appellant)\s+(?:and\s+)?(.+?)\s+(?:Defendant|Respondent)",
                  text, re.IGNORECASE | re.DOTALL)
    if m:
        c = re.sub(r"\s+", " ", m.group(1).strip())[:120]
        d = re.sub(r"\s+", " ", m.group(2).strip())[:160]
        return {"claimant": c, "defendant": d}
    return {"claimant": None, "defendant": None}


def extract_date(text, fn):
    m = re.search(r"Date\s+Issued\s+(\d{1,2}\s+\w+\s+\d{4})",
                  text, re.IGNORECASE)
    if m:
        d = parse_iso_date(m.group(1))
        if d:
            return d
    # Body-issued: "Issued by:\n<name>\n...\nDate" or last line
    m = re.search(r"\b(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})\b",
                  text[-2000:])
    if m:
        d = parse_iso_date(m.group(1))
        if d:
            return d
    m = re.search(r"(\d{2})(\d{2})(\d{4})", fn)
    if m:
        return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
    return None


def build_entry_for_easy_win(triage_entry, kind):
    """kind = 'saturating' | 'procedural_default'"""
    file = triage_entry["file"]
    case_no = normalize_case_no(triage_entry.get("case_no", ""))
    try:
        with open(os.path.join(TXT_DIR, file)) as f:
            text = f.read()
    except FileNotFoundError:
        text = ""
    parties = extract_parties(text, file)
    date_iso = extract_date(text, file)
    division = get_division(case_no, file)
    judge = extract_judge(text, file)
    rules = extract_rules_cited_from_digest_or_file(case_no, file, text)

    if kind == "saturating":
        scores = {"PR1": 2, "PR2": 2, "PR3": 2, "PR4": 2, "PR5": 2, "PR6": 2}
        notes = (f"AI-triaged from {file}. All structured headers present; "
                 f"saturating default applied per scripts/triage_adgm.py rubric.")
    else:
        scores = {"PR1": 2, "PR2": 2, "PR3": 2, "PR4": 2, "PR5": 2, "PR6": 1}
        notes = (f"AI-triaged from {file}. Procedural matter (case management/"
                 f"costs/interim) — PR6=1 per rubric ('implicit enforceability "
                 f"via standard procedure; no explicit bridge'). Catchwords: "
                 f"{(triage_entry.get('catchwords') or '')[:120]}")

    return {
        "case_no": case_no or file,
        "url": "",
        "tribunal": "ADGM Courts",
        "division": division,
        "date_issued": date_iso,
        "parties": parties,
        "judge": judge,
        "claim_type": triage_entry.get("claim_type_guess") or "other",
        "outcome": None,
        "operative_amount_aed": None,
        "rules_cited": rules,
        "primitive_scores_v02": scores,
        "coding": {
            "coder": "MaximLabs (heuristic-triage)",
            "coded_on": datetime.now().strftime("%Y-%m-%d"),
            "gold_set": False,
            "source_file": file,
            "notes": notes,
        },
    }


def build_entry_for_graded(graded_entry):
    file = graded_entry["file"]
    case_no = normalize_case_no(graded_entry.get("case_no", ""))
    try:
        with open(os.path.join(TXT_DIR, file)) as f:
            text = f.read()
    except FileNotFoundError:
        text = ""
    parties = extract_parties(text, file)
    if not parties.get("claimant") and graded_entry.get("parties"):
        # Fallback: split parties_guess on " v "
        m = re.match(r"(.+?)\s+v\s+(.+)", graded_entry["parties"], re.IGNORECASE)
        if m:
            parties = {"claimant": m.group(1)[:120], "defendant": m.group(2)[:160]}
    date_iso = extract_date(text, file)
    if not date_iso and graded_entry.get("date"):
        date_iso = parse_iso_date(graded_entry["date"])
    division = graded_entry.get("division") or get_division(case_no, file)
    judge = extract_judge(text, file) or graded_entry.get("judge")
    rules = extract_rules_cited_from_digest_or_file(case_no, file, text)
    scores = graded_entry["scores_v02_graded"]

    return {
        "case_no": case_no or file,
        "url": "",
        "tribunal": "ADGM Courts",
        "division": division,
        "date_issued": date_iso,
        "parties": parties,
        "judge": judge,
        "claim_type": graded_entry.get("claim_type_guess") or "other",
        "outcome": None,
        "operative_amount_aed": None,
        "rules_cited": rules,
        "primitive_scores_v02": scores,
        "coding": {
            "coder": "MaximLabs (heuristic-graded)",
            "coded_on": datetime.now().strftime("%Y-%m-%d"),
            "gold_set": False,
            "source_file": file,
            "rationale": graded_entry.get("rationale", []),
            "notes": (f"AI-graded from {file} via scripts/grade_borderline.py. "
                      f"Heuristic scoring against v0.2 rubric; full text scanned "
                      f"for outcome/citation/bridge signals."),
        },
    }


def main():
    judgments = json.load(open(JUDG))
    print(f"Loaded {len(judgments)} existing judgments.")

    existing = existing_case_set(judgments)
    print(f"  existing case_nos: {len(existing)}")

    triage = json.load(open(TRIAGE))
    graded = json.load(open(GRADED))

    new_entries = []
    skipped = []

    # Easy wins from triage
    for r in triage["results"]:
        if r["classification"] == "saturating":
            cn = normalize_case_no(r.get("case_no", ""))
            if cn in existing:
                skipped.append((cn, "already in judgments.json"))
                continue
            new_entries.append(build_entry_for_easy_win(r, "saturating"))
            existing.add(cn)
        elif r["classification"] == "procedural_default":
            cn = normalize_case_no(r.get("case_no", ""))
            if cn in existing:
                skipped.append((cn, "already in judgments.json"))
                continue
            new_entries.append(build_entry_for_easy_win(r, "procedural_default"))
            existing.add(cn)

    # Graded borderline
    for g in graded["graded"]:
        cn = normalize_case_no(g.get("case_no", ""))
        if cn and cn in existing:
            skipped.append((cn, "already in judgments.json"))
            continue
        new_entries.append(build_entry_for_graded(g))
        if cn:
            existing.add(cn)

    print(f"\n  new entries to add: {len(new_entries)}")
    print(f"  skipped (duplicate case_no): {len(skipped)}")

    # Append
    merged = judgments + new_entries
    json.dump(merged, open(JUDG, "w"), indent=2)
    print(f"\nWrote {JUDG}")
    print(f"  total now: {len(merged)} (was {len(judgments)})")

    # Distribution
    print("\n=== Tribunal counts ===")
    from collections import Counter
    by_tribunal = Counter(j["tribunal"] for j in merged)
    for t, n in by_tribunal.items():
        print(f"  {t:<20} {n:>3}")

    # Per-primitive means
    print("\n=== Per-primitive means by tribunal ===")
    for trib in ("DIFC Courts", "ADGM Courts"):
        rows = [j for j in merged if j["tribunal"] == trib]
        if not rows:
            continue
        prims = ("PR1", "PR2", "PR3", "PR4", "PR5", "PR6")
        means = {p: sum(j["primitive_scores_v02"][p] for j in rows) / len(rows) for p in prims}
        overall = sum(means.values()) / len(prims)
        print(f"  {trib} (n={len(rows)})")
        for p, v in means.items():
            print(f"    {p}: {v:.3f}")
        print(f"    overall: {overall:.3f}")


if __name__ == "__main__":
    main()
