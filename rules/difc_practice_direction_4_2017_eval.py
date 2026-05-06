"""
Pure-Python reference evaluator for difc_practice_direction_4_2017.

Two functions:

  * `outstanding_arbitration_costs` — Catala mirror of the
    OutstandingArbitrationCosts scope. Inputs match the
    ArbitrationCostsClaim struct field-for-field; output matches the
    ArbitrationCostsAward struct.

  * `outstanding_obligation` — legacy date-based evaluator used by
    spike/trace-02/evaluate.py (takes order_date, deadline_date,
    payment_date, computes days from those, rounds to 2dp). Retained
    for trace-02 backward compat; not a Catala mirror.

Encodes the deferred-conditional shape of DIFC Practice Direction
4/2017 (Interest on Judgments) + RDC 38.40 (14-day deadline) + 80%
practice convention:

    principal = reasonable_costs * discount_rate
    in_breach iff days_paid_after_order > deadline_days
    days_accrued = (in_breach ? days_paid_after_order - deadline_days : 0)
    interest = principal * simple_interest_rate * days_accrued / 365

Pinned source: see difc_practice_direction_4_2017_source.yaml.
Reliance: research artifact; not legal advice; not court-endorsed.
"""

from datetime import date
from decimal import Decimal, ROUND_HALF_UP


def _D(x) -> Decimal:
    return Decimal(str(x))


def _parse(s: str) -> date:
    return date.fromisoformat(s)


# ---------------------------------------------------------------------
# Catala mirror — the rule-library API.
# ---------------------------------------------------------------------

def outstanding_arbitration_costs(claim: dict) -> dict:
    """Mirrors Catala scope OutstandingArbitrationCosts.

    claim: {
      reasonable_costs_aed: decimal,
      discount_rate: decimal,            # typically 0.80
      deadline_days: decimal,            # typically 14.0
      days_paid_after_order: decimal,
      simple_interest_rate: decimal,     # 0.09 post-2017-11-20; EIBOR_3mo+0.01 pre
    }

    Returns the ArbitrationCostsAward struct — full-precision (no
    rounding); the Catala interpreter likewise emits unrounded
    rationals. A separate `_quantize_award` helper is provided for
    callers that want 2-decimal-place output.
    """
    reasonable = _D(claim["reasonable_costs_aed"])
    discount = _D(claim["discount_rate"])
    deadline = _D(claim["deadline_days"])
    days_paid = _D(claim["days_paid_after_order"])
    rate = _D(claim["simple_interest_rate"])

    principal = reasonable * discount
    in_breach = days_paid > deadline
    accrued = (days_paid - deadline) if in_breach else _D(0)
    interest = principal * rate * accrued / _D("365.00")

    return {
        "principal_aed": principal,
        "deadline_days": deadline,
        "in_breach": in_breach,
        "days_accrued": accrued,
        "interest_aed": interest,
        "total_owed_aed": principal + interest,
    }


def quantize_award(award: dict) -> dict:
    """Return a copy of an ArbitrationCostsAward with currency fields
    quantized to 2 decimal places (HALF_UP). Use when handing the
    award to a downstream system that expects pennies."""
    q = Decimal("0.01")
    return {
        **award,
        "principal_aed": _D(award["principal_aed"]).quantize(q, rounding=ROUND_HALF_UP),
        "interest_aed": _D(award["interest_aed"]).quantize(q, rounding=ROUND_HALF_UP),
        "total_owed_aed": _D(award["total_owed_aed"]).quantize(q, rounding=ROUND_HALF_UP),
    }


# ---------------------------------------------------------------------
# Legacy trace-02 evaluator (NOT a Catala mirror — date-based input).
# ---------------------------------------------------------------------

def outstanding_obligation(order: dict, status: dict) -> dict:
    """Trace-02 narrative evaluator. Takes dates and computes days
    inline; rounds to 2dp. Retained for trace-02's evaluate.py.
    Not a Catala mirror.

    Inputs:
      order: {principal_aed, interest_rate_pa, order_date, deadline_date}
      status: {paid, as_of, payment_date}
    """
    principal = _D(order["principal_aed"])
    rate = _D(order["interest_rate_pa"])
    order_date = _parse(order["order_date"])
    deadline = _parse(order["deadline_date"])

    paid = bool(status["paid"])
    as_of = _parse(status["as_of"])
    payment_date = _parse(status["payment_date"])

    reference_date = payment_date if paid else as_of
    in_breach = reference_date > deadline

    days = (reference_date - order_date).days if in_breach else 0

    interest = (principal * rate * Decimal(days) / Decimal(365)).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    total = (principal + interest).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    return {
        "deadline": deadline.isoformat(),
        "in_breach": in_breach,
        "days_accrued": days,
        "interest_accrued_aed": interest,
        "total_owed_aed": total,
    }


__all__ = [
    "outstanding_arbitration_costs",
    "quantize_award",
    "outstanding_obligation",
]
