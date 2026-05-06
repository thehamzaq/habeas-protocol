"""Conformance test for difc_third_party_disclosure.

Exercises BOTH the Catala-mirroring `third_party_disclosure_gates`
function AND the legacy trace-07 narrative `third_party_disclosure`
function (which has a different shape and is also exercised by
trace-07's evaluator). The Catala-mirror cases prove that the
rule-library scope agrees with its Python reference on the same
input shape.
"""

import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from difc_third_party_disclosure_eval import (  # noqa: E402
    third_party_disclosure_gates,
    third_party_disclosure,
)


# ---------------------------------------------------------------------
# Catala-mirroring cases (use enum-name strings for `element` / `rdc_condition`).
# ---------------------------------------------------------------------

TRACE_07_NPH_GATES = [
    {"element": "NPE_WrongEstablished", "made_out": True},
    {"element": "NPE_RespondentMixedUp", "made_out": True},
    {"element": "NPE_PossessesInformation", "made_out": True},
    {"element": "NPE_DisclosureNecessaryInInterestsOfJustice", "made_out": True},
]
TRACE_07_BT_GATES = [
    {"element": "BTE_TracingClaimAsserted", "made_out": True},
    {"element": "BTE_HoldsTraceableProceeds", "made_out": True},
    {"element": "BTE_DisclosureNecessaryForTracing", "made_out": True},
]
TRACE_07_RDC_GATES = [
    {"rdc_condition": "RDC_LikelyToSupportOrAffect", "made_out": True},
    {"rdc_condition": "RDC_NecessaryToDisposeOrSaveCosts", "made_out": True},
]
RDC_FAILS_GATES = [
    {"rdc_condition": "RDC_LikelyToSupportOrAffect", "made_out": True},
    {"rdc_condition": "RDC_NecessaryToDisposeOrSaveCosts", "made_out": False},
]


GATE_CASES = [
    {
        "label": "trace-07 — Techteryx v IG (all gates satisfied)",
        "args": (TRACE_07_NPH_GATES, TRACE_07_BT_GATES, TRACE_07_RDC_GATES),
        "expected_grantable": True,
    },
    {
        "label": "synthetic — RDC 28.52 fails (jurisdiction)",
        "args": (TRACE_07_NPH_GATES, TRACE_07_BT_GATES, RDC_FAILS_GATES),
        "expected_grantable": False,
    },
    {
        "label": "synthetic — empty NPh list rejects (vacuous-satisfaction guard)",
        "args": ([], TRACE_07_BT_GATES, TRACE_07_RDC_GATES),
        "expected_grantable": False,
    },
    {
        "label": "synthetic — duplicate NPh element pleadings still pass",
        "args": (TRACE_07_NPH_GATES + [TRACE_07_NPH_GATES[0]],
                 TRACE_07_BT_GATES, TRACE_07_RDC_GATES),
        "expected_grantable": True,
    },
    {
        "label": "synthetic — over-pleaded NPh (5 entries with all 4 distinct made out)",
        "args": (TRACE_07_NPH_GATES + [
            {"element": "NPE_WrongEstablished", "made_out": True}
        ], TRACE_07_BT_GATES, TRACE_07_RDC_GATES),
        "expected_grantable": True,
    },
    {
        "label": "synthetic — 4 entries all of one element rejects (no distinct coverage)",
        "args": ([{"element": "NPE_WrongEstablished", "made_out": True}] * 4,
                 TRACE_07_BT_GATES, TRACE_07_RDC_GATES),
        "expected_grantable": False,
    },
]


# ---------------------------------------------------------------------
# Legacy narrative cases (trace-07 inputs with `label` / `satisfied`).
# ---------------------------------------------------------------------

NARRATIVE_NPH = [
    {"label": "wrongdoing_arguably_committed", "satisfied": True},
    {"label": "respondent_mixed_up_in_wrongdoing", "satisfied": True},
    {"label": "respondent_can_provide_information", "satisfied": True},
    {"label": "necessary_to_enable_action", "satisfied": True},
]
NARRATIVE_BT = [
    {"label": "real_prospect_of_tracing", "satisfied": True},
    {"label": "respondent_innocent_party_with_information", "satisfied": True},
    {"label": "balance_of_convenience_favours_disclosure", "satisfied": True},
]
NARRATIVE_RDC = [
    {"label": "documents_relevant_to_pleaded_issue", "satisfied": True},
    {"label": "third_party_in_jurisdiction_of_court", "satisfied": True},
]
RESPONDENTS = [
    {"entity": "IG Limited"},
    {"entity": "IG Bermuda"},
    {"entity": "IG Singapore"},
    {"entity": "IG Hong Kong"},
]
WINDOWS = {"information_confirmation_days": 14, "documents_production_days": 21}


NARRATIVE_CASES = [
    {
        "label": "[narrative] trace-07 — Techteryx v IG (all gates satisfied)",
        "args": (NARRATIVE_NPH, NARRATIVE_BT, NARRATIVE_RDC, RESPONDENTS, WINDOWS),
        "expected_order": True,
        "expected_n_resp": 4,
        "expected_n_opposing": 0,
    },
    {
        "label": "[narrative] RDC 28.52 fails (jurisdiction)",
        "args": (NARRATIVE_NPH, NARRATIVE_BT,
                 [{"label": "documents_relevant", "satisfied": True},
                  {"label": "third_party_in_jurisdiction", "satisfied": False}],
                 RESPONDENTS, WINDOWS),
        "expected_order": False,
        "expected_n_resp": 4,
        "expected_n_opposing": 0,
    },
]


def main():
    fails = 0

    # Catala-mirroring tests.
    for c in GATE_CASES:
        out = third_party_disclosure_gates(*c["args"])
        if out["order_grantable"] == c["expected_grantable"]:
            print(f"  PY-OK  {c['label']}: order_grantable={out['order_grantable']}")
        else:
            fails += 1
            print(f"  PY-FAIL {c['label']}: {out}")

    # Legacy narrative tests.
    for c in NARRATIVE_CASES:
        out = third_party_disclosure(*c["args"])
        ok = (
            out["order_granted"] == c["expected_order"]
            and out["n_respondents"] == c["expected_n_resp"]
            and out["n_respondents_opposing_substance"] == c["expected_n_opposing"]
        )
        if ok:
            print(f"  PY-OK  {c['label']}: order_granted={out['order_granted']}")
        else:
            fails += 1
            print(f"  PY-FAIL {c['label']}: {out}")

    if shutil.which("catala"):
        proc = subprocess.run(
            ["catala", "interpret", "--no-stdlib",
             str(HERE / "difc_third_party_disclosure.catala_en")],
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
