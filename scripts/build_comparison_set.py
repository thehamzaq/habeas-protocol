"""
Build data/comparison_set.json — a peer-court comparison set scored against
the v0.2 rubric.

Three courts, n=30 each, stratified across claim types:

  - English Commercial Court (KBD Comm) — common-law peer, BAILII-published.
  - Delaware Court of Chancery — US peer, courts.delaware.gov / Lexis.
  - Cour d'appel de Paris, Chambre internationale (ICCP-CA) — civil-law foil.
    Tests whether PR3 (specific clause + version cited) discriminates by
    legal family. French judgments cite "article L. XXX-Y du Code de
    commerce", versioned by amendment date — should score 2 if the rubric
    measures form (versioned clause-citation) rather than common-law style.

Each entry is a CASE-TYPE SLOT, not a named case. Scoring is class-default,
parameterised by the court's typical publication form for that claim type.
A separate fetch step (scripts/fetch_peer_courts.py — TODO) is intended to
bind each slot to a real, named citation drawn from BAILII / Delaware /
the ICCP-CA register, after which scores are hand-validated.

The provisional scoring is itself diagnostically useful: if the rubric
predicts these three peer courts to score at-or-near DIFC/ADGM/SICC, that
is itself the falsifiable prediction.
"""

import json
from datetime import date
from pathlib import Path


HERE = Path(__file__).resolve().parent.parent
OUT = HERE / "data" / "comparison_set.json"

CODER = "MaximLabs (provisional-class-default)"
CODED_ON = date(2026, 5, 3).isoformat()


# Claim-type stratification target — drawn from data/schema.json claim_type
# enum. n=30 per court, distributed approximately by published frequency
# in commercial divisions.
STRATA = [
    ("substantive_breach", 8),
    ("costs_assessment", 4),
    ("jurisdictional_challenge", 4),
    ("interim_relief", 3),
    ("arbitration_recognition", 3),
    ("arbitration_enforcement", 2),
    ("summary_judgment", 2),
    ("interpretation", 2),
    ("permission_to_appeal", 1),
    ("case_management", 1),
]
assert sum(n for _, n in STRATA) == 30


def slot(
    court_id: str,
    n_in_strata: int,
    strata_label: str,
    representative_url: str,
    PR1: int,
    PR2: int,
    PR3: int,
    PR4: int,
    PR5: int,
    PR6: int,
    SP1: int,
    SP2: int,
    rationale: dict,
):
    return {
        "slot_id": f"{court_id}-{strata_label}-{n_in_strata:02d}",
        "court": court_id,
        "claim_type": strata_label,
        "named_case": None,  # populated by fetch_peer_courts.py
        "neutral_citation": None,
        "representative_url": representative_url,
        "primitive_scores_v02": {
            "PR1": PR1, "PR2": PR2, "PR3": PR3,
            "PR4": PR4, "PR5": PR5, "PR6": PR6,
        },
        "system_properties_v02": {"SP1": SP1, "SP2": SP2},
        "rationale": rationale,
        "coding": {
            "coder": CODER,
            "coded_on": CODED_ON,
            "gold_set": False,
            "notes": (
                "Class-default per-claim-type score. Bind to named case via "
                "fetch_peer_courts.py + hand-validate before publication."
            ),
        },
    }


# ============================================================================
# English Commercial Court (KBD Comm)
# - BAILII publishes full judgments with [YYYY] EWHC NNNN (Comm) citation.
# - Judgments include parties, dated procedural history, statutory and
#   precedent citation, and operative orders. PR3 is consistently 2 because
#   English Commercial Court judgments cite specific paragraphs of the CPR /
#   Arbitration Act 1996 / contractual clauses with version.
# - SP1 = 2 (Parliament + senior judiciary set rules; KBD applies them);
# - SP2 = 2 (Court of Appeal + UKSC).
# ============================================================================

ECC_BASE_RATIONALE = {
    "PR1": "2 — full party names, parties' counsel, judge in published header",
    "PR2": "2 — procedural history, witness statements, exhibits referenced "
           "with dates and bundle pagination",
    "PR3": "2 — CPR rule + practice direction, statute + section, precedent "
           "+ paragraph cited specifically",
    "PR4": "2 — pleadings → CMC → trial → judgment triplet documented",
    "PR5": "2 — operative order with quantum, interest, costs",
    "PR6": "2 — judgment debt enforceable; arbitration awards enforced under "
           "Arbitration Act 1996 ss 66, 100–104 (NY Convention)",
    "SP1": "2 — CPR Rules Committee + Parliament make rules; KBD applies them",
    "SP2": "2 — Court of Appeal + UKSC",
}

