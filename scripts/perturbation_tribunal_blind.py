#!/usr/bin/env python3
"""Tribunal-blind perturbation of the LLM grader (item 11a, the highest-stakes
single probe).

For each entry in a stratified 30-judgment sample, the tribunal name,
neutral citation, judge name, and case caption are stripped from the
input. The judgment is re-graded with the same prompt, fresh API
session.

If scores change materially when tribunal identity is masked, the
LLM grader is using tribunal identity as a feature — the headline
tribunal-mean ordering is partially a model prior on tribunal name
rather than a measurement of the rulings.

Stop rule (PREREGISTRATION.md): if mean shift > 0.20 on any tribunal,
the headline is re-reported as identity-sensitive and the tribunal-blind
result becomes the headline.

Usage: same as perturbation_test_retest.py.
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
from pathlib import Path

from _claude_grader import grade_judgment, per_primitive, PRIM_KEYS
from perturbation_test_retest import find_raw_text, stratified_sample

ROOT = Path(__file__).resolve().parent.parent
JUDGMENTS = ROOT / "data" / "judgments.json"
OUT_DIR = ROOT / "data" / "robustness"

# Tribunal names + division markers + court captions
TRIB_TOKENS = [
    "DIFC Courts", "DIFC Court of First Instance", "DIFC Court of Appeal",
    "Dubai International Financial Centre", "DIFC",
    "ADGM Courts", "ADGM Court of First Instance",
    "Abu Dhabi Global Market", "ADGM", "ADGMCFI",
    "Singapore International Commercial Court",
    "Singapore High Court", "SICC", "SGHC(I)", "SGCA(I)",
    "elitigation.sg", "judiciary.gov.sg",
    "difccourts.ae", "adgm.com",
]

# Citation patterns
CIT_PATTERNS = [
    re.compile(r"\[\s*\d{4}\s*\]\s*(?:DIFC|ADGM|SGHC|SGCA|UKHL|UKSC|EWCA|EWHC)[A-Za-z()]*\s*\d+", re.I),
    re.compile(r"\b(?:CFI|ARB|ENF|TCD|DEC|CA|ADGMCFI|OA|SIC)\s*[-_]?\s*\d+\s*[/_-]\s*\d{4}", re.I),
]


def strip_identity(text):
    """Replace tribunal/case identifiers with placeholders.
    Conservative: misses some idiosyncratic forms but catches the obvious ones.
    """
    out = text
    for tok in TRIB_TOKENS:
        out = re.sub(re.escape(tok), "[REDACTED-COURT]", out, flags=re.I)
    for pat in CIT_PATTERNS:
        out = pat.sub("[REDACTED-CITATION]", out)
    # Judge captions: "Justice X", "X J.", "Sir Y KC"
    out = re.sub(r"\b(?:Justice|Mr\.?\s*Justice|The\s+Hon\.?\s*Justice|Lord|Lady|Sir|Dame|Hon\.?)\s+[A-Z][a-zA-Z\-]+(?:\s+[A-Z][a-zA-Z\-]+)*(?:\s+(?:KC|QC|J\.?))?",
                  "[REDACTED-JUDGE]", out)
    # Closing identification headers
    out = re.sub(r"^\s*(?:IN\s+THE|BEFORE\s+THE)\s+[A-Z][^\n]{0,200}", "[REDACTED-CAPTION]", out, flags=re.M)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-per-tribunal", type=int, default=10)
    ap.add_argument("--seed", type=int, default=20260507)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    judgments = json.loads(JUDGMENTS.read_text())
    sample = stratified_sample(judgments, args.n_per_tribunal, args.seed)

    results = []
    for entry in sample:
        case = entry.get("case_no") or entry.get("neutral_citation") or "?"
        text = find_raw_text(entry)
        if not text:
            results.append({"case": case, "status": "skipped_no_raw_text"})
            continue
        blinded = strip_identity(text)
        original = entry.get("primitive_scores_v02") or {}
        if args.dry_run:
            results.append({
                "case": case,
                "redaction_chars_removed": len(text) - len(blinded.replace("[REDACTED-", "")),
                "status": "would_grade",
            })
            continue
        try:
            result = grade_judgment(blinded)
            new = per_primitive(result)
            results.append({
                "case": case,
                "tribunal": entry.get("tribunal"),
                "original": {k.lower(): original.get(k.upper()) for k in PRIM_KEYS},
                "blinded": {k: new.get(k) for k in PRIM_KEYS},
                "blinded_raw": result,
            })
            print(f"  [graded] {case}")
        except Exception as e:
            results.append({"case": case, "status": f"error: {e}"})

    raw_path = OUT_DIR / "tribunal_blind.json"
    raw_path.write_text(json.dumps(results, indent=2))
    print(f"Wrote {raw_path}")

    if args.dry_run:
        return

    # Per-tribunal mean shift
    summary = {"per_tribunal_mean_shift": {}, "per_primitive_shift": {}}
    for trib in ("DIFC Courts", "ADGM Courts",
                 "Singapore International Commercial Court"):
        rows = [r for r in results if r.get("tribunal") == trib and "blinded" in r]
        if not rows:
            continue
        orig_means = []
        blind_means = []
        for r in rows:
            o = [r["original"].get(k) for k in PRIM_KEYS if r["original"].get(k) is not None]
            b = [r["blinded"].get(k) for k in PRIM_KEYS if r["blinded"].get(k) is not None]
            if o and b:
                orig_means.append(statistics.mean(o))
                blind_means.append(statistics.mean(b))
        if orig_means:
            shift = statistics.mean(blind_means) - statistics.mean(orig_means)
            summary["per_tribunal_mean_shift"][trib] = {
                "n": len(orig_means),
                "original_mean": round(statistics.mean(orig_means), 4),
                "blinded_mean": round(statistics.mean(blind_means), 4),
                "shift": round(shift, 4),
                "stop_rule_violation": abs(shift) > 0.20,
            }

    for pk in PRIM_KEYS:
        valid = [(r["original"].get(pk), r["blinded"].get(pk))
                 for r in results if "blinded" in r
                 and r["original"].get(pk) is not None
                 and r["blinded"].get(pk) is not None]
        if not valid:
            continue
        diffs = [b - o for o, b in valid]
        summary["per_primitive_shift"][pk] = {
            "n": len(valid),
            "mean_diff": round(statistics.mean(diffs), 4),
            "exact_match_rate": round(sum(1 for o, b in valid if o == b) / len(valid), 4),
        }

    sum_path = OUT_DIR / "tribunal_blind_summary.json"
    sum_path.write_text(json.dumps(summary, indent=2))
    print(f"Wrote {sum_path}")
    print()
    for trib, s in summary["per_tribunal_mean_shift"].items():
        flag = " ⚠ STOP RULE" if s["stop_rule_violation"] else ""
        print(f"  {trib}: shift={s['shift']:+.4f}{flag}")


if __name__ == "__main__":
    main()
