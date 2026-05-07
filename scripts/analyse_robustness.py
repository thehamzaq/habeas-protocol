#!/usr/bin/env python3
"""Static robustness analyses on data/judgments.json + data/falsification_set.json.

Produces:
  - data/robustness/lopo.json          (leave-one-primitive-out)
  - data/robustness/loto.json          (leave-one-tribunal-out, falsification disc.)
  - data/robustness/threshold.json     (1->0 / 1->2 score-collapse sensitivity)
  - data/robustness/procedure_split.json (per-procedure tier means)
  - data/robustness/adversarial_sample.json (lowest-scoring real ruling per tribunal)
  - data/robustness/SUMMARY.md         (human-readable summary table)

All numbers in this script are derived from the existing AI-coded corpus.
No new API calls are made.
"""
import json
import statistics
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parent.parent
JUDGMENTS = ROOT / "data" / "judgments.json"
FALSIFICATION = ROOT / "data" / "falsification_set.json"
PRIMITIVES = ROOT / "data" / "primitives.json"
OUT_DIR = ROOT / "data" / "robustness"
OUT_DIR.mkdir(exist_ok=True)

PRIM_KEYS = ["PR1", "PR2", "PR3", "PR4", "PR5", "PR6"]
TRIBUNALS = ["DIFC Courts", "ADGM Courts", "Singapore International Commercial Court"]
TRIB_SHORT = {
    "DIFC Courts": "DIFC",
    "ADGM Courts": "ADGM",
    "Singapore International Commercial Court": "SICC",
}


def load_judgments():
    return json.loads(JUDGMENTS.read_text())


def load_falsification():
    raw = json.loads(FALSIFICATION.read_text())
    # The file has a wrapper { ..., "entries": [...] }; we want the entries list.
    if isinstance(raw, dict) and "entries" in raw:
        return raw["entries"]
    return raw


def per_judgment_mean(j, prims=PRIM_KEYS):
    s = j.get("primitive_scores_v02") or {}
    vals = [s[k] for k in prims if k in s and s[k] is not None]
    return statistics.mean(vals) if vals else None


def per_judgment_mean_collapsed(j, mode, prims=PRIM_KEYS):
    """mode: 'down' collapses 1->0; 'up' collapses 1->2; 'identity' is original."""
    s = j.get("primitive_scores_v02") or {}
    out = []
    for k in prims:
        v = s.get(k)
        if v is None:
            continue
        if mode == "down":
            v = 0 if v == 1 else v
        elif mode == "up":
            v = 2 if v == 1 else v
        out.append(v)
    return statistics.mean(out) if out else None


# ---------- 1. LOPO (leave-one-primitive-out) ----------
def lopo(judgments):
    out = {"description": "Leave-one-primitive-out: tribunal means with each PR dropped",
           "tribunals": {}}
    for trib in TRIBUNALS:
        rows = [j for j in judgments if j.get("tribunal") == trib]
        per_tribunal = {"all_six": None, "drop_each": {}}
        per_tribunal["n"] = len(rows)
        # All six
        means = [per_judgment_mean(j, PRIM_KEYS) for j in rows]
        means = [m for m in means if m is not None]
        per_tribunal["all_six"] = round(statistics.mean(means), 4) if means else None
        # Drop each
        for k in PRIM_KEYS:
            other = [p for p in PRIM_KEYS if p != k]
            ms = [per_judgment_mean(j, other) for j in rows]
            ms = [m for m in ms if m is not None]
            per_tribunal["drop_each"][f"drop_{k}"] = (
                round(statistics.mean(ms), 4) if ms else None
            )
        # Headline: which primitive is most load-bearing for the saturation?
        # Compare each drop_X mean to all_six and report deltas.
        per_tribunal["delta_from_all_six"] = {
            k: round(per_tribunal["drop_each"][f"drop_{k}"] - per_tribunal["all_six"], 4)
            for k in PRIM_KEYS
            if per_tribunal["drop_each"][f"drop_{k}"] is not None
        }
        out["tribunals"][TRIB_SHORT[trib]] = per_tribunal
    return out


