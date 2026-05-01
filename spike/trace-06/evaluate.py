#!/usr/bin/env python3
"""Predicate evaluator for trace #6 — SICC, NY Convention recognition.

Mirrors the Catala scope CompositeJudgment in rule.catala_en. Walks the
four grounds pleaded under Singapore IAA s 31 and the nine paragraphs of
the Tribunal's Order 3, then checks the final disposition against the
court's order at para 185.

Source: SIC/OA 9/2025, GNC Holdings LLC v ONI Global Pte Ltd
        [2025] SGHC(I) 25, Allsop IJ delivering 21 October 2025.
"""
import json
import os
import sys


HERE = os.path.dirname(os.path.abspath(__file__))


def evaluate(events):
    grounds = events["grounds"]
    g4 = next(g for g in grounds if g["id"] == "G4")
    excised = g4.get("excised_paragraphs", [])
    enforced = g4.get("enforced_paragraphs", [])

    n_pleaded = len(grounds)
    n_dismissed = sum(1 for g in grounds if g["court_outcome"] == "Dismissed")
    n_partial = sum(1 for g in grounds if g["court_outcome"] == "AllowedInPart")
    n_full = sum(1 for g in grounds if g["court_outcome"] == "AllowedInFull")

    if n_full > 0:
        application = "AwardSetAside"
    elif n_partial > 0:
        application = "ApplicationAllowedInPart"
    else:
        application = "ApplicationDismissedEntirely"

    award_enforced = (n_full == 0)
    n_excised = len(excised)

    return {
        "n_grounds_pleaded": n_pleaded,
        "n_grounds_dismissed": n_dismissed,
        "n_grounds_partial": n_partial,
        "n_grounds_full": n_full,
        "application_disposition": application,
        "award_enforced": award_enforced,
        "n_paras_excised": n_excised,
        "excised_paragraphs": excised,
        "enforced_paragraphs": enforced,
    }


def main():
    with open(f"{HERE}/events.json") as f:
        events = json.load(f)

    result = evaluate(events)
    orders = events["court_orders_para_185"]

    checks = [
        ("Four grounds pleaded under IAA s 31",
         result["n_grounds_pleaded"], 4),
        ("Three grounds dismissed (G1, G2, G3)",
         result["n_grounds_dismissed"], 3),
        ("One ground allowed in part (G4)",
         result["n_grounds_partial"], 1),
        ("No ground fully allowed",
         result["n_grounds_full"], 0),
        ("Application disposition matches para 185(a)",
         result["application_disposition"], "ApplicationAllowedInPart"),
        ("Award enforced (with variations) — para 185(c)",
         result["award_enforced"], True),
        ("Three paragraphs of Order 3 excised — para 185(b)",
         result["n_paras_excised"], 3),
        ("Excised paragraphs match the court's list",
         sorted(result["excised_paragraphs"]),
         sorted(["Order 3(d)(ii)", "Order 3(d)(iii)", "Order 3(f)"])),
    ]

    print(f"\nTrace #6 — {events['case_no']} ({events['neutral_citation']})")
    print(f"  {events['claimant']['entity']} v {' & '.join(d['entity'] for d in events['defendants'])}")
    print(f"  Panel: {', '.join(events['panel'])}")
    print(f"  Hearing {events['hearing_date']}; judgment {events['judgment_date']}")
    print()

    print("Per-ground reasoning:")
    for g in events["grounds"]:
        print(f"  {g['id']} ({g['statute']}) — {g['court_outcome']}: {g['label']}")
    print()

    print("Order 3 disposition (para 185(b)-(c)):")
    print(f"  enforced:     {result['enforced_paragraphs']}")
    print(f"  not enforced: {result['excised_paragraphs']}")
    print()

    print("Predicate-vs-court checks:")
    failures = 0
    for label, actual, expected in checks:
        ok = actual == expected
        mark = "OK" if ok else "FAIL"
        print(f"  [{mark}] {label}: predicate={actual!r} court={expected!r}")
        if not ok:
            failures += 1

    print()
    print(f"Court's order at para 185(a): {orders['(a)']}")
    print(f"Court's order at para 185(b): {orders['(b)']}")
    print(f"Court's order at para 185(c): {orders['(c)']}")
    print()

    if failures:
        print(f"FAIL — {failures} check(s) did not reproduce the court's order.")
        sys.exit(1)
    print("All 8 checks reproduce the court's order at para 185.")


if __name__ == "__main__":
    main()
