"""
Compute Cohen's κ per primitive between Coder A (Maxim Labs original
scores) and Coder B (independent human reviewer).

Inputs:
  data/irr/coder_a.json
  data/irr/coder_b.json    (Coder B has filled in the template)

Outputs:
  data/irr/results.md      (rendered table + interpretation)

Cohen's κ is computed for each primitive (PR1–PR6) and overall.
Bootstrap 95% CI (n=10000 resamples) is reported alongside point κ.

Interpretation thresholds (Landis & Koch 1977):
  κ < 0.20   poor
  κ 0.21–0.40 fair
  κ 0.41–0.60 moderate
  κ 0.61–0.80 substantial
  κ 0.81–1.00 almost perfect

The audit recommended target: κ ≥ 0.7 per primitive. Anything lower
indicates rubric ambiguity that must be addressed before publication.
"""

import json
import random
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent.parent
IRR = HERE / "data" / "irr"
PRIMS = ("PR1", "PR2", "PR3", "PR4", "PR5", "PR6")
LEVELS = (0, 1, 2)


def cohens_kappa(a, b):
    assert len(a) == len(b)
    n = len(a)
    if n == 0:
        return None
    # Observed agreement
    po = sum(1 for x, y in zip(a, b) if x == y) / n
    # Marginal probabilities
    counts_a = {lv: sum(1 for x in a if x == lv) / n for lv in LEVELS}
    counts_b = {lv: sum(1 for y in b if y == lv) / n for lv in LEVELS}
    pe = sum(counts_a[lv] * counts_b[lv] for lv in LEVELS)
    if pe == 1.0:
        return 1.0 if po == 1.0 else 0.0
    return (po - pe) / (1 - pe)


def bootstrap_ci(a, b, n_iter=10000, seed=42):
    rng = random.Random(seed)
    n = len(a)
    samples = []
    for _ in range(n_iter):
        idx = [rng.randrange(n) for _ in range(n)]
        sa = [a[i] for i in idx]
        sb = [b[i] for i in idx]
        try:
            samples.append(cohens_kappa(sa, sb))
        except (ZeroDivisionError, AssertionError):
            continue
    samples = [s for s in samples if s is not None]
    samples.sort()
    if not samples:
        return (None, None)
    lo = samples[int(0.025 * len(samples))]
    hi = samples[int(0.975 * len(samples))]
    return lo, hi


def label(k):
    if k is None:
        return "—"
    if k < 0.20: return "poor"
    if k < 0.41: return "fair"
    if k < 0.61: return "moderate"
    if k < 0.81: return "substantial"
    return "almost perfect"


def main():
    a_path = IRR / "coder_a.json"
    b_path = IRR / "coder_b.json"
    if not a_path.exists():
        print("error: data/irr/coder_a.json missing — run select_irr_sample.py")
        sys.exit(2)
    if not b_path.exists():
        print(f"error: {b_path} missing.")
        print()
        print("Coder B has not been populated. The IRR exercise requires an")
        print("independent human reviewer to fill in")
        print("data/irr/coder_b.template.json and rename to coder_b.json.")
        print()
        print("DO NOT populate Coder B with an LLM — the audit recommendation")
        print("specifically excludes that as invalid IRR.")
        sys.exit(1)

    A = json.loads(a_path.read_text())
    B = json.loads(b_path.read_text())
    a_idx = {e["case_no"]: e["scores"] for e in A["entries"]}
    b_idx = {e["case_no"]: e["scores"] for e in B["entries"]}

    common = sorted(set(a_idx) & set(b_idx))
    if not common:
        print("error: no overlapping case_no between coder A and coder B")
        sys.exit(1)

    rows = []
    for p in PRIMS:
        a_vec = [a_idx[c][p] for c in common]
        b_vec = [b_idx[c][p] for c in common]
        # Skip if Coder B left this primitive unscored (None in any cell).
        if any(v is None for v in b_vec):
            rows.append((p, None, None, None, "incomplete"))
            continue
        k = cohens_kappa(a_vec, b_vec)
        lo, hi = bootstrap_ci(a_vec, b_vec)
        rows.append((p, k, lo, hi, label(k)))

    # Overall κ across all primitive cells (vector concat)
    a_all = [a_idx[c][p] for c in common for p in PRIMS
             if b_idx[c][p] is not None]
    b_all = [b_idx[c][p] for c in common for p in PRIMS
             if b_idx[c][p] is not None]
    if a_all:
        k_all = cohens_kappa(a_all, b_all)
        lo_all, hi_all = bootstrap_ci(a_all, b_all)
    else:
        k_all = None
        lo_all = hi_all = None

    out_lines = []
    out_lines.append("# IRR results — Coder A vs Coder B")
    out_lines.append("")
    out_lines.append(f"n cases (common): {len(common)}")
    out_lines.append("")
    out_lines.append("| Primitive |  κ   | 95% CI lo | 95% CI hi | Strength |")
    out_lines.append("|-----------|------|-----------|-----------|----------|")
    for p, k, lo, hi, lab in rows:
        if k is None:
            out_lines.append(f"| {p}       |  —   |     —     |     —     | {lab} |")
        else:
            out_lines.append(f"| {p}       | {k:+.3f} | {lo:+.3f}    | {hi:+.3f}    | {lab} |")
    if k_all is not None:
        out_lines.append(f"| **Overall** | **{k_all:+.3f}** | "
                         f"{lo_all:+.3f}    | {hi_all:+.3f}    | "
                         f"**{label(k_all)}** |")

    out_lines.append("")
    out_lines.append("## Interpretation")
    out_lines.append("")
    out_lines.append("Audit-recommended target: κ ≥ 0.7 per primitive.")
    out_lines.append("")
    failing = [p for p, k, *_ in rows if k is not None and k < 0.7]
    if failing:
        out_lines.append("**Below target: " + ", ".join(failing) + "**")
        out_lines.append("These primitives need rubric-definition refinement "
                         "before publication. Disagreements should be reviewed "
                         "case-by-case.")
    elif all(k is None for _, k, *_ in rows):
        out_lines.append("Coder B not yet populated.")
    else:
        out_lines.append("All scored primitives meet the audit-recommended "
                         "target of κ ≥ 0.7.")

    text = "\n".join(out_lines) + "\n"
    out_path = IRR / "results.md"
    out_path.write_text(text)
    print(text)
    print(f"\nresults written to {out_path}")


if __name__ == "__main__":
    main()
