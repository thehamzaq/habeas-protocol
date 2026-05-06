"""
Analyse data/falsification_set.json: per-class means + diagnostic comparison
against the primary corpus (DIFC/ADGM/SICC).

Prints a table that the paper can reference. The diagnostic claim is:

  - Class A (sealed)            : per-ruling means well below courts
  - Class B (on-chain)          : near-zero across the board
  - Class C (regulator)         : per-ruling AT or NEAR courts; SP1 ≤ 1
  - Class D (platform, mostly)  : per-ruling well below courts; Meta OB anomaly
  - Class E (specialised, positive control): per-ruling NEAR courts
"""

import json
import statistics
from pathlib import Path


HERE = Path(__file__).resolve().parent.parent
FAL = HERE / "data" / "falsification_set.json"
JUDGMENTS = HERE / "data" / "judgments.json"


def load():
    fal = json.loads(FAL.read_text())
    judgments = json.loads(JUDGMENTS.read_text())
    return fal, judgments


def primary_corpus_means(judgments):
    by_trib = {}
    for j in judgments:
        t = j.get("tribunal", "?")
        s = j.get("primitive_scores_v02") or j.get("primitive_scores") or {}
        by_trib.setdefault(t, []).append(s)
    out = {}
    for t, rows in by_trib.items():
        out[t] = {}
        for k in ("PR1", "PR2", "PR3", "PR4", "PR5", "PR6"):
            vals = [r[k] for r in rows if k in r]
            out[t][k] = statistics.mean(vals) if vals else None
        all_vals = [v for r in rows for k, v in r.items() if k.startswith("PR")]
        out[t]["overall"] = statistics.mean(all_vals) if all_vals else None
        out[t]["n"] = len(rows)
    return out


def class_means(fal):
    by_cls = {}
    for e in fal["entries"]:
        c = e["class"]
        by_cls.setdefault(c, []).append(e)
    out = {}
    for c, rows in by_cls.items():
        out[c] = {}
        for k in ("PR1", "PR2", "PR3", "PR4", "PR5", "PR6"):
            vals = [r["primitive_scores_v02"][k] for r in rows]
            out[c][k] = statistics.mean(vals)
        all_pr = [v for r in rows for v in r["primitive_scores_v02"].values()]
        out[c]["overall"] = statistics.mean(all_pr)
        sp1 = [r["system_properties_v02"]["SP1"] for r in rows]
        sp2 = [r["system_properties_v02"]["SP2"] for r in rows]
        out[c]["SP1"] = statistics.mean(sp1)
        out[c]["SP2"] = statistics.mean(sp2)
        out[c]["n"] = len(rows)
    return out


def fmt_row(label, m, n=None):
    cells = [f"{m[k]:.2f}" if m[k] is not None else "—"
             for k in ("PR1", "PR2", "PR3", "PR4", "PR5", "PR6", "overall")]
    n_cell = f"{n}" if n is not None else f"{m.get('n','?')}"
    return f"| {label:<35} | {n_cell:>4} | " + " | ".join(c.rjust(4) for c in cells) + " |"


def header():
    return ("| Group / class                       |    n |  PR1 |  PR2 |"
            "  PR3 |  PR4 |  PR5 |  PR6 | Mean |\n"
            "|" + "-" * 38 + "|" + "-" * 6 + "|" +
            ("|" + "-" * 6) * 7 + "|")


def main():
    fal, judgments = load()
    primary = primary_corpus_means(judgments)
    fal_cls = class_means(fal)

    print("# Falsification analysis — v0.2 rubric")
    print()
    print("## Per-ruling primitive means")
    print()
    print(header())
    for label in ("DIFC Courts", "ADGM Courts",
                  "Singapore International Commercial Court"):
        if label in primary:
            print(fmt_row(label, primary[label]))
    print(fmt_row("(separator)",
                  {k: None for k in ("PR1", "PR2", "PR3", "PR4", "PR5", "PR6", "overall")},
                  n=0))
    cls_order = ("A_sealed_award", "B_on_chain", "C_regulator",
                 "D_platform", "E_specialised_positive")
    cls_label = {
        "A_sealed_award": "A. Sealed arbitral awards",
        "B_on_chain": "B. On-chain / DAO tribunals",
        "C_regulator": "C. Regulator enforcement",
        "D_platform": "D. Platform adjudicators",
        "E_specialised_positive": "E. Specialised panels (positive ctl)",
    }
    for c in cls_order:
        if c in fal_cls:
            print(fmt_row(cls_label[c], fal_cls[c]))

    print()
    print("## System properties (per-class mean)")
    print()
    print("| Class                                | SP1  | SP2  |")
    print("|" + "-" * 38 + "|" + "-" * 6 + "|" + "-" * 6 + "|")
    for c in cls_order:
        m = fal_cls[c]
        print(f"| {cls_label[c]:<36} | {m['SP1']:.2f} | {m['SP2']:.2f} |")

    print()
    print("## Diagnostic checks")
    print()
    courts_overall = statistics.mean(
        primary[t]["overall"] for t in primary if primary[t]["overall"] is not None
    )
    print(f"- Operating courts (DIFC+ADGM+SICC) per-ruling mean: {courts_overall:.2f}")
    for c in cls_order:
        gap = courts_overall - fal_cls[c]["overall"]
        verdict = ("RUBRIC SEPARATES" if gap > 0.4
                   else "rubric does not separate" if gap < 0.1
                   else "marginal")
        print(f"  - vs {cls_label[c]:<36} gap = {gap:+.2f}  → {verdict}")
    print()
    print("Expected pattern:")
    print("  A: gap ≥ 0.6   (sealed → low PR1/PR2/PR5)")
    print("  B: gap ≥ 1.0   (on-chain → low across the board)")
    print("  C: gap ≤ 0.2   (regulator → high per-ruling; SP1 fails)")
    print("  D: gap mixed   (Meta OB high; consumer programmes low)")
    print("  E: gap ≤ 0.2   (positive control — rubric should NOT mark down)")


if __name__ == "__main__":
    main()
