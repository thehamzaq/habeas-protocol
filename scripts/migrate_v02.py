#!/usr/bin/env python3
"""Migrate judgments.json from v0.1 to v0.2 schema and append ADGM cases.

v0.1 → v0.2 changes per record:
  - add tribunal field
  - rename primitive_scores → primitive_scores_v01
  - add primitive_scores_v02 (6-primitive scoring; tribunal-level SP1/SP2 in primitives.json)

Then append the ADGM first-pass entries.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = HERE + "/../data/judgments.json"

# v0.2 scores for the existing 32 DIFC cases. PR1=Identity, PR2=Evidence log,
# PR3=Rule bind, PR4=Procedure, PR5=Ruling, PR6=Enforcement bridge.
# Coded by reading the same source material as v0.1; see methodology notes.
DIFC_V02 = {
    "CFI 058/2024":  {"PR1": 2, "PR2": 2, "PR3": 2, "PR4": 2, "PR5": 2, "PR6": 1},
    "ARB 008/2026":  {"PR1": 1, "PR2": 2, "PR3": 2, "PR4": 2, "PR5": 2, "PR6": 2},
    "ENF 271/2025":  {"PR1": 2, "PR2": 2, "PR3": 1, "PR4": 2, "PR5": 2, "PR6": 1},
    "CFI 110/2025":  {"PR1": 2, "PR2": 2, "PR3": 2, "PR4": 2, "PR5": 2, "PR6": 1},
    "CFI 079/2020":  {"PR1": 2, "PR2": 2, "PR3": 1, "PR4": 1, "PR5": 2, "PR6": 1},
    "CFI 072/2025":  {"PR1": 2, "PR2": 2, "PR3": 2, "PR4": 2, "PR5": 2, "PR6": 1},
    "ARB 024/2025":  {"PR1": 1, "PR2": 2, "PR3": 2, "PR4": 2, "PR5": 2, "PR6": 2},
    "CFI 057/2021":  {"PR1": 2, "PR2": 2, "PR3": 2, "PR4": 2, "PR5": 2, "PR6": 1},
    "CFI 034/2022":  {"PR1": 2, "PR2": 2, "PR3": 1, "PR4": 2, "PR5": 2, "PR6": 2},
    "CA 002/2025":   {"PR1": 2, "PR2": 2, "PR3": 1, "PR4": 2, "PR5": 2, "PR6": 2},
    "DEC 001/2025":  {"PR1": 2, "PR2": 2, "PR3": 2, "PR4": 2, "PR5": 2, "PR6": 2},
    "CFI 035/2025":  {"PR1": 2, "PR2": 2, "PR3": 2, "PR4": 2, "PR5": 2, "PR6": 2},
    "CFI 076/2024":  {"PR1": 2, "PR2": 1, "PR3": 1, "PR4": 1, "PR5": 2, "PR6": 1},
    "ENF 053/2025":  {"PR1": 2, "PR2": 2, "PR3": 2, "PR4": 1, "PR5": 2, "PR6": 2},
    "CFI 053/2024":  {"PR1": 2, "PR2": 2, "PR3": 2, "PR4": 2, "PR5": 1, "PR6": 1},
    "TCD 001/2024":  {"PR1": 2, "PR2": 2, "PR3": 1, "PR4": 2, "PR5": 2, "PR6": 2},
    "CFI 010/2024":  {"PR1": 2, "PR2": 2, "PR3": 2, "PR4": 1, "PR5": 2, "PR6": 1},
    "CFI 092/2024":  {"PR1": 2, "PR2": 2, "PR3": 2, "PR4": 2, "PR5": 2, "PR6": 1},
    "ARB 032/2025":  {"PR1": 1, "PR2": 1, "PR3": 1, "PR4": 1, "PR5": 2, "PR6": 2},
    "CFI 067/2025":  {"PR1": 2, "PR2": 2, "PR3": 2, "PR4": 2, "PR5": 2, "PR6": 2},
    "CFI 071/2025":  {"PR1": 2, "PR2": 2, "PR3": 2, "PR4": 2, "PR5": 2, "PR6": 2},
    "CFI 098/2025":  {"PR1": 2, "PR2": 2, "PR3": 1, "PR4": 2, "PR5": 1, "PR6": 1},
    "CFI 078/2025":  {"PR1": 2, "PR2": 2, "PR3": 2, "PR4": 2, "PR5": 2, "PR6": 1},
    "CFI 022/2025":  {"PR1": 2, "PR2": 1, "PR3": 2, "PR4": 1, "PR5": 2, "PR6": 2},
    "CFI 039/2025":  {"PR1": 2, "PR2": 2, "PR3": 2, "PR4": 2, "PR5": 2, "PR6": 2},
    "ARB 029/2025":  {"PR1": 1, "PR2": 2, "PR3": 2, "PR4": 2, "PR5": 2, "PR6": 2},
    "CFI 007/2026":  {"PR1": 2, "PR2": 2, "PR3": 2, "PR4": 2, "PR5": 2, "PR6": 1},
    "DIFC Courts Order No. 3 of 2025": {"PR1": 0, "PR2": 0, "PR3": 2, "PR4": 0, "PR5": 2, "PR6": 0},
    "CFI 045/2025":  {"PR1": 2, "PR2": 1, "PR3": 1, "PR4": 2, "PR5": 1, "PR6": 1},
    "CFI 036/2025":  {"PR1": 2, "PR2": 2, "PR3": 2, "PR4": 2, "PR5": 2, "PR6": 1},
    "CFI 011/2025":  {"PR1": 2, "PR2": 2, "PR3": 2, "PR4": 2, "PR5": 2, "PR6": 2},
    "CFI 067/2024":  {"PR1": 2, "PR2": 1, "PR3": 1, "PR4": 2, "PR5": 1, "PR6": 1},
}

ADGM_ENTRIES = [
    {
        "case_no": "ADGMCFI-2025-283",
        "url": "https://www.adgm.com/adgm-courts/judgments",
        "tribunal": "ADGM Courts",
        "division": "Court of First Instance — Real Property Division",
        "date_issued": "2026-02-04",
        "parties": {"claimant": "Castello Cafe and Restaurant L.L.C - S.P.C", "defendant": "TSL Properties LLC; Three Sixty Communities Estate LLC; Modon Holding P.S.C; MENA Real Estate Solutions LLC"},
        "judge": "Justice Paul Heath KC",
        "neutral_citation": "[2026] ADGMCFI 0005",
        "claim_type": "summary_judgment",
        "outcome": "claim_partially_granted",
        "operative_amount_aed": None, "operative_amount_usd": None,
        "rules_cited": [
            "Cabinet Resolution No. (41) of 2023",
            "Abu Dhabi Law No. (4) of 2013 (as amended by Law No. (12) of 2020), Article 13(7)",
            "ADGM Application of English Law Regulations 2015",
            "ADGM Court Procedure Rules 2016 — Rules 9(2)(a), 68(1)(a), 75",
            "ADGM Practice Direction 7 — paragraph 7.33"
        ],
        "cases_cited": [
            "Union Properties PJSC v Trinkler & Partners Ltd [2024] ADGMCFI 0014",
            "Al Nashef v Empire Island Tower Ltd [2025] ADGMCFI 0025",
            "Caparo Industries Plc v Dickman [1990] 1 All ER 568 (HL)",
            "Hedley Byrne & Co Ltd v Heller & Partners Ltd [1964] AC 465 (HL)",
            "Murphy v Brentwood District Council [1991] 1 AC 398 (HL)",
            "Chandler v Cape Plc [2012] 3 All ER 640 (CA)",
            "Phonogram Ltd v Lane [1982] 3 CMLR 615 (CA)",
            "Global Private Investments RSC Ltd v Global Aerospace Underwriting Managers Ltd [2021] ADGMCFI 0005"
        ],
        "primitive_scores_v02": {"PR1": 2, "PR2": 2, "PR3": 2, "PR4": 2, "PR5": 2, "PR6": 2},
        "coding": {
            "coder": "MaximLabs", "coded_on": "2026-04-27", "gold_set": True,
            "notes": "Summary judgment for second/third/fourth defendants in commercial-lease claim. USD 1.08M sought; defendants found not parties to lease. Strong on every primitive: full English-style party identification, Caparo-test reasoning citing 8 English HL/CA cases plus 2 ADGMCFI cases, ADGM Court Procedure Rules 2016 Rule 68(1)(a) explicitly cited as the summary-judgment authority, full notice/hearing/decision triplet (hearing 20 Jan 2026, judgment 4 Feb 2026), specific operative orders. Enforcement bridge via Cabinet Resolution + Abu Dhabi Law (UAE federal level) + ADGM jurisdiction over Al Reem Island."
        }
    },
    {
        "case_no": "ADGMCFI-2024-158",
        "url": "https://www.adgm.com/adgm-courts/judgments",
        "tribunal": "ADGM Courts",
        "division": "Court of First Instance",
        "date_issued": "2026-02-19",
        "parties": {"claimant": "Xetech Solutions Ltd", "defendant": "Pulsar Capital Holdings Limited"},
        "judge": "Justice Paul Heath KC",
        "neutral_citation": "[2026] ADGMCFI 0006",
        "claim_type": "substantive_breach",
        "outcome": "claim_granted",
        "operative_amount_aed": None, "operative_amount_usd": None,
        "rules_cited": ["ADGM Application of English Law Regulations 2015"],
        "cases_cited": [
            "Arnold v Britton & Ors [2015] UKSC 36",
            "Rainy Sky SA & Ors v Kookmin Bank [2011] 1 WLR 2900",
            "Wood v Capita Insurance Services Ltd [2017] UKSC 24",
            "Reardon Smith Line Ltd v Yngvar Hansen-Tangen [1976] 1 WLR 989 (HL)",
            "Prenn v Simmonds [1971] 1 WLR 1381 (HL)",
            "Ladd v Marshall [1954] 1 WLR 1489 (CA)",
            "Providence Building Services Ltd v Hexagon Housing Association Ltd [2026] UKSC 1",
            "Dijllah Jewellery FZE v AVA Trade Middle East Ltd [2026] ADGMCFI 0001"
        ],
        "primitive_scores_v02": {"PR1": 2, "PR2": 2, "PR3": 2, "PR4": 2, "PR5": 2, "PR6": 2},
        "coding": {
            "coder": "MaximLabs", "coded_on": "2026-04-27", "gold_set": True,
            "notes": "DIRECTLY THESIS-RELEVANT: Software development contract dispute (digital healthcare platform). Claimant Xetech is UK-based, defendant Pulsar is a third-party investor. Court applies Arnold-Rainy-Sky-Wood line of English contractual interpretation. Expert evidence on Azure DevOps records used to determine 'completion' of source code. This is exactly the kind of cross-border SaaS dispute the protocol thesis targets. Full primitives across the board."
        }
    },
    {
        "case_no": "ADGMCFI-2025-198",
        "url": "https://www.adgm.com/adgm-courts/judgments",
        "tribunal": "ADGM Courts",
        "division": "Court of First Instance",
        "date_issued": "2026-02-20",
        "parties": {"claimant": "A22 & B22", "defendant": "C22"},
        "judge": "Justice Paul Heath KC",
        "neutral_citation": "[2026] ADGMCFI 0007",
        "claim_type": "costs_assessment",
        "outcome": "claim_partially_granted",
        "operative_amount_aed": None, "operative_amount_usd": None,
        "rules_cited": [
            "ADGM Court Procedure Rules 2016 — Rule 172(1), Rule 195",
            "ADGM Courts, Civil Evidence, Judgments, Enforcement and Judicial Appointments Regulations 2015 — Section 49"
        ],
        "cases_cited": [
            "A22 & B22 v. C22 [2025] ADGMCFI 0018",
            "Afkar Capital Ltd v Saifallah Fikry [2018] ADGMCFI 0002",
            "Brookes v HSBC Bank Plc [2011] EWCA Civ 354",
            "Ghafoor v Cliff [2006] EWHC 825 (Ch)",
            "R (On the Application of Gourlay) v Parole Board [2021] 3 All ER 95 (UKSC)",
            "Turcon v Assaf [2025] ADGMCFI 0002"
        ],
        "primitive_scores_v02": {"PR1": 1, "PR2": 2, "PR3": 2, "PR4": 2, "PR5": 2, "PR6": 1},
        "coding": {
            "coder": "MaximLabs", "coded_on": "2026-04-27", "gold_set": True,
            "notes": "Anti-suit injunction case (anonymised). Costs allocation following discontinuance. PR1=1 because parties are anonymised — but this is a structural protection, not an absence of identity (court has full identity, public does not). PR3 cites both ADGM Court Procedure Rules 2016 Rule 172(1) presumption + Section 49 of Courts Regulations broad discretion. Demonstrates the ADGM tribunal's facility with English-law costs jurisprudence."
        }
    },
    {
        "case_no": "ADGMCFI-2024-322 + 323",
        "url": "https://www.adgm.com/adgm-courts/judgments",
        "tribunal": "ADGM Courts",
        "division": "Court of First Instance",
        "date_issued": "2026-02-23",
        "parties": {"claimant": "A17, A18 (anonymised)", "defendant": "B17, C17, D17, B18 (anonymised)"},
        "judge": "Justice Sir Andrew Smith",
        "neutral_citation": "[2026] ADGMCFI 0008",
        "claim_type": "arbitration_enforcement",
        "outcome": "claim_partially_granted",
        "operative_amount_aed": None, "operative_amount_usd": 7859178,
        "rules_cited": [
            "ADGM Court Procedure Rules 2016 — Rules 97(1), 110, 117"
        ],
        "cases_cited": [
            "Hulley Enterprises Ltd v Russian Federation [2021] EWHC 894 (Comm)",
            "Lachesis v Lacrosse [2021] DIFC CA 005",
            "Tibbles v SIG plc [2012] EWCA Civ",
            "JSC BTA Bank v Ablaylov [2015] UKSC 64",
            "Taurus Petroleum Ltd v State Oil Marketing Co [2017] UKSC 64",
            "Hardy Exploration v Govt of India [2018] EWHC",
            "Vitol SA v Capri Marine Ltd [2010] EWHC 458"
        ],
        "primitive_scores_v02": {"PR1": 1, "PR2": 2, "PR3": 2, "PR4": 2, "PR5": 2, "PR6": 2},
        "coding": {
            "coder": "MaximLabs", "coded_on": "2026-04-27", "gold_set": True,
            "notes": "USD 140M LCIA arbitration award enforcement; Worldwide Freezing Order; Third-Party Debt Order USD 7,859,178. Cross-jurisdictional: LCIA arbitration → ADGM enforcement → English High Court fraud challenge attempt. Notably cites a DIFC CA case (Lachesis v Lacrosse) — the two tribunals cite each other, evidence of an emerging UAE common-law sphere. PR6=2: arbitration recognition under NY Convention is structural."
        }
    },
    {
        "case_no": "ADGMCFI-2023-249 + ADGMCFI-2024-047",
        "url": "https://www.adgm.com/adgm-courts/judgments",
        "tribunal": "ADGM Courts",
        "division": "Court of First Instance",
        "date_issued": "2026-03-03",
        "parties": {"claimant": "Federal Properties Limited – Sole Proprietorship L.L.C", "defendant": "Rawafid H Jazairi Ibrahim; Amir Sadik Ali Al Samarraie"},
        "judge": "Justice Paul Heath KC",
        "neutral_citation": "[2026] ADGMCFI 0009",
        "claim_type": "real_property",
        "outcome": "claim_granted",
        "operative_amount_aed": None, "operative_amount_usd": None,
        "rules_cited": [
            "ADGM Real Property Regulations 2024 — Section 144",
            "ADGM Real Property Regulations (Fees) Rules 2024"
        ],
        "cases_cited": [
            "Federal Properties Limited v Rawafid H Jazairi Ibrahim [2025] ADGMCFI 0013",
            "Federal Properties Limited v Rawafid H Jazairi Ibrahim [2025] ADGMCFI 0020",
            "Federal Properties Limited v Rawafid H Jazairi Ibrahim [2025] ADGMCFI 0002 (CA)"
        ],
        "primitive_scores_v02": {"PR1": 2, "PR2": 2, "PR3": 2, "PR4": 2, "PR5": 2, "PR6": 2},
        "coding": {
            "coder": "MaximLabs", "coded_on": "2026-04-27", "gold_set": True,
            "notes": "Constructive-trust property transfer using Torrens land registration system (operative on Al Reem Island from 1 Jan 2025). Court directs ADGM Registration Authority to use its Section 144 correction power. PR6=2: ADGM tribunal directly compels a UAE state-side registry. This is exactly the 'enforcement bridge' primitive in operation — the digital extension layer (ADGM) reaches into the territorial sovereign's land registry."
        }
    },
    {
        "case_no": "ADGMCFI-2022-265",
        "url": "https://www.adgm.com/adgm-courts/judgments",
        "tribunal": "ADGM Courts",
        "division": "Court of First Instance — Commercial & Civil Division",
        "date_issued": "2026-03-06",
        "parties": {"claimant": "Union Properties PJSC; UPP Capital Investment Co LLC", "defendant": "Trinkler & Partners Ltd; First Fund Management Ltd; Jorg Klar; Paresh Khiara; Ahmed Khouri (and others)"},
        "judge": "Justice Sir Andrew Smith",
        "neutral_citation": "[2026] ADGMCFI 0010",
        "claim_type": "fraud",
        "outcome": "claim_dismissed",
        "operative_amount_aed": 320000000, "operative_amount_usd": None,
        "rules_cited": [
            "ADGM Court Procedure Rules 2016 — Rules 97(1), 110, 117",
            "ADGM Courts, Civil Evidence, Judgments, Enforcement and Judicial Appointments Regulations 2015 — Section 67",
            "ADGM Financial Services and Markets Regulations 2015 — Sections 103, 218(1), 242",
            "ADGM Application of English Law Regulations 2015",
            "UAE Federal Law No. 2 of 2015 (Commercial Companies)",
            "UAE Federal Law No. 5 of 1985 (Civil Transactions)",
            "Private International Law (Miscellaneous Provisions) Act 1995 (UK) — Sections 11, 12"
        ],
        "cases_cited": [
            "Union Properties v Trinkler [2025] ADGMCFI 0016, [2025] ADGMCFI 0015, [2024] ADGMCFI 0014, [2024] ADGMCFI 0006, [2023] ADGMCFI 0011, [2023] ADGMCFI 0009 (six prior orders in same case)",
            "Caparo (and dozens of English authorities)",
            "Smith New Court Securities v Scrimgeour Vickers [1997] AC 254"
        ],
        "primitive_scores_v02": {"PR1": 2, "PR2": 2, "PR3": 2, "PR4": 2, "PR5": 2, "PR6": 2},
        "coding": {
            "coder": "MaximLabs", "coded_on": "2026-04-27", "gold_set": True,
            "notes": "AED 320M fraud claim dismissed — Claimants found victims of fraud but failed to prove these specific defendants were party. The richest precedent-and-rule citation in the corpus: 8+ ADGM-internal cases, 30+ English cases, UK statute, UAE federal laws, ADGM regulations across multiple instruments. Fraud was real (court so found); evidentiary failure dispositive. PR3=2 with overflow."
        }
    },
    {
        "case_no": "ADGMCFI-2020-020",
        "url": "https://www.adgm.com/adgm-courts/judgments",
        "tribunal": "ADGM Courts",
        "division": "Court of First Instance — Commercial & Civil Division",
        "date_issued": "2026-04-15",
        "parties": {"claimant": "Secure Capital Equipment L.L.C", "defendant": "NMC Healthcare Limited (in administration)"},
        "judge": "Justice Sir Andrew Smith",
        "neutral_citation": "[2026] ADGMCFI 0011",
        "claim_type": "insolvency",
        "outcome": "application_refused",
        "operative_amount_aed": 26000000, "operative_amount_usd": None,
        "rules_cited": [
            "ADGM Insolvency Regulations 2022 — Sections 45(5), 76(1), 76(3)",
            "ADGM Insolvency Regulations 2015 — Sections 45(5), 76(1), 76(3)"
        ],
        "cases_cited": [
            "NMC Healthcare Limited v Noor Capital PSC [2022] ADGMCFI 0003",
            "Noor Capital PSC v NMC Healthcare Limited [2026] ADGMCFI 0004",
            "Re Atlantic Computer Systems Plc [1992] Ch 505",
            "CargoLogicAir Ltd v WWTAI AirOpCo 1 Bermuda Ltd [2024] EWHC 508 (Comm)",
            "South Coast Construction Ltd v Iverson Road Ltd [2017] EWHC 61 (TCC)"
        ],
        "primitive_scores_v02": {"PR1": 2, "PR2": 2, "PR3": 2, "PR4": 2, "PR5": 2, "PR6": 2},
        "coding": {
            "coder": "MaximLabs", "coded_on": "2026-04-27", "gold_set": True,
            "notes": "Permission refused to continue Dubai Court proceedings against NMC Healthcare (in DOCA administration). NMC Healthcare also appears in the DIFC corpus (CFI 079/2020). The same insolvency proceeding visible in two tribunals — useful cross-tribunal triangulation point. ADGM applies 2015+2022 versions of its own Insolvency Regulations — explicit version-binding (PR3=2). PR6=2: ADGM administration order has effect over Dubai Court proceedings."
        }
    }
]


def main():
    with open(DATA) as f:
        cases = json.load(f)

    # Migrate existing DIFC cases
    migrated = []
    missing_v02 = []
    for c in cases:
        new = dict(c)
        new["tribunal"] = "DIFC Courts"
        if "primitive_scores" in new:
            new["primitive_scores_v01"] = new.pop("primitive_scores")
        v02 = DIFC_V02.get(new["case_no"])
        if v02 is None:
            missing_v02.append(new["case_no"])
            v02 = {"PR1": 2, "PR2": 2, "PR3": 2, "PR4": 2, "PR5": 2, "PR6": 1}
        new["primitive_scores_v02"] = v02
        # Reorder keys for readability
        ordered = {}
        for k in ["case_no", "url", "tribunal", "division", "date_issued",
                  "parties", "judge", "neutral_citation", "claim_type",
                  "outcome", "operative_amount_aed", "operative_amount_usd",
                  "rules_cited", "cases_cited",
                  "primitive_scores_v01", "primitive_scores_v02", "coding"]:
            if k in new:
                ordered[k] = new[k]
        migrated.append(ordered)

    if missing_v02:
        print(f"WARNING: missing v0.2 scores for {missing_v02}")

    # Append ADGM entries
    migrated.extend(ADGM_ENTRIES)

    with open(DATA, "w") as f:
        json.dump(migrated, f, indent=2)
    print(f"wrote {len(migrated)} judgments ({len(cases)} DIFC migrated + {len(ADGM_ENTRIES)} ADGM new)")


if __name__ == "__main__":
    main()
