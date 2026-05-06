"""
Pure-Python reference evaluator for ladd_v_marshall.

Mirrors the Catala scope LaddMarshallTest. Three-prong fresh-evidence
test from Ladd v Marshall [1954] 1 WLR 1489:

  (a) the evidence could not have been obtained with reasonable
      diligence for use at the trial;
  (b) the evidence is such that, if given, it would probably have an
      important influence on the result;
  (c) the evidence is such as is presumably to be believed (not
      incredible).

Conjunctive: ALL THREE must be satisfied. Canonical practice short-
circuits at the first failing prong (the dispositive ground). The
predicate honours that order so the surfaced "first failing prong" is
the one a court would cite.
"""

from typing import List


def ladd_marshall_test(prongs: List[dict]) -> dict:
    """Apply the three-prong test in canonical order.

    prongs: list of {label, satisfied (bool), court_finding (str)}
            in canonical order: (a), (b), (c).

    Returns:
      new_evidence_admissible (bool)
      first_failing_prong (str | None)
      short_circuited_at (int | None)  -- 1-indexed position of the
                                           first failing prong (None if all pass)
    """
    for i, p in enumerate(prongs, 1):
        if not p["satisfied"]:
            return {
                "new_evidence_admissible": False,
                "first_failing_prong": p["label"],
                "short_circuited_at": i,
                "all_prongs_satisfied": False,
            }
    return {
        "new_evidence_admissible": True,
        "first_failing_prong": None,
        "short_circuited_at": None,
        "all_prongs_satisfied": True,
    }


__all__ = ["ladd_marshall_test"]
