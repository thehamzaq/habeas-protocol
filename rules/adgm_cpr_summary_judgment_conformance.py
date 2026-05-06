"""Conformance test for adgm_cpr_summary_judgment."""

import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from adgm_cpr_summary_judgment_eval import summary_judgment_test  # noqa: E402


CASES = [
    {
        "label": "TestSummaryJudgmentBothLimbs (catala #[test])",
        "application": {"no_realistic_prospect": True,
                        "no_compelling_reason": True},
        "expected_granted": True,
    },
    {
        "label": "TestSummaryJudgmentRefusedOnCompellingReason",
        "application": {"no_realistic_prospect": True,
                        "no_compelling_reason": False},
        "expected_granted": False,
    },
    {
        "label": "no realistic prospect not made out",
        "application": {"no_realistic_prospect": False,
                        "no_compelling_reason": True},
        "expected_granted": False,
    },
]


def main():
    fails = 0
    for c in CASES:
        out = summary_judgment_test(c["application"])
        if out["summary_judgment_granted"] == c["expected_granted"]:
            print(f"  PY-OK  {c['label']}")
        else:
            fails += 1
            print(f"  PY-FAIL {c['label']}: {out}")
    if shutil.which("catala"):
        proc = subprocess.run(
            ["catala", "interpret", "--no-stdlib",
             str(HERE / "adgm_cpr_summary_judgment.catala_en")],
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
