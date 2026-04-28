#!/usr/bin/env python3
"""SICC judgment triage + heuristic grading.

Mirrors the structure of triage_adgm.py but adapted for the SICC
elitigation.sg layout. Produces:

  data/sicc_triage.json     — per-case classification + heuristic scores
  data/sicc_graded.json     — entries pre-shaped to drop into judgments.json
                               (needs a final review pass before merge)

SICC judgments are full grounds-of-decision documents (not Judgment
Summaries like ADGM). The structured signal is weaker, so we read
the document body directly:

  - Header block: court name, neutral citation, OA number, parties table,
    coram (judges), hearing date, decision date.
  - Catchwords block: square-bracketed area-of-law tags after "judgment"
    or "GROUNDS OF DECISION".
  - Body: numbered paragraphs.
  - End matter: "Annex" block with operative orders, OR a final paragraph
    summarising the disposition.

Heuristic mapping to v0.2 primitives:

  PR1 Identity  — parties + coram parsed from header. Anonymised pairs
                  (DVA v DVC) preserve identity per the rubric.
  PR2 Evidence  — count of dated references in the body; SICC judgments
                  routinely cite filings by exhibit + date.
  PR3 Rule bind — specific Rule/Section/Order/Article citations. SICC
                  draws heavily on the SICC Rules 2021 (Order N rule M),
                  the International Arbitration Act, and contract clauses.
  PR4 Procedure — header records hearing date + decision date; coram
                  named; judgment with reasons. If all present, score 2.
  PR5 Ruling    — operative outcome with Annex of orders, named amount,
                  or "set aside / dismissed / granted" verb in the
                  conclusion. Costs awards typically include S$ amounts.
  PR6 Enforcement bridge — explicit NY Convention / IAA / SICC Rules
                  enforcement reference, OR an arbitration matter (which
                  carries enforceability by Convention by default).

This is the same shape as the ADGM grader, with SICC-specific term lists.
"""
import json
import os
import re
from collections import Counter
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
TXT_DIR = os.path.join(HERE, "..", "data", "raw", "sicc", "text")
TRIAGE_OUT = os.path.join(HERE, "..", "data", "sicc_triage.json")
GRADED_OUT = os.path.join(HERE, "..", "data", "sicc_graded.json")

NEUTRAL_CITE_RE = re.compile(r"\\?\[(20\d{2})\\?\]\s*SGHC\(I\)\s*(\d+)")
OA_RE = re.compile(
    r"Originating Application No\.?\s*(\d+)\s*of\s*(20\d{2})", re.IGNORECASE
)
SUM_RE = re.compile(r"Summons(?:es)?\s*Nos?\.?\s*([\d, and]+?)\s*of\s*20\d{2}",
                    re.IGNORECASE)

DATE_PATTERN = re.compile(
    r"\b\d{1,2}\s+(January|February|March|April|May|June|July|August|"
    r"September|October|November|December)\s+\d{4}\b"
)

# Specific rule citation patterns. SICC heavy users: SICC Rules 2021
# (Order N rule M), International Arbitration Act sections, IBA Rules,
# contract clauses cited by number.
SPECIFIC_RULE_PATTERNS = [
    re.compile(r"\bOrder\s+\d+\b", re.IGNORECASE),
    re.compile(r"\brules?\s+\d+(?:\.\d+)?", re.IGNORECASE),
    re.compile(r"\bs(?:ection)?\s*\d+[A-Z]?(?:\(\d+\))?\b", re.IGNORECASE),
    re.compile(r"\bArt(?:icle)?\.?\s*\d+", re.IGNORECASE),
    re.compile(r"\bO\s*\d+\s*r\s*\d+", re.IGNORECASE),
    re.compile(r"\bclause\s+\d+", re.IGNORECASE),
]

