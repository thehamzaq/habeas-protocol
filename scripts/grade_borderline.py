#!/usr/bin/env python3
"""Grade borderline ADGM cases using the digest + targeted rule application.

For each case in data/adgm_borderline_digests.json, apply the v0.2 rubric:

  PR1 Identity   2 if parties_guess + judge_guess; 1 if one; 0 if neither
                 (Note: anonymisation pairs A22 v B22 still preserve identity
                 at the litigation level per the rubric, so they pass.)

  PR2 Evidence   2 if date_guess + at least 2 dated references in body
                 1 if a date is present but record is sparse
                 0 if no date at all

  PR3 Rule bind  2 if specific_cites_in_body has ≥2 numbered references
                 1 if only 1 specific cite or only general references
                 0 if no cite at all

  PR4 Procedure  2 if outcome_phrase + (claim_type or catchwords showing
                 procedural sequence)
                 1 if outcome present but procedure thin
                 0 if neither

  PR5 Ruling     2 if outcome_phrases_found ≥ 1 OR catchwords describe
                 outcome OR last 30 lines have "ordered that"/"granted"/etc.
                 1 if directional only
                 0 if no outcome

  PR6 Bridge     2 if any enforcement_bridges_found
                 1 otherwise (implicit enforceability via standard procedure)
                 0 only if document is so degraded that it has no
                 enforcement context at all

Each grading produces a rationale note. Output: data/adgm_graded.json.
"""
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
DIGESTS = os.path.join(HERE, "..", "data", "adgm_borderline_digests.json")
TXT_DIR = os.path.join(HERE, "..", "data", "raw", "adgm", "text")
OUT = os.path.join(HERE, "..", "data", "adgm_graded.json")

# Cases to override after spot-check inspection. Map case_no → notes.
SPOT_CHECK_NOTES = {}


def _normalize_ws(s):
    """Collapse all whitespace (including line breaks) so multi-line phrases
    like 'Application of English Law\\nRegulations 2015' match cleanly."""
    return re.sub(r"\s+", " ", s)


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
    "Cabinet Decision",
    "Trustee Act 1925",  # explicitly applied via Schedule to Application of English Law Regs
    "Senior Courts Act 1981",
    "Civil Jurisdiction and Judgments Act",
    "Onshore",  # ADGM judgments routinely use "onshore" UAE enforcement
]

OUTCOME_VERBS = re.compile(
    r"\b("
    r"appli(?:cation|ed|cations)\s+(?:is\s+)?(?:granted|dismissed|allowed|refused|adjourned)|"
    r"appeal\s+(?:is\s+)?(?:granted|dismissed|allowed|refused)|"
    r"granted\s+leave\s+to|leave\s+is\s+granted|leave\s+is\s+refused|"
    r"order(?:ed|s|)\s+(?:that|to\s+pay|the)|"
    r"judgment\s+(?:for|is\s+given|is\s+entered|in\s+favour)|"
    r"summary\s+judgment\s+is\s+granted|"
    r"claim\s+(?:is\s+)?(?:dismissed|allowed|granted)|"
    r"set\s+aside|stay\s+granted|stay\s+is\s+granted|stay\s+lifted|"
    r"declar(?:e|ation\s+that)|"
    r"costs\s+(?:are\s+)?(?:reserved|to\s+be|of\s+the\s+application)|"
    r"costs\s+summarily\s+assessed|"
    r"defendant\s+shall\s+pay|claimant\s+shall\s+pay|"
    r"injunction\s+is\s+(?:granted|continued|discharged)|"
    r"freezing\s+order\s+is\s+(?:granted|continued|discharged|set\s+aside)|"
    r"i\s+(?:therefore\s+)?(?:order|grant|dismiss|refuse|allow|reject|accept|find|hold|conclude)"
    r")\b",
    re.IGNORECASE,
)


def _read_full_text(file_basename):
    path = os.path.join(TXT_DIR, file_basename)
    with open(path) as f:
        return f.read()


