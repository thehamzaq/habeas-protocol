"""Conformance test for ladd_v_marshall."""

import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from ladd_v_marshall_eval import ladd_marshall_test  # noqa: E402


CASES = [
    {
        "label": "trace-05 — Xetech v Pulsar (prong (a) fails, short-circuit)",
        "prongs": [
            {"label": "could_not_have_been_obtained_with_diligence",
             "satisfied": False, "court_finding": "available pre-trial"},
            {"label": "would_have_important_influence",
             "satisfied": True, "court_finding": "n/a — short-circuited"},
            {"label": "presumably_to_be_believed",
             "satisfied": True, "court_finding": "n/a — short-circuited"},
        ],
        "expected_admissible": False,
        "expected_first_fail": "could_not_have_been_obtained_with_diligence",
        "expected_short_circuit": 1,
    },
    {
        "label": "synthetic — all three pass",
        "prongs": [
            {"label": "diligence", "satisfied": True, "court_finding": "ok"},
            {"label": "influence", "satisfied": True, "court_finding": "ok"},
            {"label": "credible", "satisfied": True, "court_finding": "ok"},
        ],
        "expected_admissible": True,
        "expected_first_fail": None,
        "expected_short_circuit": None,
    },
    {
        "label": "synthetic — prong (b) fails",
        "prongs": [
            {"label": "diligence", "satisfied": True, "court_finding": "ok"},
            {"label": "influence", "satisfied": False, "court_finding": "marginal"},
            {"label": "credible", "satisfied": True, "court_finding": "ok"},
        ],
        "expected_admissible": False,
        "expected_first_fail": "influence",
        "expected_short_circuit": 2,
    },
]


def main():
    fails = 0
    for c in CASES:
        out = ladd_marshall_test(c["prongs"])
        ok = (
            out["new_evidence_admissible"] == c["expected_admissible"]
            and out["first_failing_prong"] == c["expected_first_fail"]
            and out["short_circuited_at"] == c["expected_short_circuit"]
        )
        if ok:
            print(f"  PY-OK  {c['label']}")
        else:
            fails += 1
            print(f"  PY-FAIL {c['label']}: {out}")

    if shutil.which("catala"):
        proc = subprocess.run(
            ["catala", "interpret", "--no-stdlib",
             str(HERE / "ladd_v_marshall.catala_en")],
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