ecc_url = ("https://www.bailii.org/cgi-bin/markup.cgi?doc=/ew/cases/EWHC/Comm/"
           "&query=&method=boolean")

ecc_entries = []
for stratum, n in STRATA:
    for i in range(n):
        # Costs assessments and case management orders sometimes lack
        # explicit cross-border bridge → PR6 = 1
        rationale = dict(ECC_BASE_RATIONALE)
        if stratum in ("costs_assessment", "case_management",
                       "permission_to_appeal"):
            rationale["PR6"] = ("1 — intra-jurisdictional order; enforcement "
                                "implicit via High Court process, not "
                                "externally bridged")
            pr6 = 1
        else:
            pr6 = 2
        ecc_entries.append(slot(
            "EWHC_Comm", i + 1, stratum, ecc_url,
            2, 2, 2, 2, 2, pr6, 2, 2, rationale,
        ))


# ============================================================================
# Delaware Court of Chancery
# - Published on courts.delaware.gov; full opinions with parties, full case
#   number, vice chancellor, and operative order.
# - PR3: cites Delaware General Corporation Law (DGCL) sections + Court of
#   Chancery Rules + precedent (e.g., Trados, Aronson, Caremark) with full
#   paragraph references.
# - SP1: Delaware Legislature + Court of Chancery Rules Committee make
#   rules; Vice Chancellors apply them — 2.
# - SP2: Delaware Supreme Court — 2.
# - PR6: Delaware judgments enforceable in 49 sister states under Full
#   Faith and Credit Clause; cross-border via Hague Convention on Service.
# ============================================================================

DCC_BASE_RATIONALE = {
    "PR1": "2 — full party names, counsel, Vice Chancellor in caption",
    "PR2": "2 — Chancery's evidentiary record (exhibits JX-1, JX-2 …) "
           "indexed in opinion",
    "PR3": "2 — DGCL § cited with subsection; Court of Chancery Rule cited; "
           "precedent (e.g., Aronson, Caremark) with paragraph",
    "PR4": "2 — pleadings, motion practice, trial / paper record, opinion",
    "PR5": "2 — order in DCM-style: declarations, injunctions, fee awards "
           "with quantum",
    "PR6": "2 — Full Faith and Credit + Hague Service for cross-border; "
           "specific to corporate-law remedies",
    "SP1": "2 — General Assembly + DGCL amendments; Chancery applies",
    "SP2": "2 — Delaware Supreme Court direct appeal",
}

dcc_url = "https://courts.delaware.gov/opinions/"

dcc_entries = []
for stratum, n in STRATA:
    for i in range(n):
        rationale = dict(DCC_BASE_RATIONALE)
        # DCC handles few "arbitration_recognition" / "interim_relief" of
        # the DIFC/ADGM type; books-and-records (s 220) and merger
        # appraisal dominate. Approximate by mapping to substantive_breach
        # quality — PR scores remain at ceiling.
        if stratum in ("costs_assessment", "case_management",
                       "permission_to_appeal"):
            rationale["PR6"] = ("1 — intra-Delaware order; cross-border "
                                "enforcement implicit only")
            pr6 = 1
        else:
            pr6 = 2
        dcc_entries.append(slot(
            "DEL_Chancery", i + 1, stratum, dcc_url,
            2, 2, 2, 2, 2, pr6, 2, 2, rationale,
        ))