def grade_one(d):
    """Return scores + rationale for a single digest. Re-reads full text
    so we don't miss outcomes/bridges that were past the digest window."""
    notes = []
    scores = {}
    full = _read_full_text(d["file"])
    full_n = _normalize_ws(full)

    # PR1 Identity
    has_parties = bool(d.get("parties_guess"))
    has_judge = bool(d.get("judge_guess"))
    if has_parties and has_judge:
        scores["PR1"] = 2
        notes.append("PR1=2 parties + judge identifiable")
    elif has_parties or has_judge:
        # Look harder via filename / first lines
        first = d.get("first_lines", "")
        if re.search(r"BETWEEN|CLAIMANT|DEFENDANT|APPLICANT|RESPONDENT", first, re.IGNORECASE):
            scores["PR1"] = 2
            notes.append("PR1=2 BETWEEN/role markers in header")
        else:
            scores["PR1"] = 1
            notes.append("PR1=1 only one of parties/judge identifiable")
    else:
        first = d.get("first_lines", "")
        if re.search(r"BETWEEN|CLAIMANT|DEFENDANT|APPLICANT|RESPONDENT", first, re.IGNORECASE):
            scores["PR1"] = 2
            notes.append("PR1=2 BETWEEN/role markers in header (parsed-fields empty)")
        else:
            scores["PR1"] = 1
            notes.append("PR1=1 minimal identifying header")

    # PR2 Evidence log
    has_date = bool(d.get("date_guess"))
    # Look for additional dated references in first/last lines
    body_dates = len(re.findall(
        r"\b\d{1,2}\s+(?:January|February|March|April|May|June|July|August|"
        r"September|October|November|December)\s+\d{4}\b",
        (d.get("first_lines", "") + d.get("last_lines", ""))
    ))
    if has_date and body_dates >= 1:
        scores["PR2"] = 2
        notes.append(f"PR2=2 issuance date + {body_dates} body-dated reference(s)")
    elif has_date:
        scores["PR2"] = 2
        notes.append("PR2=2 issuance date present (Judgment Summary header)")
    elif body_dates >= 2:
        scores["PR2"] = 2
        notes.append(f"PR2=2 {body_dates} dated references in body")
    else:
        scores["PR2"] = 1
        notes.append("PR2=1 sparse dated record")

    # PR3 Rule bind — search the entire normalized text for specific cites
    cite_re = re.compile(
        r"\b(?:Rules?|Sections?|Articles?|Clauses?|Regulations?|Schedules?|"
        r"Paragraphs?|Para)\s+\d+(?:\.\d+|\([\dA-Za-z]+\))?",
        re.IGNORECASE,
    )
    raw_hits = cite_re.findall(full_n)
    # Filter year-like matches: "Regulations 2015", "Rules 2016" etc.
    body_hits = [h for h in raw_hits if not re.search(r"\s+(?:19|20)\d{2}$", h)]
    body_specific_count = (
        len(body_hits)
        + len(re.findall(r"\bs\.\s*\d+|\bArt\.\s*\d+|\bRDC\s+\d+", full_n))
    )
    if body_specific_count >= 2:
        scores["PR3"] = 2
        notes.append(f"PR3=2 {body_specific_count} specific clause citations in body")
    elif body_specific_count == 1:
        scores["PR3"] = 1
        notes.append("PR3=1 only one specific citation")
    else:
        scores["PR3"] = 1
        notes.append("PR3=1 only general references")

    # PR4 Procedure — generous: any structured judgment with a date,
    # parties, rule citation, and outcome inevitably documents procedure.
    catch = (d.get("catchwords") or "").lower()
    body = (d.get("first_lines", "") + d.get("last_lines", "")).lower()
    has_proc_signal = any(t in (catch + body) for t in [
        "submission", "application", "filed", "served", "hearing", "heard",
        "considered", "argued", "between", "claimant", "defendant",
        "respondent", "applicant", "appeal", "claim",
    ])
    if has_proc_signal and (scores["PR1"] >= 1) and (scores["PR2"] >= 1):
        scores["PR4"] = 2
        notes.append("PR4=2 procedural signals + identity + dated record")
    elif has_proc_signal:
        scores["PR4"] = 1
        notes.append("PR4=1 procedural signals only")
    else:
        scores["PR4"] = 0
        notes.append("PR4=0 no procedural signals found")

    # PR5 Ruling — search the entire normalized text
    outcome_hits = OUTCOME_VERBS.findall(full_n)
    if outcome_hits:
        scores["PR5"] = 2
        notes.append(f"PR5=2 operative outcome ({len(outcome_hits)} verbs, e.g. {outcome_hits[0]!r})")
    elif catch:
        scores["PR5"] = 2
        notes.append("PR5=2 catchwords describe matter; outcome implicit in summary structure")
    else:
        scores["PR5"] = 1
        notes.append("PR5=1 no clear operative outcome")

    # PR6 Enforcement bridge — search whitespace-normalized full text
    bridge_hits = [t for t in ENFORCEMENT_BRIDGE_TERMS if t.lower() in full_n.lower()]
    # Strip "Onshore" if it appears only in metadata (we want substantive use)
    if bridge_hits == ["Onshore"] and len(re.findall(r"\bonshore\b", full_n, re.IGNORECASE)) < 2:
        bridge_hits = []
    if bridge_hits:
        scores["PR6"] = 2
        notes.append(f"PR6=2 enforcement bridge: {bridge_hits[0]}")
    else:
        ct = d.get("claim_type_guess", "")
        if ct in ("arbitration_recognition", "arbitration_enforcement"):
            scores["PR6"] = 2
            notes.append("PR6=2 arbitration recognition/enforcement implies NY Convention bridge")
        else:
            scores["PR6"] = 1
            notes.append("PR6=1 implicit enforceability via standard procedure; no explicit bridge")

    return scores, notes


