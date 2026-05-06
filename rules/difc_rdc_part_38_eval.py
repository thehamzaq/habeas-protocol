"""
Pure-Python reference evaluator for the `difc_rdc_part_38` Catala module.

Mirrors the StandardBasisAssessment scope in difc_rdc_part_38.catala_en.
This is the *runtime* — Catala source remains the *spec*. The conformance
test (difc_rdc_part_38_conformance.py) asserts that running both gives
identical results on canonical inputs, so users can rely on the Python
evaluator without an opam toolchain on the host.

This was lifted from spike/trace-01/evaluate.py — that trace bundles the
event-log handling and the rule arithmetic; here only the rule arithmetic.

Pinned source: see difc_rdc_part_38_source.yaml.
Reliance disclaimer: research artifact; not legal advice; not court-endorsed.
"""

from decimal import Decimal
from typing import TypedDict, Union


_Number = Union[Decimal, float, int, str]


class CostsClaim(TypedDict):
    hours_worked: _Number
    hourly_rate_aed: _Number
    reasonable_disbursements_aed: _Number


class StandardBasisAward(TypedDict):
    professional_time_aed: Decimal
    disbursements_aed: Decimal
    total_aed: Decimal


def _D(x) -> Decimal:
    return Decimal(str(x))


def assess_standard_basis(claim: CostsClaim) -> StandardBasisAward:
    """RDC Part 38 standard-basis assessment.

    Catala scope: StandardBasisAssessment.
        professional_time_aed = hours_worked * hourly_rate_aed
        disbursements_aed     = reasonable_disbursements_aed
        total_aed             = professional_time + disbursements
    """
    hours = _D(claim["hours_worked"])
    rate = _D(claim["hourly_rate_aed"])
    disb = _D(claim["reasonable_disbursements_aed"])
    pt = hours * rate
    return {
        "professional_time_aed": pt,
        "disbursements_aed": disb,
        "total_aed": pt + disb,
    }


__all__ = ["assess_standard_basis", "CostsClaim", "StandardBasisAward"]
