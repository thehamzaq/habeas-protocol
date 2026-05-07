#!/usr/bin/env python3
"""Add explicit `stance` field to each trace's discrepancy.json.

Stance values:
  - "court_clerical_error": predicate is correct; court's order has a
    transcription/arithmetic error (defended in trace narrative).
  - "predicate_scope_limit": court is correct; predicate did not model
    the relevant convention or scope (acknowledged limitation).
  - "partial_finding_diagnostic": predicate reproduces disposition
    exactly; the "discrepancy" is a structural finding the predicate
    surfaces about the court's reasoning, not a divergence.
  - "none": no discrepancy; trace is clean.

Idempotent.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

STANCE_BY_TRACE = {
    "trace-01": "court_clerical_error",
    "trace-02": "none",
    "trace-03": "none",
    "trace-04": "predicate_scope_limit",
    "trace-05": "none",
    "trace-06": "partial_finding_diagnostic",
    "trace-07": "none",
}

STANCE_NOTE = {
    "court_clerical_error":
        "Stance: court_clerical_error. Schedule of Reasons sums to "
        "AED 7,121.75; operative paragraph states AED 7,127.75. The "
        "predicate is correct against the schedule arithmetic; we "
        "conclude the operative paragraph contains a 6-AED clerical "
        "transposition.",
    "predicate_scope_limit":
        "Stance: predicate_scope_limit. The court applies an inclusive-"
        "endpoint daycount convention (610 days) the predicate did not "
        "model (609 calendar days). This is recorded as a daycount "
        "scope limitation in the predicate, not a court error.",
    "partial_finding_diagnostic":
        "Stance: partial_finding_diagnostic. The predicate reproduces "
        "the court's disposition at para 185(a)–(c) exactly. The "
        "structural finding (tribunal exceeded submissions on three "
        "named sub-paragraphs) is what the predicate surfaces about "
        "the reasoning, not a divergence from the disposition.",
    "none": "Stance: none. No predicate-vs-court divergence.",
}


def main():
    for trace_id, stance in STANCE_BY_TRACE.items():
        path = ROOT / "spike" / trace_id / "discrepancy.json"
        if not path.exists():
            print(f"  skip (missing): {path}")
            continue
        data = json.loads(path.read_text())
        data["stance"] = stance
        # Append stance note to the existing note (idempotent: only if not
        # already present).
        existing_note = data.get("note") or ""
        stance_note = STANCE_NOTE[stance]
        if "Stance:" not in existing_note:
            data["note"] = (existing_note + " " + stance_note).strip()
        path.write_text(json.dumps(data, indent=2))
        print(f"  {trace_id}: stance={stance}")


if __name__ == "__main__":
    main()