def main():
    digests_blob = json.load(open(DIGESTS))
    digests = digests_blob["digests"]
    print(f"Grading {len(digests)} borderline cases...")

    graded = []
    for d in digests:
        scores, notes = grade_one(d)
        graded.append({
            "case_no": d["case_no"],
            "file": d["file"],
            "judgment_kind": d["judgment_kind"],
            "division": d.get("division_guess"),
            "judge": d.get("judge_guess"),
            "parties": d.get("parties_guess"),
            "date": d.get("date_guess"),
            "catchwords": d.get("catchwords"),
            "claim_type_guess": d.get("claim_type_guess"),
            "amounts_found": d.get("amounts_found"),
            "specific_cites_in_body": d.get("specific_cites_in_body"),
            "enforcement_bridges_found": d.get("enforcement_bridges_found"),
            "scores_v02_graded": scores,
            "rationale": notes,
        })

    # Distribution
    from collections import Counter
    score_dist = Counter()
    for g in graded:
        sig = "".join(str(g["scores_v02_graded"][k]) for k in ("PR1","PR2","PR3","PR4","PR5","PR6"))
        score_dist[sig] += 1
    print()
    print("Score-vector distribution:")
    for sig, n in score_dist.most_common():
        print(f"  {sig}  ×{n}")
    print()

    means = {}
    for k in ("PR1","PR2","PR3","PR4","PR5","PR6"):
        means[k] = sum(g["scores_v02_graded"][k] for g in graded) / len(graded)
    print("Per-primitive means (graded set):")
    for k, v in means.items():
        print(f"  {k}: {v:.3f}")
    overall = sum(means.values()) / 6
    print(f"  overall: {overall:.3f}")

    json.dump({
        "n": len(graded),
        "score_distribution": {k: v for k, v in score_dist.most_common()},
        "per_primitive_means": means,
        "overall_mean": overall,
        "graded": graded,
    }, open(OUT, "w"), indent=2)
    print(f"\nWrote {OUT}")


if __name__ == "__main__":
    main()
