#!/usr/bin/env python3
"""Model-size perturbation of the LLM grader (item 11c).

Re-grades the same stratified sample under three Claude model sizes:
Opus, Sonnet, Haiku. Stop rule: if any primitive shifts > 0.30 between
the largest and smallest model, that primitive is flagged
model-dependent.

Usage: same as the others. Slow + expensive — consider --n-per-tribunal 5.
"""
from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path

from _claude_grader import grade_judgment, per_primitive, PRIM_KEYS
from perturbation_test_retest import find_raw_text, stratified_sample

ROOT = Path(__file__).resolve().parent.parent
JUDGMENTS = ROOT / "data" / "judgments.json"
OUT_DIR = ROOT / "data" / "robustness"

MODELS = {
    "opus":   "claude-opus-4-7",
    "sonnet": "claude-sonnet-4-5-20250929",
    "haiku":  "claude-haiku-4-5-20251001",
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-per-tribunal", type=int, default=5)
    ap.add_argument("--seed", type=int, default=20260507)
    ap.add_argument("--models", nargs="*", default=list(MODELS.keys()))
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
        rec = {"case": case, "tribunal": entry.get("tribunal"), "by_model": {}}
        for size in args.models:
            model = MODELS[size]
            if args.dry_run:
                rec["by_model"][size] = {"would_grade": True, "model": model}
                continue
            try:
                result = grade_judgment(text, model=model)
                rec["by_model"][size] = {
                    "model": model,
                    "scores": per_primitive(result),
                    "raw": result,
                }
            except Exception as e:
                rec["by_model"][size] = {"model": model, "error": str(e)}
        results.append(rec)
        print(f"  graded {case}")

    raw_path = OUT_DIR / "model_size.json"
    raw_path.write_text(json.dumps(results, indent=2))
    print(f"Wrote {raw_path}")

    if args.dry_run:
        return

    # Per-primitive shift between smallest (haiku) and largest (opus)
    summary = {"per_primitive_shift": {}}
    for pk in PRIM_KEYS:
        haiku = []
        opus = []
        for r in results:
            bm = r.get("by_model", {})
            h = (bm.get("haiku") or {}).get("scores", {}).get(pk)
            o = (bm.get("opus") or {}).get("scores", {}).get(pk)
            if h is not None and o is not None:
                haiku.append(h)
                opus.append(o)
        if not haiku:
            summary["per_primitive_shift"][pk] = {"status": "no_pairs"}
            continue
        shift = statistics.mean(opus) - statistics.mean(haiku)
        summary["per_primitive_shift"][pk] = {
            "n": len(haiku),
            "haiku_mean": round(statistics.mean(haiku), 4),
            "opus_mean": round(statistics.mean(opus), 4),
            "shift_opus_minus_haiku": round(shift, 4),
            "stop_rule_violation": abs(shift) > 0.30,
        }

    sum_path = OUT_DIR / "model_size_summary.json"
    sum_path.write_text(json.dumps(summary, indent=2))
    print(f"Wrote {sum_path}")


if __name__ == "__main__":
    main()
