"""
Pure-Python reference evaluator for uae_civil_code_art_390.

Mirrors the Catala scope Article390Cap. Captures TWO distinct
mechanisms:

  1. Contract-clause LD cap (e.g. 10% of contract value). Engages
     automatically per the contract's own terms — no court finding
     required.

  2. UAE Civil Transactions Law Article 390(2) variation. The court
     has a separate statutory discretion to vary the agreed
     compensation to make it equal to actual loss, on application by
     either party. Engages only where the court was asked AND made
     the predicate gross-disproportion finding.

Inputs (LDClaim):
  contract_value_aed
  contract_cap_rate
  contract_caps_ld
  uncapped_amount_aed
  court_asked_to_vary_under_390_2
  court_finds_grossly_disproportionate

Outputs (LDAward):
  contract_cap_aed
  after_contract_cap_aed
  awarded_aed
  was_contract_capped
  was_390_2_varied
"""

from decimal import Decimal

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _inputs import as_bool, as_decimal  # noqa: E402


def _D(x) -> Decimal:
    return Decimal(str(x))


def article_390_cap(claim: dict) -> dict:
    contract_value = as_decimal(claim, "contract_value_aed")
    cap_rate = as_decimal(claim, "contract_cap_rate", maximum=Decimal(1))
    uncapped = as_decimal(claim, "uncapped_amount_aed")
    contract_caps_ld = as_bool(claim, "contract_caps_ld")
    asked_to_vary = as_bool(claim, "court_asked_to_vary_under_390_2")
    finds_disproportion = as_bool(claim, "court_finds_grossly_disproportionate")

    raw_cap = contract_value * cap_rate
    contract_cap = raw_cap if contract_caps_ld else _D(0)
    if contract_caps_ld and uncapped > raw_cap:
        after_contract_cap = raw_cap
    else:
        after_contract_cap = uncapped

    was_contract_capped = (
        contract_caps_ld and after_contract_cap < uncapped
    )
    was_390_2_varied = asked_to_vary and finds_disproportion

    return {
        "contract_cap_aed": contract_cap,
        "after_contract_cap_aed": after_contract_cap,
        "awarded_aed": after_contract_cap,
        "was_contract_capped": was_contract_capped,
        "was_390_2_varied": was_390_2_varied,
        # False when Art 390(2) engaged: awarded_aed is then the sum BEFORE
        # the court's variation, which this module does not compute.
        "awarded_is_final": not was_390_2_varied,
    }


__all__ = ["article_390_cap"]
