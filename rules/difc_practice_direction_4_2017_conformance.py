"""
Conformance test for difc_practice_direction_4_2017.

Exercises BOTH:
  * `outstanding_arbitration_costs` (Catala mirror — same field names
    and semantics as the OutstandingArbitrationCosts scope), with
    cases drawn from the catala #[test] scopes;
  * `outstanding_obligation` (legacy date-based evaluator used by
    trace-02), against the trace-02 day-count scenarios.

Catala #[test] scope assertions remain the spec-side gate; this file
adds Python-side assertions on the same numerics.
"""

import shutil
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from difc_practice_direction_4_2017_eval import (  # noqa: E402
    outstanding_arbitration_costs,
    quantize_award,
    outstanding_obligation,
)


# Trace-02 case: Oberlin v Ovidiu, ARB-008-2026.
ORDER = {
    "principal_aed": "76785.81",
    "interest_rate_pa": "0.09",
    "order_date": "2026-03-26",
    "deadline_date": "2026-04-09",
}

CASES = [
    {
        "label": "paid on time",
        "status": {"paid": True, "as_of": "2026-04-08", "payment_date": "2026-04-08"},
        "expected_in_breach": False,
        "expected_days": 0,
        "expected_total": Decimal("76785.81"),
    },
    {
        "label": "paid at deadline",
        "status": {"paid": True, "as_of": "2026-04-09", "payment_date": "2026-04-09"},
        "expected_in_breach": False,
        "expected_days": 0,
        "expected_total": Decimal("76785.81"),
    },
    {
        "label": "1 day late",
        "status": {"paid": False, "as_of": "2026-04-10", "payment_date": "2026-04-10"},
        "expected_in_breach": True,
        "expected_days": 15,  # order_date 03-26 to as_of 04-10 = 15 days
    },
    {
        "label": "61 days unpaid",
        "status": {"paid": False, "as_of": "2026-05-26", "payment_date": "2026-05-26"},
        "expected_in_breach": True,
        "expected_days": 61,
    },
    {
        "label": "92 days late",
        "status": {"paid": False, "as_of": "2026-06-26", "payment_date": "2026-06-26"},
        "expected_in_breach": True,
        "expected_days": 92,
        "expected_total": Decimal("78527.69"),
    },
]


# Catala-mirror cases (lifted from the .catala_en #[test] scopes).
CATALA_MIRROR_CASES = [
    {
        "label": "[catala-mirror] PaidOnTime — 14 days = deadline → not in breach",
        "claim": {
            "reasonable_costs_aed": "95982.26",
            "discount_rate": "0.80",
            "deadline_days": "14.0",
            "days_paid_after_order": "14.0",
            "simple_interest_rate": "0.09",
        },
        "expected_in_breach": False,
        "expected_interest": Decimal("0"),
    },
    {
        "label": "[catala-mirror] Unpaid61Days — in breach with 47 days accrued",
        "claim": {
            "reasonable_costs_aed": "95982.26",
            "discount_rate": "0.80",
            "deadline_days": "14.0",
            "days_paid_after_order": "61.0",
            "simple_interest_rate": "0.09",
        },
        "expected_in_breach": True,
        "expected_days_accrued": Decimal("47.0"),
        # 76785.808 × 0.09 × 47/365 = 889.872... full precision
        "expected_principal_quantized": Decimal("76785.81"),
    },
    {
        "label": "[catala-mirror] EIBOR pre-effective-date regime (3.5% rate)",
        "claim": {
            "reasonable_costs_aed": "95982.26",
            "discount_rate": "0.80",
            "deadline_days": "14.0",
            "days_paid_after_order": "61.0",
            "simple_interest_rate": "0.035",
        },
        "expected_in_breach": True,
        "expected_days_accrued": Decimal("47.0"),
    },
]


def main():
    fails = 0

    # Catala-mirror tests on outstanding_arbitration_costs.
    for case in CATALA_MIRROR_CASES:
        out = outstanding_arbitration_costs(case["claim"])
        ok = out["in_breach"] == case["expected_in_breach"]
        if "expected_interest" in case:
            ok = ok and out["interest_aed"] == case["expected_interest"]
        if "expected_days_accrued" in case:
            ok = ok and out["days_accrued"] == case["expected_days_accrued"]
        if "expected_principal_quantized" in case:
            q = quantize_award(out)
            ok = ok and q["principal_aed"] == case["expected_principal_quantized"]
        if ok:
            print(f"  PY-OK  {case['label']}")
        else:
            fails += 1
            print(f"  PY-FAIL {case['label']}: {out}")

    # Legacy trace-02 date-based tests.
    for case in CASES:
        out = outstanding_obligation(ORDER, case["status"])
        ok = (
            out["in_breach"] == case["expected_in_breach"]
            and out["days_accrued"] == case["expected_days"]
        )
        if "expected_total" in case:
            ok = ok and out["total_owed_aed"] == case["expected_total"]
        if ok:
            print(f"  PY-OK  [date-based] {case['label']:<22} days={out['days_accrued']:>3} "
                  f"total={out['total_owed_aed']}")
        else:
            fails += 1
            print(f"  PY-FAIL [date-based] {case['label']}: {out}")

    catala = shutil.which("catala")
    if not catala:
        print("  CATALA SKIP")
    else:
        rule = HERE / "difc_practice_direction_4_2017.catala_en"
        proc = subprocess.run(
            [catala, "interpret", "--no-stdlib", str(rule)],
            capture_output=True, text=True, timeout=30,
        )
        if proc.returncode != 0:
            fails += 1
            print(f"  CATALA-FAIL\n{proc.stderr}")
        else:
            print("  CATALA-OK  (#[test] scopes pass)")

    if fails:
        print(f"\nFAIL — {fails}")
        sys.exit(1)
    print("\nOK")


if __name__ == "__main__":
    main()
