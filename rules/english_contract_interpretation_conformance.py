"""Conformance test for english_contract_interpretation.

Exercises BOTH the Catala-mirror `wood_v_capita` (the rule-library
scope) AND the legacy `clause_alignment` (used by trace-05). The
Catala-mirror cases prove that the WoodVCapita scope agrees with its
Python reference on the same input shape post-2026-05-05 stage-2
relaxation (MatrixSignal trichotomy).
"""

import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from english_contract_interpretation_eval import (  # noqa: E402
    wood_v_capita,
    clause_alignment,
)


WV_CASES = [
    {
        "label": "wood_v_capita: plain meaning carries (trace-05 facts)",
        "evidence": {
            "clauses_unambiguously_aligned": True,
            "common_sense_supports_one_reading": True,
            "factual_matrix_signal": "Supports",
        },
        "expected_limb": "PlainMeaningCarries",
    },
    {
        "label": "wood_v_capita: BCS carries on common-sense + matrix supports",
        "evidence": {
            "clauses_unambiguously_aligned": False,
            "common_sense_supports_one_reading": True,
            "factual_matrix_signal": "Supports",
        },
        "expected_limb": "BusinessCommonSenseCarries",
    },
    {
        "label": "wood_v_capita: BCS carries on common-sense alone (matrix silent)",
        "evidence": {
            "clauses_unambiguously_aligned": False,
            "common_sense_supports_one_reading": True,
            "factual_matrix_signal": "Silent",
        },
        "expected_limb": "BusinessCommonSenseCarries",
    },
    {
        "label": "wood_v_capita: matrix contradicts → ambiguous (cs alone insufficient)",
        "evidence": {
            "clauses_unambiguously_aligned": False,
            "common_sense_supports_one_reading": True,
            "factual_matrix_signal": "Contradicts",
        },
        "expected_limb": "GenuinelyAmbiguous",
    },
    {
        "label": "wood_v_capita: BCS carries on matrix alone (cs silent)",
        "evidence": {
            "clauses_unambiguously_aligned": False,
            "common_sense_supports_one_reading": False,
            "factual_matrix_signal": "Supports",
        },
        "expected_limb": "BusinessCommonSenseCarries",
    },
    {
        "label": "wood_v_capita: ambiguous (cs=false, matrix=Silent)",
        "evidence": {
            "clauses_unambiguously_aligned": False,
            "common_sense_supports_one_reading": False,
            "factual_matrix_signal": "Silent",
        },
        "expected_limb": "GenuinelyAmbiguous",
    },
]


CA_CASES = [
    {
        "label": "trace-05 — Xetech v Pulsar (3/3 align)",
        "clauses": [
            {"clause_id": "AA-2(b)", "court_para_ref": "para 18",
             "points_to_payment_before_transfer": True},
            {"clause_id": "AA-7", "court_para_ref": "para 19",
             "points_to_payment_before_transfer": True},
            {"clause_id": "AA-10", "court_para_ref": "para 20",
             "points_to_payment_before_transfer": True},
        ],
        "expected_aligned": True,
        "expected_misaligned": [],
    },
    {
        "label": "synthetic — one clause dissents",
        "clauses": [
            {"clause_id": "X-1", "points_to_payment_before_transfer": True},
            {"clause_id": "X-2", "points_to_payment_before_transfer": False},
            {"clause_id": "X-3", "points_to_payment_before_transfer": True},
        ],
        "expected_aligned": False,
        "expected_misaligned": ["X-2"],
    },
]


def main():
    fails = 0

    # Catala-mirror tests.
    for c in WV_CASES:
        out = wood_v_capita(c["evidence"])
        if out["limb"] == c["expected_limb"]:
            print(f"  PY-OK  {c['label']}: limb={out['limb']}")
        else:
            fails += 1
            print(f"  PY-FAIL {c['label']}: {out}")

    # Legacy clause-alignment tests.
    for c in CA_CASES:
        out = clause_alignment(c["clauses"])
        ok = (
            out["clauses_aligned"] == c["expected_aligned"]
            and out["misaligned_clauses"] == c["expected_misaligned"]
        )
        if ok:
            print(f"  PY-OK  {c['label']}")
        else:
            fails += 1
            print(f"  PY-FAIL {c['label']}: {out}")

    if shutil.which("catala"):
        proc = subprocess.run(
            ["catala", "interpret", "--no-stdlib",
             str(HERE / "english_contract_interpretation.catala_en")],
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
