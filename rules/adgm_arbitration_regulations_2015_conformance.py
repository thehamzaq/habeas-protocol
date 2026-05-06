"""Conformance test for adgm_arbitration_regulations_2015."""

import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from adgm_arbitration_regulations_2015_eval import (  # noqa: E402
    adgm_recognition,
    adgm_s62_2_adjournment,
)


CASES = [
    {
        "label": "TestADGMRecognitionGranted",
        "grounds": [
            {"ground": "S62_b_ii_PublicPolicy", "court_outcome": "Dismissed", "is_severable": False},
            {"ground": "S62_a_iv_OutsideScope", "court_outcome": "Dismissed", "is_severable": False},
        ],
        "s58_available": False,
        "expected_overall": "RecognitionGranted",
        "expected_recognised": True,
        "expected_status": "ApplicationProperlyMade",
    },
    {
        "label": "TestADGMRecognitionRefused (single full public-policy ground)",
        "grounds": [
            {"ground": "S62_b_ii_PublicPolicy", "court_outcome": "AllowedInFull", "is_severable": False},
            {"ground": "S62_a_iv_OutsideScope", "court_outcome": "Dismissed", "is_severable": False},
        ],
        "s58_available": False,
        "expected_overall": "RecognitionRefused",
        "expected_recognised": False,
        "expected_status": "ApplicationProperlyMade",
    },
    {
        "label": "synthetic — partial-only → granted in part",
        "grounds": [
            {"ground": "S62_a_v_TribunalComposition", "court_outcome": "AllowedInPart", "is_severable": False},
            {"ground": "S62_a_i_Incapacity", "court_outcome": "Dismissed", "is_severable": False},
        ],
        "s58_available": False,
        "expected_overall": "RecognitionGrantedInPart",
        "expected_recognised": True,
        "expected_status": "ApplicationProperlyMade",
    },
    {
        "label": "synthetic — invalid arbitration agreement (s 62(1)(a)(ii)) fully allowed",
        "grounds": [
            {"ground": "S62_a_ii_InvalidAgreement", "court_outcome": "AllowedInFull", "is_severable": False},
        ],
        "s58_available": False,
        "expected_overall": "RecognitionRefused",
        "expected_recognised": False,
        "expected_status": "ApplicationProperlyMade",
    },
    {
        "label": "synthetic — s 62(1)(a)(iv) severability relief on fully-allowed OutsideScope",
        "grounds": [
            {"ground": "S62_a_iv_OutsideScope", "court_outcome": "AllowedInFull", "is_severable": True},
        ],
        "s58_available": False,
        "expected_overall": "RecognitionGrantedInPart",
        "expected_recognised": True,
        "expected_status": "ApplicationProperlyMade",
    },
    {
        "label": "synthetic — s 62(3) bars a fully-allowed public-policy application",
        "grounds": [
            {"ground": "S62_b_ii_PublicPolicy", "court_outcome": "AllowedInFull", "is_severable": False},
        ],
        "s58_available": True,
        "expected_overall": "RecognitionGranted",
        "expected_recognised": True,
        "expected_status": "ApplicationBarredByS62_3",
    },
]


ADJOURNMENT_CASES = [
    {
        "label": "[s 62(2)] no parallel set-aside → adjournment not lawful",
        "inputs": {"setting_aside_pending_at_seat": False,
                   "adjournment_ordered": True,
                   "security_ordered": True},
        "expected_adjourned": False,
        "expected_security": False,
        "expected_lawful": False,
    },
    {
        "label": "[s 62(2)] set-aside pending → adjournment + security pass through",
        "inputs": {"setting_aside_pending_at_seat": True,
                   "adjournment_ordered": True,
                   "security_ordered": True},
        "expected_adjourned": True,
        "expected_security": True,
        "expected_lawful": True,
    },
]


def main():
    fails = 0
    for c in CASES:
        out = adgm_recognition(c["grounds"], c.get("s58_available", False))
        ok = (
            out["overall_disposition"] == c["expected_overall"]
            and out["award_recognised"] == c["expected_recognised"]
            and out["application_status"] == c["expected_status"]
        )
        if ok:
            print(f"  PY-OK  {c['label']}")
        else:
            fails += 1
            print(f"  PY-FAIL {c['label']}: {out}")

    for c in ADJOURNMENT_CASES:
        out = adgm_s62_2_adjournment(c["inputs"])
        ok = (
            out["proceedings_adjourned"] == c["expected_adjourned"]
            and out["security_required"] == c["expected_security"]
            and out["adjournment_engaged_lawfully"] == c["expected_lawful"]
        )
        print(f"  PY-{'OK ' if ok else 'FAIL'} {c['label']}")
        if not ok:
            fails += 1

    if shutil.which("catala"):
        proc = subprocess.run(
            ["catala", "interpret", "--no-stdlib",
             str(HERE / "adgm_arbitration_regulations_2015.catala_en")],
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
