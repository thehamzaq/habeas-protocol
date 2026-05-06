"""Conformance test for caparo_three_stage_test."""

import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from caparo_three_stage_test_eval import caparo_test  # noqa: E402


CASES = [
    {
        "label": "TestCaparoEstablishedCategory (Robinson narrowing — duty by precedent)",
        "facts": {"is_established_category": True,
                  "harm_reasonably_foreseeable": True,
                  "sufficient_proximity": True,
                  "fair_just_reasonable_to_impose": False},
        "expected_owed": True,
        "expected_path": "EstablishedCategory_DutyByPrecedent",
        "expected_first_fail": "Stage_None",
    },
    {
        "label": "TestCaparoNovelAllStagesMet",
        "facts": {"is_established_category": False,
                  "harm_reasonably_foreseeable": True,
                  "sufficient_proximity": True,
                  "fair_just_reasonable_to_impose": True},
        "expected_owed": True,
        "expected_path": "NovelCategory_AllStagesMade",
        "expected_first_fail": "Stage_None",
    },
    {
        "label": "TestCaparoFailsOnPolicyGate (Caparo itself — novel duty in 1990)",
        "facts": {"is_established_category": False,
                  "harm_reasonably_foreseeable": True,
                  "sufficient_proximity": True,
                  "fair_just_reasonable_to_impose": False},
        "expected_owed": False,
        "expected_path": "NovelCategory_FailsAtStage",
        "expected_first_fail": "Stage_3_FairJustReasonable",
    },
    {
        "label": "synthetic — novel, fails at stage 1 (foreseeability)",
        "facts": {"is_established_category": False,
                  "harm_reasonably_foreseeable": False,
                  "sufficient_proximity": True,
                  "fair_just_reasonable_to_impose": True},
        "expected_owed": False,
        "expected_path": "NovelCategory_FailsAtStage",
        "expected_first_fail": "Stage_1_Foreseeability",
    },
    {
        "label": "synthetic — novel, fails at stage 2 (proximity) only",
        "facts": {"is_established_category": False,
                  "harm_reasonably_foreseeable": True,
                  "sufficient_proximity": False,
                  "fair_just_reasonable_to_impose": True},
        "expected_owed": False,
        "expected_path": "NovelCategory_FailsAtStage",
        "expected_first_fail": "Stage_2_Proximity",
    },
]


def main():
    fails = 0
    for c in CASES:
        out = caparo_test(c["facts"])
        if (out["duty_of_care_owed"] == c["expected_owed"]
                and out["path"] == c["expected_path"]
                and out["first_failing_stage"] == c["expected_first_fail"]):
            print(f"  PY-OK  {c['label']}")
        else:
            fails += 1
            print(f"  PY-FAIL {c['label']}: {out}")
    if shutil.which("catala"):
        proc = subprocess.run(
            ["catala", "interpret", "--no-stdlib",
             str(HERE / "caparo_three_stage_test.catala_en")],
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
