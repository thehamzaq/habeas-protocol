"""
Pure-Python reference evaluator for adgm_cpr_summary_judgment.

Mirrors the Catala scope SummaryJudgmentTest. ADGM CPR summary-judgment
threshold: a defendant has summary judgment entered against them iff
BOTH limbs are made out:
  - no realistic prospect of success at trial; AND
  - no compelling reason for the case to go to trial.

A failure of either limb defeats the application.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _inputs import as_bool  # noqa: E402


def summary_judgment_test(application: dict) -> dict:
    no_prospect = as_bool(application, "no_realistic_prospect")
    no_compelling = as_bool(application, "no_compelling_reason")
    both = no_prospect and no_compelling
    return {
        "both_limbs_made_out": both,
        "summary_judgment_granted": both,
    }


__all__ = ["summary_judgment_test"]
