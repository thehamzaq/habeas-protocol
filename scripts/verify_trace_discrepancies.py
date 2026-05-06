"""
CI guard: assert the count of flagged trace discrepancies matches the
claim in paper.md / README.md.

Currently both documents claim "3 of 7 traces surface a clerical or
methodological gap." If a trace's discrepancy.json is added/removed/
flipped, this script catches the drift before publication.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPIKE = ROOT / "spike"

EXPECTED_FLAGGED = 3
EXPECTED_TOTAL_TRACES = 7


def main():
    flagged = []
    none_kind = []
    missing = []
    for tdir in sorted(SPIKE.glob("trace-*")):
        if not tdir.is_dir():
            continue
        disc = tdir / "discrepancy.json"
        if not disc.exists():
            missing.append(tdir.name)
            continue
        rec = json.loads(disc.read_text())
        if rec["kind"] != "none":
            flagged.append((tdir.name, rec["kind"]))
        else:
            none_kind.append(tdir.name)

    n_flagged = len(flagged)
    n_total = n_flagged + len(none_kind)

    print(f"flagged ({n_flagged}):")
    for t, k in flagged:
        print(f"  {t}  {k}")
    print(f"clean ({len(none_kind)}):")
    for t in none_kind:
        print(f"  {t}")
    if missing:
        print(f"MISSING discrepancy.json: {missing}")
        sys.exit(2)

    if n_total != EXPECTED_TOTAL_TRACES:
        print(f"\nFAIL — expected {EXPECTED_TOTAL_TRACES} traces, "
              f"found {n_total}")
        sys.exit(1)
    if n_flagged != EXPECTED_FLAGGED:
        print(f"\nFAIL — paper.md claims {EXPECTED_FLAGGED} of "
              f"{EXPECTED_TOTAL_TRACES} surface a gap; found {n_flagged}")
        sys.exit(1)
    print(f"\nOK — {n_flagged} of {n_total} traces flagged, matches paper.md")


if __name__ == "__main__":
    main()
