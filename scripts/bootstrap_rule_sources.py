"""
Bootstrap rules/<module>_source.yaml for every Catala module.

Each <module>_source.yaml pins the rule to a specific version of its source
instrument (statute / rule of court / case-law doctrine) so that rule
outputs are auditable to a known authority and so that drift in the
official source can be detected mechanically.

The schema:

    module: <module name, == filename stem>
    version_id: <opaque identifier of the pinned version>
    source_authority:
      jurisdiction: <DIFC | ADGM | UAE | SG | England | Common-law>
      instrument: <human-readable name>
      url: <stable URL for the official source>
      retrieved_at: <YYYY-MM-DD>
      retrieved_sha256: <sha256 of canonicalised text at retrieval; populated
                        on first run of scripts/check_rule_drift.py>
    amendment_window:
      in_force_from: <YYYY-MM-DD or null>
      in_force_until: <YYYY-MM-DD or null>
    drift_check:
      url: <URL to fetch>
      method: http_get | manual | not_applicable
      canonicalisation: <how to normalise text before hashing>
    case_law_doctrine: <true if the "rule" is a doctrine of common law,
                        in which case drift = higher-court overrule rather
                        than a text amendment>
    expiry:
      reminder_at: <YYYY-MM-DD — soft reminder>
      hard_expiry_at: <YYYY-MM-DD — module must not be relied on after this>
    notes: |
      <free-text>

For doctrines (Caparo, Ladd v Marshall, Wood v Capita, Norwich Pharmacal),
"drift" is detected differently — a higher court overruling. The
drift_check method is `manual` for these; the URL points to a current
case-law database for human review.

This script is idempotent: if a source.yaml already exists, it is left
alone (so manual edits aren't clobbered).
"""

from datetime import date
from pathlib import Path
import textwrap
import sys


HERE = Path(__file__).resolve().parent.parent
RULES = HERE / "rules"

TODAY = date(2026, 4, 15).isoformat()


SOURCES = {
    "difc_rdc_part_38": {
        "version_id": "rdc-2024-11-01",
        "jurisdiction": "DIFC",
        "instrument": "Rules of the DIFC Courts (RDC), Part 38",
        "url": "https://www.difccourts.ae/rules-decisions/rules",
        "in_force_from": "2024-11-01",
        "drift_method": "http_get",
        "case_law_doctrine": False,
        "notes": "Standard-basis costs assessment under RDC 38.",
    },
    "difc_practice_direction_4_2017": {
        "version_id": "pd-4-2017",
        "jurisdiction": "DIFC",
        "instrument": "DIFC Practice Direction No. 4 of 2017 (Interest on Judgments)",
        "url": "https://www.difccourts.ae/rules-decisions/practice-directions",
        "in_force_from": "2017-01-01",
        "drift_method": "http_get",
        "case_law_doctrine": False,
        "notes": "9% per annum interest + 14-day deadline.",
    },
    "difc_rdc_38_19_indemnity": {
        "version_id": "rdc-2024-11-01",
        "jurisdiction": "DIFC",
        "instrument": "Rules of the DIFC Courts (RDC), Rule 38.17 (assessment bases) and Rule 38.19 (indemnity basis)",
        "url": "https://www.difccourts.ae/rules-decisions/rules",
        "in_force_from": "2024-11-01",
        "drift_method": "http_get",
        "case_law_doctrine": False,
        "notes": "Indemnity-basis review; bounded discretion residue.",
    },
    "difc_third_party_disclosure": {
        "version_id": "rdc-2024-11-01+norwich-pharmacal+bankers-trust",
        "jurisdiction": "DIFC",
        "instrument": "DIFC RDC 28.52 + Norwich Pharmacal v Customs and Excise [1974] AC 133 + Bankers Trust v Shapira [1980] 1 WLR 1274",
        "url": "https://www.difccourts.ae/rules-decisions/rules",
        "in_force_from": "2024-11-01",
        "drift_method": "http_get",
        "case_law_doctrine": True,
        "notes": "Composite rule: RDC 28.52 + two House of Lords / CA doctrines. Drift on RDC checks via http_get; drift on doctrines is manual review.",
    },
    "uae_civil_code_art_390": {
        "version_id": "uae-civil-1985-as-amended-2016",
        "jurisdiction": "UAE",
        "instrument": "UAE Civil Transactions Law, Federal Law No. 5 of 1985, Article 390",
        # MoJ main-legislations index — stable, free, fetchable. Drift on
        # this page indicates a new amendment publication (the listing
        # updates when a law revision lands). The index does not contain
        # Article 390's text directly; it is the official roster page.
        "url": "https://www.moj.gov.ae/en/laws-and-legislation/legislative-framework-of-the-judicial-system-in-uae/main-legislations.aspx",
        "in_force_from": "1985-12-15",
        "drift_method": "http_get",
        "case_law_doctrine": False,
        "notes": "Liquidated-damages cap (judicial variation of agreed compensation). Drift is checked against the MoJ main-legislations roster page; uaelegislation.gov.ae and elaws.moj.gov.ae block headless / non-browser access.",
    },
    "adgm_cpr_admissions": {
        "version_id": "adgm-cpr-2016-amended-30112023",
        "jurisdiction": "ADGM",
        "instrument": "ADGM Court Procedure Rules 2016, Rule 42 (admissions and withdrawal)",
        # Official PDF on assets.adgm.com — stable, free, no auth.
        "url": "https://assets.adgm.com/download/assets/ADGM+Court+Procedure+Rules+2016+-+30112023+-+FINAL.pdf/1e4cdd0c45c011efa7762ac4d0cba84b",
        "in_force_from": "2016-12-30",
        "drift_method": "http_get",
        "case_law_doctrine": False,
        "notes": "Admissions and set-off arithmetic. Drift hash is sha256 of the PDF bytes (binary).",
    },
    "adgm_cpr_summary_judgment": {
        "version_id": "adgm-cpr-2016-amended-30112023",
        "jurisdiction": "ADGM",
        "instrument": "ADGM Court Procedure Rules 2016 — summary judgment",
        "url": "https://assets.adgm.com/download/assets/ADGM+Court+Procedure+Rules+2016+-+30112023+-+FINAL.pdf/1e4cdd0c45c011efa7762ac4d0cba84b",
        "in_force_from": "2016-12-30",
        "drift_method": "http_get",
        "case_law_doctrine": False,
        "notes": "Same PDF as adgm_cpr_admissions; share hash on drift.",
    },
    "adgm_arbitration_regulations_2015": {
        "version_id": "adgm-arb-reg-2015-as-amended",
        "jurisdiction": "ADGM",
        "instrument": "ADGM Arbitration Regulations 2015 — recognition / set-aside",
        "url": "https://en.adgm.thomsonreuters.com/rulebook/arbitration-regulations-2015",
        "in_force_from": "2015-12-17",
        "drift_method": "http_get",
        "case_law_doctrine": False,
    },
    "english_contract_interpretation": {
        "version_id": "wood-v-capita-2017",
        "jurisdiction": "England",
        "instrument": "Wood v Capita Insurance Services Ltd [2017] UKSC 24 applying Rainy Sky SA v Kookmin Bank [2011] UKSC 50",
        "url": "https://www.bailii.org/uk/cases/UKSC/2017/24.html",
        "in_force_from": "2017-03-29",
        "drift_method": "manual",
        "case_law_doctrine": True,
        "notes": "Drift = higher-court overruling. Manual review on each major UKSC contract-interpretation decision.",
    },
    "ladd_v_marshall": {
        "version_id": "ladd-v-marshall-1954",
        "jurisdiction": "England",
        "instrument": "Ladd v Marshall [1954] 1 WLR 1489",
        "url": "https://www.bailii.org/ew/cases/EWCA/Civ/1954/1.html",
        "in_force_from": "1954-11-29",
        "drift_method": "manual",
        "case_law_doctrine": True,
        "notes": "Three-prong fresh-evidence test. Doctrine; drift = higher-court overrule (none to date).",
    },
    "sg_iaa_s_31": {
        "version_id": "sg-iaa-2002-as-amended-2020",
        "jurisdiction": "SG",
        "instrument": "Singapore International Arbitration Act 2002, s 31 (NY Convention Article V grounds)",
        "url": "https://sso.agc.gov.sg/Act/IAA1994#pr31-",
        "in_force_from": "2002-01-31",
        "drift_method": "http_get",
        "case_law_doctrine": False,
        "notes": "Refusal-of-recognition grounds + DKT v DKU four-condition framework.",
    },
    "caparo_three_stage_test": {
        "version_id": "caparo-v-dickman-1990",
        "jurisdiction": "Common-law",
        "instrument": "Caparo Industries plc v Dickman [1990] UKHL 2, [1990] 2 AC 605",
        "url": "https://www.bailii.org/uk/cases/UKHL/1990/2.html",
        "in_force_from": "1990-02-08",
        "drift_method": "manual",
        "case_law_doctrine": True,
        "notes": "Three-stage duty-of-care test. Doctrine; drift = Supreme Court overrule. Note that Robinson v CC West Yorkshire [2018] UKSC 4 narrowed the application of stage 2; check on update.",
    },
}


