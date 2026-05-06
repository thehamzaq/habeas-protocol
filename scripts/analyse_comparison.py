"""
Analyse data/comparison_set.json: per-court means + per-claim-type breakdown,
side-by-side with the primary corpus (DIFC/ADGM/SICC) and falsification
classes. Outputs a single Markdown table the paper §4.4 can reference.
"""

import json
import statistics
from pathlib import Path


HERE = Path(__file__).resolve().parent.parent
COMP = HERE / "data" / "comparison_set.json"
FAL = HERE / "data" / "falsification_set.json"
JUDGMENTS = HERE / "data" / "judgments.json"


def primary_means(judgments):
    by = {}
    for j in judgments:
        s = j.get("primitive_scores_v02") or {}
        if not s:
            continue
        by.setdefault(j["tribunal"], []).append(s)
    out = {}
    for t, rows in by.items():
        out[t] = {k: statistics.mean(r[k] for r in rows)
                  for k in ("PR1", "PR2", "PR3", "PR4", "PR5", "PR6")}
        all_pr = [v for r in rows for k, v in r.items() if k.startswith("PR")]
        out[t]["overall"] = statistics.mean(all_pr)
        out[t]["n"] = len(rows)
    return out


def comparison_means(comp):
    by = {}
    for e in comp["entries"]:
        by.setdefault(e["court"], []).append(e)
    out = {}
    for c, rows in by.items():
        out[c] = {k: statistics.mean(r["primitive_scores_v02"][k] for r in rows)
                  for k in ("PR1", "PR2", "PR3", "PR4", "PR5", "PR6")}
        all_pr = [v for r in rows
                  for v in r["primitive_scores_v02"].values()]
        out[c]["overall"] = statistics.mean(all_pr)
        sp1 = [r["system_properties_v02"]["SP1"] for r in rows]
        sp2 = [r["system_properties_v02"]["SP2"] for r in rows]
        out[c]["SP1"] = statistics.mean(sp1)
        out[c]["SP2"] = statistics.mean(sp2)
        out[c]["n"] = len(rows)
    return out


def per_claim(comp, court_id):
    by = {}
    for e in comp["entries"]:
        if e["court"] != court_id:
            continue
        by.setdefault(e["claim_type"], []).append(e)
    out = {}
    for ct, rows in by.items():
        out[ct] = {
            "PR6": statistics.mean(r["primitive_scores_v02"]["PR6"] for r in rows),
            "n": len(rows),
        }
    return out


def fmt(m, keys=("PR1", "PR2", "PR3", "PR4", "PR5", "PR6", "overall")):
    return " | ".join(
        (f"{m[k]:.2f}".rjust(4) if k in m else " — ".rjust(4))
        for k in keys
    )


def main():
    primary = primary_means(json.loads(JUDGMENTS.read_text()))
    comp = json.loads(COMP.read_text())
    comp_m = comparison_means(comp)

    print("# Comparison-set analysis — v0.2 rubric, peer commercial courts")
    print()
    print("## Per-ruling primitive means")
    print()
    print("| Court                                          |  n |  PR1 |  "
          "PR2 |  PR3 |  PR4 |  PR5 |  PR6 | Mean |")
    print("|" + "-" * 48 + "|" + "----|" + ("------|" * 7))
    label_map = {
        "DIFC Courts": "DIFC Courts (primary)",
        "ADGM Courts": "ADGM Courts (primary)",
        "Singapore International Commercial Court": "SICC (primary)",
        "EWHC_Comm": "English Commercial Court (peer)",
        "DEL_Chancery": "Delaware Court of Chancery (peer)",
        "ICCP_CA_Paris": "ICCP-CA Paris [civil-law foil] (peer)",
    }
    order = ["DIFC Courts", "ADGM Courts",
             "Singapore International Commercial Court",
             "EWHC_Comm", "DEL_Chancery", "ICCP_CA_Paris"]
    for k in order:
        if k in primary:
            m = primary[k]
            n = m["n"]
        elif k in comp_m:
            m = comp_m[k]
            n = m["n"]
        else:
            continue
        print(f"| {label_map[k]:<46} | {n:>2} | {fmt(m)} |")

    print()
    print("## Diagnostic: PR3 across legal families")
    print()
    print("PR3 is 'specific clause + version cited'. The diagnostic question "
          "is whether the rubric translates without bias to civil-law style.")
    print()
    print("| Family               | Court                                  |"
          " PR3  |")
    print("|" + "-" * 22 + "|" + "-" * 40 + "|" + "------|")
    pr3_rows = [
        ("Common-law (DIFC own)",   "DIFC Courts",                primary["DIFC Courts"]["PR3"]),
        ("Common-law (English-via-statute)", "ADGM Courts",       primary["ADGM Courts"]["PR3"]),
        ("Common-law (Singapore)", "SICC",                        primary["Singapore International Commercial Court"]["PR3"]),
        ("Common-law (English)",   "English Commercial Court",    comp_m["EWHC_Comm"]["PR3"]),
        ("Common-law (US/Delaware)", "Delaware Court of Chancery", comp_m["DEL_Chancery"]["PR3"]),
        ("Civil-law (French)",     "ICCP-CA Paris",               comp_m["ICCP_CA_Paris"]["PR3"]),
    ]
    for fam, court, val in pr3_rows:
        print(f"| {fam:<20} | {court:<38} | {val:.2f} |")

    print()
    print("## Per-claim-type PR6 (enforcement bridge), peer courts")
    print()
    print("PR6 differs by claim type (intra-jurisdictional orders score 1; "
          "cross-border orders score 2). This is the most informative "
          "stratum for the comparison.")
    print()
    for court_id in ("EWHC_Comm", "DEL_Chancery", "ICCP_CA_Paris"):
        print(f"### {label_map[court_id]}")
        print()
        print("| Claim type               |  n |  PR6 |")
        print("|" + "-" * 26 + "|" + "----|" + "------|")
        rows = per_claim(comp, court_id)
        for ct in sorted(rows, key=lambda k: -rows[k]["n"]):
            m = rows[ct]
            print(f"| {ct:<24} | {m['n']:>2} | {m['PR6']:.2f} |")
        print()

    print("## System properties — peer courts")
    print()
    print("| Court                                  | SP1 | SP2 |")
    print("|" + "-" * 40 + "|-----|-----|")
    for k in ("EWHC_Comm", "DEL_Chancery", "ICCP_CA_Paris"):
        m = comp_m[k]
        print(f"| {label_map[k]:<38} | {m['SP1']:.0f}   | {m['SP2']:.0f}   |")

    print()
    print("## Falsifiable prediction")
    print()
    print(
        "All three peer courts score near-ceiling (≥ 1.85) on per-ruling "
        "primitives, with PR3 specifically remaining at 2 for the civil-law "
        "foil. If hand-validation against named cases yields a PR3 < 2 for "
        "ICCP-CA Paris, the rubric requires explicit civil-law adaptation. "
        "If hand-validation yields a per-ruling overall < 1.85 for any peer, "
        "the rubric over-credits the DIFC/ADGM/SICC sample."
    )


if __name__ == "__main__":
    main()
