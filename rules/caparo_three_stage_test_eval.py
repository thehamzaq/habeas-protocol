"""
Pure-Python reference evaluator for caparo_three_stage_test.

Mirrors the Catala scope CaparoTest. Caparo Industries plc v Dickman
[1990] UKHL 2 three-stage duty-of-care test, as narrowed by
Robinson v Chief Constable of West Yorkshire [2018] UKSC 4.

  (1) harm reasonably foreseeable
  (2) sufficient proximity between claimant and defendant
  (3) fair, just and reasonable to impose a duty (the policy gate)

Conjunctive: in a NOVEL duty case, all three must be satisfied.
Robinson narrowing: where the duty is in an ESTABLISHED category,
the three-stage test is not run; duty is owed by precedent.

Output `path` is one of:
  - EstablishedCategory_DutyByPrecedent
  - NovelCategory_AllStagesMade
  - NovelCategory_FailsAtStage
"""


def caparo_test(facts: dict) -> dict:
    is_established = bool(facts["is_established_category"])
    foreseeable = bool(facts["harm_reasonably_foreseeable"])
    proximity = bool(facts["sufficient_proximity"])
    fjr = bool(facts["fair_just_reasonable_to_impose"])
    raw_n = int(foreseeable) + int(proximity) + int(fjr)
    novel_pass = foreseeable and proximity and fjr
    if is_established:
        owed = True
        path = "EstablishedCategory_DutyByPrecedent"
        first_fail = "Stage_None"
    elif novel_pass:
        owed = True
        path = "NovelCategory_AllStagesMade"
        first_fail = "Stage_None"
    else:
        owed = False
        path = "NovelCategory_FailsAtStage"
        if not foreseeable:
            first_fail = "Stage_1_Foreseeability"
        elif not proximity:
            first_fail = "Stage_2_Proximity"
        elif not fjr:
            first_fail = "Stage_3_FairJustReasonable"
        else:
            first_fail = "Stage_None"  # unreachable
    # n_stages_satisfied is meaningful only on the novel-duty path.
    # On the established-category path we emit -1 as a sentinel so
    # downstream consumers don't misread "established" as "passed N
    # of 3 stages."
    n_stages_satisfied = -1 if is_established else raw_n
    return {
        "path": path,
        "n_stages_satisfied": n_stages_satisfied,
        "first_failing_stage": first_fail,
        "duty_of_care_owed": owed,
        "stage_findings": {
            "stage_1_foreseeability": foreseeable,
            "stage_2_proximity": proximity,
            "stage_3_fair_just_reasonable": fjr,
        },
    }


__all__ = ["caparo_test"]
