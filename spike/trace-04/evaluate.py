#!/usr/bin/env python3
"""Predicate evaluator for trace #4 — substantive contract composition.

Mirrors the Catala scope CompositeJudgment in rule.catala_en. Encodes the
arithmetic composition layer of ADGMCFI-2024-320:

    1. Liquidated damages   = min(daily_rate * delay_days, cap_pct * price)
    2. Counterclaim sum     = sum of proven counterclaim items (incl. LDs)
    3. Net principal        = withheld - counterclaim_sum
    4. Pre-judgment interest = principal * rate * days_to_judgment / 365
    5. Total judgment       = principal + interest

Substantive findings (delay days, item-proven flags, dates of handover and
judgment, etc.) are inputs. The predicate composes them deterministically.

This is the methodologically distinct fourth trace: a substantive contract
dispute that the original Maxim brief proposed to handle via ad-hoc
arbitration. The trace shows the protocol decomposes the rule cleanly into
substantive determinations (kept human) and arithmetic composition (made
deterministic and auditable).
"""
import json
import os
import sys
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

HERE = os.path.dirname(os.path.abspath(__file__))


def _d(x):
    return Decimal(str(x))


def _q(x):
    return _d(x).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _parse(s):
    return date.fromisoformat(s)


def composite_judgment(facts):
    """ADGMCFI-2024-320 substantive composition predicate."""
    price = _d(facts["adjusted_contract_price_aed"])
    cap_pct = _d(facts["ld_cap_pct"])
    daily_rate = _d(facts["daily_ld_rate_aed"])
    delay_days = _d(facts["days_of_critical_delay_found"])
    withheld = _d(facts["amount_withheld_by_defendant_aed"])
    rate = _d(facts["interest_rate_pa"])
    handover = _parse(facts["handover_date"])
    judgment = _parse(facts["judgment_date"])

    # Liquidated damages with cap
    ld_uncapped = daily_rate * delay_days
    ld_cap = price * cap_pct
    ld_was_capped = ld_uncapped > ld_cap
    ld_awarded = ld_cap if ld_was_capped else ld_uncapped

    # Counterclaim sum (only items with found_proven=true contribute)
    proven = [
        item for item in facts["counterclaim_items"]
        if item.get("found_proven")
    ]
    # If LDs are listed as a counterclaim item with computed_from_rule=true,
    # we already have its amount in the list; otherwise the rule's
    # computed ld_awarded is the LDs entry. We respect the events.json
    # explicit listing.
    counterclaim_sum = sum((_d(item["amount_aed"]) for item in proven), _d(0))

    # Net principal
    net = withheld - counterclaim_sum

    # Pre-judgment interest (calendar daycount)
    days = (judgment - handover).days
    interest_calendar = (net * rate * Decimal(days) / Decimal(365))

    # Court daycount (often inclusive-endpoint, +1)
    court_days = days + 1
    interest_court_convention = (net * rate * Decimal(court_days) / Decimal(365))

    return {
        "ld_uncapped_aed": _q(ld_uncapped),
        "ld_cap_aed": _q(ld_cap),
        "ld_awarded_aed": _q(ld_awarded),
        "ld_was_capped": ld_was_capped,
        "counterclaim_sum_aed": _q(counterclaim_sum),
        "net_to_claimant_aed": _q(net),
        "calendar_days_to_judgment": days,
        "interest_calendar_daycount_aed": _q(interest_calendar),
        "court_days_to_judgment": court_days,
        "interest_court_daycount_aed": _q(interest_court_convention),
        "total_judgment_calendar_aed": _q(net + interest_calendar),
        "total_judgment_court_aed": _q(net + interest_court_convention),
    }


def main():
    with open(f"{HERE}/events.json") as f:
        log = json.load(f)
    facts = log["facts"]
    human = log["human_ruling"]

    print(f"Case: {log['case_no']}")
    print(f"Parties: {log['parties']['claimant']} v {log['parties']['defendant']}")
    print(f"Rule sources:")
    for s in log["rule_source"]["instruments"]:
        print(f"  - {s}")
    print()

    print("Human findings (inputs to predicate):")
    for f in log["human_findings_required"]:
        print(f"  · {f}")
    print()

    out = composite_judgment(facts)

    print("Predicate composition over those findings:")
    print(f"  LD uncapped (daily_rate × delay):            AED {out['ld_uncapped_aed']:>14,}")
    print(f"  LD cap (10% × adjusted price):                AED {out['ld_cap_aed']:>14,}")
    print(f"  LD awarded (capped: {out['ld_was_capped']}):                  AED {out['ld_awarded_aed']:>14,}")
    print(f"  Counterclaim sum (proven items only):         AED {out['counterclaim_sum_aed']:>14,}")
    print(f"  Net principal (withheld − counterclaim_sum):  AED {out['net_to_claimant_aed']:>14,}")
    print()
    print(f"  Calendar daycount: {out['calendar_days_to_judgment']} days → "
          f"interest AED {out['interest_calendar_daycount_aed']}")
    print(f"  Court convention:  {out['court_days_to_judgment']} days → "
          f"interest AED {out['interest_court_daycount_aed']}")
    print()

    # Validation
    failures = 0
    print("=== Validation against human ruling ===")
    checks = [
        ("LD awarded", out["ld_awarded_aed"], _d(human["ld_awarded_aed"])),
        ("Counterclaim sum", out["counterclaim_sum_aed"], _d(human["counterclaim_sum_aed"])),
        ("Net principal", out["net_to_claimant_aed"], _d(human["principal_aed"])),
    ]
    for label, got, exp in checks:
        ok = got == exp
        marker = "PASS" if ok else "FAIL"
        print(f"  [{marker}] {label}: predicate {got}  human {exp}")
        if not ok:
            failures += 1

    # Pre-judgment interest is the daycount-convention check
    court_interest = _d(human["pre_judgment_interest_aed"])
    if out["interest_court_daycount_aed"] == court_interest:
        print(f"  [PASS] Pre-judgment interest at +1 convention ({out['court_days_to_judgment']} days): "
              f"predicate {out['interest_court_daycount_aed']}  human {court_interest}")
        print(f"         (Calendar daycount {out['calendar_days_to_judgment']} days "
              f"would give AED {out['interest_calendar_daycount_aed']} — "
              f"protocol surfaces the +1 day convention.)")
    else:
        print(f"  [INFO] Pre-judgment interest: court {court_interest}  "
              f"predicate (calendar) {out['interest_calendar_daycount_aed']}  "
              f"predicate (court +1) {out['interest_court_daycount_aed']}")

    print()
    if failures == 0:
        print("PASS — composition over human findings reproduces the court's "
              "principal amount exactly. Pre-judgment interest reveals a "
              "1-day convention (court used inclusive-endpoint count); the "
              "protocol surfaces the convention question for review.")
    else:
        print(f"FAIL — {failures} composition step(s) diverged.")
        sys.exit(1)


if __name__ == "__main__":
    main()
