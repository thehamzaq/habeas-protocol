"""
Pure-Python reference evaluator for sg_iaa_s_31.

Mirrors the Catala scopes IAA_S31_Refusal (NY Convention Article V
grounds via Singapore IAA s 31) and DKTvDKUChallenge (the four-condition
framework for s 31(2)(b) refusals on natural-justice grounds).

Composite walk:
  - Count grounds pleaded
  - Count grounds dismissed / allowed-in-part / allowed-in-full
  - Disposition is:
      AwardSetAside              if any ground fully allowed
      ApplicationAllowedInPart   if any ground partially allowed
      ApplicationDismissedEntirely otherwise
  - Track which paragraphs of the tribunal's Order are excised vs enforced.
"""

from typing import List


def iaa_s31_disposition(grounds: List[dict]) -> dict:
    """Walk the IAA s 31 grounds and return the disposition.

    grounds: list of {id?, statute?, label?, court_outcome,
                       is_severable?, ground? (IAAGroundId),
                       excised_paragraphs?, enforced_paragraphs?}

    court_outcome ∈ {"Dismissed", "AllowedInPart", "AllowedInFull"}

    s 31(3) severability proviso: a fully-allowed OutsideScope ground
    (s 31(2)(d)) that is severable is NOT dispositive — the in-scope
    decisions can be enforced. Other grounds admit no severability.
    The legacy `id`-based input shape (no `is_severable` field) is
    treated as is_severable=false (the conservative reading).
    """
    n_pleaded = len(grounds)
    n_dismissed = sum(1 for g in grounds if g["court_outcome"] == "Dismissed")
    n_partial = sum(1 for g in grounds if g["court_outcome"] == "AllowedInPart")
    n_full = sum(1 for g in grounds if g["court_outcome"] == "AllowedInFull")

    # s 31(3) severability relief — only applies to fully-allowed
    # OutsideScope grounds. Identifies via either the canonical
    # `ground` field or a `statute` string containing "31(2)(d)".
    def is_outside_scope(g: dict) -> bool:
        if g.get("ground") == "S31_2_d_OutsideScope":
            return True
        st = (g.get("statute") or "").lower()
        return "31(2)(d)" in st or "outsidescope" in st.replace(" ", "")

    n_full_severable_relief = sum(
        1 for g in grounds
        if g["court_outcome"] == "AllowedInFull"
        and bool(g.get("is_severable", False))
        and is_outside_scope(g)
    )
    n_full_dispositive = n_full - n_full_severable_relief

    if n_full_dispositive > 0:
        application = "AwardSetAside"
    elif n_partial > 0 or n_full_severable_relief > 0:
        application = "ApplicationAllowedInPart"
    else:
        application = "ApplicationDismissedEntirely"

    award_enforced = (n_full_dispositive == 0)

    excised = []
    enforced = []
    for g in grounds:
        excised.extend(g.get("excised_paragraphs", []))
        enforced.extend(g.get("enforced_paragraphs", []))

    return {
        "n_grounds_pleaded": n_pleaded,
        "n_grounds_dismissed": n_dismissed,
        "n_grounds_partial": n_partial,
        "n_grounds_full": n_full,
        "application_disposition": application,
        "award_enforced": award_enforced,
        "n_paras_excised": len(excised),
        "excised_paragraphs": excised,
        "enforced_paragraphs": enforced,
    }


def iaa_s31_5_adjournment(inputs: dict) -> dict:
    """Mirrors Catala scope IAA_S31_5_Adjournment.

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


def iaa_s31_2_c_infra_petita(conditions: dict, court_outcome_on_31_2_c: str) -> dict:
    """Mirrors Catala scope IAA_S31_2_c_InfraPetita.

    conditions: {point_properly_before_tribunal, point_essential_to_dispute,
                 tribunal_completely_failed_to_consider, prejudice_demonstrated}
    court_outcome_on_31_2_c: one of "Dismissed" | "AllowedInPart" | "AllowedInFull"

    Returns the DKT-v-court consistency analysis. challenge_succeeds iff
    all four conditions met; consistent iff (succeeds → AllowedInFull)
    AND (¬succeeds → Dismissed).
    """
    challenge_succeeds = (
        bool(conditions["point_properly_before_tribunal"])
        and bool(conditions["point_essential_to_dispute"])
        and bool(conditions["tribunal_completely_failed_to_consider"])
        and bool(conditions["prejudice_demonstrated"])
    )
    if challenge_succeeds:
        consistent = (court_outcome_on_31_2_c == "AllowedInFull")
    else:
        consistent = (court_outcome_on_31_2_c == "Dismissed")
    return {
        "conditions": conditions,
        "court_outcome_on_31_2_c": court_outcome_on_31_2_c,
        "dkt_challenge_succeeds": challenge_succeeds,
        "dkt_analysis_consistent": consistent,
    }


__all__ = [
    "iaa_s31_disposition",
    "iaa_s31_5_adjournment",
    "iaa_s31_2_c_infra_petita",
]