# ---------- 2. LOTO (leave-one-tribunal-out) on falsification discrimination ----------
def loto_falsification(judgments, falsif):
    """For each tribunal-only baseline, recompute the falsification gap."""
    out = {
        "description": "Leave-one-tribunal-out: falsification discrimination using each "
                       "tribunal as the sole 'court' baseline",
        "tribunals": {},
        "falsification_classes": {},
    }
    # Falsification class means
    fclass_scores = defaultdict(list)
    for entry in falsif:
        cls = entry.get("class") or entry.get("instrument_class") or "unknown"
        m = per_judgment_mean(entry, PRIM_KEYS)
        if m is not None:
            fclass_scores[cls].append(m)
    fclass_means = {k: round(statistics.mean(v), 4) for k, v in fclass_scores.items()}
    out["falsification_classes"] = fclass_means

    # Per-tribunal court-baseline + per-class gaps
    for trib in TRIBUNALS:
        rows = [j for j in judgments if j.get("tribunal") == trib]
        means = [per_judgment_mean(j, PRIM_KEYS) for j in rows]
        means = [m for m in means if m is not None]
        court_baseline = round(statistics.mean(means), 4) if means else None
        gaps = {cls: round(court_baseline - m, 4) for cls, m in fclass_means.items()
                if court_baseline is not None}
        out["tribunals"][TRIB_SHORT[trib]] = {
            "n": len(rows),
            "court_baseline_mean": court_baseline,
            "gap_vs_class": gaps,
        }
    return out


# ---------- 3. Threshold sensitivity ----------
def threshold_sensitivity(judgments):
    out = {"description": "Per-tribunal mean under three score-collapse rules: "
                          "identity (0/1/2), 1→0, 1→2",
           "tribunals": {}}
    for trib in TRIBUNALS:
        rows = [j for j in judgments if j.get("tribunal") == trib]
        rec = {"n": len(rows)}
        for mode in ("identity", "down", "up"):
            ms = [per_judgment_mean_collapsed(j, mode, PRIM_KEYS) for j in rows]
            ms = [m for m in ms if m is not None]
            rec[mode] = round(statistics.mean(ms), 4) if ms else None
        rec["delta_down_minus_identity"] = round(rec["down"] - rec["identity"], 4)
        rec["delta_up_minus_identity"] = round(rec["up"] - rec["identity"], 4)
        out["tribunals"][TRIB_SHORT[trib]] = rec
    return out


# ---------- 4. Per-procedure-tier means ----------
def procedure_split(judgments):
    out = {"description": "Per-tribunal × per-procedure-tier means + per-primitive splits",
           "tribunals": {}}
    for trib in TRIBUNALS:
        rows = [j for j in judgments if j.get("tribunal") == trib]
        by_coder = defaultdict(list)
        for j in rows:
            c = (j.get("coding") or {}).get("coder", "unknown")
            by_coder[c].append(j)
        per_tribunal = {"by_procedure": {}}
        for coder, group in by_coder.items():
            ms = [per_judgment_mean(j, PRIM_KEYS) for j in group]
            ms = [m for m in ms if m is not None]
            entry = {
                "n": len(group),
                "overall_mean": round(statistics.mean(ms), 4) if ms else None,
                "per_primitive": {},
            }
            for k in PRIM_KEYS:
                vs = [(j.get("primitive_scores_v02") or {}).get(k) for j in group]
                vs = [v for v in vs if v is not None]
                entry["per_primitive"][k] = round(statistics.mean(vs), 4) if vs else None
            per_tribunal["by_procedure"][coder] = entry
        out["tribunals"][TRIB_SHORT[trib]] = per_tribunal
    return out


# ---------- 5. Adversarial self-sample ----------
def adversarial_sample(judgments, k=3):
    """Find lowest-scoring real ruling per tribunal."""
    out = {"description": "Lowest-scoring rulings per tribunal under v0.2 rubric",
           "tribunals": {}}
    for trib in TRIBUNALS:
        rows = [j for j in judgments if j.get("tribunal") == trib]
        scored = []
        for j in rows:
            m = per_judgment_mean(j, PRIM_KEYS)
            if m is not None:
                scored.append((m, j))
        scored.sort(key=lambda x: x[0])
        bottom = scored[:k]
        out["tribunals"][TRIB_SHORT[trib]] = [
            {
                "case_no": j.get("case_no"),
                "neutral_citation": j.get("neutral_citation"),
                "tribunal": trib,
                "claim_type": j.get("claim_type"),
                "outcome": j.get("outcome"),
                "url": j.get("url"),
                "primitive_scores_v02": j.get("primitive_scores_v02"),
                "mean": round(m, 4),
                "coder": (j.get("coding") or {}).get("coder"),
                "rationale": (j.get("coding") or {}).get("rationale")
                              or (j.get("coding") or {}).get("notes"),
            }
            for m, j in bottom
        ]
    return out


