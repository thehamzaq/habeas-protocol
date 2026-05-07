#!/usr/bin/env python3
"""Audit grading-provenance metadata across data/judgments.json,
data/falsification_set.json, data/comparison_set.json. Reports per-entry
which provenance fields are missing for each grader_type.

Run: python3 scripts/check_grading_provenance.py
"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

REQUIRED_LLM = ["coder", "grader_type", "model", "temperature",
                "prompt_template_id", "system_prompt_sha256", "run_date"]
REQUIRED_REGEX = ["coder", "grader_type", "grader_script", "run_date"]
REQUIRED_CLASS_DEFAULT = ["coder", "grader_type", "scoring_basis", "run_date"]


def audit_file(path, container_key=None):
    if not path.exists():
        return f"[skip-missing] {path}"
    raw = json.loads(path.read_text())
    items = raw[container_key] if container_key and isinstance(raw, dict) else raw
    if not isinstance(items, list):
        return f"[skip-shape] {path}"

    missing = defaultdict(Counter)
    n_total = 0
    n_unknown = 0
    grader_counts = Counter()
    for it in items:
        if not isinstance(it, dict):
            continue
        c = it.get("coding") or {}
        gt = c.get("grader_type", "missing")
        grader_counts[gt] += 1
        n_total += 1
        required = (REQUIRED_LLM if gt == "llm"
                    else REQUIRED_REGEX if gt == "regex_heuristic"
                    else REQUIRED_CLASS_DEFAULT if gt == "author_class_default"
                    else [])
        for k in required:
            if k not in c or c[k] in (None, "", "unknown"):
                missing[gt][k] += 1
                n_unknown += 1
    out = [f"\n=== {path.name} ({n_total} entries) ==="]
    for gt, n in grader_counts.items():
        out.append(f"  grader_type='{gt}': {n} entries")
        if missing[gt]:
            for k, c in missing[gt].most_common():
                out.append(f"    missing '{k}': {c}")
    return "\n".join(out)


def main():
    print("# Grading-provenance audit")
    print(audit_file(ROOT / "data" / "judgments.json"))
    print(audit_file(ROOT / "data" / "falsification_set.json", "entries"))
    print(audit_file(ROOT / "data" / "comparison_set.json", "entries"))


if __name__ == "__main__":
    main()
