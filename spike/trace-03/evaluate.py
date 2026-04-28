#!/usr/bin/env python3
"""Predicate evaluator for trace #3 — indemnity-basis costs review.

Mirrors the Catala scope IndemnityBasisReview in rule.catala_en. This is
the bounded-discretion case: the rule strips proportionality and leaves
reasonableness, which is not formulaic. The predicate's job is therefore
NOT to derive a single award number, but to:

    1. Mechanically dispose of objections that fail the "names a specific
       element of the schedule" structural test (Cooke J., §4).
    2. Hold deterministic findings (rejected_on_evidence,
       accepted_with_named_amount) and resolve them.
    3. Flag the residual region where human judgment is required.

The predicate output is a *triage* of the objections plus, where rules
fully resolve the schedule, a deterministic award. Where rules do not
fully resolve it, the predicate exits with requires_human_judgment=true.

On the facts of ENF 271/2025 the predicate disposes of one objection,
holds another at zero on evidence, and surfaces the residual senior-
associate-time concern as bounded discretion. The court's AED 8,914.80
reduction is the structured-discretion residue.
"""
import json
import os
import sys
from decimal import Decimal, ROUND_HALF_UP

HERE = os.path.dirname(os.path.abspath(__file__))


def _d(x):
    return Decimal(str(x))


def _q(x):
    return _d(x).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def indemnity_basis_review(schedule):
    """Indemnity-basis review predicate.

    schedule = { "claimed_aed": Decimal, "objections": [Objection] }

    Each objection is triaged into one of four buckets:
      - mechanically_disposed:   no specific line item named
      - held_to_zero:            specific + rejected_on_evidence
      - deterministic_reduction: specific + accepted_with_named_amount
      - requires_human_judgment: anything else
    """
    claimed = _d(schedule["claimed_aed"])

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
            deterministic.append((o["label"], _d(o["named_amount_aed"])))
        else:
            residual.append(o["label"])

    det_reductions = sum((amt for _, amt in deterministic), _d(0))
    requires_human = len(residual) > 0
    deterministic_award = (
        None if requires_human else _q(claimed - det_reductions)
    )

    return {
        "claimed_aed": _q(claimed),
        "objections_mechanically_disposed": mechanically_disposed,
        "objections_held_to_zero": held_to_zero,
        "objections_deterministic_reductions": deterministic,
        "objections_requiring_human_judgment": residual,
        "deterministic_reductions_aed": _q(det_reductions),
        "requires_human_judgment": requires_human,
        "deterministic_award_aed": deterministic_award,
    }


def _resolve_schedule(log, scenario):
    if "schedule_override" in scenario:
        return scenario["schedule_override"]
    assess = next(e for e in log["events"] if e["type"] == "indemnity_assessment")
    return assess["schedule"]


def _check(label, computed, expected):
    """Validate a single scenario result against expected fields."""
    failures = []
    for k, want in expected.items():
        got = computed.get(k)
        if k.endswith("_aed"):
            if _d(got) != _d(want):
                failures.append(f"{k}: expected {want}, got {got}")
        elif isinstance(want, list):
            if sorted(got or []) != sorted(want):
                failures.append(f"{k}: expected {want}, got {got}")
        else:
            if got != want:
                failures.append(f"{k}: expected {want}, got {got}")
    return failures


def main():
    with open(f"{HERE}/events.json") as f:
        log = json.load(f)

    print(f"Case: {log['case_no']}")
    print(f"Parties: {log['parties']['claimant']} v {log['parties']['defendant']}")
    print(f"Rule: {log['rule_source']['instrument']}")
    print(f"Principle: {log['rule_source']['governing_principle']}")
    print()
    print(
        f"Court's actual award: AED {log['human_ruling']['awarded_aed']:,.2f} "
        f"(claimed AED {log['human_ruling']['claimed_aed']:,.2f}; "
        f"discretion residue AED {log['human_ruling']['discretion_delta_aed']:,.2f}, "
        f"~{log['human_ruling']['discretion_delta_pct']:.2f}% of claim)"
    )
    print()

    total_failures = 0
    for sc in log["scenarios"]:
        schedule = _resolve_schedule(log, sc)
        review = indemnity_basis_review(schedule)

        print(f"=== Scenario: {sc['label']} ===")
        print(f"  claimed:                       AED {review['claimed_aed']:,}")
        print(f"  mechanically disposed:         {review['objections_mechanically_disposed']}")
        print(f"  held to zero (rejected):       {review['objections_held_to_zero']}")
        print(
            "  deterministic reductions:      "
            + str([(lbl, str(amt)) for lbl, amt in review['objections_deterministic_reductions']])
        )
        print(f"  requires human judgment:       {review['objections_requiring_human_judgment']}")
        print(f"  deterministic_reductions_aed:  AED {review['deterministic_reductions_aed']:,}")
        print(f"  requires_human_judgment:       {review['requires_human_judgment']}")
        if review["deterministic_award_aed"] is not None:
            print(f"  deterministic_award_aed:       AED {review['deterministic_award_aed']:,}")
        else:
            print(f"  deterministic_award_aed:       — (bounded-discretion residue)")

        exp = sc.get("expected")
        if exp:
            failures = _check(sc["label"], review, exp)
            if failures:
                total_failures += len(failures)
                for f in failures:
                    print(f"    FAIL — {f}")
            else:
                print("  PASS")
        print()

    if total_failures == 0:
        print("PASS — all scenarios match the predicate.")
        print()
        award = _d(log["human_ruling"]["awarded_aed"])
        claimed = _d(log["human_ruling"]["claimed_aed"])
        residue = _q(claimed - award)
        print(
            f"Constructive finding: on ENF 271/2025 the predicate "
            f"disposes of 1 objection mechanically and holds 1 at zero "
            f"on the evidence, leaving 1 in the human-judgment region. "
            f"The AED {residue} reduction is the structured-discretion residue."
        )
    else:
        print(f"FAIL — {total_failures} expectation(s) diverged.")
        sys.exit(1)


if __name__ == "__main__":
    main()
