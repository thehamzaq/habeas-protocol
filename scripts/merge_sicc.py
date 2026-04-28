#!/usr/bin/env python3
"""Merge SICC graded entries into judgments.json.

Reads data/sicc_graded.json and data/judgments.json, validates the new
entries match the existing schema (loose check), backs up judgments.json
to judgments.json.pre_sicc.bak, and appends.
"""
import json
import os
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(HERE + "/..")
JUDGMENTS = ROOT + "/data/judgments.json"
BACKUP = ROOT + "/data/judgments.json.pre_sicc.bak"
GRADED = ROOT + "/data/sicc_graded.json"


REQUIRED = {"case_no", "url", "tribunal", "division", "date_issued",
            "parties", "judge", "claim_type", "primitive_scores_v02", "coding"}


def main():
    with open(JUDGMENTS) as f:
        existing = json.load(f)
    with open(GRADED) as f:
        graded = json.load(f)
    new_entries = graded["entries"]

    # Validate each
    bad = []
    for e in new_entries:
        missing = REQUIRED - set(e.keys())
        if missing:
            bad.append((e.get("neutral_citation"), missing))
    if bad:
        print("VALIDATION FAILURES:")
        for c, m in bad:
            print(f"  {c}: missing {m}")
        return

    # Dedupe by url
    existing_urls = {e["url"] for e in existing}
    to_add = [e for e in new_entries if e["url"] not in existing_urls]
    print(f"Existing entries: {len(existing)}")
    print(f"SICC entries to add: {len(to_add)} (skipped duplicates: {len(new_entries) - len(to_add)})")

    if not to_add:
        print("Nothing to add; exiting.")
        return

    # Backup
    if not os.path.exists(BACKUP):
        shutil.copy2(JUDGMENTS, BACKUP)
        print(f"Backed up judgments.json -> {BACKUP}")
    else:
        print(f"Backup already exists at {BACKUP} (not overwriting).")

    merged = existing + to_add
    with open(JUDGMENTS, "w") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)
    print(f"Wrote {JUDGMENTS} with {len(merged)} total entries.")

    # Per-tribunal means (sanity)
    from collections import defaultdict
    by_trib = defaultdict(list)
    for e in merged:
        by_trib[e["tribunal"]].append(e)
    prims = ["PR1","PR2","PR3","PR4","PR5","PR6"]
    print()
    print("Per-tribunal means (v0.2 primitives):")
    print(f"  {'tribunal':<45} n   " + "  ".join(prims))
    for trib, rows in sorted(by_trib.items()):
        means = [sum(r["primitive_scores_v02"][p] for r in rows)/len(rows)
                 for p in prims]
        print(f"  {trib:<45} {len(rows):<3} " +
              "  ".join(f"{m:.2f}" for m in means))


if __name__ == "__main__":
    main()