# ---------- 6. Per-primitive procedure-tier comparison (ADGM only — has 3 tiers) ----------
def adgm_procedure_comparison(judgments):
    """ADGM is the only tribunal with all three procedure tiers. Show whether
    the per-primitive means agree across the three tiers."""
    rows = [j for j in judgments if j.get("tribunal") == "ADGM Courts"]
    by_coder = defaultdict(list)
    for j in rows:
        c = (j.get("coding") or {}).get("coder", "unknown")
        by_coder[c].append(j)
    out = {"description": "ADGM per-primitive means by procedure tier (the only "
                          "tribunal with all three tiers represented)"}
    for coder, group in by_coder.items():
        rec = {"n": len(group), "per_primitive": {}}
        for k in PRIM_KEYS:
            vs = [(j.get("primitive_scores_v02") or {}).get(k) for j in group]
            vs = [v for v in vs if v is not None]
            rec["per_primitive"][k] = round(statistics.mean(vs), 4) if vs else None
        out[coder] = rec
    return out


# ---------- 7. Headline saturation under SP1/SP2-excluded mean ----------
def per_ruling_only(judgments):
    """Confirm that the headline saturation finding doesn't depend on SP1/SP2.
    The headline is per-ruling-only by construction (SP1/SP2 are tribunal-level,
    not per-ruling), but we explicitly state this and report the per-ruling mean
    here for clarity."""
    out = {"description": "Per-ruling-only (PR1-PR6) means — SP1/SP2 are architectural "
                          "pre-conditions, scored once per tribunal, not blended into "
                          "the per-ruling mean. This is the headline statistic.",
           "tribunals": {}}
    for trib in TRIBUNALS:
        rows = [j for j in judgments if j.get("tribunal") == trib]
        ms = [per_judgment_mean(j, PRIM_KEYS) for j in rows]
        ms = [m for m in ms if m is not None]
        out["tribunals"][TRIB_SHORT[trib]] = {
            "n": len(rows),
            "per_ruling_mean": round(statistics.mean(ms), 4) if ms else None,
        }
    return out


