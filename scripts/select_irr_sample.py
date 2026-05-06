"""
Select a stratified 20-judgment subsample from the hand-coded gold set
(n=39) for inter-rater-reliability (IRR) re-coding.

Stratification: at least one judgment per (tribunal, claim_type) cell
present in the gold set; remaining slots filled proportionally.

Outputs:
  - data/irr/sample.json         : the 20 selected case_no's (ordered)
  - data/irr/coder_a.json        : Coder A scores (lifted from judgments.json)
  - data/irr/coder_b.template.json: blank coding sheet for Coder B (human)

Coder A is the original Maxim Labs hand-coder. Coder B MUST be an
independent human reviewer (UAE/SG-licensed counsel, common-law
academic). The κ exercise compares A and B.

Use of an LLM as Coder B is INVALID for IRR — the reviewer attempting
this audit specifically flagged that risk. The script will refuse to
populate Coder B from any source other than the explicit human-coded
file.

Run:
    python3 scripts/select_irr_sample.py
"""

import json
import random
from collections import defaultdict
from pathlib import Path


HERE = Path(__file__).resolve().parent.parent
JUDGMENTS = HERE / "data" / "judgments.json"
OUT_DIR = HERE / "data" / "irr"

TARGET_N = 20
SEED = 42  # reproducible


def main():
    OUT_DIR.mkdir(exist_ok=True)
    judgments = json.loads(JUDGMENTS.read_text())
    hand = [j for j in judgments
            if (j.get("coding") or {}).get("coder") == "MaximLabs"]
    if len(hand) < TARGET_N:
        raise SystemExit(f"hand-coded set has only {len(hand)} entries; "
                         f"cannot draw n={TARGET_N}")

    # Bucket by (tribunal, claim_type)
    buckets = defaultdict(list)
    for j in hand:
        key = (j["tribunal"], j.get("claim_type", "other"))
        buckets[key].append(j)

    rng = random.Random(SEED)
    sample = []
    # Pass 1: one per non-empty bucket.
    for key, items in sorted(buckets.items()):
        sample.append(rng.choice(items))
    # Pass 2: fill remaining slots proportional to bucket size.
    remaining = TARGET_N - len(sample)
    if remaining < 0:
        # Too many strata — randomly drop down to TARGET_N preserving
        # stratification.
        sample = rng.sample(sample, TARGET_N)
        remaining = 0
    pool = []
    for key, items in buckets.items():
        already = sum(1 for s in sample
                      if s["case_no"] in {x["case_no"] for x in items})
        for it in items:
            if it["case_no"] not in {s["case_no"] for s in sample}:
                # weight = bucket size (so larger buckets contribute more)
                pool.extend([it] * len(items))
    rng.shuffle(pool)
    seen = {s["case_no"] for s in sample}
    while remaining > 0 and pool:
        cand = pool.pop()
        if cand["case_no"] in seen:
            continue
        sample.append(cand)
        seen.add(cand["case_no"])
        remaining -= 1

    sample.sort(key=lambda j: (j["tribunal"], j.get("claim_type", ""),
                               j["case_no"]))

    sample_path = OUT_DIR / "sample.json"
    sample_path.write_text(json.dumps({
        "n": len(sample),
        "selection_seed": SEED,
        "stratification": "one per (tribunal, claim_type) cell in gold set, "
                          "remainder proportional to bucket size",
        "case_nos": [j["case_no"] for j in sample],
    }, indent=2))

    coder_a = {
        "coder": "Coder A — original Maxim Labs hand-coder (lifted from "
                 "data/judgments.json without re-reading)",
        "coding_method": "lifted-from-master",
        "rubric_version": "v0.2",
        "entries": [
            {
                "case_no": j["case_no"],
                "tribunal": j["tribunal"],
                "claim_type": j.get("claim_type"),
                "url": j.get("url"),
                "scores": j["primitive_scores_v02"],
            }
            for j in sample
        ],
    }
    (OUT_DIR / "coder_a.json").write_text(json.dumps(coder_a, indent=2))

    coder_b_template = {
        "coder": "Coder B — INDEPENDENT HUMAN REVIEWER (e.g. UAE/SG-licensed "
                 "counsel or common-law academic). Populate by re-reading "
                 "each judgment in full against the rubric in "
                 "data/primitives.json. DO NOT use an LLM.",
        "coding_method": "blind-second-coder",
        "rubric_version": "v0.2",
        "entries": [
            {
                "case_no": j["case_no"],
                "tribunal": j["tribunal"],
                "claim_type": j.get("claim_type"),
                "url": j.get("url"),
                "scores": {
                    "PR1": None, "PR2": None, "PR3": None,
                    "PR4": None, "PR5": None, "PR6": None,
                },
                "rationale": {
                    "PR1": "", "PR2": "", "PR3": "",
                    "PR4": "", "PR5": "", "PR6": "",
                },
            }
            for j in sample
        ],
    }
    (OUT_DIR / "coder_b.template.json").write_text(
        json.dumps(coder_b_template, indent=2)
    )

    print(f"selected n={len(sample)} judgments")
    print(f"  → {sample_path}")
    print(f"  → {OUT_DIR / 'coder_a.json'}")
    print(f"  → {OUT_DIR / 'coder_b.template.json'}")
    print()
    print("Coder B template is blank. Provide to an independent human reviewer.")
    print("Then run: python3 scripts/score_irr.py")


if __name__ == "__main__":
    main()
