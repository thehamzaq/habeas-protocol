"""
Build data/falsification_set.json — 30 non-DIFC/ADGM/SICC instruments scored
against the v0.2 rubric to test whether the rubric can discriminate genuine
commercial-court rulings from instruments that share some, but not all, of
the procedural form of a tribunal ruling.

The set is class-stratified across five classes of six instruments:

  A. Sealed / digest-only commercial-arbitration awards
     (ICC, LCIA, SIAC, HKIAC, JAMS, ICDR-AAA International).
     Expected: very low on PR1/PR2/PR5 (identity/evidence/operative outcome
     not externally observable), partial on PR3/PR4, high on PR6 (NY Convention).

  B. Decentralised / on-chain "tribunals"
     (Kleros, Aragon Court, ENS DAO governance, MakerDAO governance,
     Decentraland DAO, Optimism Citizens House).
     Expected: low across the board, especially SP1/SP2.

  C. Regulator-issued enforcement instruments
     (UK FCA Final Notice, US SEC OIP, DIFC DFSA Enforcement Decision Notice,
     ADGM FSRA Enforcement Decision Notice, Dubai VARA enforcement notice,
     Singapore MAS Civil Penalty notice).
     Expected: HIGH on per-ruling primitives, MID on SP1 (rulemaker
     ≈ rule-applier in a single regulator).

  D. Platform / private adjudication
     (Meta Oversight Board, Apple App Store Review Board, eBay Money Back
     Guarantee, Amazon A-to-z Guarantee, PayPal Resolution Center, GitHub
     DMCA appeals).
     Expected: Meta OB scores high (the positive private-tribunal control);
     consumer-protection programmes score very low on PR2/PR3/PR5.

  E. Specialised dispute panels — POSITIVE CONTROL
     (WIPO UDRP, NAF UDRP, Czech Arbitration Court UDRP, Nominet DRS,
     ICANN URS, ICC Court of Expertise).
     Expected: NEAR-CEILING on per-ruling primitives. UDRP decisions are
     reasoned, published, rule-bound — the rubric *should* score them high.
     This is the falsification of the falsification: if a non-court instrument
     scores high, the rubric is measuring procedural form, not pedigree.

Each entry carries:
  - real institutional identifier or representative case citation
  - class-level prior + per-primitive rationale
  - coder = "MaximLabs (provisional-class-default)"

Hand-validation IS REQUIRED before any of these scores are reported in the
paper. The provenance tag makes that explicit.
"""

import json
from datetime import date
from pathlib import Path


HERE = Path(__file__).resolve().parent.parent
OUT = HERE / "data" / "falsification_set.json"

CODER = "MaximLabs (provisional-class-default)"
CODED_ON = date(2026, 5, 3).isoformat()


def entry(
    instrument_id: str,
    instrument_name: str,
    class_: str,
    parent_institution: str,
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
    notes: str = "",
):
    return {
        "instrument_id": instrument_id,
        "instrument_name": instrument_name,
        "class": class_,
        "parent_institution": parent_institution,
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
            "notes": notes
            or "Provisional class-default scoring; hand-validation required "
            "before publication.",
        },
    }


# ============================================================================
# Class A — Sealed / digest-only commercial-arbitration awards
# Default vector reasoning: confidentiality strips PR1 (parties), PR2 (evidence
# log), and PR5 (operative outcome) from external observability. Published
# digests carry partial PR3/PR4. PR6 is high (NY Convention reach). SP scoring
# is per-institution, not per-award.
# ============================================================================

CLASS_A_RATIONALE = {
    "PR1": "0 — parties anonymised in published digests by institutional rule",
    "PR2": "0 — submissions, exhibits, dated record not externally observable",
    "PR3": "1 — published summaries cite governing rules but typically not the "
           "specific clause-and-version applied to the operative finding",
    "PR4": "1 — procedure documented at institutional level (rules + practice "
           "notes) but per-award procedural triplet not externally verifiable",
    "PR5": "0 — operative amounts, deadlines, payee, payer not in digests",
    "PR6": "2 — institutional awards enforceable under NY Convention",
    "SP1": "2 — institution distinct from rule-maker (national arbitration "
           "law) and from rule-applier (tribunal of arbitrators)",
    "SP2": "1 — limited; set-aside / refusal of recognition under Article V "
           "rather than appeal on the merits",
}

