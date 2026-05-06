#!/usr/bin/env python3
"""Property tests for the rule library.

`#[test]` scopes inside each `rules/*.catala_en` only check single fact
patterns. These property tests run each rule module under random inputs
and assert invariants — the kinds of bugs `#[test]` scopes can't catch:
non-monotonic outputs, off-by-one boundaries, sign errors, the wrong
short-circuit on a conjunctive test.

Each rule module is invoked through `catala interpret -F json --input=-`
exactly the way the API runs it, so the property tests double as
contract tests for the API path.

Run:
    eval $(opam env --switch=catala)
    python3 tests/property_tests.py
"""
from __future__ import annotations

import json
import os
import random
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(HERE + "/..")
RULES = ROOT + "/rules"

random.seed(20260501)
N_TRIALS = 50  # per property; bumps to 200 in CI if HABEAS_PROPERTY_TRIALS=200

CATALA_BIN = shutil.which("catala")
if not CATALA_BIN:
    candidate = os.path.expanduser("~/.opam/catala/bin/catala")
    CATALA_BIN = candidate if os.path.exists(candidate) else None
if not CATALA_BIN:
    sys.exit("catala not on PATH. eval $(opam env --switch=catala) first.")


def run_rule(module: str, scope: str, inputs: dict) -> dict:
    rule_file = f"{RULES}/{module}.catala_en"
    cmd = [
        CATALA_BIN, "interpret",
        "-F", "json",
        "--no-stdlib",
        f"--scope={scope}",
        "--input=-",
        rule_file,
    ]
    out = subprocess.run(cmd, input=json.dumps(inputs), capture_output=True, text=True, timeout=15)
    if out.returncode != 0:
        raise AssertionError(f"catala failed for {module}/{scope}\ninputs={inputs}\nstderr={out.stderr.strip()}")
    raw = out.stdout.strip()
    if not raw:
        raise AssertionError(f"catala produced no JSON for {module}/{scope}")
    return json.loads(raw)


PASS = 0
FAIL = 0
FAILURES: list[str] = []


def check(name: str, condition: bool, detail: str = ""):
    global PASS, FAIL
    if condition:
        PASS += 1
    else:
        FAIL += 1
        msg = f"  [FAIL] {name}"
        if detail:
            msg += f"\n         {detail}"
        FAILURES.append(msg)


# ---------------------------------------------------------------------
# difc_rdc_part_38 / StandardBasisAssessment
#   total = hours * rate + disbursements
#   monotonic in each input
# ---------------------------------------------------------------------

def prop_rdc_part_38():
    name = "difc_rdc_part_38 · standard-basis"
    print(f"\n— {name} —")
    for _ in range(N_TRIALS):
        h = round(random.uniform(0, 200), 2)
        r = round(random.uniform(0, 5000), 2)
        d = round(random.uniform(0, 100000), 2)
        out = run_rule("difc_rdc_part_38", "StandardBasisAssessment",
                       {"claim": {"hours_worked": str(h), "hourly_rate_aed": str(r),
                                  "reasonable_disbursements_aed": str(d)}})["award"]
        check("total = hours*rate + disbursements",
              abs(out["total_aed"] - (h * r + d)) < 0.01,
              f"got {out['total_aed']}, want {h*r+d}")
        # monotonic in hours: increase by 1 → total increases by rate
        out2 = run_rule("difc_rdc_part_38", "StandardBasisAssessment",
                        {"claim": {"hours_worked": str(h + 1), "hourly_rate_aed": str(r),
                                   "reasonable_disbursements_aed": str(d)}})["award"]
        check("monotonic in hours",
              abs((out2["total_aed"] - out["total_aed"]) - r) < 0.01)


# ---------------------------------------------------------------------
# uae_civil_code_art_390 / Article390Cap (post-refactor: 2 layers)
#   Layer 1 (contract cap): if contract_caps_ld and uncapped > cap →
#                           after = cap, was_contract_capped = true
#   Layer 1 otherwise:       after = uncapped
#   Layer 2 (390(2)):        was_390_2_varied iff asked_to_vary AND
#                            court_finds_grossly_disproportionate
#   awarded_aed = after_contract_cap_aed (390(2) variation amount is
#                 a human-judgment input not modelled here)
# ---------------------------------------------------------------------

