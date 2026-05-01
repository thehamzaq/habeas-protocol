#!/usr/bin/env python3
"""Predicate evaluator for trace #7 — DIFC DEC, Norwich Pharmacal +
Bankers Trust + RDC 28.52 third-party disclosure.

Mirrors the Catala scope ThirdPartyDisclosureOrder in rule.catala_en.
Walks the three jurisdictional gates (each conjunctive over its own
elements), the four-respondent posture, and the agreed compliance
windows, and checks the result against Black KC's order at para 24.

Source: DEC 001/2025, Techteryx Ltd v IG Limited (and others), Order
        of H.E. Justice Michael Black KC, 3 April 2026.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def evaluate(events):
    nph_made_out = all(x["satisfied"] for x in events["norwich_pharmacal_elements"])
    bt_made_out  = all(x["satisfied"] for x in events["bankers_trust_elements"])
    rdc_made_out = all(x["satisfied"] for x in events["rdc_2852_conditions"])
    all_gates = nph_made_out and bt_made_out and rdc_made_out

    respondents = events["respondents"]
    n_resp = len(respondents)
    # The "opposes substance" posture comes from the witness statement; in this
    # case James Fisher said IG does not oppose, so 0 — but we model it
    # explicitly so a future trace with a contested response can reuse the rule.
    n_opposing = sum(1 for r in respondents if r.get("opposes_substance", False))

    return {
        "nph_made_out": nph_made_out,
        "bankers_trust_made_out": bt_made_out,
        "rdc_2852_made_out": rdc_made_out,
        "all_gates_satisfied": all_gates,
        "order_granted": all_gates,
        "n_respondents": n_resp,
        "n_respondents_opposing_substance": n_opposing,
        "information_window_days": events["compliance_windows"]["information_confirmation_days"],
        "documents_window_days": events["compliance_windows"]["documents_production_days"],
    }


def main():
    with open(f"{HERE}/events.json") as f:
        events = json.load(f)

    result = evaluate(events)
    order = events["court_order_para_24"]

    checks = [
        ("Norwich Pharmacal — all four elements made out",
         result["nph_made_out"], True),
        ("Bankers Trust — all three elements made out",
         result["bankers_trust_made_out"], True),
        ("RDC 28.52 — both conditions made out",
         result["rdc_2852_made_out"], True),
        ("All three gates conjunctively satisfied",
         result["all_gates_satisfied"], True),
        ("Order granted (para 24)",
         result["order_granted"], True),
        ("Four IG respondents",
         result["n_respondents"], 4),
        ("None opposing substance — Fisher witness statement",
         result["n_respondents_opposing_substance"], 0),
        ("Information window: 14 days (para 24(1))",
         result["information_window_days"], 14),
        ("Documents window: 21 days (modification agreed at para 19, ordered para 24(2))",
         result["documents_window_days"], 21),
    ]

    print(f"\nTrace #7 — {events['case_no']}")
    print(f"  {events['claimant']['entity']} v {' & '.join(r['entity'] for r in events['respondents'])}")
    print(f"  Tribunal: {events['tribunal']}")
    print(f"  Judge: {events['judge']}")
    print(f"  Order date: {events['order_date']}")
    print(f"  Underlying fraud: USD {events['underlying_dispute']['alleged_fraud_quantum_usd']:,}")
    print(f"  Tracing target: {events['underlying_dispute']['tracing_target']}")
    print()

    print("Three jurisdictional gates (each conjunctive over its elements):")
    for gate, name in [
        ("norwich_pharmacal_elements", "Norwich Pharmacal"),
        ("bankers_trust_elements", "Bankers Trust"),
        ("rdc_2852_conditions", "RDC 28.52"),
    ]:
        elements = events[gate]
        n_made_out = sum(1 for e in elements if e["satisfied"])
        print(f"  {name:18s}: {n_made_out}/{len(elements)} made out — {'✓' if n_made_out == len(elements) else '✗'}")
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
    print(f"Court's order at para 24:")
    for k, v in order.items():
        print(f"  {k}: {v}")
    print()

    if failures:
        print(f"FAIL — {failures} check(s) did not reproduce the court's order.")
        sys.exit(1)
    print("All 9 checks reproduce the court's order at para 24.")


if __name__ == "__main__":
    main()