class_a = [
    entry(
        "FAL-A-01", "ICC Court of Arbitration", "A_sealed_award",
        "International Chamber of Commerce", "https://iccwbo.org/dispute-resolution/",
        0, 0, 1, 1, 0, 2, 2, 1, CLASS_A_RATIONALE,
        "ICC publishes selected redacted excerpts in ICC Dispute Resolution "
        "Bulletin; per-award identity and quantum withheld by default.",
    ),
    entry(
        "FAL-A-02", "London Court of International Arbitration", "A_sealed_award",
        "LCIA", "https://www.lcia.org/",
        0, 0, 1, 1, 0, 2, 2, 1, CLASS_A_RATIONALE,
        "LCIA publishes Annual Casework Reports with aggregated statistics; "
        "individual awards confidential under LCIA Rules Art 30.",
    ),
    entry(
        "FAL-A-03", "Singapore International Arbitration Centre", "A_sealed_award",
        "SIAC", "https://siac.org.sg/",
        0, 0, 1, 1, 0, 2, 2, 1, CLASS_A_RATIONALE,
        "SIAC publishes Annual Reports and selected anonymised case summaries; "
        "awards are confidential under SIAC Rule 39.",
    ),
    entry(
        "FAL-A-04", "Hong Kong International Arbitration Centre", "A_sealed_award",
        "HKIAC", "https://www.hkiac.org/",
        0, 0, 1, 1, 0, 2, 2, 1, CLASS_A_RATIONALE,
        "HKIAC publishes statistics + brief decision summaries; full awards "
        "confidential under 2024 Administered Arbitration Rules.",
    ),
    entry(
        "FAL-A-05", "JAMS International", "A_sealed_award",
        "JAMS", "https://www.jamsadr.com/",
        0, 0, 1, 1, 0, 2, 2, 1, CLASS_A_RATIONALE,
        "JAMS provides ADR services; awards confidential by default unless "
        "parties opt to publish.",
    ),
    entry(
        "FAL-A-06", "ICDR / AAA International Centre for Dispute Resolution",
        "A_sealed_award", "AAA-ICDR",
        "https://www.icdr.org/",
        0, 0, 1, 1, 0, 2, 2, 1, CLASS_A_RATIONALE,
        "AAA-ICDR publishes anonymised summaries of selected awards; per-award "
        "operative content confidential.",
    ),
]


# ============================================================================
# Class B — Decentralised / on-chain "tribunals"
# These score low SP1/SP2 by design (no separation of rule-making from
# rule-application; no defined external appeal). On-chain disclosure means PR1
# and PR2 score better than confidential awards (everything is on-chain), but
# operative outcomes typically lack reasoned rule application.
# ============================================================================

