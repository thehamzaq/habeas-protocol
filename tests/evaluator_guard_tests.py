#!/usr/bin/env python3
"""Guard tests for the Python reference evaluators.

Two jobs the conformance scripts did not do:

  1. Hostile inputs must be rejected, not coerced. The string "false"
     used to count as true; NaN and negative sums flowed into awards.
  2. Boundary and value assertions that kill the mutants a mutation
     pass found alive on 2026-10-05 (day-count basis, award value,
     third Ladd prong, zero-net boundary, uncapped contract cap).

Run: python3 tests/evaluator_guard_tests.py   (exit 1 on any failure)
"""

import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rules"))

from adgm_arbitration_regulations_2015_eval import adgm_recognition  # noqa: E402
from adgm_cpr_admissions_eval import admissions_and_set_off  # noqa: E402
from adgm_cpr_summary_judgment_eval import summary_judgment_test  # noqa: E402
from caparo_three_stage_test_eval import caparo_test  # noqa: E402
from difc_practice_direction_4_2017_eval import (  # noqa: E402
    outstanding_arbitration_costs, outstanding_obligation, quantize_award)
from difc_rdc_38_19_indemnity_eval import indemnity_basis_review  # noqa: E402
from difc_rdc_part_38_eval import assess_standard_basis  # noqa: E402
from difc_third_party_disclosure_eval import third_party_disclosure_gates  # noqa: E402
from ladd_v_marshall_eval import ladd_marshall_test  # noqa: E402
from sg_iaa_s_31_eval import iaa_s31_disposition  # noqa: E402
from uae_civil_code_art_390_eval import article_390_cap  # noqa: E402

FAILS = []


def check(label, condition):
    print(f"  {'ok  ' if condition else 'FAIL'} {label}")
    if not condition:
        FAILS.append(label)


def rejects(label, fn, *args):
    try:
        result = fn(*args)
    except ValueError:
        check(f"rejects {label}", True)
    else:
        check(f"rejects {label} (returned {result!r})", False)


PD4 = {"reasonable_costs_aed": "95982.26", "discount_rate": "0.80",
       "deadline_days": "14", "days_paid_after_order": "61",
       "simple_interest_rate": "0.09"}
CAPARO = {"is_established_category": False, "harm_reasonably_foreseeable": True,
          "sufficient_proximity": True, "fair_just_reasonable_to_impose": True}
ART390 = {"contract_value_aed": "1000", "contract_cap_rate": "0.1",
          "uncapped_amount_aed": "500", "contract_caps_ld": True,
          "court_asked_to_vary_under_390_2": False,
          "court_finds_grossly_disproportionate": False}
COSTS = {"hours_worked": "24", "hourly_rate_aed": "1500",
         "reasonable_disbursements_aed": "250"}


def prongs(a, b, c):
    return [{"label": x, "satisfied": v, "court_finding": ""}
            for x, v in (("a", a), ("b", b), ("c", c))]