def prop_uae_390():
    name = "uae_civil_code_art_390 · LD-cap engagement"
    print(f"\n— {name} —")
    for _ in range(N_TRIALS):
        contract = round(random.uniform(100000, 50000000), 2)
        cap_rate = round(random.uniform(0.05, 0.30), 4)
        uncapped = round(random.uniform(0, contract * 2), 2)
        cap = round(contract * cap_rate, 2)
        for contract_caps_ld in (True, False):
            for asked, finds in [(False, False), (True, False), (True, True)]:
                out = run_rule("uae_civil_code_art_390", "Article390Cap",
                               {"claim": {
                                   "uncapped_amount_aed": str(uncapped),
                                   "contract_value_aed": str(contract),
                                   "contract_cap_rate": str(cap_rate),
                                   "contract_caps_ld": contract_caps_ld,
                                   "court_asked_to_vary_under_390_2": asked,
                                   "court_finds_grossly_disproportionate": finds,
                               }})["award"]
                if contract_caps_ld and uncapped > cap:
                    expected_after = cap
                    expected_capped = True
                else:
                    expected_after = uncapped
                    expected_capped = False
                check("after_contract_cap_aed correct",
                      abs(out["after_contract_cap_aed"] - expected_after) < 0.02,
                      f"contract_caps_ld={contract_caps_ld} cap={cap} "
                      f"uncapped={uncapped} got={out['after_contract_cap_aed']}")
                check("awarded_aed equals after_contract_cap_aed",
                      abs(out["awarded_aed"] - out["after_contract_cap_aed"]) < 0.001)
                check("was_contract_capped flag",
                      out["was_contract_capped"] == expected_capped)
                check("was_390_2_varied iff asked AND finds",
                      out["was_390_2_varied"] == (asked and finds))


# ---------------------------------------------------------------------
# ladd_v_marshall / LaddMarshallTest
#   admissible iff all 3 prongs satisfied
#   n_prongs_satisfied is the count of `satisfied: true` prongs
# ---------------------------------------------------------------------

def prop_ladd():
    print("\n— ladd_v_marshall · three-prong conjunctive —")
    PRONGS = ["ReasonableDiligence", "ImportantInfluence", "PresumablyCredible"]
    for trial in range(min(N_TRIALS, 8)):  # 2^3 = 8 truth tables, exhaust
        bits = [(trial >> i) & 1 for i in range(3)]
        prongs = [{"prong": p, "satisfied": bool(b)} for p, b in zip(PRONGS, bits)]
        out = run_rule("ladd_v_marshall", "LaddMarshallTest",
                       {"prongs": prongs})["disposition"]
        n_sat = sum(bits)
        check(f"truth table {bits}: n_prongs_satisfied = {n_sat}",
              int(out["n_prongs_satisfied"]) == n_sat,
              f"got {out['n_prongs_satisfied']}")
        check(f"truth table {bits}: admissible iff all three",
              out["evidence_admissible"] == (n_sat == 3))


# ---------------------------------------------------------------------
# caparo_three_stage_test / CaparoTest (with Robinson narrowing)
#   established_category → duty owed by precedent (3-stage skipped)
#   novel:                duty_owed iff all 3 stages
# ---------------------------------------------------------------------