class_b = [
    entry(
        "FAL-B-01", "Kleros Court", "B_on_chain",
        "Kleros Cooperative", "https://kleros.io/",
        1, 1, 0, 1, 1, 0, 0, 0,
        {
            "PR1": "1 — Ethereum addresses, no legal-name binding; pseudonymous",
            "PR2": "1 — case file is on-chain (IPFS evidence pointers), but no "
                   "structured submissions log akin to a court",
            "PR3": "0 — jurors apply Court Policy + their own judgment; no "
                   "specific clause-citation requirement",
            "PR4": "1 — voting procedure documented; no notice/hearing/reasons "
                   "triplet for the loser",
            "PR5": "1 — token transfer is unambiguous; rationale absent",
            "PR6": "0 — no enforcement bridge outside the protocol",
            "SP1": "0 — Kleros DAO sets policy and stakers apply it; merged",
            "SP2": "0 — appeals are de novo Kleros rounds, not external review",
        },
        "https://klerosboard.com/ tracks dispute IDs publicly.",
    ),
    entry(
        "FAL-B-02", "Aragon Court (now Aragon Network DAO arbitration)",
        "B_on_chain", "Aragon Association",
        "https://docs.aragon.org/",
        1, 1, 0, 1, 1, 0, 0, 0,
        {
            "PR1": "1 — pseudonymous EVM addresses",
            "PR2": "1 — IPFS evidence; on-chain submissions",
            "PR3": "0 — guardians vote on \"the right outcome\"; no clause cite",
            "PR4": "1 — voting flow defined; no procedural triplet enforced",
            "PR5": "1 — token outcome on-chain; no reasoned ruling",
            "PR6": "0 — no external enforcement bridge",
            "SP1": "0 — Aragon DAO ≈ rule-maker and rule-applier",
            "SP2": "0 — internal appeal rounds only",
        },
        "Aragon Court was wound down 2023; protocol historical reference.",
    ),
    entry(
        "FAL-B-03", "ENS DAO governance dispute resolution",
        "B_on_chain", "Ethereum Name Service DAO",
        "https://docs.ens.domains/dao/",
        0, 1, 0, 1, 1, 0, 0, 0,
        {
            "PR1": "0 — token-holder addresses; no party identification",
            "PR2": "1 — proposals on Snapshot/Tally; comments off-chain",
            "PR3": "0 — votes apply preference, not a rule-of-decision",
            "PR4": "1 — proposal flow defined; no hearing right",
            "PR5": "1 — token outcome unambiguous; no reasons",
            "PR6": "0 — protocol-internal only",
            "SP1": "0 — token-holders both make and apply policy",
            "SP2": "0 — no defined appeal",
        },
    ),
    entry(
        "FAL-B-04", "MakerDAO governance dispute",
        "B_on_chain", "MakerDAO (now Sky)",
        "https://vote.makerdao.com/",
        0, 1, 0, 1, 1, 0, 0, 0,
        {
            "PR1": "0 — anonymous token-holders",
            "PR2": "1 — on-chain proposal record",
            "PR3": "0 — no rule-of-decision constraint on voters",
            "PR4": "1 — vote flow + cooldown defined",
            "PR5": "1 — outcome unambiguous as state change",
            "PR6": "0 — no external enforcement",
            "SP1": "0 — token-holder = rulemaker = rule-applier",
            "SP2": "0",
        },
    ),
    entry(
        "FAL-B-05", "Decentraland DAO Security Council decisions",
        "B_on_chain", "Decentraland DAO",
        "https://governance.decentraland.org/",
        0, 1, 0, 1, 1, 0, 1, 0,
        {
            "PR1": "0 — pseudonymous Council members; complainants pseudonymous",
            "PR2": "1 — proposal record on Snapshot; partial",
            "PR3": "0 — Code of Ethics referenced but not applied as rule",
            "PR4": "1 — Council process documented; no hearing right",
            "PR5": "1 — Council action on-chain",
            "PR6": "0 — no external enforcement bridge",
            "SP1": "1 — Council distinct from DAO general vote",
            "SP2": "0 — no defined appeal beyond DAO override vote",
        },
    ),
    entry(
        "FAL-B-06", "Optimism Citizens' House grant disputes",
        "B_on_chain", "Optimism Collective",
        "https://community.optimism.io/",
        0, 1, 0, 1, 1, 0, 1, 0,
        {
            "PR1": "0 — Citizen badge holders pseudonymous",
            "PR2": "1 — Charter Bicameral process logged on Snapshot",
            "PR3": "0 — Citizenship Charter cited at level of principle only",
            "PR4": "1 — process steps defined; no hearing right",
            "PR5": "1 — RetroPGF allocations on-chain",
            "PR6": "0 — no external enforcement",
            "SP1": "1 — Citizens' House distinct from Token House",
            "SP2": "0",
        },
    ),
]


# ============================================================================
# Class C — Regulator-issued enforcement instruments
# These score high on per-ruling primitives by design (regulators publish
# reasoned, rule-bound notices) but fail SP1: the actor that wrote the rule
# (e.g., the FCA Handbook) is the actor that applies it.
# ============================================================================