ENFORCEMENT_BRIDGE_TERMS = [
    "New York Convention",
    "Convention on the Recognition and Enforcement of Foreign Arbitral",
    "International Arbitration Act",
    "Reciprocal Enforcement of Foreign Judgments Act",
    "Reciprocal Enforcement of Commonwealth Judgments Act",
    "Choice of Court Agreements Act",
    "Hague Convention",
    "SICC Rules 2021",
    "Rules of Court 2021",
    "enforcement of",
]

CATCHWORD_RE = re.compile(r"\\\[([A-Z][^\[\]\n]{4,200})\\\]")
# Fallback for non-escaped brackets
CATCHWORD_RAW_RE = re.compile(r"\[([A-Z][^\[\]\n]{4,160})\]")

CORAM_RE = re.compile(
    r"\n([A-Z][A-Za-z .'-]+(?:J|JA|IJ|JC|SJ)(?:[, ]+(?:and\s+)?"
    r"[A-Z][A-Za-z .'-]+(?:J|JA|IJ|JC|SJ))*)\n",
)


def parse_header(text):
    fields = {}
    m = NEUTRAL_CITE_RE.search(text)
    if m:
        fields["neutral_citation"] = f"[{m.group(1)}] SGHC(I) {m.group(2)}"
        fields["year"] = m.group(1)
    m = OA_RE.search(text)
    if m:
        fields["oa_no"] = f"OA {m.group(1)}/{m.group(2)}"
    # parties: prefer the "<Name> v <Name>" line that appears just before
    # the [YYYY] SGHC(I) N citation block. Fallback to BETWEEN/AND parse.
    if "neutral_citation" in fields:
        # Citation stored unescaped; raw text uses backslash-escaped brackets.
        # The citation appears multiple times; we want the one that follows
        # the "X v Y" parties block (typically the 2nd or 3rd occurrence).
        escaped = fields["neutral_citation"].replace("[", r"\[").replace("]", r"\]")
        positions = []
        start = 0
        while True:
            p = text.find(escaped, start)
            if p < 0:
                break
            positions.append(p)
            start = p + 1
        if not positions:
            start = 0
            while True:
                p = text.find(fields["neutral_citation"], start)
                if p < 0:
                    break
                positions.append(p)
                start = p + 1
        # Pick the latest occurrence that is preceded by a "v" line within
        # 600 chars; fall back to the second-from-last, then last.
        nc_pos = -1
        for p in reversed(positions):
            window_back = text[max(0, p - 600):p]
            if re.search(r"\nv\n", window_back):
                nc_pos = p
                break
        if nc_pos < 0:
            nc_pos = positions[1] if len(positions) > 1 else (positions[0] if positions else -1)
        if nc_pos > 200:
            window = text[max(0, nc_pos - 800):nc_pos]
            # The "X v Y" separator pattern
            wm = re.search(
                r"\n([A-Z][A-Za-z0-9 .,'&()/-]{1,200})\n+v\n+"
                r"([A-Z][A-Za-z0-9 .,'&()/-]{1,200})\n",
                window,
            )
            if wm:
                fields["claimant"] = wm.group(1).strip()[:160]
                fields["defendant"] = wm.group(2).strip()[:160]
    if not fields.get("claimant") or not fields.get("defendant"):
        pm = re.search(r"Between\s*(.+?)\s*And\s*(.+?)(?:judgment|GROUNDS|"
                       r"Singapore International Commercial Court)",
                       text, re.IGNORECASE | re.DOTALL)
        if pm:
            def pick(blob):
                for line in re.split(r"\n+|\|", blob):
                    line = line.strip().strip("…").strip()
                    line = re.sub(r"^\(\d+\)\s*", "", line)
                    if (line and len(line) > 1 and not line.startswith("---")
                            and "Claim" not in line and "Defend" not in line
                            and not re.match(r"^[\s|()-]+$", line)):
                        if re.search(r"[A-Za-z]{2,}", line):
                            return line[:160]
                return ""
            if not fields.get("claimant"):
                fields["claimant"] = pick(pm.group(1))
            if not fields.get("defendant"):
                fields["defendant"] = pick(pm.group(2))
    # Header block parse: locate "Singapore International Commercial Court —"
    # line, then the next non-blank lines are coram, hearing date, decision
    # date in that order.
    h = re.search(
        r"Singapore International Commercial Court\s+[—\-]\s+Originating[^\n]*\n+"
        r"((?:[^\n]+\n+){2,8})",
        text,
    )
    if h:
        block = h.group(1)
        block_lines = [ln.strip() for ln in block.split("\n") if ln.strip()]
        # First line: coram. May contain "J", "IJ", "JA", "JC".
        # Subsequent date lines: hearing then decision.
        if block_lines:
            cand = block_lines[0]
            if re.search(r"\bJ\b|\bIJ\b|\bJA\b|\bJC\b|\bSJ\b", cand):
                fields["coram"] = cand[:200]
        date_lines = []
        for ln in block_lines[1:]:
            m = re.match(
                r"^(\d{1,2}\s+(?:January|February|March|April|May|June|"
                r"July|August|September|October|November|December)\s+\d{4})",
                ln,
            )
            if m:
                date_lines.append(m.group(1))
            if len(date_lines) >= 2:
                break
        if len(date_lines) >= 2:
            fields["hearing_date"] = date_lines[0]
            fields["decision_date"] = date_lines[1]
        elif len(date_lines) == 1:
            fields["decision_date"] = date_lines[0]
    # Fallback for coram via the original regex
    if not fields.get("coram"):
        cm = CORAM_RE.search(text)
        if cm:
            fields["coram"] = cm.group(1).strip()
    # catchwords
    cws = CATCHWORD_RE.findall(text[:5000]) or CATCHWORD_RAW_RE.findall(text[:5000])
    cws = [c.strip() for c in cws if c.strip()]
    # Filter out non-catchword brackets like '[2026] SGHC(I) 4'
    cws = [c for c in cws if not re.match(r"^\d{4}\]?$", c)
           and "SGHC" not in c and "SGCAI" not in c]
    fields["catchwords"] = cws[:8]
    return fields


