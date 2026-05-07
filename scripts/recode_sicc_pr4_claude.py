#!/usr/bin/env python3
"""Re-grade SICC PR4 using Claude (item 12 of the soundness plan).

The regex-based PR4 detection in `triage_sicc.py` underscores PR4 on
SICC's narrative-style grounds-of-decision documents. This script
re-grades PR4 *only* for the 80 SICC entries using Claude with a
prompt explicitly instructed to recognise narrative procedural form
(hearing event, decision date, named coram, reasons-or-grounds-of-
decision section), *including in narrative form*, not only via
structural markers.

Output:
  - data/sicc_pr4_recoded.json  (per-entry: regex_score, claude_score, rationale)
  - data/robustness/sicc_pr4_summary.json (regex_mean vs claude_mean per tribunal)

The corrected PR4 is what enters the headline SICC mean (paper §4.1, §4.9).
The regex result is preserved at data/robustness/sicc_pr4_regex.json.
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
from pathlib import Path

from _claude_grader import grade_judgment as _g, _client, _build_system_prompt
from perturbation_test_retest import find_raw_text

ROOT = Path(__file__).resolve().parent.parent
JUDGMENTS = ROOT / "data" / "judgments.json"
OUT = ROOT / "data" / "sicc_pr4_recoded.json"
ROBUST = ROOT / "data" / "robustness"
ROBUST.mkdir(exist_ok=True)
REGEX_SNAPSHOT = ROBUST / "sicc_pr4_regex.json"

PR4_PROMPT = """You are scoring ONE primitive (PR4 — Procedure) of the v0.2 Habeas Protocol rubric on a single judgment.

PR4 — Procedure: The ruling documents the procedural triplet — notice was given, both sides had opportunity to be heard, the decision is recorded with reasons. Each leg of the triplet must be visible in the document, *including in narrative form* — you are NOT looking only for structural markers like "GROUNDS OF DECISION" headers or explicit "hearing date:" labels. SICC writes integrated narrative grounds-of-decision; you must read the substantive text to identify whether the procedural triplet is satisfied.

Score 0/1/2:
  - 2: All three legs visible. There was notice (filing date, service confirmation, or implicit-but-clear acknowledgement that the matter was set down before the parties); both sides had opportunity to respond (parties' submissions discussed, parties' positions characterised, hearing or written-submission round acknowledged); the decision is recorded with reasons (the document itself contains analytical reasoning). Narrative-style grounds count.
  - 1: Two of three legs visible. Common case: decision with reasons + one of (notice, opportunity), but the third is not stated.
  - 0: Fewer than two legs visible.
  - -1: Document is so degraded or fragmentary that PR4 cannot be assessed.

Return strict JSON:
{
  "pr4": <int 0|1|2|-1>,
  "rationale": "<one paragraph quoting specific text supporting the score>",
  "markers_found": {
    "notice": "<quote or 'not visible'>",
    "opportunity_to_be_heard": "<quote or 'not visible'>",
    "decision_with_reasons": "<quote or 'not visible'>"
  }
}
"""


def grade_pr4(text):
    client = _client()
    msg = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        temperature=0.0,
        max_tokens=1024,
        system=PR4_PROMPT,
        messages=[{"role": "user",
                   "content": "Judgment text follows.\n\n=== JUDGMENT ===\n" + text}],
    )
    raw = "".join(b.text for b in msg.content if hasattr(b, "text"))
    m = re.search(r"\{.*\}", raw, flags=re.DOTALL)
    if not m:
        raise ValueError(f"No JSON in response. Raw:\n{raw[:500]}")
    return json.loads(m.group(0))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int, default=None,
                    help="Cap number of entries graded (for testing)")
    args = ap.parse_args()

    judgments = json.loads(JUDGMENTS.read_text())
    sicc = [j for j in judgments
            if j.get("tribunal") == "Singapore International Commercial Court"]
    if args.limit:
        sicc = sicc[:args.limit]
    print(f"SICC entries to recode: {len(sicc)}")

    # Snapshot regex scores
    regex_snapshot = []
    for entry in sicc:
        regex_snapshot.append({
            "case_no": entry.get("case_no"),
            "neutral_citation": entry.get("neutral_citation"),
            "pr4_regex": (entry.get("primitive_scores_v02") or {}).get("PR4"),
        })
    REGEX_SNAPSHOT.write_text(json.dumps(regex_snapshot, indent=2))
    print(f"Wrote regex snapshot {REGEX_SNAPSHOT}")

    out = []
    for entry in sicc:
        case = entry.get("case_no") or entry.get("neutral_citation") or "?"
        text = find_raw_text(entry)
        if not text:
            out.append({"case": case, "status": "skipped_no_raw_text",
                        "pr4_regex": (entry.get("primitive_scores_v02") or {}).get("PR4")})
            continue
        if args.dry_run:
            out.append({"case": case, "status": "would_grade",
                        "pr4_regex": (entry.get("primitive_scores_v02") or {}).get("PR4")})
            continue
        try:
            res = grade_pr4(text)
            out.append({
                "case": case,
                "pr4_regex": (entry.get("primitive_scores_v02") or {}).get("PR4"),
                "pr4_claude": res.get("pr4"),
                "rationale": res.get("rationale"),
                "markers": res.get("markers_found"),
            })
            print(f"  [graded] {case}: regex={out[-1]['pr4_regex']} claude={res.get('pr4')}")
        except Exception as e:
            out.append({"case": case, "status": f"error: {e}"})

    OUT.write_text(json.dumps(out, indent=2))
    print(f"Wrote {OUT}")

    if args.dry_run:
        return

    # Compare means
    regex_scores = [r["pr4_regex"] for r in out
                    if isinstance(r.get("pr4_regex"), int) and r["pr4_regex"] >= 0]
    claude_scores = [r["pr4_claude"] for r in out
                     if isinstance(r.get("pr4_claude"), int) and r["pr4_claude"] >= 0]
    summary = {
        "n_total": len(sicc),
        "n_graded_by_claude": len(claude_scores),
        "regex_mean": round(statistics.mean(regex_scores), 4) if regex_scores else None,
        "claude_mean": round(statistics.mean(claude_scores), 4) if claude_scores else None,
    }
    if summary["regex_mean"] is not None and summary["claude_mean"] is not None:
        summary["delta_claude_minus_regex"] = round(summary["claude_mean"] - summary["regex_mean"], 4)
    (ROBUST / "sicc_pr4_summary.json").write_text(json.dumps(summary, indent=2))
    print(f"  regex mean: {summary['regex_mean']}")
    print(f"  claude mean: {summary['claude_mean']}")


if __name__ == "__main__":
    main()