def prop_caparo():
    print("\n— caparo_three_stage_test · three-stage conjunctive (+Robinson) —")
    KEYS = ["harm_reasonably_foreseeable", "sufficient_proximity", "fair_just_reasonable_to_impose"]
    for trial in range(8):
        bits = [(trial >> i) & 1 for i in range(3)]
        for is_established in (True, False):
            facts = {"is_established_category": is_established}
            facts.update({k: bool(b) for k, b in zip(KEYS, bits)})
            out = run_rule("caparo_three_stage_test", "CaparoTest", {"facts": facts})["disposition"]
            n = sum(bits)
            if is_established:
                check("Robinson: established → duty owed by precedent",
                      out["duty_of_care_owed"] is True)
                check("Robinson: established → path = EstablishedCategory_DutyByPrecedent",
                      out["path"] == "EstablishedCategory_DutyByPrecedent")
                check("Robinson: established → n_stages_satisfied = -1 (sentinel)",
                      int(out["n_stages_satisfied"]) == -1)
            else:
                check(f"caparo novel {bits}: n_stages_satisfied = {n}",
                      int(out["n_stages_satisfied"]) == n)
                check(f"caparo novel {bits}: duty iff all three",
                      out["duty_of_care_owed"] == (n == 3))
                expected_path = ("NovelCategory_AllStagesMade" if n == 3
                                 else "NovelCategory_FailsAtStage")
                check(f"caparo novel {bits}: path = {expected_path}",
                      out["path"] == expected_path)


# ---------------------------------------------------------------------
# adgm_cpr_summary_judgment / SummaryJudgmentTest
#   granted iff both limbs
# ---------------------------------------------------------------------

def prop_summary_judgment():
    print("\n— adgm_cpr_summary_judgment · two-limb conjunctive —")
    for a in (False, True):
        for b in (False, True):
            out = run_rule("adgm_cpr_summary_judgment", "SummaryJudgmentTest",
                           {"application": {"no_realistic_prospect": a, "no_compelling_reason": b}})["disposition"]
            check(f"summary judgment ({a}, {b}) — granted iff both",
                  out["summary_judgment_granted"] == (a and b))


# ---------------------------------------------------------------------
# sg_iaa_s_31 / IAA_S31_Refusal
#   if any ground AllowedInFull → AwardSetAside, award_enforced=false
#   if none full but at least one AllowedInPart → ApplicationAllowedInPart, award_enforced=true
#   if all Dismissed → ApplicationDismissedEntirely, award_enforced=true
# ---------------------------------------------------------------------

def prop_iaa_s31():
    print("\n— sg_iaa_s_31 · refusal-disposition logic —")
    GROUNDS = ["S31_2_a_Incapacity", "S31_2_b_InvalidAgreement", "S31_2_c_NaturalJustice",
               "S31_2_d_OutsideScope", "S31_2_e_TribunalComposition", "S31_2_f_NotBindingOrSetAside",
               "S31_4_a_NotArbitrable", "S31_4_b_PublicPolicy"]
    OUTCOMES = ["Dismissed", "AllowedInPart", "AllowedInFull"]
    for _ in range(N_TRIALS):
        n = random.randint(1, 5)
        grounds = [{"ground": random.choice(GROUNDS),
                    "court_outcome": random.choice(OUTCOMES),
                    "is_severable": random.choice([True, False])}
                   for _ in range(n)]
        out = run_rule("sg_iaa_s_31", "IAA_S31_Refusal", {"grounds": grounds})["disposition"]
        n_full = sum(1 for g in grounds if g["court_outcome"] == "AllowedInFull")
        n_part = sum(1 for g in grounds if g["court_outcome"] == "AllowedInPart")
        n_dis = sum(1 for g in grounds if g["court_outcome"] == "Dismissed")
        # s 31(3) severability: a fully-allowed OutsideScope ground that
        # is severable yields AllowedInPart, not AwardSetAside.
        n_full_relief = sum(
            1 for g in grounds
            if g["court_outcome"] == "AllowedInFull"
            and g["ground"] == "S31_2_d_OutsideScope"
            and g["is_severable"]
        )
        n_full_dispositive = n_full - n_full_relief
        if n_full_dispositive > 0:
            expected = "AwardSetAside"
        elif n_part > 0 or n_full_relief > 0:
            expected = "ApplicationAllowedInPart"
        else:
            expected = "ApplicationDismissedEntirely"
        check(f"disposition: full={n_full} relief={n_full_relief} part={n_part} dis={n_dis}",
              out["application_disposition"] == expected,
              f"got {out['application_disposition']}, want {expected}")
        check("award_enforced iff no full-dispositive ground",
              out["award_enforced"] == (n_full_dispositive == 0))
        check("counts add up",
              int(out["n_grounds_pleaded"]) == n
              and int(out["n_grounds_full"]) == n_full
              and int(out["n_grounds_partial"]) == n_part
              and int(out["n_grounds_dismissed"]) == n_dis)