class_c = [
    entry(
        "FAL-C-01", "UK FCA Final Notice", "C_regulator",
        "Financial Conduct Authority",
        "https://www.fca.org.uk/publications/final-notices",
        2, 2, 2, 2, 2, 2, 1, 1,
        {
            "PR1": "2 — firm name, FRN, addresses for service published",
            "PR2": "2 — investigation timeline, witness list, exhibits indexed",
            "PR3": "2 — Handbook clauses cited with versioned reference",
            "PR4": "2 — Warning Notice → Decision Notice → Final Notice triplet",
            "PR5": "2 — penalty quantum, restitution, prohibition unambiguous",
            "PR6": "2 — directly enforceable as debt under FSMA s 390",
            "SP1": "1 — FCA writes Handbook AND issues Final Notices; partial",
            "SP2": "1 — Upper Tribunal review available but no merits appeal",
        },
        "Representative: FCA Final Notice templates 2020–2026. Per-ruling "
        "primitives are at ceiling — rubric correctly recognises regulator "
        "notices as procedurally well-formed; SP1 marks the institutional "
        "merger.",
    ),
    entry(
        "FAL-C-02", "US SEC Order Instituting Proceedings (OIP)",
        "C_regulator", "Securities and Exchange Commission",
        "https://www.sec.gov/litigation/admin",
        2, 2, 2, 2, 2, 2, 1, 2,
        {
            "PR1": "2 — respondent identified with full corporate detail",
            "PR2": "2 — investigative record summarised in OIP",
            "PR3": "2 — Securities Act / Exchange Act sections cited with "
                   "rule numbers",
            "PR4": "2 — administrative procedure under APA s 554",
            "PR5": "2 — sanction unambiguous (fine, disgorgement, bar)",
            "PR6": "2 — federal court enforceable under SEA s 21",
            "SP1": "1 — SEC writes rules and applies them in OIPs (in-house ALJ)",
            "SP2": "2 — D.C. Circuit / federal court appeal under APA s 706",
        },
        "Lucia v SEC (2018) made ALJ separation more salient but the "
        "rule-maker / rule-applier merger remains structural.",
    ),
    entry(
        "FAL-C-03", "DFSA Enforcement Decision Notice",
        "C_regulator", "Dubai Financial Services Authority",
        "https://www.dfsa.ae/enforcement",
        2, 2, 2, 2, 2, 2, 1, 1,
        {
            "PR1": "2 — firm and individual respondents fully named",
            "PR2": "2 — DFSA investigation findings indexed in notice",
            "PR3": "2 — DFSA Rulebook modules + GEN/COB rules cited specifically",
            "PR4": "2 — Decision Notice + representations process",
            "PR5": "2 — fine, restitution, prohibition unambiguous",
            "PR6": "2 — DIFC Court enforcement under Regulatory Law 2004 Art 90",
            "SP1": "1 — DFSA writes Rulebook AND issues notices",
            "SP2": "1 — Financial Markets Tribunal review on points of law",
        },
        "Direct foil to DIFC Courts: SAME jurisdiction, different institutional "
        "type — the rubric should cleanly separate court from regulator.",
    ),
    entry(
        "FAL-C-04", "FSRA Enforcement Decision Notice",
        "C_regulator", "ADGM Financial Services Regulatory Authority",
        "https://en.adgm.thomsonreuters.com/rulebook/fsra-enforcement",
        2, 2, 2, 2, 2, 2, 1, 1,
        {
            "PR1": "2 — respondent identification full",
            "PR2": "2 — investigation and exhibits indexed",
            "PR3": "2 — FSRA Rulebook (FSMR, COBS, GEN) cited with module/rule",
            "PR4": "2 — Decision-and-Appeals Process under Regulations",
            "PR5": "2 — penalty quantum unambiguous",
            "PR6": "2 — ADGM Court enforcement",
            "SP1": "1 — FSRA rulemaker + applier",
            "SP2": "1 — ADGM Court review on points of law/procedure",
        },
        "ADGM-side foil — same separation diagnostic as DFSA.",
    ),
    entry(
        "FAL-C-05", "Dubai VARA Enforcement Notice",
        "C_regulator", "Virtual Assets Regulatory Authority",
        "https://www.vara.ae/en/regulations/regulatory-notices/",
        1, 1, 2, 1, 2, 2, 1, 1,
        {
            "PR1": "1 — firm named, individual respondents sometimes redacted",
            "PR2": "1 — investigation findings summarised, not indexed",
            "PR3": "2 — VARA Rulebook cited with chapter/rule",
            "PR4": "1 — process documented but limited representation rights",
            "PR5": "2 — fine quantum unambiguous (AED 50k–600k range observed)",
            "PR6": "2 — Dubai courts enforcement under Cabinet Decision",
            "SP1": "1 — VARA writes Rulebook + issues notices",
            "SP2": "1 — recent administrative-law appeal channel via Dubai courts",
        },
        "VARA already in primary corpus as comparator; reproducing here for "
        "cross-class consistency.",
    ),
    entry(
        "FAL-C-06", "Singapore MAS Civil Penalty Notice",
        "C_regulator", "Monetary Authority of Singapore",
        "https://www.mas.gov.sg/regulation/enforcement",
        2, 2, 2, 2, 2, 2, 1, 1,
        {
            "PR1": "2 — respondent fully identified",
            "PR2": "2 — facts and timeline indexed",
            "PR3": "2 — Securities and Futures Act sections cited",
            "PR4": "2 — civil penalty under SFA s 232 with consent / contested process",
            "PR5": "2 — penalty quantum unambiguous",
            "PR6": "2 — Singapore courts enforcement",
            "SP1": "1 — MAS rulemaker + applier",
            "SP2": "1 — judicial review only",
        },
    ),
]


