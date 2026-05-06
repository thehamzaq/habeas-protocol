"""Conformance test for difc_rdc_38_19_indemnity (trace-03 facts)."""

import shutil
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from difc_rdc_38_19_indemnity_eval import indemnity_basis_review  # noqa: E402


# Trace-03: ENF 271/2025 Taylor v Yao Affi.
SCHEDULE = {
    "claimed_aed": "128914.80",
    "objections": [
        {
            "label": "objection_1_no_specific_item",
            "names_specific_line_item": False,
            "factual_finding": "rejected_on_evidence",
        },
        {
            "label": "objection_2_disbursement_rejected",
            "names_specific_line_item": True,
            "factual_finding": "rejected_on_evidence",
        },
        {
            "label": "objection_3_senior_associate_time",
            "names_specific_line_item": True,
            "factual_finding": "requires_human_judgment",
        },
    ],
}


def main():
    fails = 0
    out = indemnity_basis_review(SCHEDULE)
    if out["objections_mechanically_disposed"] != ["objection_1_no_specific_item"]:
        fails += 1
        print(f"  FAIL mechanically_disposed: {out['objections_mechanically_disposed']}")
    else:
        print("  PY-OK  one objection mechanically disposed")
    if out["objections_held_to_zero"] != ["objection_2_disbursement_rejected"]:
        fails += 1
        print(f"  FAIL held_to_zero: {out['objections_held_to_zero']}")
    else:
        print("  PY-OK  one objection held to zero on evidence")
    if not out["requires_human_judgment"]:
        fails += 1
        print("  FAIL requires_human_judgment should be True")
    else:
        print("  PY-OK  one objection in human-judgment residue")
    if out["deterministic_award_aed"] is not None:
        fails += 1
        print(f"  FAIL deterministic_award_aed should be None (residue), got {out['deterministic_award_aed']}")
    else:
        print("  PY-OK  no deterministic award (bounded-discretion residue)")

    if shutil.which("catala"):
        proc = subprocess.run(
            ["catala", "interpret", "--no-stdlib",
             str(HERE / "difc_rdc_38_19_indemnity.catala_en")],
            capture_output=True, text=True, timeout=30,
        )
        if proc.returncode != 0:
            fails += 1
            print(f"  CATALA-FAIL\n{proc.stderr}")
        else:
            print("  CATALA-OK")
    else:
        print("  CATALA SKIP")

    if fails:
        print(f"\nFAIL — {fails}")
        sys.exit(1)
    print("\nOK")


if __name__ == "__main__":
    main()