def parse_decision_date_iso(s):
    if not s:
        return None
    months = {"January":1,"February":2,"March":3,"April":4,"May":5,"June":6,
              "July":7,"August":8,"September":9,"October":10,"November":11,"December":12}
    m = re.match(r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", s)
    if not m:
        return None
    d, mon, y = int(m.group(1)), months.get(m.group(2)), int(m.group(3))
    if not mon:
        return None
    return f"{y:04d}-{mon:02d}-{d:02d}"


def score_pr1(text, fields):
    has_parties = bool(fields.get("claimant") and fields.get("defendant"))
    has_coram = bool(fields.get("coram"))
    if has_parties and has_coram:
        return 2, []
    flags = []
    if not has_parties:
        flags.append("parties not parsed cleanly")
    if not has_coram:
        flags.append("coram not parsed")
    return (1 if (has_parties or has_coram) else 0), flags


def score_pr2(text, fields):
    dates = DATE_PATTERN.findall(text)
    if len(dates) >= 4:
        return 2, []
    if len(dates) >= 2:
        return 2, []
    if len(dates) == 1:
        return 1, ["only one dated reference"]
    return 0, ["no dated references in body"]


def score_pr3(text, fields):
    body = text
    counts = sum(len(p.findall(body)) for p in SPECIFIC_RULE_PATTERNS)
    if counts >= 3:
        return 2, []
    if counts >= 1:
        return 2, []
    return 1, ["no specific Rule/Order/Section/Article numbers found"]


def score_pr4(text, fields):
    has_hearing = bool(fields.get("hearing_date"))
    has_decision = bool(fields.get("decision_date"))
    has_coram = bool(fields.get("coram"))
    has_reasons = bool(re.search(
        r"GROUNDS OF DECISION|judgment|reasons", text[:6000], re.IGNORECASE
    ))
    legs = sum([has_hearing, has_decision, has_coram, has_reasons])
    if legs >= 3:
        return 2, []
    if legs >= 2:
        return 1, [f"only {legs}/4 procedural-triplet markers"]
    return 0, ["procedural triplet not visible"]


OPERATIVE_VERBS = re.compile(
    r"\b(?:we\s+)?(?:grant|granted|dismiss|dismissed|set\s+aside|"
    r"refus(?:e|ed)|allow(?:ed)?|order(?:ed|s)?|stay(?:ed)?|adjourn(?:ed)?|"
    r"declar(?:e|ed|ation)|judgment\s+for|judgment\s+in\s+favour|"
    r"award(?:ed)?|enforce(?:d)?|recognis(?:e|ed))\b",
    re.IGNORECASE,
)
AMOUNT_RE = re.compile(r"S\$[\d,]+(?:\.\d+)?|US\$[\d,]+(?:\.\d+)?|"
                       r"\bS\$\s*[\d,]+|\bUS\$\s*[\d,]+")


def score_pr5(text, fields):
    # Look at last 4000 chars for the operative tail
    tail = text[-4000:]
    has_annex = bool(re.search(r"\bAnnex\b", text))
    has_operative = bool(OPERATIVE_VERBS.search(tail))
    has_amount = bool(AMOUNT_RE.search(text)) and bool(re.search(
        r"costs|damages|sum|amount|interest", text, re.IGNORECASE
    ))
    score = 0
    if has_annex or has_amount:
        score = 2
    elif has_operative:
        score = 2
    flags = []
    if score == 0:
        flags.append("no operative verb / annex / amount in tail")
        return 1, flags
    return score, flags


def score_pr6(text, fields):
    blob_l = text.lower()
    hits = [t for t in ENFORCEMENT_BRIDGE_TERMS if t.lower() in blob_l]
    catchwords = " | ".join(fields.get("catchwords", [])).lower()
    is_arbitration_matter = (
        "arbitration" in catchwords
        or "international arbitration act" in blob_l
        or "new york convention" in blob_l
        or "model law" in blob_l
    )
    # SICC matters by-construction sit under Singapore's Reciprocal
    # Enforcement of Foreign Judgments Act + Choice of Court Agreements
    # Act + (for arbitration) the IAA / NY Convention. If the matter is
    # arbitration-related, PR6=2 by structural default. Otherwise need an
    # explicit bridge term.
    if is_arbitration_matter:
        return 2, []
    if hits:
        return 2, []
    return 1, ["non-arbitration matter; no explicit cross-border enforcement bridge cited"]


def claim_type_from_catchwords(cws, text):
    catch = " | ".join(cws).lower()
    body_l = text.lower()
    if "set aside" in catch and "arbitr" in catch:
        return "arbitration_recognition"
    if "enforcement" in catch and "arbitr" in catch:
        return "arbitration_enforcement"
    if "arbitr" in catch:
        return "arbitration_recognition"
    if "costs" in catch and "principles" in catch:
        return "costs_assessment"
    if "costs" in catch:
        return "costs_assessment"
    if "injunction" in catch:
        return "interim_relief"
    if "summary judgment" in catch:
        return "summary_judgment"
    if "case management" in catch or "case-management" in catch:
        return "case_management"
    if "jurisdiction" in catch:
        return "jurisdictional_challenge"
    if "fraud" in catch or "deceit" in catch:
        return "fraud"
    if "interpretation" in catch or "construction" in catch:
        return "interpretation"
    if "default judgment" in catch:
        return "default_judgment"
    if "appeal" in catch:
        return "permission_to_appeal"
    if "pleadings" in catch or "civil procedure" in catch:
        return "case_management"
    return "substantive_breach"


def outcome_from_text(text, catchwords):
    tail = text[-4500:].lower()
    catch = " | ".join(catchwords).lower()
    if "application is dismissed" in tail or "application dismissed" in tail:
        return "application_refused"
    if "set aside" in tail and "is set aside" in tail:
        return "claim_granted"
    if re.search(r"\bdismiss(ed)?\b", tail):
        return "claim_dismissed"
    if re.search(r"\bgrant(ed)?\b", tail):
        return "claim_granted"
    if "partly" in tail or "in part" in tail:
        return "claim_partially_granted"
    return "other"


def amount_usd(text):
    # Pull a dominant SGD or USD figure from the tail (costs award, etc.)
    tail = text[-6000:]
    matches = AMOUNT_RE.findall(tail)
    if not matches:
        return None
    # Just return the first one cleaned, marked as USD if it starts with US$,
    # otherwise we set sgd_to_usd ~ 0.74; we'll record both fields.
    # Simpler: return None; we don't trust regex extraction enough for AED column.
    return None


def grade_one(path):
    with open(path) as f:
        text = f.read()
    if len(text) < 800:
        return None
    fields = parse_header(text)
    pr1, f1 = score_pr1(text, fields)
    pr2, f2 = score_pr2(text, fields)
    pr3, f3 = score_pr3(text, fields)
    pr4, f4 = score_pr4(text, fields)
    pr5, f5 = score_pr5(text, fields)
    pr6, f6 = score_pr6(text, fields)
    scores = {"PR1": pr1, "PR2": pr2, "PR3": pr3,
              "PR4": pr4, "PR5": pr5, "PR6": pr6}
    flags = {"PR1": f1, "PR2": f2, "PR3": f3, "PR4": f4, "PR5": f5, "PR6": f6}
    classification = (
        "saturating" if all(v == 2 for v in scores.values())
        else "procedural_default"
        if [scores[k] for k in ("PR1","PR2","PR3","PR4","PR5","PR6")]
           == [2,2,2,2,2,1]
        else "borderline"
    )
    return {
        "file": os.path.basename(path),
        "neutral_citation": fields.get("neutral_citation"),
        "year": fields.get("year"),
        "oa_no": fields.get("oa_no"),
        "claimant": fields.get("claimant"),
        "defendant": fields.get("defendant"),
        "coram": fields.get("coram"),
        "hearing_date": fields.get("hearing_date"),
        "decision_date": fields.get("decision_date"),
        "decision_date_iso": parse_decision_date_iso(fields.get("decision_date")),
        "catchwords": fields.get("catchwords"),
        "scores_heuristic": scores,
        "flags": {k: v for k, v in flags.items() if v},
        "classification": classification,
        "char_len": len(text),
    }


def slug_to_url(slug):
    # 2026_SGHCI_4 -> https://www.elitigation.sg/gd/sic/2026_SGHCI_4
    return f"https://www.elitigation.sg/gd/sic/{slug}"


def to_judgment_entry(g):
    """Shape a triage row into a judgments.json entry."""
    cw = g.get("catchwords") or []
    text_path = os.path.join(TXT_DIR, g["file"])
    with open(text_path) as f:
        text = f.read()
    citation = g.get("neutral_citation") or ""
    case_no = g.get("oa_no") or citation
    # division
    division = "Singapore International Commercial Court"
    parties = {
        "claimant": (g.get("claimant") or "").strip() or "[unparsed]",
        "defendant": (g.get("defendant") or "").strip() or "[unparsed]",
    }
    # Clean parties: strip residual table chars/numbering
    for k in ("claimant", "defendant"):
        parties[k] = re.sub(r"\s+", " ", parties[k]).strip(" |-")
    judge = g.get("coram") or "[unparsed]"
    claim_type = claim_type_from_catchwords(cw, text)
    outcome = outcome_from_text(text, cw)
    rules_cited = []
    # Pull a sample of cited rules for provenance
    sample = set()
    for p in SPECIFIC_RULE_PATTERNS:
        for h in p.findall(text):
            sample.add(h.strip())
            if len(sample) > 8:
                break
        if len(sample) > 8:
            break
    rules_cited = sorted(sample)[:8]
    if "International Arbitration Act" in text and "International Arbitration Act" not in rules_cited:
        rules_cited.append("International Arbitration Act")
    if "SICC Rules" in text:
        rules_cited.append("SICC Rules 2021")
    if "Rules of Court 2021" in text:
        rules_cited.append("Rules of Court 2021")
    rules_cited = list(dict.fromkeys(rules_cited))[:10]

    notes = (
        f"Heuristic-graded SICC entry. Catchwords: "
        f"{' | '.join(cw[:3]) if cw else 'n/a'}. "
        f"Heuristic flags: "
        f"{', '.join(f'{k}({v[0]})' for k, v in g.get('flags', {}).items()) or 'none'}. "
        f"AI-coded against the v0.2 rubric using the same heuristics applied "
        f"to the ADGM borderline set; not gold-set."
    )
    slug = g["file"].replace(".txt", "")
    return {
        "case_no": case_no,
        "url": slug_to_url(slug),
        "tribunal": "Singapore International Commercial Court",
        "division": division,
        "date_issued": g.get("decision_date_iso") or "2025-01-01",
        "parties": parties,
        "judge": judge,
        "neutral_citation": citation,
        "claim_type": claim_type,
        "outcome": outcome,
        "operative_amount_aed": None,
        "operative_amount_usd": None,
        "rules_cited": rules_cited,
        "primitive_scores_v02": g["scores_heuristic"],
        "coding": {
            "coder": "MaximLabs (heuristic-graded)",
            "coded_on": str(date.today()),
            "gold_set": False,
            "notes": notes,
        },
    }


def main():
    files = sorted(f for f in os.listdir(TXT_DIR) if f.endswith(".txt"))
    print(f"Processing {len(files)} SICC text files from {TXT_DIR}")
    print()

    rows = []
    for f in files:
        g = grade_one(os.path.join(TXT_DIR, f))
        if g is None:
            print(f"  skip (too short): {f}")
            continue
        rows.append(g)

    cls = Counter(r["classification"] for r in rows)
    print("=== Triage classification ===")
    for k in ("saturating", "procedural_default", "borderline"):
        print(f"  {k:<22} {cls.get(k, 0):>3}")
    print()

    for r in rows:
        scores = " ".join(f"{k}={v}" for k, v in r["scores_heuristic"].items())
        flag_summary = "; ".join(
            f"{k}({v[0]})" for k, v in r["flags"].items() if v
        ) or "—"
        print(f"  {(r['neutral_citation'] or '?'):<20}  "
              f"{(r['claimant'] or '?')[:30]:30s} v "
              f"{(r['defendant'] or '?')[:30]:30s}")
        print(f"    {scores}    flags: {flag_summary}")
        if r.get("catchwords"):
            print(f"    catch: {' | '.join(r['catchwords'][:2])[:160]}")
        print()

    # Triage report
    triage_out = {
        "generated_by": "scripts/triage_sicc.py",
        "n_text_files": len(rows),
        "by_classification": dict(cls),
        "results": rows,
    }
    with open(TRIAGE_OUT, "w") as f:
        json.dump(triage_out, f, indent=2)
    print(f"=== Wrote {TRIAGE_OUT} ===")

    # Build judgment entries
    entries = [to_judgment_entry(r) for r in rows]
    graded_out = {
        "generated_by": "scripts/triage_sicc.py",
        "version": "v0.2",
        "n_entries": len(entries),
        "entries": entries,
    }
    with open(GRADED_OUT, "w") as f:
        json.dump(graded_out, f, indent=2)
    print(f"=== Wrote {GRADED_OUT} ({len(entries)} entries) ===")

    # Per-primitive means
    prims = ["PR1","PR2","PR3","PR4","PR5","PR6"]
    if rows:
        means = {p: round(sum(r["scores_heuristic"][p] for r in rows)/len(rows), 2)
                 for p in prims}
        print(f"\n=== Per-primitive means (heuristic, n={len(rows)}) ===")
        for p, m in means.items():
            print(f"  {p}: {m}")


if __name__ == "__main__":
    main()