def main():
    judgments = load_judgments()
    falsif = load_falsification()
    print(f"Loaded {len(judgments)} judgments, {len(falsif)} falsification entries")

    results = {
        "lopo.json": lopo(judgments),
        "loto.json": loto_falsification(judgments, falsif),
        "threshold.json": threshold_sensitivity(judgments),
        "procedure_split.json": procedure_split(judgments),
        "adversarial_sample.json": adversarial_sample(judgments, k=3),
        "adgm_procedure_comparison.json": adgm_procedure_comparison(judgments),
        "per_ruling_only.json": per_ruling_only(judgments),
    }

    for name, data in results.items():
        path = OUT_DIR / name
        path.write_text(json.dumps(data, indent=2))
        print(f"  wrote {path}")

    # Generate human-readable summary
    md = ["# Static robustness analyses\n",
          f"Generated by `scripts/analyse_robustness.py`. All numbers derived from "
          f"the existing AI-coded corpus; no new API calls.\n"]

    md.append("## 1. Per-ruling-only mean (headline statistic)\n")
    md.append("SP1 and SP2 are architectural pre-conditions, scored once per tribunal. "
              "They do not enter the per-ruling mean; the headline is PR1–PR6 only.\n")
    md.append("| Tribunal | n | Per-ruling mean (PR1–PR6) |")
    md.append("|---|---:|---:|")
    for trib_short, row in results["per_ruling_only.json"]["tribunals"].items():
        md.append(f"| {trib_short} | {row['n']} | {row['per_ruling_mean']:.4f} |")
    md.append("")

    md.append("## 2. Procedure-tier split\n")
    md.append("Per-tribunal × per-procedure-tier overall means.\n")
    md.append("| Tribunal | Procedure | n | Mean |")
    md.append("|---|---|---:|---:|")
    for trib_short, row in results["procedure_split.json"]["tribunals"].items():
        for coder, sub in row["by_procedure"].items():
            md.append(f"| {trib_short} | {coder} | {sub['n']} | {sub['overall_mean']:.4f} |")
    md.append("")

    md.append("## 3. ADGM per-primitive by procedure (only tribunal with all three tiers)\n")
    md.append("| Procedure | n | PR1 | PR2 | PR3 | PR4 | PR5 | PR6 |")
    md.append("|---|---:|---:|---:|---:|---:|---:|---:|")
    adgm = results["adgm_procedure_comparison.json"]
    for coder, rec in adgm.items():
        if coder == "description":
            continue
        pp = rec.get("per_primitive", {})
        cells = " | ".join(f"{pp.get(k, 0):.2f}" if pp.get(k) is not None else "—"
                            for k in PRIM_KEYS)
        md.append(f"| {coder} | {rec['n']} | {cells} |")
    md.append("")

    md.append("## 4. Leave-one-primitive-out\n")
    md.append("Per-tribunal mean with each primitive dropped. The smallest-magnitude "
              "delta indicates the primitive least load-bearing for the headline.\n")
    md.append("| Tribunal | All six | drop PR1 | drop PR2 | drop PR3 | drop PR4 | drop PR5 | drop PR6 |")
    md.append("|---|---:|---:|---:|---:|---:|---:|---:|")
    for trib_short, row in results["lopo.json"]["tribunals"].items():
        d = row["drop_each"]
        cells = " | ".join(f"{d[f'drop_{k}']:.4f}" for k in PRIM_KEYS)
        md.append(f"| {trib_short} | {row['all_six']:.4f} | {cells} |")
    md.append("")

    md.append("## 5. Threshold sensitivity\n")
    md.append("Mean under three score-collapse rules.\n")
    md.append("| Tribunal | identity (0/1/2) | 1→0 | 1→2 |")
    md.append("|---|---:|---:|---:|")
    for trib_short, row in results["threshold.json"]["tribunals"].items():
        md.append(f"| {trib_short} | {row['identity']:.4f} | {row['down']:.4f} | {row['up']:.4f} |")
    md.append("")

    md.append("## 6. Leave-one-tribunal-out (LOTO) — falsification discrimination per court baseline\n")
    md.append("For each tribunal alone, the gap from court mean to each falsification class.\n")
    fclasses = list(results["loto.json"]["falsification_classes"].keys())
    md.append("Falsification class means: " +
              ", ".join(f"{c}={v:.4f}" for c, v in results["loto.json"]["falsification_classes"].items()))
    md.append("")
    md.append("| Tribunal | court baseline | " + " | ".join(f"gap vs {c}" for c in fclasses) + " |")
    md.append("|---|---:|" + "|".join(["---:"] * len(fclasses)) + "|")
    for trib_short, row in results["loto.json"]["tribunals"].items():
        cells = " | ".join(f"{row['gap_vs_class'].get(c, 0):.4f}" for c in fclasses)
        md.append(f"| {trib_short} | {row['court_baseline_mean']:.4f} | {cells} |")
    md.append("")

    md.append("## 7. Adversarial self-sample (3 lowest-scoring rulings per tribunal)\n")
    for trib_short, items in results["adversarial_sample.json"]["tribunals"].items():
        md.append(f"### {trib_short}")
        md.append("")
        for it in items:
            md.append(f"- **{it.get('case_no') or it.get('neutral_citation') or '(no id)'}** "
                      f"— mean {it['mean']:.4f}, claim_type={it.get('claim_type')}, "
                      f"outcome={it.get('outcome')}, scores={it.get('primitive_scores_v02')}")
        md.append("")

    (OUT_DIR / "SUMMARY.md").write_text("\n".join(md))
    print(f"  wrote {OUT_DIR / 'SUMMARY.md'}")
    print()
    print("Done.")


if __name__ == "__main__":
    main()
