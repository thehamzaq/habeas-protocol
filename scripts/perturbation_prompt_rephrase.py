#!/usr/bin/env python3
"""Prompt-rephrase perturbation of the LLM grader (item 11d).

The rubric prompt is rewritten with different ordering and examples;
same criteria. Tests whether the grader is following the prompt or
following memorised priors.

Stop rule: if any primitive shifts > 0.20 between the canonical and
rephrased prompt, that primitive is flagged prompt-sensitive.
"""
from __future__ import annotations

import argparse
import json
import statistics
import tempfile
from pathlib import Path

from _claude_grader import grade_judgment, per_primitive, PRIM_KEYS, DEFAULT_PROMPT_PATH
from perturbation_test_retest import find_raw_text, stratified_sample

ROOT = Path(__file__).resolve().parent.parent
JUDGMENTS = ROOT / "data" / "judgments.json"
OUT_DIR = ROOT / "data" / "robustness"
ALT_PROMPT = ROOT / "scripts" / "ai_grade_prompt_v0_2_rephrased.txt"

REPHRASED = """You are an empirical reviewer applying a measurement rubric to a court judgment.

Given the full text of a single court judgment or order, score it on the v0.2 Habeas Protocol rubric. The rubric (concatenated below) defines six per-ruling primitives PR1..PR6 and two system properties SP1..SP2 on a 0/1/2 scale (absent / partial / fully implemented). Where the document is genuinely silent on a primitive, return -1.

Read the rubric definitions and worked examples carefully. Apply them to the actual content of this document. Where you can quote a specific phrase from the document supporting your score, do so in the rationale.

Output: strict JSON, this exact shape:

{
  "pr1": <int>,
  "pr2": <int>,
  "pr3": <int>,
  "pr4": <int>,
  "pr5": <int>,
  "pr6": <int>,
  "sp1": <int>,
  "sp2": <int>,
  "rationale": {
    "pr1": "...", "pr2": "...", "pr3": "...", "pr4": "...",
    "pr5": "...", "pr6": "...", "sp1": "...", "sp2": "..."
  },
  "notes": "..."
}

Apply the rubric as written. Do not interpolate.

# Rubric (v0.2)

[The full text of data/primitives.json v0.2 is concatenated to this prompt at runtime.]

End of prompt. Return ONLY the JSON object specified above.
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-per-tribunal", type=int, default=10)
    ap.add_argument("--seed", type=int, default=20260507)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    # Materialise the rephrased prompt
    ALT_PROMPT.write_text(REPHRASED)

    judgments = json.loads(JUDGMENTS.read_text())
    sample = stratified_sample(judgments, args.n_per_tribunal, args.seed)

    results = []
    for entry in sample:
        case = entry.get("case_no") or entry.get("neutral_citation") or "?"
        text = find_raw_text(entry)
        if not text:
            results.append({"case": case, "status": "skipped_no_raw_text"})
            continue
        if args.dry_run:
            results.append({"case": case, "status": "would_grade"})
            continue
        try:
            canonical = per_primitive(grade_judgment(text, prompt_template_path=DEFAULT_PROMPT_PATH))
            rephrased = per_primitive(grade_judgment(text, prompt_template_path=ALT_PROMPT))
            results.append({
                "case": case,
                "tribunal": entry.get("tribunal"),
                "canonical": {k: canonical.get(k) for k in PRIM_KEYS},
                "rephrased": {k: rephrased.get(k) for k in PRIM_KEYS},
            })
            print(f"  graded {case}")
        except Exception as e:
            results.append({"case": case, "status": f"error: {e}"})

    raw_path = OUT_DIR / "prompt_rephrase.json"
    raw_path.write_text(json.dumps(results, indent=2))
    print(f"Wrote {raw_path}")

    if args.dry_run:
        return

    summary = {"per_primitive_shift": {}}
    for pk in PRIM_KEYS:
        valid = [(r["canonical"].get(pk), r["rephrased"].get(pk))
                 for r in results if "canonical" in r
                 and r["canonical"].get(pk) is not None
                 and r["rephrased"].get(pk) is not None]
        if not valid:
            continue
        diffs = [b - a for a, b in valid]
        summary["per_primitive_shift"][pk] = {
            "n": len(valid),
            "mean_diff": round(statistics.mean(diffs), 4),
            "exact_match_rate": round(sum(1 for a, b in valid if a == b) / len(valid), 4),
            "stop_rule_violation": abs(statistics.mean(diffs)) > 0.20,
        }

    sum_path = OUT_DIR / "prompt_rephrase_summary.json"
    sum_path.write_text(json.dumps(summary, indent=2))
    print(f"Wrote {sum_path}")


if __name__ == "__main__":
    main()
