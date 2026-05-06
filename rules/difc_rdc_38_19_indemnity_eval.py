"""
Pure-Python reference evaluator for difc_rdc_38_19_indemnity.

Mirrors the Catala scope IndemnityBasisReview. The bounded-discretion
case: the rule strips proportionality and leaves reasonableness, which
is not formulaic. The predicate triages each objection into one of four
buckets and produces a deterministic award only when no bucket residue
remains.

Lifted from spike/trace-03/evaluate.py.
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Optional


def _D(x) -> Decimal:
    return Decimal(str(x))


def _Q(x) -> Decimal:
    return _D(x).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def indemnity_basis_review(schedule: dict) -> dict:
    """Indemnity-basis review predicate.

    schedule = {
      "claimed_aed": <number>,
      "objections": [
        {
          "label": str,
          "names_specific_line_item": bool,
          "factual_finding": "rejected_on_evidence" |
                             "accepted_with_named_amount" |
                             "requires_human_judgment",
          "named_amount_aed": <number>  (only if accepted_with_named_amount)
        },
        ...
      ]
    }
    """
    claimed = _D(schedule["claimed_aed"])

    mechanically_disposed = []
    held_to_zero = []
    deterministic = []
    residual = []

    for o in schedule["objections"]:
        specific = bool(o["names_specific_line_item"])
        finding = o["factual_finding"]
        if not specific and finding != "requires_human_judgment":
            mechanically_disposed.append(o["label"])
        elif specific and finding == "rejected_on_evidence":
            held_to_zero.append(o["label"])
        elif specific and finding == "accepted_with_named_amount":
            deterministic.append((o["label"], _D(o["named_amount_aed"])))
        else:
            residual.append(o["label"])

    det_reductions = sum((amt for _, amt in deterministic), _D(0))
    requires_human = len(residual) > 0
    deterministic_award: Optional[Decimal] = (
        None if requires_human else _Q(claimed - det_reductions)
    )

    return {
        "claimed_aed": _Q(claimed),
        "objections_mechanically_disposed": mechanically_disposed,
        "objections_held_to_zero": held_to_zero,
        "objections_deterministic_reductions": deterministic,
        "objections_requiring_human_judgment": residual,
        "deterministic_reductions_aed": _Q(det_reductions),
        "requires_human_judgment": requires_human,
        "deterministic_award_aed": deterministic_award,
    }


__all__ = ["indemnity_basis_review"]
