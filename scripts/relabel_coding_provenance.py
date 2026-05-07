#!/usr/bin/env python3
"""Relabel `coding` blocks in data/judgments.json + falsification + comparison
sets to use clean per-procedure-tier labels and pin AI-grader provenance.

Mapping:
  - coder == "MaximLabs"                       → "MaximLabs (first-pass-claude)"
  - coder == "MaximLabs (heuristic-triage)"     → unchanged
  - coder == "MaximLabs (heuristic-graded)"    → unchanged
  - coder == "MaximLabs (provisional-class-default)" → unchanged (falsification/comparison)
  - gold_set: True → first_pass: True; gold_set field removed

Pinned provenance fields (added per entry):
  - model: "claude-sonnet-4-5-20250929"
  - temperature: 0.0
  - prompt_template_id: "v0_2_grade"
  - system_prompt_sha256: <sha of scripts/ai_grade_prompt_v0_2.txt if present, else "unknown">

Idempotent: running twice produces no further changes.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JUDGMENTS = ROOT / "data" / "judgments.json"
FALSIF = ROOT / "data" / "falsification_set.json"
COMPARISON = ROOT / "data" / "comparison_set.json"
PROMPT_FILE = ROOT / "scripts" / "ai_grade_prompt_v0_2.txt"

MODEL = "claude-sonnet-4-5-20250929"
TEMPERATURE = 0.0
PROMPT_TEMPLATE_ID = "v0_2_grade"

PROCEDURE_RUN_DATES = {
    # Per GRADING_SPEC.md
    "MaximLabs (first-pass-claude)": "2026-04-27",
    "MaximLabs (heuristic-triage)": "2026-04-12",
    "MaximLabs (heuristic-graded)": "unknown",  # mixed: ADGM 2026-04-12, SICC 2026-04-29
    "MaximLabs (provisional-class-default)": "2026-04-15",
}


def prompt_sha():
    if PROMPT_FILE.exists():
        return hashlib.sha256(PROMPT_FILE.read_bytes()).hexdigest()
    return "unknown"


def relabel_coding(coding, default_run_date=None):
    """Return new coding object. Idempotent."""
    if not isinstance(coding, dict):
        return coding
    new = dict(coding)
    coder = new.get("coder")

    # 1. Rename ambiguous "MaximLabs" to first-pass-claude
    if coder == "MaximLabs":
        new["coder"] = "MaximLabs (first-pass-claude)"
        coder = new["coder"]

    # 2. gold_set → first_pass
    if "gold_set" in new:
        new["first_pass"] = bool(new.pop("gold_set"))

    # 3. Pin grader provenance.
    #    - first-pass-claude: AI-coded with Claude (model fields apply)
    #    - provisional-class-default: author-assigned class defaults
    #      (NOT LLM-graded; tagged with grader_type "author_class_default" so the
    #       provenance can never be misread as a per-instrument LLM run).
    #    - heuristic-triage / heuristic-graded: REGEX heuristics only — no LLM in
    #      the loop. Pin script identity instead of model identity.
    is_claude = coder == "MaximLabs (first-pass-claude)"
    is_class_default = coder == "MaximLabs (provisional-class-default)"
    is_regex = coder in (
        "MaximLabs (heuristic-triage)",
        "MaximLabs (heuristic-graded)",
    )
    if is_claude:
        new.setdefault("grader_type", "llm")
        new.setdefault("model", MODEL)
        new.setdefault("temperature", TEMPERATURE)
        new.setdefault("prompt_template_id", PROMPT_TEMPLATE_ID)
        new.setdefault("system_prompt_sha256", prompt_sha())
    elif is_class_default:
        # Set the grader_type to author_class_default and PURGE any model
        # fields that an earlier pass of this script may have added.
        new["grader_type"] = "author_class_default"
        for k in ("model", "temperature", "prompt_template_id", "system_prompt_sha256"):
            new.pop(k, None)
        new.setdefault(
            "scoring_basis",
            "Author-assigned class-level default reflecting the published "
            "structural form of the instrument class. NOT a per-instance "
            "LLM grading. Bind to named instruments + practitioner review "
            "before publication-grade citation."
        )
    elif is_regex:
        new["grader_type"] = "regex_heuristic"
        # Drop any spurious model fields a previous run may have added.
        for k in ("model", "temperature", "prompt_template_id", "system_prompt_sha256"):
            new.pop(k, None)
        # Identify the script that produced the score.
        if coder == "MaximLabs (heuristic-triage)":
            new.setdefault("grader_script", "scripts/triage_adgm.py")
        else:
            # heuristic-graded: ADGM via grade_borderline.py, SICC via triage_sicc.py
            # We don't disambiguate per-entry here; both scripts are documented in
            # GRADING_SPEC.md and tagged in the rationale field.
            new.setdefault("grader_script", "scripts/grade_borderline.py | scripts/triage_sicc.py")
    rd = new.get("coded_on") or new.get("run_date")
    if rd:
        new.setdefault("run_date", rd)
    else:
        new.setdefault("run_date", PROCEDURE_RUN_DATES.get(coder,
                                                            default_run_date or "unknown"))
    return new


def relabel_file(path, container_key=None):
    if not path.exists():
        print(f"  skip (missing): {path}")
        return
    raw = json.loads(path.read_text())
    if container_key and isinstance(raw, dict) and container_key in raw:
        items = raw[container_key]
    elif isinstance(raw, list):
        items = raw
    else:
        # fall back to known shapes
        items = raw if isinstance(raw, list) else None
    if items is None:
        print(f"  unknown shape: {path}")
        return

    changed = 0
    for it in items:
        if not isinstance(it, dict):
            continue
        before = json.dumps(it.get("coding"), sort_keys=True)
        it["coding"] = relabel_coding(it.get("coding"))
        after = json.dumps(it.get("coding"), sort_keys=True)
        if before != after:
            changed += 1
    path.write_text(json.dumps(raw, indent=2))
    print(f"  {path.name}: {changed}/{len(items)} entries updated")


def main():
    print("Relabeling coding-provenance blocks (idempotent)...")
    relabel_file(JUDGMENTS)
    relabel_file(FALSIF, container_key="entries")
    relabel_file(COMPARISON, container_key="entries")
    print("Done.")


if __name__ == "__main__":
    main()
