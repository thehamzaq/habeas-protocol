#!/usr/bin/env python3
"""Generate per-rule `<module>_metadata.json` from each rule module's
docstring + the existing _index.json + _jurisdictions.json. Idempotent —
preserves any existing metadata file (does not overwrite if present).

Use to bootstrap the certification process: every existing rule module
starts at `state: draft` with its source citations populated from the
docstring. A reviewer can then promote modules to `submitted` / `reviewed`
/ `certified` by editing the metadata file.

Run once at install / when new modules are added:
    python3 scripts/bootstrap_rule_metadata.py
"""
from __future__ import annotations
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
RULES = ROOT / "rules"

# Hand-curated source citations per existing module — drawn from the
# docstrings of each .catala_en file. Future modules will need to add
# their own when authored.
KNOWN_SOURCES: dict[str, dict] = {
    "difc_rdc_part_38": {
        "human_label": "DIFC RDC Part 38 — standard-basis costs assessment",
        "sources": [
            {"kind": "rules_of_court", "citation": "Rules of the DIFC Courts (RDC), Part 38"},
        ],
    },
    "difc_rdc_38_7_indemnity": {
        "human_label": "DIFC RDC 38.7 — indemnity-basis costs review (bounded discretion)",
        "sources": [
            {"kind": "rules_of_court", "citation": "Rules of the DIFC Courts (RDC) 38.7"},
        ],
    },
    "difc_practice_direction_4_2017": {
        "human_label": "DIFC PD 4/2017 — arbitration costs framework (80% / 14-day / 9%)",
        "sources": [
            {"kind": "practice_direction", "citation": "DIFC Courts Practice Direction No. 4 of 2017"},
        ],
    },
    "difc_third_party_disclosure": {
        "human_label": "DIFC Norwich Pharmacal + Bankers Trust + RDC 28.52 — third-party disclosure jurisdiction",
        "sources": [
            {"kind": "statute", "citation": "DIFC Courts Law (Law No. 2 of 2025), Articles 15(1), 24(D)"},
            {"kind": "statute", "citation": "DIFC Law of Damages and Remedies (Law No. 7 of 2005), Article 36"},
            {"kind": "rules_of_court", "citation": "RDC 25.1(10), 28.51, 28.52"},
            {"kind": "case", "citation": "Norwich Pharmacal Co v Customs and Excise Commissioners [1974] AC 133 (HL)"},
            {"kind": "case", "citation": "Bankers Trust Co v Shapira [1980] 1 WLR 1274 (CA)"},
        ],
    },
    "adgm_cpr_admissions": {
        "human_label": "ADGM CPR 2016 — admissions and set-off arithmetic",
        "sources": [
            {"kind": "rules_of_court", "citation": "ADGM Court Procedure Rules 2016"},
            {"kind": "statute", "citation": "ADGM Civil Evidence, Judgments, Enforcement and Judicial Cooperation Regulations 2015"},
        ],
    },
    "adgm_cpr_summary_judgment": {
        "human_label": "ADGM CPR Rule 24 — summary judgment two-limb test",
        "sources": [
            {"kind": "rules_of_court", "citation": "ADGM Court Procedure Rules 2016, Rule 24"},
        ],
    },
    "adgm_arbitration_regulations_2015": {
        "human_label": "ADGM Arbitration Regulations 2015 — recognition of foreign awards (parallel of SG IAA s 31)",
        "sources": [
            {"kind": "statute", "citation": "ADGM Arbitration Regulations 2015, ss 56-58"},
            {"kind": "international_convention", "citation": "New York Convention 1958, Article V"},
        ],
        "cross_jurisdiction_note": "Structurally parallel to sg_iaa_s_31. Statutory references and public-policy authority differ.",
    },
    "english_contract_interpretation": {
        "human_label": "Wood v Capita / Rainy Sky / Arnold v Britton — unitary contractual interpretation",
        "sources": [
            {"kind": "case", "citation": "Wood v Capita Insurance Services Ltd [2017] UKSC 24"},
            {"kind": "case", "citation": "Rainy Sky SA v Kookmin Bank [2011] UKSC 50"},
            {"kind": "case", "citation": "Arnold v Britton [2015] UKSC 36"},
        ],
        "cross_jurisdiction_note": "Applied wholesale by ADGM via the Application of English Law Regulations 2015. Reaches DIFC by analogy through DIFC Contract Law.",
    },
    "caparo_three_stage_test": {
        "human_label": "Caparo v Dickman — three-stage duty-of-care test",
        "sources": [
            {"kind": "case", "citation": "Caparo Industries plc v Dickman [1990] UKHL 2, [1990] 2 AC 605"},
        ],
        "cross_jurisdiction_note": "Applied wholesale by ADGM via the AELR. Persuasive in DIFC and SICC.",
    },
    "ladd_v_marshall": {
        "human_label": "Ladd v Marshall — fresh evidence three-prong test",
        "sources": [
            {"kind": "case", "citation": "Ladd v Marshall [1954] 1 WLR 1489 (CA)"},
        ],
        "cross_jurisdiction_note": "Applied by ADGM via the AELR. Persuasive in DIFC and SICC.",
    },
    "sg_iaa_s_31": {
        "human_label": "Singapore IAA s 31 (NY Convention Art V refusal grounds) + DKT v DKU framework",
        "sources": [
            {"kind": "statute", "citation": "International Arbitration Act 1994 (2020 Rev Ed), s 31"},
            {"kind": "international_convention", "citation": "New York Convention 1958, Article V"},
            {"kind": "case", "citation": "DKT v DKU [2025] 1 SLR 806 (CA)"},
            {"kind": "case", "citation": "COD v COE [2023] 4 SLR 708"},
        ],
        "cross_jurisdiction_note": "Structurally parallel to adgm_arbitration_regulations_2015.",
    },
    "uae_civil_code_art_390": {
        "human_label": "UAE Civil Transactions Law Article 390(2) — liquidated-damages cap",
        "sources": [
            {"kind": "statute", "citation": "UAE Civil Transactions Law (Federal Law No. 5 of 1985), Article 390"},
        ],
        "cross_jurisdiction_note": "Applied as subsidiary federal law in both ADGM and DIFC, parametric on cap rate (commonly 10% in ADGM CFI commercial disputes).",
    },
}


