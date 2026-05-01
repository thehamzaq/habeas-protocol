#!/usr/bin/env python3
"""Predicate evaluator for trace #5 — conjunctive logical composition.

Mirrors the Catala scope CompositeJudgment in rule.catala_en. Encodes the
structural reasoning of ADGMCFI-2024-158 Xetech v Pulsar:

    1. ClauseAlignment   — all named clauses must point the same way
                           (clauses 2(b), 7, 10 — payment before transfer).
    2. WeightOfEvidence  — preponderance counted from named witnesses
                           against the burden borne by the claimant.
    3. LaddMarshallTest  — three-prong conjunctive admissibility test;
                           failure of any prong is dispositive (monotonic,
                           short-circuiting on canonical order:
                           diligence -> influence -> credibility).
    4. Disposition       — Judgment Sum is the face-value total of the
                           five invoices the court accepted (para 5,
                           para 99(a)(i)). Costs are claimed costs +
                           court fees (the court found these reasonable
                           and proportionate, so they pass through
                           unmodified).

The methodologically distinct feature of trace #5: the rule is Boolean,
not arithmetic. The protocol does not replace contractual interpretation
or witness credibility assessment - those remain human judgments. What
it makes auditable is the LOGICAL STRUCTURE: that the court's holding
is the conjunction of named, individually-recorded findings, and that
the Ladd v Marshall test was applied in canonical order with
short-circuiting on the first failing prong.
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


def composite_judgment(facts):
    """ADGMCFI-2024-158 conjunctive-composition predicate."""

    # (1) Clause alignment - conjunction over named clauses
    clauses = facts["clauses"]
    misaligned = [
        c for c in clauses if not c["points_to_payment_before_transfer"]
    ]
    aligned = len(misaligned) == 0
    interpretation_holding = (
        "Xetech entitled to be paid before transfer of source code"
        if aligned
        else "clauses do not align - interpretation contested"
    )

    # (2) Weight of evidence - named-witness preponderance
    witnesses = facts["witnesses"]
    supporters = [w for w in witnesses if w["supports_completion"]]
    dissenters = [w for w in witnesses if not w["supports_completion"]]
    completion_proven = len(supporters) > len(dissenters)

    # The court placed special weight on access to the DevOps system.
    # Surface this as auxiliary structural info: of the dissenters,
    # how many lacked DevOps access? (Mr Anil and Mr Emam: both 0 access.)
    dissenters_without_devops = [
        w for w in dissenters if not w.get("accessed_devops", False)
    ]

    # (3) Ladd v Marshall - conjunctive, short-circuiting, canonical order
    prongs = facts["ladd_prongs"]
    failing_prongs = [p for p in prongs if not p["satisfied"]]
    new_evidence_admissible = len(failing_prongs) == 0
    first_failing_prong = failing_prongs[0]["label"] if failing_prongs else ""
    short_circuited_after = len(prongs) - len(
        [p for p in prongs[: prongs.index(failing_prongs[0]) + 1]]
        if failing_prongs
        else prongs
    )

    # (4) Disposition arithmetic - sum of accepted-invoice principals
    invoices = facts["outstanding_invoices"]
    judgment_sum = sum((_d(inv["principal_gbp"]) for inv in invoices), _d(0))

    costs = _d(facts["claimed_costs_usd"]) + _d(facts["claimed_court_fees_usd"])

    counterclaim_dismissed = aligned and completion_proven

    return {
        "clauses_aligned": aligned,
        "interpretation_holding": interpretation_holding,
        "supporters_count": len(supporters),
        "dissenters_count": len(dissenters),
        "dissenters_lacking_devops_access": len(dissenters_without_devops),
        "completion_proven": completion_proven,
        "new_evidence_admissible": new_evidence_admissible,
        "first_failing_prong": first_failing_prong,
        "judgment_sum_gbp": _q(judgment_sum),
        "costs_usd": _q(costs),
        "counterclaim_dismissed": counterclaim_dismissed,
    }


def main():
    with open(f"{HERE}/events.json") as f:
        log = json.load(f)
    facts = log["facts"]
    human = log["human_ruling"]

    print(f"Case: {log['case_no']}  ({log['neutral_citation']})")
    print(
        f"Parties: {log['parties']['claimant']} v {log['parties']['defendant']}"
    )
    print(f"Judge: {log['judge']}    Decision: {log['decision_date']}")
    print()
    print("Rule sources:")
    for s in log["rule_source"]["instruments"]:
        print(f"  - {s}")
    print()

    print("Human findings (inputs to predicate):")
    for f in log["human_findings_required"]:
        print(f"  - {f}")
    print()

    out = composite_judgment(facts)

    print("=== Predicate composition over those findings ===")
    print()
    print("(1) ClauseAlignment - conjunction over named clauses:")
    for c in facts["clauses"]:
        marker = "->" if c["points_to_payment_before_transfer"] else "<-"
        print(
            f"    {marker} {c['clause_id']:<12} (judgment {c['court_para_ref']})"
        )
    print(f"    aligned: {out['clauses_aligned']}")
    print(f"    interpretation holding: {out['interpretation_holding']}")
    print()

    print("(2) WeightOfEvidence - named-witness preponderance:")
    print(
        f"    supporters: {out['supporters_count']}    "
        f"dissenters: {out['dissenters_count']}"
    )
    print(
        f"    of dissenters, {out['dissenters_lacking_devops_access']} lacked "
        f"DevOps-system access (court flagged this at para 77, 90-91)"
    )
    print(f"    completion proven on balance of probabilities: {out['completion_proven']}")
    print()

    print("(3) LaddMarshallTest - conjunctive, canonical order:")
    for i, p in enumerate(facts["ladd_prongs"], 1):
        marker = "PASS" if p["satisfied"] else "FAIL"
        print(f"    [{marker}] prong {i}: {p['label']}")
        print(f"           court finding: {p['court_finding']}")
    print(f"    new evidence admissible: {out['new_evidence_admissible']}")
    if not out["new_evidence_admissible"]:
        print(
            f"    first failing prong (dispositive, short-circuiting): "
            f"{out['first_failing_prong']}"
        )
    print()

    print("(4) Disposition arithmetic:")
    for inv in facts["outstanding_invoices"]:
        print(
            f"    {inv['invoice_id']:<6} {inv['label']:<48} "
            f"GBP {inv['principal_gbp']:>10,.2f}"
        )
    print(f"    Judgment Sum (face-value sum of accepted invoices):  "
          f"GBP {out['judgment_sum_gbp']:>10,.2f}")
    print(f"    Costs (claimed costs + court fees):                  "
          f"USD {out['costs_usd']:>10,.2f}")
    print()

    # Validation
    failures = 0
    print("=== Validation against the court's ruling ===")
    checks = [
        (
            "clauses aligned (para 59-60)",
            out["clauses_aligned"],
            True,
        ),
        (
            "interpretation holding (para 60(a))",
            out["interpretation_holding"],
            human["interpretation_holding"],
        ),
        (
            "completion proven (para 92)",
            out["completion_proven"],
            human["completion_proven"],
        ),
        (
            "new evidence admissible (para 49)",
            out["new_evidence_admissible"],
            human["new_evidence_admissible"],
        ),
        (
            "first failing Ladd prong (para 48)",
            out["first_failing_prong"],
            human["first_failing_ladd_prong"],
        ),
        (
            "judgment sum (para 99(a)(i))",
            out["judgment_sum_gbp"],
            _d(human["judgment_sum_gbp"]),
        ),
        (
            "costs (para 99(c))",
            out["costs_usd"],
            _d(human["costs_usd"]),
        ),
        (
            "counterclaim dismissed (para 96, 99(b))",
            out["counterclaim_dismissed"],
            human["counterclaim_dismissed"],
        ),
    ]
    for label, got, exp in checks:
        ok = got == exp
        marker = "PASS" if ok else "FAIL"
        print(f"  [{marker}] {label}")
        print(f"         predicate: {got}")
        print(f"         human:     {exp}")
        if not ok:
            failures += 1

    print()
    if failures == 0:
        print(
            "PASS - the predicate composition reproduces the court's "
            "holding on every axis: clause alignment, evidentiary "
            "preponderance, admissibility (with first-failing-prong "
            "match), judgment sum, costs, and counterclaim. The "
            "constructive claim of trace #5: even contractual-"
            "interpretation reasoning has a verifiable structural "
            "skeleton. The protocol records, per clause and per witness "
            "and per Ladd prong, what the court found; the conjunction "
            "is mechanical."
        )
    else:
        print(f"FAIL - {failures} composition step(s) diverged.")
        sys.exit(1)


if __name__ == "__main__":
    main()
