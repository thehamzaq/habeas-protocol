#!/usr/bin/env python3
"""Predicate evaluator for trace #1 — DIFC RDC Part 38 standard-basis costs.

Mirrors the Catala scope StandardBasisAssessment in rule.catala_en. Runs the
same predicate against events.json and reports whether the evaluator's
output matches the human ruling.
"""
import json
import os
import sys
from decimal import Decimal

HERE = os.path.dirname(os.path.abspath(__file__))


def assess_standard_basis(claim):
    """RDC Part 38 standard-basis cost assessment.

    professional_time = hours_worked * hourly_rate
    disbursements     = court_fee
    total             = professional_time + disbursements
    """
    hours = Decimal(str(claim["hours_worked"]))
    rate = Decimal(str(claim["hourly_rate_aed"]))
    fee = Decimal(str(claim["court_fee_aed"]))
    professional_time = hours * rate
    disbursements = fee
    total = professional_time + disbursements
    return {
        "professional_time_aed": professional_time,
        "disbursements_aed": disbursements,
        "total_aed": total,
    }


def main():
    with open(f"{HERE}/events.json") as f:
        log = json.load(f)

    assessment_event = next(e for e in log["events"] if e["type"] == "costs_assessment")
    award = assess_standard_basis(assessment_event["claim"])
    schedule_total = Decimal(str(log["human_ruling"]["schedule_total_aed"]))
    operative_total = Decimal(str(log["human_ruling"]["stated_total_aed"]))

    print(f"Case: {log['case_no']}")
    print(f"Rule: {log['rule_source']['instrument']}")
    print()
    print("Predicate evaluation:")
    print(f"  professional_time_aed = {award['professional_time_aed']}")
    print(f"  disbursements_aed     = {award['disbursements_aed']}")
    print(f"  total_aed             = {award['total_aed']}")
    print()
    print(f"Human ruling (Schedule of Reasons): AED {schedule_total}")
    print(f"Human ruling (operative order):     AED {operative_total}")
    print()

    if award["total_aed"] == schedule_total:
        print(f"PASS — predicate matches Schedule of Reasons total.")
    else:
        print(f"FAIL — predicate {award['total_aed']} != schedule {schedule_total}.")
        sys.exit(1)

    if operative_total != schedule_total:
        print(
            f"FLAG — operative order ({operative_total}) differs from schedule "
            f"total ({schedule_total}) by {operative_total - schedule_total} AED. "
            f"The protocol surfaces an arithmetic discrepancy in the order."
        )


if __name__ == "__main__":
    main()