def extract_test_scopes(rule_path: Path) -> list[str]:
    text = rule_path.read_text()
    return re.findall(r"#\[test\]\s+declaration scope\s+([A-Za-z][A-Za-z0-9_]*)", text)


def main():
    if not RULES.exists():
        sys.exit(f"rules/ not found at {RULES}")
    written = 0
    skipped = 0
    for rule_path in sorted(RULES.glob("*.catala_en")):
        module = rule_path.stem
        meta_path = RULES / f"{module}_metadata.json"
        if meta_path.exists():
            skipped += 1
            continue
        info = KNOWN_SOURCES.get(module, {
            "human_label": module,
            "sources": [{"kind": "bespoke", "citation": "(populate me — sources unknown)"}],
        })
        meta = {
            "module_name": module,
            "human_label": info["human_label"],
            "source_authorities": info["sources"],
            "test_scopes": extract_test_scopes(rule_path),
            "certification": {
                "state": "draft",
                "states_history": [],
            },
        }
        if "cross_jurisdiction_note" in info:
            meta["cross_jurisdiction_note"] = info["cross_jurisdiction_note"]
        meta_path.write_text(json.dumps(meta, indent=2) + "\n")
        written += 1
        print(f"  wrote rules/{module}_metadata.json (state=draft)")
    print(f"\nWrote {written} new metadata files; skipped {skipped} existing.")
    print("Edit each file to advance through draft → submitted → reviewed → certified.")


if __name__ == "__main__":
    main()
