#!/usr/bin/env python3
"""External correlate of rubric scores against an outside metric (item 22).

Takes the n=188 corpus and computes Spearman rank correlation between
the per-judgment v0.2 mean (PR1-PR6) and one or more external metrics
extractable from the same court sites:

  - subsequent_citation_count: how many later judgments of the same
    court (by neutral citation) cite this case_no in their text.
  - was_appealed: boolean, derived from whether a CA / Court of Appeal
    output references this case_no.
  - days_to_judgment: from filing date (or first hearing date in the
    text) to date_issued (extractable from `date_issued` field).

A null correlation is NOT a refutation of the rubric. The rubric
measures procedural form / computational legibility; a null vs
citation count would mean the rubric and citation-network centrality
measure different things, which is fine. A positive correlation is a
strong external-validity result. Both outcomes are reported.

Output:
  - data/robustness/external_correlate.json
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JUDGMENTS = ROOT / "data" / "judgments.json"
RAW_ROOT = ROOT / "data" / "raw"
OUT = ROOT / "data" / "robustness" / "external_correlate.json"


def per_judgment_mean(j):
    s = j.get("primitive_scores_v02") or {}
    vs = [v for v in s.values() if isinstance(v, int) and 0 <= v <= 2]
    return statistics.mean(vs) if vs else None


def extract_subsequent_citations(target_caseno, all_text_files):
    """Count occurrences of the target case_no in other judgments' text."""
    if not target_caseno:
        return None
    pat = re.compile(re.escape(target_caseno), flags=re.I)
    count = 0
    for f in all_text_files:
        try:
            text = f.read_text(errors="replace")
            if pat.search(text):
                count += 1
        except Exception:
            continue
    # Subtract the self-match if applicable
    return max(count - 1, 0)


def days_to_judgment(entry):
    """Extract days from earliest mentioned date to date_issued.
    Heuristic; many judgments don't expose a clean filing date."""
    date_issued = entry.get("date_issued")
    if not date_issued:
        return None
    try:
        di = datetime.strptime(date_issued, "%Y-%m-%d")
    except (ValueError, TypeError):
        return None
    # Try to read raw text and find earliest YYYY-MM-DD or DD MMM YYYY date.
    return None  # Implementation deferred; honest "unknown" rather than guessed.


def was_appealed(entry, all_text_files):
    """True if some CA/Court of Appeal text mentions the case_no."""
    cn = entry.get("case_no")
    if not cn:
        return None
    pat = re.compile(re.escape(cn), flags=re.I)
    for f in all_text_files:
        if any(tag in f.name.lower() for tag in ("court_of_appeal", "ca_", "_ca", "sgca")):
            try:
                text = f.read_text(errors="replace")
                if pat.search(text):
                    return True
            except Exception:
                continue
    return False


def spearman_rank_corr(xs, ys):
    """Spearman rank correlation. Returns (rho, n) where rho in [-1, 1]."""
    pairs = [(x, y) for x, y in zip(xs, ys)
             if x is not None and y is not None]
    if len(pairs) < 4:
        return (None, len(pairs))
    n = len(pairs)
    xs = [p[0] for p in pairs]
    ys = [p[1] for p in pairs]
    rx = _ranks(xs)
    ry = _ranks(ys)
    d2 = sum((a - b) ** 2 for a, b in zip(rx, ry))
    rho = 1 - (6 * d2) / (n * (n * n - 1))
    return (round(rho, 4), n)


def _ranks(values):
    """Average-rank ranks."""
    indexed = sorted(enumerate(values), key=lambda p: p[1])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(indexed):
        j = i
        while j + 1 < len(indexed) and indexed[j + 1][1] == indexed[i][1]:
            j += 1
        avg = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[indexed[k][0]] = avg
        i = j + 1
    return ranks


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--metrics", nargs="*",
                    default=["subsequent_citations", "was_appealed", "days_to_judgment"])
    args = ap.parse_args()

    judgments = json.loads(JUDGMENTS.read_text())
    print(f"Loaded {len(judgments)} judgments")

    # Index raw text files
    text_files = list(RAW_ROOT.rglob("*.txt")) if RAW_ROOT.exists() else []
    print(f"Indexed {len(text_files)} raw text files for citation/appeal scan")

    rows = []
    for entry in judgments:
        rec = {
            "case_no": entry.get("case_no"),
            "tribunal": entry.get("tribunal"),
            "rubric_mean": per_judgment_mean(entry),
        }
        if "subsequent_citations" in args.metrics:
            rec["subsequent_citations"] = extract_subsequent_citations(
                entry.get("case_no"), text_files)
        if "was_appealed" in args.metrics:
            rec["was_appealed"] = was_appealed(entry, text_files)
        if "days_to_judgment" in args.metrics:
            rec["days_to_judgment"] = days_to_judgment(entry)
        rows.append(rec)

    # Spearman rho per metric
    out = {"per_metric": {}, "n": len(rows)}
    rubric = [r["rubric_mean"] for r in rows]
    for metric in args.metrics:
        if metric == "was_appealed":
            xs = [(1 if r.get(metric) else 0) if r.get(metric) is not None else None
                  for r in rows]
        else:
            xs = [r.get(metric) for r in rows]
        rho, n = spearman_rank_corr(rubric, xs)
        out["per_metric"][metric] = {
            "n_pairs": n,
            "spearman_rho": rho,
            "interpretation": (
                "positive correlation: rubric tracks this metric"
                if rho is not None and rho > 0.10 else
                "negative correlation: rubric inversely tracks this metric"
                if rho is not None and rho < -0.10 else
                "null correlation: rubric and metric measure different things"
            ),
        }

    out["rows"] = rows
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2))
    print(f"Wrote {OUT}")
    for metric, rec in out["per_metric"].items():
        print(f"  {metric}: n={rec['n_pairs']}, rho={rec['spearman_rho']}, "
              f"{rec['interpretation']}")


if __name__ == "__main__":
    main()
