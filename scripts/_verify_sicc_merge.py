#!/usr/bin/env python3
"""Sanity check: backup is identical to first 108 entries of new file."""
import json

old = json.load(open("data/judgments.json.pre_sicc.bak"))
new = json.load(open("data/judgments.json"))
print("old:", len(old), "new:", len(new))
diff = False
for i in range(len(old)):
    if json.dumps(old[i], sort_keys=True) != json.dumps(new[i], sort_keys=True):
        print("DIFF at", i, old[i].get("case_no"))
        diff = True
        break
if not diff:
    print("All", len(old), "existing entries unchanged.")
print("SICC tribunals in new:",
      sum(1 for e in new if e["tribunal"] == "Singapore International Commercial Court"))
