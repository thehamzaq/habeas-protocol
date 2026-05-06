"""
Pure-Python reference evaluator for english_contract_interpretation.

This module exposes TWO functions:

  * `wood_v_capita` — Catala-mirror of the WoodVCapita scope. Inputs:
    {clauses_unambiguously_aligned, common_sense_supports_one_reading,
     factual_matrix_signal: 'Supports'|'Silent'|'Contradicts'}. Output
    matches the InterpretationDisposition struct.
  * `clause_alignment` — legacy utility used by trace-05's evaluator.
    Boolean conjunction over named clauses; not a Catala mirror. Each
    clause has {clause_id, points_to_payment_before_transfer}.

The doctrine encoded in `wood_v_capita`: read the contract as a whole,
weigh each candidate construction against the other clauses, the
factual matrix, and commercial common sense, and choose the
construction that fits best (Wood v Capita Insurance Services Ltd
[2017] UKSC 24, applying Rainy Sky [2011] UKSC 50, with Arnold v
Britton [2015] UKSC 36 supplying the textual-emphasis limb). Stage 2
of the encoding uses Lord Hodge's balancing rule: BCS carries when
(common_sense supports OR matrix supports) AND matrix does not
contradict.
"""

from typing import List


# ---------------------------------------------------------------------
# Catala mirror — the rule-library API.
# ---------------------------------------------------------------------

def wood_v_capita(evidence: dict) -> dict:
    """Mirrors Catala scope WoodVCapita.

    evidence: {
      clauses_unambiguously_aligned: bool,
      common_sense_supports_one_reading: bool,
      factual_matrix_signal: 'Supports' | 'Silent' | 'Contradicts',
    }
    """
    plain = bool(evidence["clauses_unambiguously_aligned"])
    cs = bool(evidence["common_sense_supports_one_reading"])
    mtx = evidence["factual_matrix_signal"]
    if mtx not in ("Supports", "Silent", "Contradicts"):
        raise ValueError(
            f"factual_matrix_signal must be one of "
            f"Supports/Silent/Contradicts; got {mtx!r}"
        )
    mtx_supports = (mtx == "Supports")
    mtx_contradicts = (mtx == "Contradicts")
    bcs = (
        (not plain)
        and (cs or mtx_supports)
        and (not mtx_contradicts)
    )
    if plain:
        limb = "PlainMeaningCarries"
    elif bcs:
        limb = "BusinessCommonSenseCarries"
    else:
        limb = "GenuinelyAmbiguous"
    return {
        "limb": limb,
        "unambiguous_carries": plain,
        "business_sense_carries": bcs,
    }


# ---------------------------------------------------------------------
# Legacy trace-05 utility — Boolean conjunction over named clauses.
# ---------------------------------------------------------------------

def clause_alignment(clauses: List[dict]) -> dict:
    """Conjunctive clause alignment under the resolved construction.

    clauses: list of {clause_id, court_para_ref, points_to_payment_before_transfer}

    Returns:
      clauses_aligned (bool): True iff every clause points in the same direction
      misaligned_clauses (list): clauses that don't align (empty if aligned)
      interpretation_holding (str): canonical disposition tag
    """
    misaligned = [c for c in clauses
                  if not c.get("points_to_payment_before_transfer", False)]
    aligned = len(misaligned) == 0
    return {
        "clauses_aligned": aligned,
        "misaligned_clauses": [c.get("clause_id") for c in misaligned],
        "interpretation_holding": (
            "named clauses align — construction supports the proposition"
            if aligned else
            "named clauses do not align — construction contested"
        ),
    }


__all__ = ["wood_v_capita", "clause_alignment"]
