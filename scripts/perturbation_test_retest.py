#!/usr/bin/env python3
"""Test-retest stability of the LLM grader (item 10 of the soundness plan).

Re-runs the v0.2 grading prompt against a stratified 30-judgment sample
(10 per tribunal, drawn from the 39-entry first-pass set + 21 additional
judgments re-graded under the LLM procedure for this purpose).

For each entry, compares re-run scores against the original `coding`
scores. Reports per-primitive exact-match rate, weighted Cohen's κ,
mean absolute difference, and writes raw pairs to
`data/robustness/test_retest.json` plus a summary to
`data/robustness/test_retest_summary.json`.

**This measures grader stability under repeated invocation. It does NOT
measure validity against ground truth.** If exact-match agreement is
below 80% on any primitive (the stop rule committed in
PREREGISTRATION.md), that primitive is reported as unstable.

Requires: ANTHROPIC_API_KEY, `pip install anthropic`. Reads raw judgment
text from data/raw/<tribunal>/text/<filename>; if the raw text is not
locally available, the script reports the entry as `skipped`.

Usage:
    export ANTHROPIC_API_KEY=...
    python3 scripts/perturbation_test_retest.py [--n-per-tribunal 10] [--seed 20260507]
"""
from __future__ import annotations

import argparse
import json
import random
import statistics
from pathlib import Path

from _claude_grader import grade_judgment, per_primitive, PRIM_KEYS

ROOT = Path(__file__).resolve().parent.parent
JUDGMENTS = ROOT / "data" / "judgments.json"
OUT_DIR = ROOT / "data" / "robustness"
OUT_DIR.mkdir(exist_ok=True)


def find_raw_text(entry):
    """Locate raw judgment text for an entry. Returns the text or None.

    Matching strategy, in order:
      1. coding.source_file (heuristic-graded SICC + ADGM entries pin this)
      2. URL slug (DIFC entries: URL ends with /<slug>; raw text at
         data/raw/text/<slug>.txt or <slug>-N.txt)
      3. case_no exact match in any *.txt under data/raw/ (ADGM entries:
         case_no like 'ADGMCFI-2025-283' appears in filenames literally)
    """
    import re as _re
    raw_root = ROOT / "data" / "raw"
    case_no = entry.get("case_no") or ""
    url = entry.get("url") or ""
    sf = (entry.get("coding") or {}).get("source_file")

    candidates = []

    # 1) Pinned source_file
    if sf:
        for sub in raw_root.rglob(sf):
            candidates.append(sub)
        # Strip leading dash sometimes present
        if sf.startswith("-"):
            for sub in raw_root.rglob(sf.lstrip("-")):
                candidates.append(sub)

    # 2) URL slug for DIFC entries
    if "difccourts.ae" in url and not candidates:
        slug_match = _re.search(r"/([a-z0-9][a-z0-9\-]+?)(?:/?$|/\?)", url)
        if slug_match:
            slug = slug_match.group(1).rstrip("/")
            for sub in (raw_root / "text").glob(f"{slug}*.txt"):
                candidates.append(sub)

    # 3) ADGM case_no literal match
    if "ADGMCFI" in case_no.upper() and not candidates:
        # case_no like 'ADGMCFI-2025-283'; search for that token in filenames
        token = case_no.replace(" ", "").upper()
        for sub in (raw_root / "adgm" / "text").glob("*.txt"):
            if token in sub.name.upper():
                candidates.append(sub)
        # Also try with dashes stripped both ways
        if not candidates:
            slim = token.replace("-", "")
            for sub in (raw_root / "adgm" / "text").glob("*.txt"):
                nm = sub.name.upper().replace("-", "").replace("_", "")
                if slim in nm:
                    candidates.append(sub)

    # 4) SICC: derive filename from neutral_citation. Pattern:
    #    "[YYYY] SGHC(I) N"  →  YYYY_SGHCI_N.txt
    #    "[YYYY] SGCA(I) N"  →  YYYY_SGCAI_N.txt
    nc = entry.get("neutral_citation") or ""
    if not candidates and ("SGHC(I)" in nc or "SGCA(I)" in nc):
        m = _re.search(r"\[(\d{4})\]\s*(SGHC|SGCA)\(I\)\s*(\d+)", nc)
        if m:
            year, court, num = m.group(1), m.group(2), m.group(3)
            target = f"{year}_{court}I_{num}.txt"
            sicc_dir = raw_root / "sicc" / "text"
            if (sicc_dir / target).exists():
                candidates.append(sicc_dir / target)

    # 5) Fallback: case_no fragments
    if case_no and not candidates:
        frag = case_no.replace("/", "-").replace(" ", "-")
        for sub in raw_root.rglob("*.txt"):
            if frag.lower() in sub.name.lower():
                candidates.append(sub)
                break  # first hit good enough

    # Pick the longest candidate that looks substantive
    candidates.sort(key=lambda p: p.stat().st_size if p.exists() else 0,
                    reverse=True)
    for c in candidates:
        try:
            text = c.read_text(errors="replace")
            if len(text) > 500:
                return text
        except Exception:
            continue
    return None