# ============================================================================
# Class D — Platform / private adjudication
# Mixed: Meta Oversight Board scores high (positive private-tribunal control);
# consumer-protection programmes score very low.
# ============================================================================

class_d = [
    entry(
        "FAL-D-01", "Meta Oversight Board case decision",
        "D_platform", "Meta Oversight Board (LLC)",
        "https://www.oversightboard.com/decision/",
        2, 2, 2, 2, 2, 0, 2, 1,
        {
            "PR1": "2 — case caption + parties (user vs Meta) clear",
            "PR2": "2 — public-comment record, exhibits, prior decisions cited",
            "PR3": "2 — Meta Community Standards section + version cited; "
                   "international human-rights standards (ICCPR Art 19) cited",
            "PR4": "2 — written procedure with public comments",
            "PR5": "2 — leave-up / take-down / overturn unambiguous",
            "PR6": "0 — Meta is the only enforcer; Board is not externally enforceable",
            "SP1": "2 — Board structurally distinct from Meta (LLC, trust)",
            "SP2": "1 — no appeal; Board decision is final on the case",
        },
        "Positive private-tribunal control. If MOB scores ≥ DIFC on per-ruling "
        "primitives, the rubric is measuring *form*, not pedigree — which is "
        "the protocol's claim. PR6=0 + SP2=1 separate it from a court.",
    ),
    entry(
        "FAL-D-02", "Apple App Store Review Board decision",
        "D_platform", "Apple Inc.",
        "https://developer.apple.com/app-store/review/",
        1, 0, 1, 1, 1, 0, 0, 0,
        {
            "PR1": "1 — developer account named; appellant identified",
            "PR2": "0 — submissions and exhibits not externally observable",
            "PR3": "1 — App Review Guideline section cited; version handling unclear",
            "PR4": "1 — appeal flow exists; no hearing right",
            "PR5": "1 — outcome (approved / rejected) clear to developer; no reasons publicly published",
            "PR6": "0 — internal to App Store",
            "SP1": "0 — Apple writes guidelines AND adjudicates",
            "SP2": "0 — no external appeal",
        },
    ),
    entry(
        "FAL-D-03", "eBay Money Back Guarantee decision",
        "D_platform", "eBay Inc.",
        "https://www.ebay.com/help/policies/ebay-money-back-guarantee-policy",
        1, 0, 1, 0, 1, 0, 0, 0,
        {
            "PR1": "1 — buyer/seller account IDs",
            "PR2": "0 — case file not externally observable",
            "PR3": "1 — MBG policy referenced; no clause-cite",
            "PR4": "0 — no notice/hearing/decision triplet documented",
            "PR5": "1 — refund / no-refund unambiguous to parties",
            "PR6": "0 — internal to platform",
            "SP1": "0",
            "SP2": "0",
        },
    ),
    entry(
        "FAL-D-04", "Amazon A-to-z Guarantee decision",
        "D_platform", "Amazon.com, Inc.",
        "https://www.amazon.com/gp/help/customer/display.html?nodeId=GTGSMBE7XC2KQ73K",
        1, 0, 1, 0, 1, 0, 0, 0,
        {
            "PR1": "1 — buyer/seller IDs",
            "PR2": "0 — submissions opaque",
            "PR3": "1 — A-to-z policy referenced",
            "PR4": "0 — no procedural triplet",
            "PR5": "1 — refund decision unambiguous",
            "PR6": "0",
            "SP1": "0", "SP2": "0",
        },
    ),
    entry(
        "FAL-D-05", "PayPal Resolution Center decision",
        "D_platform", "PayPal Holdings, Inc.",
        "https://www.paypal.com/us/cshelp/article/help546",
        1, 0, 1, 0, 1, 0, 0, 0,
        {
            "PR1": "1 — account IDs",
            "PR2": "0 — submissions opaque",
            "PR3": "1 — User Agreement / Buyer Protection cited",
            "PR4": "0 — no procedural triplet",
            "PR5": "1 — outcome unambiguous to parties",
            "PR6": "0",
            "SP1": "0", "SP2": "0",
        },
    ),
    entry(
        "FAL-D-06", "GitHub DMCA / Acceptable Use appeals",
        "D_platform", "GitHub, Inc. (Microsoft)",
        "https://docs.github.com/en/site-policy/content-removal-policies/dmca-takedown-policy",
        1, 1, 1, 1, 1, 1, 0, 0,
        {
            "PR1": "1 — claimant + respondent in DMCA archive",
            "PR2": "1 — DMCA notice + counter-notice archived publicly at "
                   "github.com/github/dmca",
            "PR3": "1 — DMCA section 512 statutory basis; AUP otherwise",
            "PR4": "1 — notice / counter-notice flow documented",
            "PR5": "1 — restore / remove unambiguous",
            "PR6": "1 — DMCA-grounded statutory effect; AUP otherwise internal",
            "SP1": "0 — GitHub writes AUP + adjudicates",
            "SP2": "0 — no external appeal beyond external DMCA litigation",
        },
        "DMCA archive is a partial transparency exemplar — public DMCA archive "
        "lifts PR2 above platform-norm.",
    ),
]


