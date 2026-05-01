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
# uae_civil_code_art_390 / Article390Cap
#   if grossly_exaggerated and uncapped > cap → awarded == cap
#   if not grossly_exaggerated → awarded == uncapped (no cap)
#   was_capped iff awarded < uncapped
# ---------------------------------------------------------------------

def prop_uae_390():
    name = "uae_civil_code_art_390 · LD-cap engagement"
    print(f"\n— {name} —")
    for _ in range(N_TRIALS):
        contract = round(random.uniform(100000, 50000000), 2)
        cap_rate = round(random.uniform(0.05, 0.30), 4)
        uncapped = round(random.uniform(0, contract * 2), 2)
        cap = round(contract * cap_rate, 2)
        for engaged in (True, False):
            out = run_rule("uae_civil_code_art_390", "Article390Cap",
                           {"claim": {"uncapped_amount_aed": str(uncapped),
                                      "contract_value_aed": str(contract),
                                      "cap_rate": str(cap_rate),
                                      "court_finds_grossly_exaggerated": engaged}})["award"]
            if not engaged:
                check("not engaged → awarded == uncapped",
                      abs(out["awarded_aed"] - uncapped) < 0.02,
                      f"engaged={engaged} uncapped={uncapped} got={out['awarded_aed']}")
                check("not engaged → was_capped is false",
                      out["was_capped"] is False)
            else:
                expected = cap if uncapped > cap else uncapped
                check("engaged → awarded = min(cap, uncapped)",
                      abs(out["awarded_aed"] - expected) < 0.02,
                      f"cap={cap} uncapped={uncapped} got={out['awarded_aed']}")
            check("was_capped iff awarded < uncapped",
                  out["was_capped"] == (out["awarded_aed"] < uncapped))


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
# caparo_three_stage_test / CaparoTest
#   duty_owed iff all 3 stages
# ---------------------------------------------------------------------

def prop_caparo():
    print("\n— caparo_three_stage_test · three-stage conjunctive —")
    KEYS = ["harm_reasonably_foreseeable", "sufficient_proximity", "fair_just_reasonable_to_impose"]
    for trial in range(8):
        bits = [(trial >> i) & 1 for i in range(3)]
        facts = {k: bool(b) for k, b in zip(KEYS, bits)}
        out = run_rule("caparo_three_stage_test", "CaparoTest", {"facts": facts})["disposition"]
        n = sum(bits)
        check(f"caparo truth table {bits}: n_stages = {n}",
              int(out["n_stages_satisfied"]) == n)
        check(f"caparo truth table {bits}: duty iff all three",
              out["duty_of_care_owed"] == (n == 3))


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
    GROUNDS = ["S31_2_a_Incapacity", "S31_2_b_NaturalJustice", "S31_2_c_TribunalComposition",
               "S31_2_d_OutsideScope", "S31_2_e_NotBindingOrSetAside", "S31_2_f_NotArbitrable",
               "S31_4_b_PublicPolicy"]
    OUTCOMES = ["Dismissed", "AllowedInPart", "AllowedInFull"]
    for _ in range(N_TRIALS):
        n = random.randint(1, 5)
        grounds = [{"ground": random.choice(GROUNDS), "court_outcome": random.choice(OUTCOMES)}
                   for _ in range(n)]
        out = run_rule("sg_iaa_s_31", "IAA_S31_Refusal", {"grounds": grounds})["disposition"]
        n_full = sum(1 for g in grounds if g["court_outcome"] == "AllowedInFull")
        n_part = sum(1 for g in grounds if g["court_outcome"] == "AllowedInPart")
        n_dis = sum(1 for g in grounds if g["court_outcome"] == "Dismissed")
        if n_full > 0:
            expected = "AwardSetAside"
        elif n_part > 0:
            expected = "ApplicationAllowedInPart"
        else:
            expected = "ApplicationDismissedEntirely"
        check(f"disposition: full={n_full} part={n_part} dis={n_dis}",
              out["application_disposition"] == expected,
              f"got {out['application_disposition']}, want {expected}")
        check("award_enforced iff no full ground",
              out["award_enforced"] == (n_full == 0))
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
#   plain unambiguous → PlainMeaningCarries (regardless of other limbs)
#   not plain + business_sense (with matrix) → BusinessCommonSenseCarries
#   neither → GenuinelyAmbiguous
# ---------------------------------------------------------------------

def prop_wood_capita():
    print("\n— english_contract_interpretation · branch logic —")
    for plain in (False, True):
        for bcs in (False, True):
            for matrix in (False, True):
                ev = {"clauses_unambiguously_aligned": plain,
                      "common_sense_supports_one_reading": bcs,
                      "factual_matrix_supports_that_reading": matrix}
                out = run_rule("english_contract_interpretation", "WoodVCapita",
                               {"evidence": ev})["disposition"]
                if plain:
                    expected = "PlainMeaningCarries"
                elif bcs and matrix:
                    expected = "BusinessCommonSenseCarries"
                else:
                    expected = "GenuinelyAmbiguous"
                check(f"wood_capita ({plain},{bcs},{matrix}) → {expected}",
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