def stratified_sample(judgments, n_per_tribunal, seed):
    rng = random.Random(seed)
    out = []
    for trib in ("DIFC Courts", "ADGM Courts",
                 "Singapore International Commercial Court"):
        rows = [j for j in judgments if j.get("tribunal") == trib]
        rng.shuffle(rows)
        out.extend(rows[:n_per_tribunal])
    return out


def cohens_kappa_weighted(a, b):
    """Linearly-weighted κ on integer scores in {0,1,2}."""
    pairs = [(x, y) for x, y in zip(a, b) if x is not None and y is not None
             and 0 <= x <= 2 and 0 <= y <= 2]
    if not pairs:
        return None
    n = len(pairs)
    # Observed weighted agreement
    w_obs = sum(1 - abs(x - y) / 2 for x, y in pairs) / n
    # Expected weighted agreement under marginal independence
    cnts_a = [sum(1 for x, _ in pairs if x == k) / n for k in (0, 1, 2)]
    cnts_b = [sum(1 for _, y in pairs if y == k) / n for k in (0, 1, 2)]
    w_exp = sum(cnts_a[i] * cnts_b[j] * (1 - abs(i - j) / 2)
                for i in range(3) for j in range(3))
    if w_exp >= 1.0:
        return 1.0
    return round((w_obs - w_exp) / (1 - w_exp), 4)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-per-tribunal", type=int, default=10)
    ap.add_argument("--seed", type=int, default=20260507)
    ap.add_argument("--dry-run", action="store_true",
                    help="Don't call the API; just write the sample plan")
    args = ap.parse_args()

    judgments = json.loads(JUDGMENTS.read_text())
    sample = stratified_sample(judgments, args.n_per_tribunal, args.seed)
    print(f"Sampled {len(sample)} entries for test-retest.")

    pairs = []
    for entry in sample:
        case = entry.get("case_no") or entry.get("neutral_citation") or "?"
        original = entry.get("primitive_scores_v02") or {}
        text = find_raw_text(entry)
        if not text:
            pairs.append({"case": case, "status": "skipped_no_raw_text"})
            print(f"  [skip-text] {case}")
            continue
        if args.dry_run:
            pairs.append({"case": case, "status": "would_grade",
                          "text_chars": len(text)})
            continue
        try:
            result = grade_judgment(text)
            new = per_primitive(result)
            pairs.append({
                "case": case,
                "tribunal": entry.get("tribunal"),
                "original": {k.lower(): original.get(k.upper()) for k in PRIM_KEYS},
                "rerun": {k: new.get(k) for k in PRIM_KEYS},
                "rerun_raw": result,
            })
            print(f"  [graded]  {case}")
        except Exception as e:
            pairs.append({"case": case, "status": f"error: {e}"})
            print(f"  [error]   {case}: {e}")

    raw_path = OUT_DIR / "test_retest.json"
    raw_path.write_text(json.dumps(pairs, indent=2))
    print(f"Wrote {raw_path}")

    if args.dry_run:
        return

    # Per-primitive summary
    summary = {"n_entries": sum(1 for p in pairs if "rerun" in p),
               "primitives": {}}
    for pk in PRIM_KEYS:
        a = [p["original"].get(pk) for p in pairs if "rerun" in p]
        b = [p["rerun"].get(pk) for p in pairs if "rerun" in p]
        # Filter pairs with both scores set
        valid = [(x, y) for x, y in zip(a, b) if x is not None and y is not None]
        if not valid:
            summary["primitives"][pk] = {"status": "no_valid_pairs"}
            continue
        n = len(valid)
        exact = sum(1 for x, y in valid if x == y) / n
        mad = sum(abs(x - y) for x, y in valid) / n
        kappa = cohens_kappa_weighted([x for x, _ in valid], [y for _, y in valid])
        summary["primitives"][pk] = {
            "n_valid": n,
            "exact_match_rate": round(exact, 4),
            "mean_abs_diff": round(mad, 4),
            "weighted_kappa": kappa,
            "stop_rule_violation": exact < 0.80,
        }
        print(f"  {pk}: exact={exact:.2%} κ={kappa} mad={mad:.3f}"
              + (" ⚠ STOP RULE" if exact < 0.80 else ""))

    sum_path = OUT_DIR / "test_retest_summary.json"
    sum_path.write_text(json.dumps(summary, indent=2))
    print(f"Wrote {sum_path}")


if __name__ == "__main__":
    main()