# ============================================================================
# Class E — POSITIVE CONTROL: specialised dispute panels (UDRP and adjacent)
# These are NOT national courts. They ARE reasoned, published, rule-bound,
# and procedurally regular. The rubric SHOULD score them near-ceiling.
# If it does, the rubric is measuring procedural form (the claim of the paper).
# If it scores them at zero just because they aren't a court, the rubric is
# really measuring "is this a court."
# ============================================================================

CLASS_E_RATIONALE = {
    "PR1": "2 — complainant, respondent, registrar, mark-holder fully named",
    "PR2": "2 — complaint, response, exhibits, dated procedural orders archived",
    "PR3": "2 — UDRP Policy ¶ 4(a)(i)/(ii)/(iii) and Rules cited with version",
    "PR4": "2 — Notification + Response + Decision triplet under Rules",
    "PR5": "2 — transfer / cancel / deny unambiguous; effective via registrar",
    "PR6": "1 — domain transfer is registrar-enforceable, but court override "
           "available under ACPA / equivalent national law (UDRP ¶ 4(k))",
    "SP1": "2 — ICANN Policy distinct from provider's panel",
    "SP2": "1 — no appeal within UDRP; de novo court action available",
}

class_e = [
    entry(
        "FAL-E-01", "WIPO UDRP panel decision", "E_specialised_positive",
        "WIPO Arbitration and Mediation Center",
        "https://www.wipo.int/amc/en/domains/decisions/",
        *list(CLASS_E_RATIONALE_VALUES := (2, 2, 2, 2, 2, 1)),
        2, 1, CLASS_E_RATIONALE,
        "WIPO is the largest UDRP provider; over 60,000 published decisions "
        "since 1999. Strong positive control.",
    ),
    entry(
        "FAL-E-02", "NAF (Forum) UDRP panel decision",
        "E_specialised_positive", "Forum (formerly NAF)",
        "https://www.adrforum.com/decision-search",
        *CLASS_E_RATIONALE_VALUES, 2, 1, CLASS_E_RATIONALE,
        "Second-largest UDRP provider. Same UDRP Policy + Rules; identical "
        "procedural form.",
    ),
    entry(
        "FAL-E-03", "Czech Arbitration Court UDRP panel decision",
        "E_specialised_positive", "Czech Arbitration Court",
        "https://www.adr.eu/",
        *CLASS_E_RATIONALE_VALUES, 2, 1, CLASS_E_RATIONALE,
    ),
    entry(
        "FAL-E-04", "Nominet Dispute Resolution Service decision",
        "E_specialised_positive", "Nominet UK",
        "https://www.nominet.uk/disputes/",
        2, 2, 2, 2, 2, 1, 2, 2,
        {
            **CLASS_E_RATIONALE,
            "PR3": "2 — Nominet DRS Policy ¶ 2 + 3 cited specifically",
            "SP2": "2 — Nominet DRS has internal Appeal Panel before court "
                   "review; full SP2 ceiling",
        },
        "Nominet DRS is interesting because it has an INTERNAL APPEAL PANEL — "
        "scores SP2=2, exceeding most UDRP providers.",
    ),
    entry(
        "FAL-E-05", "ICANN Uniform Rapid Suspension (URS) decision",
        "E_specialised_positive", "ICANN URS providers",
        "https://www.icann.org/resources/pages/urs-2014-01-09-en",
        2, 2, 2, 2, 2, 1, 2, 1,
        {
            **CLASS_E_RATIONALE,
            "PR4": "2 — accelerated procedure documented; clear-and-convincing "
                   "evidence standard",
            "SP2": "1 — de novo URS available within 6 months",
        },
    ),
    entry(
        "FAL-E-06", "AAA Construction Industry Arbitration (published award)",
        "E_specialised_positive", "AAA Construction",
        "https://www.adr.org/construction",
        1, 1, 2, 2, 1, 2, 2, 1,
        {
            "PR1": "1 — typically anonymised in published digests",
            "PR2": "1 — partial — exhibits referenced in award not externally observable",
            "PR3": "2 — AIA / ConsensusDOCS clauses cited with version",
            "PR4": "2 — AAA Construction Rules procedure",
            "PR5": "1 — quantum often anonymised",
            "PR6": "2 — NY Convention / FAA",
            "SP1": "2 — AAA distinct from rule-maker (FAA + state law)",
            "SP2": "1 — limited FAA s 10 set-aside grounds",
        },
        "Compare to Class A — published-with-redaction sits between Class A "
        "(fully sealed) and Class E (fully published).",
    ),
]
del CLASS_E_RATIONALE_VALUES


