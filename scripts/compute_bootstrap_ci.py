#!/usr/bin/env python3
"""Bootstrap 95% confidence intervals on per-tribunal composite means.

Reads data/judgments.json. For each tribunal computes the per-judgment
composite mean (mean of PR1..PR6) and a 10000-resample bootstrap 95% CI
on the mean of those means. Also computes pairwise difference CIs to
support claims like "ADGM > DIFC".

Output: a markdown table on stdout + a json file at
data/bootstrap_ci.json so the dashboard / paper builds can pick it up.
"""
from __future__ import annotations
import json
import random
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JUDGMENTS = ROOT / "data" / "judgments.json"
OUTPUT_JSON = ROOT / "data" / "bootstrap_ci.json"

N_RESAMPLES = 10000
ALPHA = 0.05
SEED = 20260505


def composite_mean(scores: dict) -> float:
    keys = ("PR1", "PR2", "PR3", "PR4", "PR5", "PR6")
    vals = [scores[k] for k in keys]
    return sum(vals) / len(vals)


def bootstrap_mean_ci(values, n_resamples=N_RESAMPLES, alpha=ALPHA, rng=None):
    rng = rng or random.Random(SEED)
    n = len(values)
    means = []
    for _ in range(n_resamples):
        sample = [values[rng.randrange(n)] for _ in range(n)]
        means.append(sum(sample) / n)
    means.sort()
    lo = means[int((alpha / 2) * n_resamples)]
    hi = means[int((1 - alpha / 2) * n_resamples) - 1]
    return statistics.mean(values), lo, hi


def bootstrap_diff_ci(a, b, n_resamples=N_RESAMPLES, alpha=ALPHA, rng=None):
    rng = rng or random.Random(SEED + 1)
    na, nb = len(a), len(b)
    diffs = []
    for _ in range(n_resamples):
        ma = sum(a[rng.randrange(na)] for _ in range(na)) / na
        mb = sum(b[rng.randrange(nb)] for _ in range(nb)) / nb
        diffs.append(ma - mb)
    diffs.sort()
    lo = diffs[int((alpha / 2) * n_resamples)]
    hi = diffs[int((1 - alpha / 2) * n_resamples) - 1]
    point = statistics.mean(a) - statistics.mean(b)
    return point, lo, hi


def main():
    judgments = json.loads(JUDGMENTS.read_text())
    by_tribunal: dict[str, list[float]] = {}
    for j in judgments:
        scores = j.get("primitive_scores_v02")
        if not scores:
            continue
        try:
            cm = composite_mean(scores)
        except (KeyError, TypeError):
            continue
        by_tribunal.setdefault(j["tribunal"], []).append(cm)

    results = {}
    print("\n## Per-tribunal composite means with bootstrap 95% CI")
    print()
    print("| Tribunal | n | mean | 95% CI |")
    print("|---|---:|---:|:---|")
    short = {
        "DIFC Courts": "DIFC",
        "ADGM Courts": "ADGM",
        "Singapore International Commercial Court": "SICC",
    }
    for trib in ("DIFC Courts", "ADGM Courts",
                 "Singapore International Commercial Court"):
        vals = by_tribunal.get(trib, [])
        if not vals:
            continue
        m, lo, hi = bootstrap_mean_ci(vals)
        results[short[trib]] = {
            "n": len(vals),
            "mean": round(m, 4),
            "ci_lo": round(lo, 4),
            "ci_hi": round(hi, 4),
        }
        print(f"| {short[trib]} | {len(vals)} | {m:.2f} | "
              f"[{lo:.2f}, {hi:.2f}] |")

    print("\n## Pairwise difference CIs (a − b)")
    print()
    print("| Pair | Δ | 95% CI | Significant? |")
    print("|---|---:|:---|:---:|")
    pairs = [
        ("ADGM Courts", "DIFC Courts"),
        ("ADGM Courts", "Singapore International Commercial Court"),
        ("Singapore International Commercial Court", "DIFC Courts"),
    ]
    diffs_out = {}
    for a, b in pairs:
        va, vb = by_tribunal[a], by_tribunal[b]
        d, lo, hi = bootstrap_diff_ci(va, vb)
        sig = "yes" if (lo > 0 or hi < 0) else "no"
        diffs_out[f"{short[a]}_minus_{short[b]}"] = {
            "delta": round(d, 4),
            "ci_lo": round(lo, 4),
            "ci_hi": round(hi, 4),
            "significant_at_0_05": sig == "yes",
        }
        print(f"| {short[a]} − {short[b]} | {d:+.3f} | "
              f"[{lo:+.3f}, {hi:+.3f}] | {sig} |")

    OUTPUT_JSON.write_text(json.dumps({
        "n_resamples": N_RESAMPLES,
        "alpha": ALPHA,
        "seed": SEED,
        "tribunals": results,
        "pairwise_differences": diffs_out,
    }, indent=2) + "\n")
    print(f"\nWrote {OUTPUT_JSON.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
