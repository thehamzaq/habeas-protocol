"""
Build / refresh `spike/trace-*/discrepancy.json` for each trace.

Each trace's predicate either reproduces the court's stated value
exactly, or surfaces a discrepancy. The discrepancy claim is currently
narrative-only (paper.md §5.8). This script writes a structured record
per trace so the "3 of 7 surface a clerical/methodological gap" claim
becomes machine-readable and CI-verifiable.

Schema (per trace):

  {
    "trace_id": "trace-NN",
    "case_no": "...",
    "kind": "none" | "clerical_arithmetic" | "daycount_methodology"
            | "partial_finding_beyond_submissions",
    "quantum": {"value": <number>, "unit": "AED" | "GBP" | "USD"} | null,
    "operative_value": ... | null,
    "predicate_value": ... | null,
    "paragraph_ref": "..." | null,
    "note": "free text"
  }

`build_trace_outputs.sh` is a separate CI step; this discrepancy file
is independent (it is *not* derived from Catala interpret output —
it is a curated record of where the predicate diverged from the
court's stated number).
"""

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
SPIKE = HERE / "spike"


DISCREPANCIES = {
    "trace-01": {
        "case_no": "CFI 058/2024",
        "kind": "clerical_arithmetic",
        "quantum": {"value": 6.00, "unit": "AED"},
        "operative_value": 7127.75,
        "predicate_value": 7121.75,
        "paragraph_ref": "operative order vs Schedule of Reasons",
        "note": (
            "Operative order states AED 7,127.75; Schedule of Reasons "
            "computes AED 7,121.75. The protocol reproduces the "
            "Schedule total; the 6 AED gap is consistent with a "
            "clerical error in the operative paragraph."
        ),
    },
    "trace-02": {
        "case_no": "ARB 008/2026",
        "kind": "none",
        "quantum": None,
        "operative_value": None,
        "predicate_value": None,
        "paragraph_ref": None,
        "note": (
            "All five scenarios (on-time, at-deadline, 1/61/92 days "
            "late) reproduce the implicit schedule exactly. No "
            "discrepancy surfaced."
        ),
    },
    "trace-03": {
        "case_no": "ENF 271/2025",
        "kind": "none",
        "quantum": None,
        "operative_value": None,
        "predicate_value": None,
        "paragraph_ref": None,
        "note": (
            "Bounded-discretion case by design. Predicate triages "
            "objections and surfaces the AED 8,914.80 (≈6.92%) "
            "discretion residue. This is the *operating point* of the "
            "rule, not a discrepancy with the court."
        ),
    },
    "trace-04": {
        "case_no": "ADGMCFI-2024-320",
        "kind": "daycount_methodology",
        "quantum": {"value": 1.44, "unit": "AED"},
        "operative_value": 877.48,
        "predicate_value": 876.04,
        "paragraph_ref": "pre-judgment interest computation",
        "note": (
            "Calendar daycount (609 days from 2024-02-29 to "
            "2025-10-30) yields AED 876.04. The court's stated "
            "AED 877.48 corresponds to 610 days, indicating an "
            "inclusive-endpoint convention. Methodological gap, not "
            "arithmetic — the protocol surfaces the daycount choice "
            "for review. Net principal AED 10,500.96 reproduces "
            "exactly."
        ),
    },
    "trace-05": {
        "case_no": "ADGMCFI-2024-158",
        "kind": "none",
        "quantum": None,
        "operative_value": None,
        "predicate_value": None,
        "paragraph_ref": None,
        "note": (
            "Boolean composition. Judgment Sum GBP 409,870, costs "
            "USD 125,483.84, counterclaim dismissed — all match "
            "exactly."
        ),
    },
    "trace-06": {
        "case_no": "SIC/OA 9/2025",
        "kind": "partial_finding_beyond_submissions",
        "quantum": None,
        "operative_value": "9 paras pleaded under Order 3",
        "predicate_value": "3 paras (Order 3(d)(ii), (d)(iii), (f)) excised; 6 enforced",
        "paragraph_ref": "para 185(b)-(c)",
        "note": (
            "Partial refusal of NY Convention enforcement: the "
            "tribunal made findings on three paragraphs of Order 3 "
            "the parties had not been heard on. The protocol "
            "reproduces the court's disposition exactly (3 paras "
            "excised) and surfaces the structural finding that the "
            "tribunal exceeded the submissions on those paragraphs."
        ),
    },
    "trace-07": {
        "case_no": "DEC 001/2025",
        "kind": "none",
        "quantum": None,
        "operative_value": None,
        "predicate_value": None,
        "paragraph_ref": None,
        "note": (
            "Three jurisdictional gates conjunctively satisfied; "
            "order granted on the agreed compliance windows. "
            "Reproduces para 24 exactly."
        ),
    },
}


def main():
    written = 0
    for tdir in sorted(SPIKE.glob("trace-*")):
        if not tdir.is_dir():
            continue
        tid = tdir.name
        if tid not in DISCREPANCIES:
            print(f"  WARN no discrepancy entry for {tid}")
            continue
        rec = {"trace_id": tid, **DISCREPANCIES[tid]}
        out = tdir / "discrepancy.json"
        out.write_text(json.dumps(rec, indent=2) + "\n")
        kind = rec["kind"]
        marker = "FLAG" if kind != "none" else "    "
        print(f"  [{marker}] {tid:<10} {kind:<40}")
        written += 1

    n_flagged = sum(1 for r in DISCREPANCIES.values() if r["kind"] != "none")
    print(f"\nwrote {written} discrepancy.json files; "
          f"{n_flagged}/{written} traces surface a discrepancy.")
    if n_flagged != 3:
        print(f"WARN: paper.md claims 3 traces surface a gap; "
              f"current count is {n_flagged}.")


if __name__ == "__main__":
    main()
