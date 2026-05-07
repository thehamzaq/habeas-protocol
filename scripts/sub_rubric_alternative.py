#!/usr/bin/env python3
"""Sub-rubric coherence check (item 21).

A fresh Claude session — with no exposure to the v0.2 rubric — is
asked to propose six properties a digital-first commercial tribunal
should satisfy for its rulings to be re-executable by software. The
corpus is then scored under the alternative rubric (Claude as grader
again).

Same model proposing and scoring is NOT independent. This is a
COHERENCE check, not a validity check. If Claude's de novo rubric
saturates the same three tribunals, the v0.2 rubric is at least not
idiosyncratic to the human author. If the orderings diverge, that is
an honest finding about rubric stability under model authorship.

Output:
  - data/robustness/sub_rubric_proposed.json  (Claude's proposed rubric)
  - data/robustness/sub_rubric_scores.json    (per-entry scores under alternative)
  - data/robustness/sub_rubric_summary.json   (per-tribunal mean + ordering)
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
from pathlib import Path

from _claude_grader import _client
from perturbation_test_retest import find_raw_text, stratified_sample

ROOT = Path(__file__).resolve().parent.parent
JUDGMENTS = ROOT / "data" / "judgments.json"
OUT = ROOT / "data" / "robustness"
OUT.mkdir(exist_ok=True)

PROPOSE_PROMPT = """You are an empirical-methods reviewer with no prior exposure to any specific tribunal-evaluation rubric.

Propose six properties a digital-first commercial tribunal must satisfy for its individual rulings to be re-executable by software. Each property should be:
- A property of *individual rulings*, not of the institution as a whole.
- Scoreable on a 0/1/2 scale (absent / partial / fully implemented).
- Operationally observable from the text of a published judgment alone.

Return strict JSON:
{
  "rubric_id": "claude_alt_v1",
  "primitives": [
    {
      "id": "AP1",
      "name": "<short name>",
      "definition": "<one paragraph definition>",
      "score_0": "<what absence looks like>",
      "score_1": "<what partial implementation looks like>",
      "score_2": "<what full implementation looks like>"
    },
    ...six entries...
  ]
}
"""


def propose_rubric():
    client = _client()
    msg = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        temperature=0.0,
        max_tokens=2048,
        messages=[{"role": "user", "content": PROPOSE_PROMPT}],
    )
    text = "".join(b.text for b in msg.content if hasattr(b, "text"))
    m = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not m:
        raise ValueError(f"No JSON. Raw: {text[:500]}")
    return json.loads(m.group(0))


def grade_under_alt(text, rubric):
    """Score a judgment against the Claude-proposed alternative rubric."""
    client = _client()
    rubric_text = json.dumps(rubric["primitives"], indent=2)
    sys = (
        "You will score a single court judgment against the rubric provided. "
        "Each primitive is scored 0/1/2 (absent/partial/full) per its definition. "
        "If silent, return -1.\n\n"
        "Return strict JSON:\n"
        "{\n"
        '  "scores": {"<primitive id>": <int>, ...},\n'
        '  "rationale": {"<primitive id>": "<one sentence>", ...}\n'
        "}\n\n"
        f"Rubric:\n{rubric_text}\n"
    )
    msg = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        temperature=0.0,
        max_tokens=1024,
        system=sys,
        messages=[{"role": "user",
                   "content": "Judgment text:\n\n" + text}],
    )
    raw = "".join(b.text for b in msg.content if hasattr(b, "text"))
    m = re.search(r"\{.*\}", raw, flags=re.DOTALL)
    return json.loads(m.group(0))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-per-tribunal", type=int, default=10)
    ap.add_argument("--seed", type=int, default=20260507)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if args.dry_run:
        print("Dry run: would propose alternative rubric and grade sample.")
        return

    print("Proposing alternative rubric...")
    rubric = propose_rubric()
    (OUT / "sub_rubric_proposed.json").write_text(json.dumps(rubric, indent=2))
    print(f"  Proposed primitives: {[p['id'] + ' ' + p['name'] for p in rubric['primitives']]}")

    judgments = json.loads(JUDGMENTS.read_text())
    sample = stratified_sample(judgments, args.n_per_tribunal, args.seed)

    rows = []
    for entry in sample:
        case = entry.get("case_no") or entry.get("neutral_citation") or "?"
        text = find_raw_text(entry)
        if not text:
            rows.append({"case": case, "status": "skipped_no_raw_text"})
            continue
        try:
            r = grade_under_alt(text, rubric)
            rows.append({
                "case": case,
                "tribunal": entry.get("tribunal"),
                "scores": r.get("scores"),
                "rationale": r.get("rationale"),
            })
            print(f"  [graded] {case}")
        except Exception as e:
            rows.append({"case": case, "status": f"error: {e}"})

    (OUT / "sub_rubric_scores.json").write_text(json.dumps(rows, indent=2))

    # Per-tribunal mean
    summary = {"per_tribunal_mean_under_alternative": {}}
    for trib in ("DIFC Courts", "ADGM Courts",
                 "Singapore International Commercial Court"):
        vs = [r for r in rows if r.get("tribunal") == trib and "scores" in r]
        per_means = []
        for r in vs:
            scores = [v for v in r["scores"].values()
                       if isinstance(v, int) and 0 <= v <= 2]
            if scores:
                per_means.append(statistics.mean(scores))
        if per_means:
            summary["per_tribunal_mean_under_alternative"][trib] = {
                "n": len(per_means),
                "mean": round(statistics.mean(per_means), 4),
            }
    (OUT / "sub_rubric_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