def yaml_quote(s):
    if s is None:
        return "null"
    s = str(s)
    if any(c in s for c in ":#&*?{}[]|>%@`-,") or s.strip() != s:
        return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return s


def render(module_name, src):
    lines = [
        f"module: {module_name}",
        f"version_id: {yaml_quote(src['version_id'])}",
        "source_authority:",
        f"  jurisdiction: {yaml_quote(src['jurisdiction'])}",
        f"  instrument: {yaml_quote(src['instrument'])}",
        f"  url: {yaml_quote(src['url'])}",
        f"  retrieved_at: {TODAY}",
        f"  retrieved_sha256: null    # populated by scripts/check_rule_drift.py",
        "amendment_window:",
        f"  in_force_from: {src.get('in_force_from', 'null')}",
        f"  in_force_until: null      # current",
        "drift_check:",
        f"  method: {src['drift_method']}",
        f"  url: {yaml_quote(src['url'])}",
        f"  canonicalisation: strip-whitespace-and-html",
        f"case_law_doctrine: {'true' if src.get('case_law_doctrine') else 'false'}",
        "expiry:",
        f"  reminder_at: 2027-04-15",
        f"  hard_expiry_at: 2028-04-15",
    ]
    notes = src.get("notes")
    if notes:
        lines.append("notes: |")
        for line in textwrap.wrap(notes, width=72):
            lines.append(f"  {line}")
    return "\n".join(lines) + "\n"


def main():
    written = 0
    skipped = 0
    missing = []
    for catala in sorted(RULES.glob("*.catala_en")):
        name = catala.stem
        out = RULES / f"{name}_source.yaml"
        if out.exists():
            print(f"  skip {name}_source.yaml  (already exists)")
            skipped += 1
            continue
        if name not in SOURCES:
            print(f"  WARN missing template for {name} — please add to SOURCES")
            missing.append(name)
            continue
        out.write_text(render(name, SOURCES[name]))
        print(f"  wrote {name}_source.yaml")
        written += 1
    print(f"\nwrote {written}, skipped {skipped}, missing {len(missing)}")
    if missing:
        sys.exit(1)


if __name__ == "__main__":
    main()
