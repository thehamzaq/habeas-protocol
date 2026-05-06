"""Conformance test for adgm_cpr_admissions."""

import shutil
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from adgm_cpr_admissions_eval import admissions_and_set_off  # noqa: E402


CASES = [
    {
        "label": "TestAdmissionsNetPositive (catala #[test])",
        "admitted": [
            {"item_no": 1, "admitted_aed": "100000.00"},
            {"item_no": 2, "admitted_aed": "50000.00"},
        ],
        "counter": [{"item_no": 1, "proven_aed": "30000.00"}],
        "expected_net": Decimal("120000.00"),
        "expected_signed": Decimal("120000.00"),
        "expected_surplus": Decimal("0.00"),
        "expected_exceeds": False,
    },
    {
        "label": "TestCounterclaimSwallowsAdmissions (clamped at 0)",
        "admitted": [{"item_no": 1, "admitted_aed": "100000.00"}],
        "counter": [{"item_no": 1, "proven_aed": "250000.00"}],
        "expected_net": Decimal("0.00"),
        "expected_signed": Decimal("-150000.00"),
        "expected_surplus": Decimal("150000.00"),
        "expected_exceeds": True,
    },
    {
        "label": "trace-04 — Projeco v Ideacrate (synthetic admissions input)",
        "admitted": [{"item_no": 1, "admitted_aed": "766287.15"}],
        "counter": [{"item_no": 1, "proven_aed": "755786.19"}],
        "expected_net": Decimal("10500.96"),
        "expected_signed": Decimal("10500.96"),
        "expected_surplus": Decimal("0.00"),
        "expected_exceeds": False,
    },
]


def main():
    fails = 0
    for c in CASES:
        out = admissions_and_set_off(c["admitted"], c["counter"])
        ok = (
            out["net_to_claimant_aed"] == c["expected_net"]
            and out["signed_net_aed"] == c["expected_signed"]
            and out["counterclaim_surplus_aed"] == c["expected_surplus"]
            and out["counterclaim_exceeds_admissions"] == c["expected_exceeds"]
        )
        if ok:
            print(f"  PY-OK  {c['label']}: net={out['net_to_claimant_aed']} surplus={out['counterclaim_surplus_aed']}")
        else:
            fails += 1
            print(f"  PY-FAIL {c['label']}: {out}")

    if shutil.which("catala"):
        proc = subprocess.run(
            ["catala", "interpret", "--no-stdlib",
             str(HERE / "adgm_cpr_admissions.catala_en")],
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
