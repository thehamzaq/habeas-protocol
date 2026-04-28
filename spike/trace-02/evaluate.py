#!/usr/bin/env python3
"""Predicate evaluator for trace #2 — DIFC RDC 38.40 + PD 4/2017.

Mirrors the Catala scope OutstandingObligation in rule.catala_en. Encodes
the deferred-conditional shape of the Oberlin v Ovidiu costs order:

    if payment is made within `deadline_days` of `order_date`:
        no interest accrues
    otherwise:
        interest accrues at `interest_rate_pa` per annum, day-count
        basis 365, FROM `order_date` (not from the deadline) UNTIL
        payment in full.

The predicate is run against each scenario in events.json and reports
whether the computed amount-owed schedule matches the expected schedule.
"""
import json
import os
import sys
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

HERE = os.path.dirname(os.path.abspath(__file__))


def _d(x):
    return Decimal(str(x))


def _parse(s):
    return date.fromisoformat(s)


def outstanding_obligation(order, status):
    """RDC 38.40 + PD 4/2017 outstanding-obligation predicate."""
    principal = _d(order["principal_aed"])
    rate = _d(order["interest_rate_pa"])
    order_date = _parse(order["order_date"])
    deadline = _parse(order["deadline_date"])

    paid = bool(status["paid"])
    as_of = _parse(status["as_of"])
    payment_date = _parse(status["payment_date"])

    reference_date = payment_date if paid else as_of
    in_breach = reference_date > deadline

    if in_breach:
        days = (reference_date - order_date).days
    else:
        days = 0

    interest = (principal * rate * Decimal(days) / Decimal(365))
    interest = interest.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    total = (principal + interest).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    return {
        "deadline": deadline.isoformat(),
        "in_breach": in_breach,
        "days_accrued": days,
        "interest_accrued_aed": interest,
        "total_owed_aed": total,
    }


def main():
    with open(f"{HERE}/events.json") as f:
        log = json.load(f)

    order_event = next(e for e in log["events"] if e["type"] == "costs_order_issued")
    order = order_event["order"]

    print(f"Case: {log['case_no']}")
    print(f"Parties: {log['parties']['claimant']} v {log['parties']['defendant']}")
    print(f"Rule: {log['rule_source']['instruments'][0]}")
    print(f"      {log['rule_source']['instruments'][1]}")
    print()
    print(
        f"Order: principal AED {order['principal_aed']:,.2f}, "
        f"date {order['order_date']}, "
        f"deadline {order['deadline_date']} (+{order['deadline_days']} days), "
        f"interest {order['interest_rate_pa']*100:.0f}% p.a."
    )
    print()
    print("Predicate evaluation across scenarios:")
    print()

    fmt = "  {label:<22} {breach:<10} {days:>4}d  {interest:>10}  {total:>12}"
    print(fmt.format(label="scenario", breach="in_breach", days="days",
                     interest="interest", total="total_owed"))
    print("  " + "-" * 70)

    failures = 0
    for sc in log["scenarios"]:
        owed = outstanding_obligation(order, sc["status"])
        print(fmt.format(
            label=sc["label"],
            breach=str(owed["in_breach"]),
            days=owed["days_accrued"],
            interest=f"{owed['interest_accrued_aed']:,}",
            total=f"{owed['total_owed_aed']:,}",
        ))

        exp = sc.get("expected")
        if not exp:
            continue
        ok = (
            owed["in_breach"] == exp["in_breach"]
            and owed["days_accrued"] == exp["days_accrued"]
            and owed["interest_accrued_aed"] == _d(exp["interest_accrued_aed"])
            and owed["total_owed_aed"] == _d(exp["total_owed_aed"])
        )
        if not ok:
            failures += 1
            print(
                f"    FAIL — expected in_breach={exp['in_breach']}, "
                f"days={exp['days_accrued']}, "
                f"interest={exp['interest_accrued_aed']}, "
                f"total={exp['total_owed_aed']}"
            )

    print()
    if failures == 0:
        print("PASS — all scenarios match the predicate.")
    else:
        print(f"FAIL — {failures} scenario(s) diverged.")
        sys.exit(1)


if __name__ == "__main__":
    main()