def main():
    print("-- hostile inputs are rejected")
    rejects("caparo string 'false'", caparo_test,
            {**CAPARO, "is_established_category": "false"})
    rejects("summary judgment string limbs", summary_judgment_test,
            {"no_realistic_prospect": "false", "no_compelling_reason": "false"})
    rejects("costs negative hours", assess_standard_basis,
            {**COSTS, "hours_worked": "-24"})
    rejects("costs NaN rate", assess_standard_basis,
            {**COSTS, "hourly_rate_aed": "NaN"})
    rejects("costs absurdly large disbursements", assess_standard_basis,
            {**COSTS, "reasonable_disbursements_aed": "1e400"})
    rejects("pd4 discount above 1", outstanding_arbitration_costs,
            {**PD4, "discount_rate": "1.5"})
    rejects("pd4 negative interest rate", outstanding_arbitration_costs,
            {**PD4, "simple_interest_rate": "-1"})
    rejects("pd4 negative deadline", outstanding_arbitration_costs,
            {**PD4, "deadline_days": "-100"})
    rejects("pd4 deadline before order date", outstanding_obligation,
            {"principal_aed": "100", "interest_rate_pa": "0.09",
             "order_date": "2026-03-26", "deadline_date": "2026-03-01"},
            {"paid": True, "as_of": "2026-03-10", "payment_date": "2026-03-10"})
    rejects("art 390 cap rate above 1", article_390_cap,
            {**ART390, "contract_cap_rate": "5"})
    rejects("art 390 negative uncapped sum", article_390_cap,
            {**ART390, "uncapped_amount_aed": "-500"})
    rejects("admissions negative item", admissions_and_set_off,
            [{"admitted_aed": "-5"}], [])
    rejects("ladd with no prongs", ladd_marshall_test, [])
    rejects("ladd with one prong", ladd_marshall_test, prongs(True, True, True)[:1])
    rejects("ladd string 'False'", ladd_marshall_test, prongs(True, True, "False"))
    rejects("sg unknown outcome", iaa_s31_disposition,
            [{"ground": "S31_2_d_OutsideScope", "court_outcome": "allowedinfull"}])
    rejects("adgm misspelt outcome", adgm_recognition,
            [{"ground": "S62_a_iv_OutsideScope", "court_outcome": "AllowedInfull"}])
    rejects("third-party contradictory finding", third_party_disclosure_gates,
            [{"element": "NPE_WrongEstablished", "made_out": True},
             {"element": "NPE_WrongEstablished", "made_out": False}], [], [])
    rejects("indemnity unknown finding", indemnity_basis_review,
            {"claimed_aed": "1000", "objections": [
                {"label": "x", "names_specific_line_item": True,
                 "factual_finding": "maybe"}]})

    print("-- values and boundaries")
    award = quantize_award(outstanding_arbitration_costs(PD4))
    check("pd4 61 days from order date = 1154.94 on a 365-day year",
          award["interest_aed"] == Decimal("1154.94"))
    unpaid = outstanding_obligation(
        {"principal_aed": "76785.81", "interest_rate_pa": "0.09",
         "order_date": "2026-03-26", "deadline_date": "2026-04-09"},
        {"paid": False, "as_of": "2026-04-10"})
    check("pd4 unpaid status needs no payment_date; 15 days accrue",
          unpaid["days_accrued"] == 15
          and unpaid["interest_accrued_aed"] == Decimal("284.00"))

    review = indemnity_basis_review({"claimed_aed": "1000", "objections": [
        {"label": "o1", "names_specific_line_item": True,
         "factual_finding": "accepted_with_named_amount",
         "named_amount_aed": "300"}]})
    check("indemnity deterministic award = claim minus named reduction",
          review["deterministic_award_aed"] == Decimal("700.00"))

    last = ladd_marshall_test(prongs(True, True, False))
    check("ladd fails on prong (c) alone",
          last["new_evidence_admissible"] is False
          and last["short_circuited_at"] == 3)
    check("ladd admits when all three are satisfied",
          ladd_marshall_test(prongs(True, True, True))["new_evidence_admissible"])

    level = admissions_and_set_off([{"admitted_aed": "100"}], [{"proven_aed": "100"}])
    check("admissions equal to counterclaim: no excess, nothing owed",
          level["counterclaim_exceeds_admissions"] is False
          and level["net_to_claimant_aed"] == 0
          and level["counterclaim_surplus_aed"] == 0)

    uncapped = article_390_cap({**ART390, "contract_caps_ld": False})
    check("art 390 reports no contract cap when the contract has none",
          uncapped["contract_cap_aed"] == 0 and uncapped["awarded_aed"] == Decimal("500"))
    varied = article_390_cap({**ART390, "court_asked_to_vary_under_390_2": True,
                              "court_finds_grossly_disproportionate": True})
    check("art 390 marks the sum as not final once 390(2) engages",
          varied["was_390_2_varied"] is True and varied["awarded_is_final"] is False)
    check("art 390 sum is final without a 390(2) variation",
          article_390_cap(ART390)["awarded_is_final"] is True)

    novel = caparo_test(CAPARO)
    check("caparo novel category counts three satisfied stages",
          novel["n_stages_satisfied"] == 3 and novel["duty_of_care_owed"] is True)
    check("caparo established category reports the -1 sentinel",
          caparo_test({**CAPARO, "is_established_category": True})["n_stages_satisfied"] == -1)

    sg = iaa_s31_disposition([{"ground": "S31_2_d_OutsideScope",
                               "court_outcome": "AllowedInFull", "is_severable": False}])
    check("sg non-severable outside-scope ground is not a partial allowance",
          sg["application_disposition"] == "AwardSetAside")

    print()
    if FAILS:
        print(f"FAIL: {len(FAILS)} guard test(s)")
        for f in FAILS:
            print(f"  - {f}")
        sys.exit(1)
    print("evaluator guard tests: all passed")


if __name__ == "__main__":
    main()
