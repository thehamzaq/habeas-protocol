#!/usr/bin/env python3
"""Bulk-update legacy 'gold-set' / 'AI-coded' phrasings inside auto-generated
`coding.notes` strings in data/judgments.json. Idempotent.

The notes are produced by `scripts/triage_sicc.py` and similar; the
heuristic grading is regex, not LLM. The note text now reflects that.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

TARGETS = [
    ROOT / "data" / "judgments.json",
    ROOT / "data" / "sicc_graded.json",
    ROOT / "data" / "adgm_graded.json",
]

REPLACEMENTS = [
    (
        "AI-coded against the v0.2 rubric using the same heuristics applied to the ADGM borderline set; not gold-set.",
        "Regex-heuristic graded against the v0.2 rubric using the same heuristics applied to the ADGM borderline set; not in first-pass set.",
    ),
    ("Including this in the gold set is intentional",
     "Including this in the first-pass set is intentional"),
    ("Including in gold set", "Including in first-pass set"),
    ("in gold set ", "in first-pass set "),
    ("gold-set.", "first-pass set."),
    ("gold set.", "first-pass set."),
    ("not gold-set", "not in first-pass set"),
    ("not gold set", "not in first-pass set"),
    ("the gold set", "the first-pass set"),
    ("hand-coded gold set", "first-pass set"),
    ("AI-coded against the v0.2 rubric", "regex-heuristic graded against the v0.2 rubric"),
]


def walk(node, fn):
    """Recursively apply fn to every string-valued field under node."""
    if isinstance(node, dict):
        for k, v in list(node.items()):
            if isinstance(v, str):
                node[k] = fn(v)
            else:
                walk(v, fn)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            if isinstance(v, str):
                node[i] = fn(v)
            else:
                walk(v, fn)


def replace_all(s):
    out = s
    for old, new in REPLACEMENTS:
        out = out.replace(old, new)
    return out


def main():
    for path in TARGETS:
        if not path.exists():
            print(f"  skip-missing: {path}")
            continue
        data = json.loads(path.read_text())
        before = json.dumps(data, sort_keys=True)
        walk(data, replace_all)
        after = json.dumps(data, sort_keys=True)
        if before != after:
            path.write_text(json.dumps(data, indent=2))
            print(f"  updated: {path}")
        else:
            print(f"  unchanged: {path}")


if __name__ == "__main__":
    main()