# ---------------------------------------------------------------------
# adgm_arbitration_regulations_2015 / ADGMRecognition
#   structural parallel of sg_iaa_s_31, with two additional inputs:
#     - is_severable (per ground; only effective on S62_a_iv_OutsideScope)
#     - s58_was_or_could_have_been_available (top-level; bars the
#       application under s 62(3) regardless of grounds)
#
# Invariants:
#   if s58_available: overall=RecognitionGranted, award_recognised=True,
#                     application_status=ApplicationBarredByS62_3
#   else: full_dispositive = full - (severable-relief on S62_a_iv only)
#         RecognitionRefused      iff full_dispositive > 0
#         RecognitionGrantedInPart iff partial>0 OR severable_relief>0
#         RecognitionGranted      otherwise
#         award_recognised iff full_dispositive == 0
#         application_status = ApplicationProperlyMade
# ---------------------------------------------------------------------

def prop_adgm_s62():
    print("\n— adgm_arbitration_regulations_2015 · refusal-disposition + s 62(3) —")
    GROUNDS = ["S62_a_i_Incapacity", "S62_a_ii_InvalidAgreement", "S62_a_iii_NaturalJustice",
               "S62_a_iv_OutsideScope", "S62_a_v_TribunalComposition", "S62_a_vi_NotBindingOrSetAside",
               "S62_b_i_NotArbitrable", "S62_b_ii_PublicPolicy"]
    OUTCOMES = ["Dismissed", "AllowedInPart", "AllowedInFull"]
    for _ in range(N_TRIALS):
        n = random.randint(1, 5)
        grounds = [{"ground": random.choice(GROUNDS),
                    "court_outcome": random.choice(OUTCOMES),
                    "is_severable": random.choice([True, False])}
                   for _ in range(n)]
        s58 = random.choice([True, False])
        out = run_rule("adgm_arbitration_regulations_2015", "ADGMRecognition",
                       {"grounds": grounds,
                        "s58_was_or_could_have_been_available": s58})["disposition"]
        n_full = sum(1 for g in grounds if g["court_outcome"] == "AllowedInFull")
        n_part = sum(1 for g in grounds if g["court_outcome"] == "AllowedInPart")
        n_dis = sum(1 for g in grounds if g["court_outcome"] == "Dismissed")
        n_full_relief = sum(
            1 for g in grounds
            if g["court_outcome"] == "AllowedInFull"
            and g["ground"] == "S62_a_iv_OutsideScope"
            and g["is_severable"]
        )
        n_full_dispositive = n_full - n_full_relief

        if s58:
            expected_overall = "RecognitionGranted"
            expected_recognised = True
            expected_status = "ApplicationBarredByS62_3"
        else:
            expected_status = "ApplicationProperlyMade"
            if n_full_dispositive > 0:
                expected_overall = "RecognitionRefused"
                expected_recognised = False
            elif n_part > 0 or n_full_relief > 0:
                expected_overall = "RecognitionGrantedInPart"
                expected_recognised = True
            else:
                expected_overall = "RecognitionGranted"
                expected_recognised = True

        check(f"overall: full={n_full} relief={n_full_relief} part={n_part} dis={n_dis} s58={s58}",
              out["overall_disposition"] == expected_overall,
              f"got {out['overall_disposition']}, want {expected_overall}")
        check("award_recognised invariant",
              out["award_recognised"] == expected_recognised)
        check("application_status invariant",
              out["application_status"] == expected_status)
        check("counts add up",
              int(out["n_grounds_pleaded"]) == n
              and int(out["n_grounds_full"]) == n_full
              and int(out["n_grounds_partial"]) == n_part
              and int(out["n_grounds_dismissed"]) == n_dis)


