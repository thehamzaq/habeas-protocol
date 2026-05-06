"""Conformance test for uae_civil_code_art_390."""

import shutil
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from uae_civil_code_art_390_eval import article_390_cap  # noqa: E402


CASES = [
    {
        "label": "trace-04 — Projeco v Ideacrate (contract cap engages, 390(2) refused)",
        "claim": {
            "contract_value_aed": "6085211.90",
            "contract_cap_rate": "0.10",
            "contract_caps_ld": True,
            "uncapped_amount_aed": "9700000",
            "court_asked_to_vary_under_390_2": True,
            "court_finds_grossly_disproportionate": False,
        },
        "expected_after_cap": Decimal("608521.190"),
        "expected_awarded": Decimal("608521.190"),
        "expected_contract_capped": True,
        "expected_390_2_varied": False,
    },
    {
        "label": "no contract cap, no 390(2) — agreed sum stands",
        "claim": {
            "contract_value_aed": "100000",
            "contract_cap_rate": "0.10",
            "contract_caps_ld": False,
            "uncapped_amount_aed": "5000",
            "court_asked_to_vary_under_390_2": False,
            "court_finds_grossly_disproportionate": False,
        },
        "expected_after_cap": Decimal("5000"),
        "expected_awarded": Decimal("5000"),
        "expected_contract_capped": False,
        "expected_390_2_varied": False,
    },
    {
        "label": "contract caps but uncapped < cap → no contractual reduction",
        "claim": {
            "contract_value_aed": "100000",
            "contract_cap_rate": "0.10",
            "contract_caps_ld": True,
            "uncapped_amount_aed": "5000",
            "court_asked_to_vary_under_390_2": False,
            "court_finds_grossly_disproportionate": False,
        },
        "expected_after_cap": Decimal("5000"),
        "expected_awarded": Decimal("5000"),
        "expected_contract_capped": False,
        "expected_390_2_varied": False,
    },
    {
        "label": "synthetic — both layers engage (hypothetical)",
        "claim": {
            "contract_value_aed": "6085211.90",
            "contract_cap_rate": "0.10",
            "contract_caps_ld": True,
            "uncapped_amount_aed": "9700000",
            "court_asked_to_vary_under_390_2": True,
            "court_finds_grossly_disproportionate": True,
        },
        "expected_after_cap": Decimal("608521.190"),
        "expected_awarded": Decimal("608521.190"),
        "expected_contract_capped": True,
        "expected_390_2_varied": True,
    },
]


def main():
    fails = 0
    for c in CASES:
        out = article_390_cap(c["claim"])
        ok = (
            out["awarded_aed"] == c["expected_awarded"]
            and out["was_contract_capped"] == c["expected_contract_capped"]
            and out["was_390_2_varied"] == c["expected_390_2_varied"]
        )
        if ok:
            print(f"  PY-OK  {c['label']}")
        else:
            fails += 1
            print(f"  PY-FAIL {c['label']}: expected awarded={c['expected_awarded']} "
                  f"contract_capped={c['expected_contract_capped']} "
                  f"390_2_varied={c['expected_390_2_varied']}, got {out}")

    if shutil.which("catala"):
        proc = subprocess.run(
            ["catala", "interpret", "--no-stdlib",
             str(HERE / "uae_civil_code_art_390.catala_en")],
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