entries = class_a + class_b + class_c + class_d + class_e


def main():
    payload = {
        "$schema": "data/schema_falsification.json",
        "version": "v0.2",
        "purpose": (
            "Falsification set: 30 instruments scored against the v0.2 rubric "
            "to test whether the rubric discriminates genuine commercial-court "
            "rulings from instruments that share some, but not all, of the "
            "procedural form of a tribunal ruling. Includes a positive control "
            "(Class E) — non-court instruments that the rubric SHOULD score "
            "high, demonstrating that the rubric measures procedural form "
            "rather than institutional pedigree."
        ),
        "scoring_provenance": (
            "All entries are class-default provisional scores assigned on "
            "the basis of public, institutionally-documented characteristics "
            "of the instrument class. Hand-validation against ≥3 specific "
            "instruments per class is REQUIRED before any of these scores "
            "are reported in the working paper. Coder tag "
            "'MaximLabs (provisional-class-default)' marks this provenance."
        ),
        "classes": {
            "A_sealed_award": "Confidential commercial-arbitration awards "
                              "(ICC, LCIA, SIAC, HKIAC, JAMS, AAA-ICDR)",
            "B_on_chain": "Decentralised / on-chain 'tribunals' (Kleros, "
                          "Aragon Court, ENS DAO, MakerDAO, Decentraland, "
                          "Optimism Citizens House)",
            "C_regulator": "Regulator-issued enforcement instruments (FCA, "
                           "SEC, DFSA, FSRA, VARA, MAS)",
            "D_platform": "Platform / private adjudication (Meta Oversight "
                          "Board, Apple App Store, eBay, Amazon, PayPal, "
                          "GitHub DMCA)",
            "E_specialised_positive": "POSITIVE CONTROL — specialised "
                                      "dispute panels (WIPO UDRP, Forum "
                                      "UDRP, Czech AC UDRP, Nominet DRS, "
                                      "ICANN URS, AAA Construction)",
        },
        "n_total": len(entries),
        "entries": entries,
    }
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    print(f"wrote {OUT} with {len(entries)} entries across "
          f"{len(payload['classes'])} classes")


if __name__ == "__main__":
    main()