# ---------------------------------------------------------------------
# difc_third_party_disclosure / ThirdPartyDisclosureGates
#   order_grantable iff all elements of all three gates made_out
# ---------------------------------------------------------------------

def prop_third_party():
    print("\n— difc_third_party_disclosure · three-gate conjunctive —")
    NPH = ["NPE_WrongEstablished", "NPE_RespondentMixedUp", "NPE_PossessesInformation",
           "NPE_DisclosureNecessaryInInterestsOfJustice"]
    BT = ["BTE_TracingClaimAsserted", "BTE_HoldsTraceableProceeds", "BTE_DisclosureNecessaryForTracing"]
    RDC = ["RDC_LikelyToSupportOrAffect", "RDC_NecessaryToDisposeOrSaveCosts"]
    for _ in range(N_TRIALS):
        nph = [{"element": e, "made_out": bool(random.getrandbits(1))} for e in NPH]
        bt = [{"element": e, "made_out": bool(random.getrandbits(1))} for e in BT]
        rdc = [{"rdc_condition": e, "made_out": bool(random.getrandbits(1))} for e in RDC]
        out = run_rule("difc_third_party_disclosure", "ThirdPartyDisclosureGates",
                       {"nph_findings": nph, "bt_findings": bt, "rdc_findings": rdc})["gates"]
        nph_ok = all(e["made_out"] for e in nph)
        bt_ok = all(e["made_out"] for e in bt)
        rdc_ok = all(e["made_out"] for e in rdc)
        check("nph_made_out", out["nph_made_out"] == nph_ok)
        check("bankers_trust_made_out", out["bankers_trust_made_out"] == bt_ok)
        check("rdc_2852_made_out", out["rdc_2852_made_out"] == rdc_ok)
        check("order_grantable iff all gates", out["order_grantable"] == (nph_ok and bt_ok and rdc_ok))


# ---------------------------------------------------------------------
# english_contract_interpretation / WoodVCapita
# (post-2026-05 audit: Stage 2 relaxed to Lord Hodge balancing)
#   plain unambiguous → PlainMeaningCarries (regardless of other limbs)
#   not plain + (cs OR matrix=Supports) AND (matrix != Contradicts)
#                                       → BusinessCommonSenseCarries
#   else                                → GenuinelyAmbiguous
# ---------------------------------------------------------------------

def prop_wood_capita():
    print("\n— english_contract_interpretation · branch logic —")
    for plain in (False, True):
        for cs in (False, True):
            for matrix in ("Supports", "Silent", "Contradicts"):
                ev = {"clauses_unambiguously_aligned": plain,
                      "common_sense_supports_one_reading": cs,
                      "factual_matrix_signal": matrix}
                out = run_rule("english_contract_interpretation", "WoodVCapita",
                               {"evidence": ev})["disposition"]
                if plain:
                    expected = "PlainMeaningCarries"
                else:
                    bcs_carries = (
                        (cs or matrix == "Supports")
                        and matrix != "Contradicts"
                    )
                    expected = ("BusinessCommonSenseCarries" if bcs_carries
                                else "GenuinelyAmbiguous")
                check(f"wood_capita ({plain},{cs},{matrix}) → {expected}",
                      out["limb"] == expected,
                      f"got {out['limb']}")


def main():
    global N_TRIALS
    if os.environ.get("HABEAS_PROPERTY_TRIALS"):
        try:
            N_TRIALS = max(8, int(os.environ["HABEAS_PROPERTY_TRIALS"]))
        except ValueError:
            pass

    prop_rdc_part_38()
    prop_uae_390()
    prop_ladd()
    prop_caparo()
    prop_summary_judgment()
    prop_iaa_s31()
    prop_adgm_s62()
    prop_third_party()
    prop_wood_capita()

    total = PASS + FAIL
    print()
    print(f"property tests: {PASS}/{total} passed")
    if FAIL:
        print("\nfailures:")
        for f in FAILURES[:20]:
            print(f)
        sys.exit(1)


if __name__ == "__main__":
    main()