# ============================================================================
# Cour d'appel de Paris — Chambre internationale commerciale (ICCP-CA)
# CIVIL-LAW FOIL.
# - The chamber publishes judgments in French + English on the official site
#   with full case caption, parties, parties' counsel, court composition.
# - PR3 (rule-bind): French judgments cite "article L. XXX-Y du Code de
#   commerce" or "article XXXX du Code civil" with the in-force date implied
#   by the version used. Modern French commercial-court practice references
#   the article AT THE DATE OF THE FACTS, which is operationally a versioned
#   citation. Score: 2 if rubric measures form, 1 if rubric is implicitly
#   common-law-shaped.
#   - We score 2 here as the FALSIFIABLE PREDICTION. A second coder may
#     argue 1 — that disagreement is itself diagnostic of rubric bias.
# - PR4 (procedure): civil-law procedure is written-record-heavy; mise en
#   état + audience de plaidoirie + délibéré → fully documented. Score 2.
# - PR5 (operative ruling): dispositif is unambiguous in French judgments
#   (DECIDE: confirms / overturns / awards quantum). Score 2.
# - PR6 (enforcement bridge): EU-internal (Brussels I bis Recast) +
#   NY Convention for arbitration. Score 2 for cross-border-flagged matters.
# - SP1: Parliament + Conseil constitutionnel make rules; courts apply. 2.
# - SP2: Cour de cassation. 2.
# ============================================================================

ICCP_BASE_RATIONALE = {
    "PR1": "2 — caption identifies parties, counsel (avocats), composition",
    "PR2": "2 — pièces de procédure indexed; conclusions communiquées dated",
    "PR3": ("2 — articles of the Code de commerce / Code civil cited with "
            "the in-force version applicable to the facts (versioning is "
            "implicit in French civilian practice but operationally "
            "equivalent to common-law version-pinning)"),
    "PR4": "2 — mise en état + plaidoirie + délibéré documented",
    "PR5": "2 — dispositif unambiguous: confirme / infirme / condamne with "
           "quantum and astreinte where applicable",
    "PR6": "2 — Brussels I bis Recast for EU + NY Convention for arbitration; "
           "ICCP cases are by design cross-border",
    "SP1": "2 — Parlement + Conseil constitutionnel make law; the court applies",
    "SP2": "2 — Cour de cassation",
}

iccp_url = ("https://www.cours-appel.justice.fr/paris/"
            "international-chamber-paris-court-appeal")

iccp_entries = []
for stratum, n in STRATA:
    for i in range(n):
        rationale = dict(ICCP_BASE_RATIONALE)
        # ICCP-CA cases are by design cross-border — PR6 stays at 2 even
        # for costs / case management. The civil-law-foil diagnostic
        # depends on PR3 staying at 2; a hand-validation finding PR3=1
        # would be informative.
        iccp_entries.append(slot(
            "ICCP_CA_Paris", i + 1, stratum, iccp_url,
            2, 2, 2, 2, 2, 2, 2, 2, rationale,
        ))


entries = ecc_entries + dcc_entries + iccp_entries
assert len(entries) == 90, len(entries)


def main():
    payload = {
        "$schema": "data/schema_comparison.json",
        "version": "v0.2",
        "purpose": (
            "Peer-court comparison set (n=90 across 3 courts × 30 case-type "
            "slots). Tests whether the v0.2 rubric translates beyond the "
            "DIFC/ADGM/SICC family to other commercial courts of comparable "
            "stature, including a civil-law foil (ICCP-CA Paris). The "
            "falsifiable prediction is that all three peer courts score "
            "near-ceiling on per-ruling primitives — confirming the rubric "
            "measures procedural form rather than DIFC/ADGM/SICC-specific "
            "idiom. The civil-law foil specifically tests PR3."
        ),
        "scoring_provenance": (
            "Each entry is a class-default slot keyed by (court, claim type). "
            "Slots are NOT bound to named cases; binding + hand-validation "
            "happens via scripts/fetch_peer_courts.py (TODO) and an IRR "
            "exercise. Coder tag 'MaximLabs (provisional-class-default)' "
            "marks this provenance. These provisional scores function as "
            "the falsifiable prediction; deviations on hand-validation are "
            "themselves the empirical contribution."
        ),
        "courts": {
            "EWHC_Comm": "English Commercial Court (King's Bench Division, Commercial Court)",
            "DEL_Chancery": "Delaware Court of Chancery",
            "ICCP_CA_Paris": "Cour d'appel de Paris — Chambre internationale commerciale",
        },
        "claim_type_strata": [
            {"claim_type": s, "n_per_court": n} for s, n in STRATA
        ],
        "n_total": len(entries),
        "n_per_court": 30,
        "entries": entries,
    }
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    print(f"wrote {OUT} with {len(entries)} entries across "
          f"{len(payload['courts'])} courts")


if __name__ == "__main__":
    main()
