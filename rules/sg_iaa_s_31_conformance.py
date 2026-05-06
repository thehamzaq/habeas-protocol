"""Conformance test for sg_iaa_s_31."""

import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from sg_iaa_s_31_eval import (  # noqa: E402
    iaa_s31_disposition,
    iaa_s31_5_adjournment,
    iaa_s31_2_c_infra_petita,
)


# Trace-06: SIC/OA 9/2025, GNC Holdings v ONI Global, [2025] SGHC(I) 25.
# Statute references corrected to match the IAA s 31 letter-for-letter
# alignment (audit 2026-05-05): (b) is invalid agreement, (c) is natural
# justice, (d) is outside scope, (e) is tribunal composition.
TRACE_06_GROUNDS = [
    {"id": "G1", "statute": "IAA s 31(4)(b)",
     "label": "public policy",
     "court_outcome": "Dismissed",
     "is_severable": False},
    {"id": "G2", "statute": "IAA s 31(2)(c)",
     "label": "natural-justice — DKT v DKU",
     "court_outcome": "Dismissed",
     "is_severable": False},
    {"id": "G3", "statute": "IAA s 31(2)(d)",
     "label": "award beyond scope of submission to arbitration",
     "court_outcome": "Dismissed",
     "is_severable": False},
    {"id": "G4", "statute": "IAA s 31(2)(c)/(d)",
     "label": "natural-justice + outside-scope on Order 3 specifics",
     "court_outcome": "AllowedInPart",
     "is_severable": True,
     "excised_paragraphs": ["Order 3(d)(ii)", "Order 3(d)(iii)", "Order 3(f)"],
     "enforced_paragraphs": ["Order 3(a)", "Order 3(b)", "Order 3(c)",
                              "Order 3(d)(i)", "Order 3(e)",
                              "Order 3(g)", "Order 3(h)"]},
]

CASES = [
    {
        "label": "trace-06 — GNC Holdings v ONI Global",
        "grounds": TRACE_06_GROUNDS,
        "expected_disposition": "ApplicationAllowedInPart",
        "expected_excised": 3,
        "expected_award_enforced": True,
    },
    {
        "label": "synthetic — full set-aside",
        "grounds": [
            {"id": "G1", "statute": "s 31(2)(a)", "label": "x",
             "court_outcome": "AllowedInFull"},
        ],
        "expected_disposition": "AwardSetAside",
        "expected_excised": 0,
        "expected_award_enforced": False,
    },
    {
        "label": "synthetic — full dismissal",
        "grounds": [
            {"id": "G1", "statute": "s 31(2)(a)", "label": "x",
             "court_outcome": "Dismissed"},
            {"id": "G2", "statute": "s 31(2)(b)", "label": "y",
             "court_outcome": "Dismissed"},
        ],
        "expected_disposition": "ApplicationDismissedEntirely",
        "expected_excised": 0,
        "expected_award_enforced": True,
    },
    {
        "label": "synthetic — s 31(3) severability relief on fully-allowed OutsideScope",
        "grounds": [
            {"ground": "S31_2_d_OutsideScope",
             "court_outcome": "AllowedInFull",
             "is_severable": True},
        ],
        "expected_disposition": "ApplicationAllowedInPart",
        "expected_excised": 0,
        "expected_award_enforced": True,
    },
    {
        "label": "synthetic — fully-allowed NaturalJustice never qualifies for severability",
        "grounds": [
            {"ground": "S31_2_c_NaturalJustice",
             "court_outcome": "AllowedInFull",
             "is_severable": True},  # is_severable does not apply to (c)
        ],
        "expected_disposition": "AwardSetAside",
        "expected_excised": 0,
        "expected_award_enforced": False,
    },
]


ADJOURNMENT_CASES = [
    {
        "label": "[s 31(5)] no parallel set-aside → adjournment not lawful",
        "inputs": {"setting_aside_pending_at_seat": False,
                   "adjournment_ordered": True,
                   "security_ordered": True},
        "expected_adjourned": False,
        "expected_security": False,
        "expected_lawful": False,
    },
    {
        "label": "[s 31(5)] set-aside pending → adjournment + security pass through",
        "inputs": {"setting_aside_pending_at_seat": True,
                   "adjournment_ordered": True,
                   "security_ordered": True},
        "expected_adjourned": True,
        "expected_security": True,
        "expected_lawful": True,
    },
]

INFRA_PETITA_CASES = [
    {
        "label": "[s 31(2)(c) DKT] all 4 conditions + court AllowedInFull → consistent",
        "conditions": {"point_properly_before_tribunal": True,
                       "point_essential_to_dispute": True,
                       "tribunal_completely_failed_to_consider": True,
                       "prejudice_demonstrated": True},
        "court_outcome": "AllowedInFull",
        "expected_succeeds": True,
        "expected_consistent": True,
    },
    {
        "label": "[s 31(2)(c) DKT] DKT fails + court Dismissed → consistent",
        "conditions": {"point_properly_before_tribunal": True,
                       "point_essential_to_dispute": False,
                       "tribunal_completely_failed_to_consider": False,
                       "prejudice_demonstrated": False},
        "court_outcome": "Dismissed",
        "expected_succeeds": False,
        "expected_consistent": True,
    },
    {
        "label": "[s 31(2)(c) DKT] DKT fails + court AllowedInFull → inconsistent",
        "conditions": {"point_properly_before_tribunal": True,
                       "point_essential_to_dispute": False,
                       "tribunal_completely_failed_to_consider": True,
                       "prejudice_demonstrated": True},
        "court_outcome": "AllowedInFull",
        "expected_succeeds": False,
        "expected_consistent": False,
    },
]


def main():
    fails = 0
    for c in CASES:
        out = iaa_s31_disposition(c["grounds"])
        ok = (
            out["application_disposition"] == c["expected_disposition"]
            and out["n_paras_excised"] == c["expected_excised"]
            and out["award_enforced"] == c["expected_award_enforced"]
        )
        if ok:
            print(f"  PY-OK  {c['label']}")
        else:
            fails += 1
            print(f"  PY-FAIL {c['label']}: {out}")

    for c in ADJOURNMENT_CASES:
        out = iaa_s31_5_adjournment(c["inputs"])
        ok = (
            out["proceedings_adjourned"] == c["expected_adjourned"]
            and out["security_required"] == c["expected_security"]
            and out["adjournment_engaged_lawfully"] == c["expected_lawful"]
        )
        print(f"  PY-{'OK ' if ok else 'FAIL'} {c['label']}")
        if not ok:
            fails += 1

    for c in INFRA_PETITA_CASES:
        out = iaa_s31_2_c_infra_petita(c["conditions"], c["court_outcome"])
        ok = (
            out["dkt_challenge_succeeds"] == c["expected_succeeds"]
            and out["dkt_analysis_consistent"] == c["expected_consistent"]
        )
        print(f"  PY-{'OK ' if ok else 'FAIL'} {c['label']}")
        if not ok:
            fails += 1

    if shutil.which("catala"):
        proc = subprocess.run(
            ["catala", "interpret", "--no-stdlib",
             str(HERE / "sg_iaa_s_31.catala_en")],
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
