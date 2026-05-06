"""
Pure-Python reference evaluator for adgm_arbitration_regulations_2015.

Mirrors the Catala scope ADGMRecognition. Walks a list of NY-Convention-
style refusal grounds (s 62(1)(a)(i)..(vi) and s 62(1)(b)(i)..(ii) of the
ADGM Arbitration Regulations 2015 — historically s 56(2)/(3) in the 2015
enacted version) and returns:

  RecognitionRefused        if any ground fully allowed
  RecognitionGrantedInPart  if any ground partially allowed
  RecognitionGranted        otherwise
"""

from typing import List


VALID_OUTCOMES = {"Dismissed", "AllowedInPart", "AllowedInFull"}


def adgm_recognition(
    grounds: List[dict],
    s58_was_or_could_have_been_available: bool = False,
) -> dict:
    """Mirrors Catala scope ADGMRecognition.

    grounds: list of {ground, court_outcome, is_severable?}
    s58_was_or_could_have_been_available: s 62(3) carve-out. When True,
        the s 62 application is barred regardless of grounds.
    """
    dismissed = sum(1 for g in grounds if g["court_outcome"] == "Dismissed")
    partial = sum(1 for g in grounds if g["court_outcome"] == "AllowedInPart")
    full = sum(1 for g in grounds if g["court_outcome"] == "AllowedInFull")

    # s 62(1)(a)(iv) severability relief — applies only to fully-allowed
    # OutsideScope grounds.
    full_severable_relief = sum(
        1 for g in grounds
        if g["court_outcome"] == "AllowedInFull"
        and g.get("ground") == "S62_a_iv_OutsideScope"
        and bool(g.get("is_severable", False))
    )
    full_dispositive = full - full_severable_relief

    if s58_was_or_could_have_been_available:
        overall = "RecognitionGranted"
        application_status = "ApplicationBarredByS62_3"
        award_recognised = True
    else:
        application_status = "ApplicationProperlyMade"
        if full_dispositive > 0:
            overall = "RecognitionRefused"
            award_recognised = False
        elif partial > 0 or full_severable_relief > 0:
            overall = "RecognitionGrantedInPart"
            award_recognised = True
        else:
            overall = "RecognitionGranted"
            award_recognised = True

    return {
        "n_grounds_pleaded": len(grounds),
        "n_grounds_dismissed": dismissed,
        "n_grounds_partial": partial,
        "n_grounds_full": full,
        "overall_disposition": overall,
        "award_recognised": award_recognised,
        "application_status": application_status,
    }


def adgm_s62_2_adjournment(inputs: dict) -> dict:
    """Mirrors Catala scope ADGM_S62_2_Adjournment.

    inputs: {setting_aside_pending_at_seat, adjournment_ordered, security_ordered}
    The adjournment / security order is lawful only where a parallel
    set-aside application is pending at the seat.
    """
    lawful = bool(inputs["setting_aside_pending_at_seat"])
    return {
        "proceedings_adjourned": bool(inputs["adjournment_ordered"]) and lawful,
        "security_required": bool(inputs["security_ordered"]) and lawful,
        "adjournment_engaged_lawfully": lawful,
    }


__all__ = ["adgm_recognition", "adgm_s62_2_adjournment"]
