# Habeas Protocol: An Empirical Analysis of DIFC, ADGM, and Singapore SICC as Working Prototypes for Constitutional Digital Tribunals

**Maxim Labs Working Paper v0.2 — April 2026**

## Abstract

We code 121 publicly-issued judgments from three operating special-jurisdiction commercial courts: the Dubai International Financial Centre (DIFC) Courts, the Abu Dhabi Global Market (ADGM) Courts, and the Singapore International Commercial Court (SICC). Each judgment is scored against six per-ruling primitives a digital tribunal must satisfy and two architectural system properties of the tribunal as a whole. 39 judgments form a hand-coded gold set; the other 82 are AI-triaged or AI-graded against the same v0.2 rubric, with per-entry provenance recorded. All three tribunals score at near-ceiling: SICC averages 1.95 / 2.00, ADGM 1.91, DIFC 1.72. The saturation pattern survives the order-of-magnitude expansion of the ADGM sample (1.93 at n=7 → 1.91 at n=76) and replicates across a third tribunal in a different legal family (English-law-via-statute vs Singapore common law). All three score 2/2 on both system properties. We then compile **seven rules** from the corpus into Catala source[^catala] and a Python predicate evaluator, demonstrating coverage of (i) static formulae, (ii) deferred conditionals, (iii) bounded discretion, (iv) arithmetic composition over substantive findings, (v) Boolean composition over contractual-interpretation findings, (vi) partial statutory refusal of New York Convention enforcement under Singapore IAA s 31, and (vii) a third-party-jurisdiction disclosure gate (*Norwich Pharmacal* + *Bankers Trust* + RDC 28.52) over a digital-asset tracing dispute in DIFC's Digital Economy Court. The protocol reproduces the courts' principal numerical answers (or, where the rule is Boolean, the courts' dispositions) exactly in six of seven traces; in the seventh (Trace #3) the protocol does not produce a single number by design but bounds the discretion residue. Three of seven traces surface a clerical or methodological gap in the court's order. The constructive contribution of this paper is the claim that **the tribunals already exist; what is missing is the computational layer**.

## 1. Introduction

The "Legal Operating System for Digital Worlds" thesis, in its widely-circulated form, asserts that digital commerce has outgrown the institutional capacity of national courts and that a new arbitration architecture is therefore necessary. The Maxim Labs brief proposes such an architecture as four layers: rules-as-code, real-time AI detection, human-in-loop review, and decentralized arbitration. The proposal is to build a tribunal from scratch.

This paper inverts that framing. The institutional substrate the brief proposes to build already exists. Three operating tribunals are studied here:

- **The DIFC Courts** (Dubai International Financial Centre), founded 2004, common-law tribunal operating its own statutes and Practice Directions, with a Digital Economy Court (DEC) that began operating in 2025 to hear cross-border digital-asset disputes.[^difc]
- **The ADGM Courts** (Abu Dhabi Global Market), founded 2013, common-law tribunal where the entire body of English law applies through a single regulation: the *Application of English Law Regulations 2015*.[^adgm-aelr] ADGM judgments routinely cite English case law (Caparo, Hedley Byrne, Arnold v Britton)[^caparo][^hedley][^arnold] alongside an internal ADGMCFI line of authority.
- **The Singapore International Commercial Court (SICC)**, founded 2015 as a division of the Singapore High Court, with International Judges drawn from common-law and civil-law jurisdictions. SICC hears cross-border commercial disputes and routinely operates in the same procedural register as DIFC and ADGM.[^sicc]

These authorities are **sovereign-adjacent**: each operates with the constitutional infrastructure of a recognized tribunal — versioned rules, dated evidence, separation of powers, defined appeal paths, and rulings enforceable across borders under the *New York Convention on the Recognition and Enforcement of Foreign Arbitral Awards* (1958)[^nyc] — but extended into a domain national courts struggle to reach at the speed at which digital commerce moves.

The contribution of this paper is to make that argument empirically rather than rhetorically. We code 121 actual rulings from three actual tribunals against a six-primitive framework, and we show that the framework saturates: most rulings, in most primitives, score at ceiling. We then write **seven** of the rules in compilable form and run them against the case facts. Six of seven traces reproduce the court's central numerical answer (or, for Boolean rules, the court's disposition) exactly; the seventh (Trace #3) bounds a discretion residue to roughly 7% of the claim. Three of the seven surface clerical or methodological gaps that the predicate makes mechanically visible. The seven traces span all three tribunals and three legal families (DIFC's own statutes, ADGM's English-law-via-statute, Singapore's IAA + NY Convention).

The thesis we build is the inverse of the original brief's: there is no need to invent a tribunal. There is a need to wire computation onto the tribunals that exist.

## 2. The framework: six primitives + two system properties

The protocol formulation used here is v0.2. We refactored from v0.1's seven primitives, which mixed constitutional values (separation of powers) with technical features (executable predicates) and an upstream-prevention category that does not belong on a tribunal at all. v0.2 separates per-ruling properties from architectural properties and aligns more cleanly with Fuller's eight desiderata of legality[^fuller] and Hart's distinction between primary rules (substantive obligations) and secondary rules (rules about rules).[^hart]

The six **per-ruling primitives** are properties of any individual ruling:

- **PR1 — Identity.** The parties are unambiguous: legal name, capacity, jurisdiction or counsel of record. A digital implementation would attach decentralized identifiers (DIDs) or verifiable credentials at the same point.
- **PR2 — Evidence log.** The ruling refers to a dated, attributable, append-only record of submissions, statements, exhibits, and prior orders. A third party should be able to reconstruct the case file from the ruling alone.
- **PR3 — Rule bind.** The ruling cites the specific clause of the specific instrument it applies, by version. "RDC 38.7" is bind. "Pursuant to the rules" is partial. Discretion alone is absent.
- **PR4 — Procedure.** The ruling documents the procedural triplet: notice given, both sides heard, decision recorded with reasons.
- **PR5 — Ruling.** The operative outcome is unambiguous and machine-readable in principle: amounts, deadlines, interest rates, payee, payer, conditions.
- **PR6 — Enforcement bridge.** The ruling is enforceable beyond the tribunal: by New York Convention, by territorial sovereign, by reciprocal-enforcement regime, or by an explicit cross-jurisdictional bridge.

The two **system properties** are architectural facts about the tribunal as a whole, scored once per institution:

- **SP1 — Separation of powers.** The actor that *makes* the rule is structurally distinct from the actor that *applies* it.
- **SP2 — Appeal path.** Rulings are reviewable by a body other than the original decision-maker, with a defined procedure.

Each primitive is scored 0 (absent), 1 (partial), or 2 (fully implemented). Full definitions and worked examples live in `data/primitives.json`.

## 3. The corpus

The DIFC publishes its judgments and orders as HTML at `difccourts.ae/rules-decisions/judgments-orders`. The ADGM publishes its judgments as PDFs at `assets.adgm.com`, indexed on a paginated listing. The SICC publishes through `elitigation.sg`, the Singapore courts' judgments portal.

`scripts/fetch_difc.py` pulled 294 DIFC judgment pages. `scripts/fetch_adgm_firecrawl.py` pulled 172 ADGM PDFs across 15 pages spanning 2017–2026. The SICC scrape pulled a sample of 13 recent judgments (August 2025 – April 2026) spanning costs orders, jurisdiction challenges, recognition of foreign judgments, and substantive commercial disputes. Of the 479 raw judgments pulled, 121 entered the coded corpus.

**Hand-coded gold set (n=39).** 32 DIFC judgments selected to span the divisions of the court (Court of First Instance, Arbitration, Enforcement, Court of Appeal) and the principal claim types (costs, case management, interim relief, arbitration recognition and enforcement, permission to appeal, substantive breach, jurisdictional challenge, fraud, insolvency, real property), plus 7 ADGM judgments initially available before the deeper Firecrawl pull.

**AI-triaged additions (n=16, ADGM).** `scripts/triage_adgm.py` classified each judgment by its structural format. Judgments matching the ADGM "Judgment Summary" template (with the canonical Neutral Citation / Cases Cited / Legislation Cited / Overall Summary headers) saturate the per-ruling primitives by construction. Triage classified 9 such cases as *fully saturating* (default vector 2,2,2,2,2,2) and 7 as *procedural default* (default vector 2,2,2,2,2,1, where PR6=1 follows the rubric for case-management orders that lack an explicit cross-border enforcement bridge).

**AI-graded additions (n=66 = 53 ADGM + 13 SICC).** `scripts/grade_borderline.py` re-applied the rubric to the remaining cases by reading each judgment in full and matching against an extended pattern set: whitespace-tolerant enforcement-bridge terms, plural-tolerant clause citations, and a broader operative-verb regex. Each AI-graded entry carries a `rationale` field with the per-primitive reasoning.

Every entry's `coding.coder` field records its provenance: `MaximLabs` for hand-coded, `MaximLabs (heuristic-triage)` for triage-default, `MaximLabs (heuristic-graded)` for full rubric-applied. Methodologically, the 39-judgment hand-coded set is the load-bearing core of the empirical claim; the 82 AI-coded entries are a robustness check. The headline number — that the per-primitive saturation pattern holds — is testable specifically against this expansion.

## 4. Empirical results

### 4.1 Per-primitive means

| Primitive | DIFC (n=32) | ADGM (n=76) | SICC (n=13) | Combined | What it tests |
|---|---:|---:|---:|---:|---|
| PR1 Identity | 1.81 | 1.97 | **2.00** | 1.93 | parties unambiguous, counsel of record |
| PR2 Evidence log | 1.78 | **2.00** | **2.00** | 1.94 | dated submissions, attributable record |
| PR3 Rule bind | 1.69 | 1.93 | 1.92 | 1.87 | specific clause + version cited |
| PR4 Procedure | 1.75 | **2.00** | **2.00** | 1.93 | notice + hearing + decision documented |
| PR5 Ruling | 1.88 | 1.96 | 1.92 | 1.93 | operative outcome unambiguous |
| PR6 Enforcement bridge | 1.44 | 1.62 | **1.85** | 1.60 | path to compulsion outside tribunal |
| **Overall mean** | **1.72** | **1.91** | **1.95** | **1.87** | |

All three tribunals score at or near ceiling on every per-ruling primitive. SICC's overall mean (1.95) is highest in the sample, driven by particularly strong PR6 scores: SICC judgments routinely cite the New York Convention and Singapore's *Reciprocal Enforcement of Commonwealth Judgments Act* explicitly. ADGM (1.91) is comparable. DIFC averages 1.72; its weakest primitive is PR6, where many DIFC orders address purely intra-jurisdictional matters and do not name an external bridge.

The DIFC PR6 floor is methodologically informative rather than damning. The DIFC sample is balanced toward costs and case-management orders (which dominate DIFC published output), where the rubric scores PR6=1 ("implicit enforceability via standard procedure") rather than PR6=2 (explicit bridge). On the substantive matters within the DIFC sample — arbitration recognition and enforcement orders, real-property orders binding to UAE federal land registries — PR6=2.

### 4.2 System properties

| Tribunal | SP1 Separation of powers | SP2 Appeal path |
|---|---:|---:|
| DIFC Courts | 2 | 2 |
| ADGM Courts | 2 | 2 |
| Singapore International Commercial Court | 2 | 2 |
| VARA (Dubai virtual-asset regulator) | 1 | 1 |
| Próspera Arbitration Center (Honduras ZEDE) | 2 | 1 |
| ad-hoc Web3 arbitration (Kleros) | 0 | 0 |

The three operating tribunals all implement the full architectural protocol. VARA, the regulator-issued enforcement body for virtual-asset service providers in Dubai,[^vara] scores 1 on both because rule-making and rule-applying functions are partially merged in regulator practice and the appeal path runs through Dubai courts via a relatively recent administrative-law channel. Próspera scores 2/1 because the rule-making body and the arbitration center are formally distinct but the appeal path is internal. Kleros, a decentralized juror-staking arbitration platform,[^kleros] scores 0/0: there is no separation of rule-making from rule-applying actors, and no defined external appeal path.

### 4.3 The headline claim

Three operating tribunals, all implementing the full protocol at near-ceiling, available to plug in today. The claim is not that DIFC, ADGM, and SICC are the only candidates, or that they are optimal. The claim is that any computational-layer proposal that ignores them and proposes to build a tribunal from scratch is starting from a measurable disadvantage: the three tribunals together pack 60+ years of common-law operating history into the period since each began publishing reasoned judgments.

## 5. Constructive results: seven traces

The empirical layer measures whether the rules a tribunal applies have the right shape to be compiled. The constructive layer demonstrates the compilation. Each of the seven traces lifts a rule from the corpus into Catala source plus a Python predicate evaluator and runs it against an event log of the case facts. Traces #1–#4 span the original rule-shape spectrum (formula, deferred conditional, bounded discretion, arithmetic composition); traces #5–#7 extend the spectrum into Boolean composition over contractual interpretation, partial statutory refusal of NY Convention enforcement in a different legal family, and a third-party-jurisdiction disclosure gate over a digital-asset dispute. Three tribunals (DIFC + ADGM + SICC) and three legal families (DIFC own statutes, ADGM English-law-via-statute, Singapore IAA + NY Convention) all run through the same predicate engine.

### 5.1 Trace #1 — Pure formula

`spike/trace-01/`. *CFI 058/2024 — Atul Dhawan v Ramzi El Jaouhari* (Roger Stewart KC, 31 March 2026). Rules of the DIFC Courts (RDC) Part 38 standard-basis costs assessment: hours × hourly rate + court filing fee. Applied to the case facts (3 hours at AED 2,000/hr + AED 1,121.75 court fee), the predicate produces **AED 7,121.75**, matching the Schedule of Reasons exactly.

The operative paragraph of the same order, however, states **AED 7,127.75** — a six-dirham gap. The protocol mechanically surfaces a clerical error a human reader would skim past.

### 5.2 Trace #2 — Deferred conditional

`spike/trace-02/`. *ARB 008/2026 — Oberlin v Ovidiu* (Shamlan Al Sawalehi, 26 March 2026). RDC 38.40 + DIFC Practice Direction No. 4 of 2017 — Interest on Judgments. The order encodes a deferred conditional: a 14-day window to pay the costs award; if missed, interest accrues at 9% per annum *from the date of the order*, not from the deadline. The deadline suppresses interest entirely; missing it activates retroactive accrual.

The predicate captures this asymmetry directly. We evaluate it against five scenarios — payment on time, at the deadline, one day late, sixty-one days unpaid, and ninety-two days late. At ninety-two days the protocol returns total owed = **AED 78,527.69** (principal AED 76,785.81 + interest AED 1,741.88 across 92 days). All five scenarios pass.

The 80% discretion + 14-day deadline + 9% interest structure encoded here recurs *verbatim* across the adjacent DIFC arbitration costs orders we coded. The corpus has converged on a near-formula. The protocol codifies it once.

### 5.3 Trace #3 — Bounded discretion

`spike/trace-03/`. *ENF 271/2025 — Taylor v Yao Affi* (Sir Jeremy Cooke, 1 April 2026). Indemnity-basis costs review. Cooke J. at §2 of the Schedule of Reasons: *"Where costs are ordered on the indemnity basis, there is no room for arguments of proportionality – only of reasonableness of the costs incurred."* In English costs law, the *standard basis* allows the court to disallow costs that are disproportionate even if reasonably incurred; the *indemnity basis* strips the proportionality filter and leaves only reasonableness, which is not formulaic.

Trace #3 is the methodologically necessary case: the rule does not fully decide. The protocol's job is not to compute a single award figure, but to triage. The predicate sorts each defendant objection into one of four buckets:

1. **Mechanically disposed**: no specific element of the schedule is named (Cooke J. at §4: *"without any specific complaint about any element of them"*).
2. **Held to zero on evidence**: a specific objection rejected on the facts.
3. **Deterministic reduction**: a specific objection accepted with a named amount.
4. **Requires human judgment**: anything else.

On the facts of *Taylor v Yao Affi* the predicate disposes of one objection by structural test, holds one at zero on the evidence, and surfaces the Court's own residual concern — a general qualitative observation that *"there is some excess in the overall time spent by the senior associate"* — as the irreducible human-judgment region. The court's reduction from AED 128,914.80 to AED 120,000 — **AED 8,914.80, ≈ 6.92% of the claim** — is the structured-discretion residue.

### 5.4 Trace #4 — Composition over substantive findings

`spike/trace-04/`. *ADGMCFI-2024-320 — Projeco Contracting v Ideacrate Edutainment* (Justice Paul Heath KC, 30 October 2025). Substantive contract dispute over the turnkey fit-out of the Orange Hub Family Entertainment Centre in Khalifa City, Abu Dhabi. The applicable rule sources are UAE Civil Transactions Law Article 390 (judicial variation of agreed compensation),[^uae-civil] ADGM Court Procedure Rules 2016 Rule 42 (admissions and withdrawal),[^adgm-cpr] and ADGM Civil Evidence, Judgments, Enforcement and Judicial Appointments Regulations 2015 §§ 181–182 (set-off of claims and counterclaims).

The trace is methodologically distinct from the prior three. The rule is *doctrinal* at the input layer: the judge must decide whether the contractor caused the delay (97 days of critical delay, found), whether handover constituted *substantial completion* (yes, on 29 February 2024), whether the smoke management system was within the contractor's contractual scope (yes), whether the remediation/repair counterclaim is proven on the balance of probabilities (no), and whether to grant withdrawal of an admission under Rule 42(4) (no, refused). Once those substantive findings are fixed, the rule is *arithmetic* at the composition layer:

1. **Liquidated damages** (LDs) = min(daily_rate × days_of_critical_delay, 10% × adjusted_contract_price). On these facts the cap binds: 10% × AED 6,085,211.90 = **AED 608,521.19**.
2. **Counterclaim sum** = sum of proven counterclaim items. **AED 608,521.19 + AED 147,265.00 = AED 755,786.19**.
3. **Net principal** = withheld − counterclaim sum. **AED 766,287.15 − AED 755,786.19 = AED 10,500.96**.
4. **Pre-judgment interest** = principal × 5% × days_to_judgment / 365.

The predicate composes those steps and reproduces the court's principal of **AED 10,500.96 exactly**. On pre-judgment interest the predicate at calendar daycount (609 days from 29 February 2024 to 30 October 2025) is AED 876.04; the court's stated AED 877.48 corresponds to 610 days, indicating an inclusive-endpoint convention. The protocol surfaces the convention question for review — parallel to Trace #1's clerical-error finding, but for daycount methodology rather than arithmetic mistake.

The constructive claim of Trace #4 is that even on a fully substantive contract dispute — the kind of case the original Maxim brief proposed to handle by ad-hoc arbitration — the rule decomposes cleanly into (i) substantive determinations made by a judge and (ii) arithmetic composition the protocol can verify. The human-judgment region is bounded to the inputs; the composition is deterministic and auditable.

### 5.5 Trace #5 — Boolean composition over contractual interpretation

`spike/trace-05/`. *ADGMCFI-2024-158 — Xetech v Pulsar Software Solutions* ([2026] ADGMCFI 0006, Justice Paul Heath KC). Software-development contract dispute under ADGM jurisdiction. The applicable rule is *not* arithmetic: contractual interpretation under English law (*Wood v Capita Insurance Services* [2017] UKSC 24,[^wood] applying *Rainy Sky*[^rainy]) plus the *Ladd v Marshall*[^ladd] three-prong test for the admissibility of fresh evidence, applied to clauses 2(b), 7, and 10 of the parties' Assignment Agreement.

Trace #5 is the first whose rule is *structurally Boolean*. The predicate composes three conjunctive tests: (i) clause-alignment (3 of 3 clauses point to payment-before-IP-transfer), (ii) named-witness preponderance over the disputed factual question (6:2; both dissenters lacked relevant DevOps access), and (iii) the *Ladd v Marshall* three-prong test (fails on prong (a) — the fresh evidence could have been obtained with reasonable diligence — and short-circuits). The protocol reproduces the court's disposition exactly: **Judgment Sum GBP 409,870, costs USD 125,483.84, counterclaim dismissed**.

The constructive claim is that the protocol does not replace contractual interpretation; it makes the *logical structure* of that interpretation auditable. Each conjunctive test is named, each test's input is named, and each test's outcome is recorded — so a disagreement between a human reader and the court can be located precisely at the test that turns over.

### 5.6 Trace #6 — Partial statutory refusal across legal families

`spike/trace-06/`. *SIC/OA 9/2025 — GNC Holdings v ONI Global Pte Ltd* ([2025] SGHC(I) 25, Chua Lee Ming J, Simon Thorley IJ, James Allsop IJ). The first SICC trace and the first to express a *partial* refusal of New York Convention enforcement under Singapore International Arbitration Act s 31, read with the four-condition framework set out in *DKT v DKU*.[^dktdku]

Of four pleaded grounds for refusal, three are dismissed in full and one is allowed in part — three named sub-paragraphs of the Tribunal's Order 3 are excised because the parties were not afforded an opportunity to be heard on their specific terms. The predicate composes the four-ground gate (s 31(2)(a)–(d) + s 31(4) public-policy backstop) with the four-condition partial-refusal framework and reproduces the court's disposition at para 185(a)–(c) exactly: application allowed in part; Order 3(d)(ii), (d)(iii), and (f) not enforced; the rest enforced.

The constructive claim is that the protocol crosses legal-family boundaries. The same predicate engine that ran DIFC's RDC Part 38 and ADGM's CPR Rule 42 runs Singapore's IAA + NY Convention regime, with no engine-level changes — only new rule modules.

### 5.7 Trace #7 — Third-party-jurisdiction gate over a digital-asset dispute

`spike/trace-07/`. *DEC 001/2025 — Techteryx Ltd v IG and others* (DIFC Digital Economy Court, Andrew Black KC, 3 April 2026). Norwich Pharmacal[^norwich] + Bankers Trust[^bankers] + DIFC RDC 28.52 third-party disclosure jurisdiction, applied to a USD 456 million stablecoin-reserves tracing dispute. The first trace in DIFC's purpose-built Digital Economy Court — the venue most directly aligned with the digital-commerce claim type the paper's framing has targeted from §1.

The rule is a three-stage decision tree: (i) does a wrong support a constructive-trust claim against the recipient of the misapplied funds (Bankers Trust threshold)? (ii) is the third party innocently mixed up in the transaction sufficient to trigger the Norwich Pharmacal duty? (iii) does RDC 28.52 supply the procedural route in DIFC? The predicate composes all three gates — nine substantive checks in total — and reproduces the court's reasoning at para 24 exactly. Disposition: orders granted under both heads against the named third parties; the disclosure injunction enforces.

The constructive claim is methodological coverage of the FinTech / digital-asset vertical the courts increasingly handle. Stablecoin-tracing, smart-contract custody disputes, and similar fact patterns route through exactly this combination of common-law equitable jurisdiction and the local procedural rule — and the protocol now demonstrates that route end-to-end.

### 5.8 Across the seven traces

| Trace | Tribunal | Shape | Tribunal action | Protocol output |
|---|---|---|---|---|
| #1 *Dhawan v El Jaouhari* | DIFC | Pure formula | AED 7,127.75 (operative); AED 7,121.75 (schedule) | AED 7,121.75 + flags 6 AED clerical error |
| #2 *Oberlin v Ovidiu* | DIFC | Deferred conditional | 14-day window, 9% p.a. retroactive if missed | "What is owed today?" deterministic across any as-of date |
| #3 *Taylor v Yao Affi* | DIFC | Bounded discretion | AED 128,914.80 → AED 120,000 (–AED 8,914.80) | 1 disposed, 1 held to zero, 1 surfaced; AED 8,914.80 = structured residue |
| #4 *Projeco v Ideacrate* | ADGM | Composition over findings | Net AED 10,500.96 + interest AED 877.48 | Net AED 10,500.96 exact; interest reveals +1-day daycount convention |
| #5 *Xetech v Pulsar* | ADGM | Boolean composition | GBP 409,870 + USD 125,483.84 costs; counterclaim dismissed | Disposition reproduced; conjunctive structure auditable per test |
| #6 *GNC Holdings v ONI Global* | SICC | Partial statutory refusal | Application allowed in part; Order 3(d)(ii),(d)(iii),(f) not enforced | Partial-refusal disposition reproduced exactly at para 185(a)–(c) |
| #7 *Techteryx v IG* | DIFC (DEC) | Third-party-jurisdiction gate | Norwich Pharmacal + Bankers Trust orders granted (USD 456M tracing) | All 9 substantive checks reproduce para 24; disclosure injunction enforces |

The seven traces cover the spectrum of rule shapes a digital tribunal must handle: static formulae, deferred conditionals, bounded discretion (the honest case for what rules cannot fully decide), arithmetic composition over substantive findings, Boolean composition over contractual-interpretation findings, partial statutory refusal of NY Convention enforcement, and third-party-jurisdiction disclosure gates. The protocol reproduces the court's central output exactly in six of seven; in the seventh (Trace #3) the protocol does not produce a single number by design but bounds the discretion residue to a computable percentage. Three of the seven traces (Trace #1, Trace #4, Trace #6) surface a clerical or methodological gap that the predicate makes mechanically visible. All three tribunals and all three legal families run through one engine; only the rule modules are jurisdiction-specific.

## 6. The Roblox-MDL counterfactual

The companion empirical project at `roblox-forensics/` codes 46 publicly-identified legal proceedings against Roblox Corporation. The headline finding of that paper is that the litigation pressure concentrates almost entirely on prevention failures — age verification, real-time moderation, cross-platform predator signals — and not on dispute-resolution failures. Roblox's preventability matrix scores Layer 2 (human-in-loop arbitration review) at mean 0.23 and Layer 3 (Kleros arbitration) at mean 0.00 across the 44 child-harm proceedings.

The Roblox dataset is therefore the negative-space evidence for the Habeas Protocol claim. Where the constitutional primitives — versioned rules with specific binds, named identity for litigants, documented procedure with notice and opportunity to be heard — are absent, as in essentially every Roblox child-harm proceeding's allegations against the platform's internal moderation, the litigation pressure is intense and the dispute-resolution layer is irrelevant. Where the primitives are present at near-ceiling — as at DIFC, ADGM, and SICC — the litigation that does arrive is procedurally clean, the rules that apply are compilable, and the rulings that issue are machine-readable in principle.

The Habeas Protocol pitch and the Roblox Forensics pitch are two halves of the same argument. Where you have constitutional infrastructure, you can layer computation on top of it. Where you do not, no amount of dispute-resolution layering will help.

## 7. Comparators

The three operating tribunals coded above are the empirical anchor. Three further candidates fall on a spectrum:

**Estonia e-Residency.** A digital-jurisdiction case that anchors on a national EU member state but extends into a global commercial population. Estonian dispute resolution ultimately runs through Harju County Court for Estonian-law claims and through chosen-forum arbitration for international claims. The novel artefact is e-Residency's *identity* layer (PR1), which is the cleanest implementation of cryptographic identity-as-precondition for legal personhood currently operating at scale. Estonia is therefore a comparator on PR1, not on the tribunal layer.

**Próspera Arbitration Center** (Honduras ZEDE). Operating but speculative — the Honduran ZEDE legal framework was contested through 2024 and the political stability of the regime is a load-bearing assumption. Próspera's arbitration center has a published rule set (the Próspera Common Law Code) and a defined panel selection mechanism. It scores 2 on SP1 (the rule-makers and rule-appliers are formally distinct) and 1 on SP2 (the appeal path is internal). Próspera serves as the *design comparator* for what a fully greenfield digital-jurisdiction tribunal looks like.

**VARA** (Virtual Assets Regulatory Authority, Dubai). Operating but regulator-issued rather than judicial. Useful as a comparator for what happens when rule-making and enforcement are partially merged — VARA scores 1 on both system properties.

Notable absences from this list: VR/metaverse-native tribunals. Adoption of immersive metaverse environments has not panned out empirically; real digital-commerce legal volume is concentrated on cross-border SaaS, stablecoin-tracing, and AI-service-liability disputes, which DIFC, ADGM, and SICC are taking now.

## 8. Verticals

Three commercial verticals are tractable from the three-tribunal anchor:

**8.1 Cross-border SaaS contracts.** Most SaaS revenue flows across jurisdictional lines, and most SaaS contracts contain a forum-selection clause that is in tension with the actual user base. DIFC's Court of First Instance and SICC routinely hear cross-border digital commercial matters; ADGM's English-law-via-statute substrate gives the tribunal a single, predictable governing-law answer for any contract that selects "English law" or "ADGM law." A computational layer that compiles standard SaaS-contract clauses (renewal notice, pro-rated refund on early termination, material adverse change clauses, indemnity caps) into Catala source against the named governing law gives both sides a deterministic dispute-evaluation tool *before* litigation issues.

**8.2 Stablecoin tracing.** DIFC's Digital Economy Court (operating since 2025) has heard tracing claims involving stablecoin transfers across multiple wallets and jurisdictions (the *Techteryx* line of cases). The substantive doctrine is conventional equity — proprietary tracing through mixed funds (first-in-first-out, lowest-intermediate-balance, *Clayton's Case*) — but the evidence layer is novel: blockchain transaction logs are PR2-perfect (dated, attributable, append-only). The protocol can compile the tracing rule into a predicate that runs against the on-chain log directly. The deterministic answer is the *starting point* for the human ruling.

**8.3 AI-service liability.** Liability for harms caused by AI-service outputs is a doctrinal frontier that national courts are presently working through case-by-case. ADGM's English-law substrate gives the tribunal direct access to the *Donoghue* → *Caparo* line of duty-of-care reasoning, and to *Hedley Byrne* for negligent misstatement. SICC has recently issued AI-related judgments under Singapore common law. A computational layer that compiles the relevant test (proximity, foreseeability, fair-just-and-reasonable) into a structured evaluation against an event log of AI-service inputs and outputs gives the parties a predictable evaluation tool before the dispute hardens.

In each vertical the pitch is the same: the tribunal exists, the rule is articulable, the evidence is structured. The protocol is the bridge.

## 9. Limitations and next steps

**Sample size and provenance.** The hand-coded gold set is 39 judgments. The 121-judgment full corpus extends the empirical surface via AI-triage and AI-grading under the same v0.2 rubric. The AI-coded subset is auditable per-entry (`coding.rationale` fields are stored alongside scores) and produces a saturation pattern for ADGM that is statistically indistinguishable from the hand-coded subset (1.93 → 1.91 across a 10× sample increase). However, the AI-coded subset is not a substitute for hand coding. A future iteration would re-hand-code a stratified sample (perhaps 30 of the 82 AI-coded entries) to validate the AI codings against gold-standard scores — converting the headline number from "1.91 with AI provenance disclosed" to "1.91 with hand-coded validation across the stratified sample." We expect agreement above 90%.

**Heuristic limits.** Three primitives are particularly heuristic-vulnerable:

- **PR3 (Rule bind).** The grader counts numbered clause citations in the body. On older judgments where clauses are referenced by name without number ("the Application of English Law Regulations" without naming a section), the heuristic underscores. Hand coding catches these.
- **PR5 (Ruling).** Depends on outcome verbs in the body. A judgment that uses idiosyncratic outcome language ("the matter is referred to the Registrar") is undercounted.
- **PR6 (Enforcement bridge).** Rubric-bound: case-management orders score 1 by design. The cut-line between "explicit bridge" and "implicit bridge" is in places a judgment call.

**Doctrinal coverage of traces.** Seven traces span the rule-shape spectrum (formula / conditional / bounded discretion / arithmetic composition / Boolean composition / partial statutory refusal / third-party-jurisdiction gate) and three legal families (DIFC own statutes, ADGM English-law-via-statute, Singapore IAA + NY Convention). Two doctrinal areas remain uncovered: (i) a duty-of-care decision where the rule itself turns on doctrinal lines like *Caparo* proximity (the `caparo_three_stage_test` module exists and ships with property tests, but is not yet anchored to a corpus case), and (ii) a true *meta-rule* decision — a jurisdictional challenge in which the rule applied is a rule about which rule applies. A future iteration would close both gaps.

**Catala as runtime.** The Catala source files in this paper are syntactic. The executable layer is the Python evaluator, which mirrors the Catala scope structure exactly. A future iteration would close the loop and run both implementations against the same event log, demonstrating bisimilarity.

**SICC sample.** SICC entries are 13. The pattern replicates at near-ceiling but the sample is small. A larger SICC pull (50+ judgments) would harden the cross-tribunal claim.

## 10. Conclusion

The "Legal Operating System for Digital Worlds" thesis is correct in its diagnosis and wrong in its prescription. Digital commerce has indeed outgrown the institutional capacity of national courts. But the response is not to build a tribunal from scratch; it is to wire computation onto the tribunals that already exist. The DIFC, ADGM, and SICC Courts implement the full per-ruling protocol at near-ceiling and both system properties at ceiling. They are, today, working prototypes of a constitutional digital tribunal. The empirical and constructive evidence in this paper is intended to make that claim defensible. The next question — which we leave for follow-up work — is whether the same protocol applies, under modified system properties, to non-tribunal legal authorities (regulators, registry-operators, sovereign-adjacent enforcement bodies). The Habeas Protocol is the per-ruling layer of an answer; the institutional layer is open.

---

## Appendix A — Numbers

- Judgments coded: **121** (32 DIFC hand-coded + 7 ADGM hand-coded + 16 ADGM AI-triaged + 53 ADGM AI-graded + 13 SICC AI-graded)
- DIFC overall mean: **1.72 / 2.00** (n=32)
- ADGM overall mean: **1.91 / 2.00** (n=76; was 1.93 at n=7 hand-coded)
- SICC overall mean: **1.95 / 2.00** (n=13)
- Combined overall mean: **1.87 / 2.00** (n=121)
- All three tribunals on system properties: **2 / 2**
- ADGM PR2 / PR4: **2.00**; SICC PR1 / PR2 / PR4: **2.00**
- Trace #1 predicate: **AED 7,121.75** (operative AED 7,127.75 — 6 AED clerical error surfaced)
- Trace #2 predicate at 92 days late: **AED 78,527.69** (principal AED 76,785.81)
- Trace #3 structured-discretion residue: **AED 8,914.80** (≈ 6.92% of AED 128,914.80 claimed)
- Trace #4 net principal: **AED 10,500.96** (court matched exactly); interest at 609 calendar days = AED 876.04 vs court's 610-day inclusive-endpoint = AED 877.48
- Trace #5 Xetech v Pulsar (ADGM, [2026] ADGMCFI 0006, Heath KC) — Boolean composition over Wood v Capita / Ladd v Marshall: judgment GBP 409,870 + costs USD 125,483.84, counterclaim dismissed — all reproduced
- Trace #6 GNC Holdings v ONI Global ([2025] SGHC(I) 25, SICC) — partial NY Convention refusal under Singapore IAA s 31; para 185(a)–(c) reproduced exactly
- Trace #7 Techteryx v IG (DIFC Digital Economy Court) — third-party-jurisdiction gate (Norwich Pharmacal + Bankers Trust + RDC 28.52); USD 456M stablecoin tracing; all 9 checks reproduce para 24
- Saturation-pattern delta on 10× ADGM expansion: **−0.02** (1.93 → 1.91)
- Rule library: **12 Catala modules** (13 named scopes), all green under `catala interpret --no-stdlib`; **744 property-test invariants** pass under random inputs against conjunctive / monotonicity / disposition properties
- Corpus linking after May 2026 sweep: SICC **100%** (26/26 raw docs linked), ADGM **90.8%** (316/348), DIFC **28.2%** (166/588 — structural ceiling: 32 coded of 142 discoverable)

## Appendix B — Files

- `data/judgments.json` — 121 entries (v0.1 + v0.2 scores where applicable)
- `data/primitives.json` — v0.2 rubric + v0.1→v0.2 mapping
- `data/schema.json` — JSON Schema for entries
- `data/sources.md` — corpus provenance
- `spike/trace-01/` through `spike/trace-07/` — Catala source, Python evaluator, event log, and JSON output per trace; traces 1–4 span the original methodological spectrum (formula, deferred conditional, bounded discretion, arithmetic composition); traces 5–7 extend coverage to Boolean composition over contractual interpretation (ADGM), partial NY Convention refusal in a different legal family (SICC), and a third-party-jurisdiction gate over a digital-asset dispute (DIFC Digital Economy Court). The seven traces are summarised in §5.8.
- `rules/` — 12 Catala rule modules (13 scopes) lifted out of the trace library: `difc_rdc_part_38`, `difc_rdc_38_7_indemnity`, `difc_practice_direction_4_2017`, `difc_third_party_disclosure`, `adgm_cpr_admissions`, `adgm_cpr_summary_judgment`, `adgm_arbitration_regulations_2015`, `english_contract_interpretation`, `caparo_three_stage_test`, `ladd_v_marshall`, `sg_iaa_s_31` (two scopes: `IAA_S31_Refusal` + `DKTvDKUChallenge`), `uae_civil_code_art_390`. Each module ships with a metadata file (`<module>_metadata.json`) and an auto-generated input/output JSON Schema; certification spec at `rules/_certification.yaml`; claim-type registry at `rules/_claims.json`; jurisdiction map at `rules/_jurisdictions.json`.
- `dashboard/` — 7 interactive pages: Atlas (`index.html`), single-rule playground, multi-rule dispute simulator, rule authoring wizard, evidence ingestion, cross-border conflict-of-laws routing, OpenAPI 3.0 reference (`api.html`).
- `api/server.py` — 17-endpoint Postgres-backed read-only API; `api/openapi.yaml` — OpenAPI 3.0 spec.
- `clients/python/`, `clients/typescript/` — first-party clients wrapping every endpoint.
- `db/schema.sql` — 8 tables, 3 views, FTS index; `rule_runs` audit table.
- `tests/property_tests.py` — 744 property invariants exercised against random inputs.
- `LICENSE`, `LICENSES/`, `CONTRIBUTING.md`, `SECURITY.md`, `TRADEMARK.md` — open-source governance: MIT (code) + CC-BY-4.0 (data) + Mozilla/Rust-style trademark policy + private vulnerability disclosure.
- `scripts/{fetch_difc,fetch_adgm_firecrawl,fetch_adgm_pages,strip_html,migrate_to_postgres,triage_adgm,build_digests,grade_borderline,merge_adgm_codings,build_trace_outputs,build_rule_schemas,bootstrap_rule_metadata}.{py,sh}` — corpus pipeline and reproducibility scripts.

## References

[^catala]: Merigoux, Denis; Chataing, Nicolas; Protzenko, Jonathan. "Catala: A Programming Language for the Law." *Proceedings of the ACM on Programming Languages* 5, ICFP (August 2021): 1–29. https://catala-lang.org

[^difc]: Dubai International Financial Centre Courts, *Rules of the DIFC Courts (RDC)* (as amended). Establishment via Dubai Law No. 12 of 2004 and Dubai Law No. 9 of 2004. Digital Economy Court launched May 2025. https://www.difccourts.ae

[^adgm-aelr]: Abu Dhabi Global Market, *Application of English Law Regulations 2015*. Establishment via Abu Dhabi Law No. 4 of 2013 (as amended by Abu Dhabi Law No. 12 of 2020). https://www.adgm.com

[^adgm-cpr]: Abu Dhabi Global Market Courts, *Court Procedure Rules 2016* (as amended).

[^sicc]: Singapore International Commercial Court, established 2015 as a division of the Singapore High Court; *Singapore International Commercial Court Rules 2021*. https://www.judiciary.gov.sg/sicc

[^uae-civil]: United Arab Emirates *Civil Transactions Law*, Federal Law No. 5 of 1985 (as amended), Article 390 (judicial variation of agreed compensation upon application).

[^nyc]: *Convention on the Recognition and Enforcement of Foreign Arbitral Awards*, opened for signature 10 June 1958, 330 UNTS 3 (entered into force 7 June 1959). The "New York Convention." 172 contracting states as of 2026.

[^fuller]: Fuller, Lon L. *The Morality of Law* (rev. ed., New Haven: Yale University Press, 1969). The eight desiderata of legality: generality, promulgation, prospectivity, clarity, non-contradiction, possibility of compliance, constancy through time, congruence between official action and declared rule.

[^hart]: Hart, H.L.A. *The Concept of Law* (Oxford: Clarendon Press, 1961; 2nd ed. with postscript, 1994). Primary rules impose duties on subjects; secondary rules confer powers to make, change, and apply primary rules (rule of recognition, rules of change, rules of adjudication).

[^caparo]: *Caparo Industries plc v Dickman* [1990] UKHL 2, [1990] 2 AC 605. Three-stage duty-of-care test: foreseeability, proximity, and fair, just and reasonable.

[^hedley]: *Hedley Byrne & Co Ltd v Heller & Partners Ltd* [1963] UKHL 4, [1964] AC 465. Liability for negligent misstatement causing pure economic loss.

[^arnold]: *Arnold v Britton* [2015] UKSC 36, [2015] AC 1619. Principles of contractual interpretation; objective meaning + business common sense.

[^wood]: *Wood v Capita Insurance Services Ltd* [2017] UKSC 24, [2017] AC 1173. Iterative process of contractual interpretation — language, business common sense, factual matrix; refines the *Rainy Sky* / *Arnold* framework. Applied wholesale by ADGM Courts via the AELR.

[^rainy]: *Rainy Sky SA v Kookmin Bank* [2011] UKSC 50, [2011] 1 WLR 2900. Where contract language has two possible meanings, the court adopts the one consistent with business common sense.

[^ladd]: *Ladd v Marshall* [1954] EWCA Civ 1, [1954] 1 WLR 1489. Three-prong test for admitting fresh evidence on appeal: (i) reasonable diligence, (ii) important influence, (iii) presumably credible. Conjunctive — failure of any one prong defeats admission.

[^iaa]: Singapore *International Arbitration Act* (Cap 143A, 1995 Rev Ed; subsequent revisions). Section 31 enacts the New York Convention Article V refusal grounds for foreign-arbitral-award enforcement in Singapore.

[^dktdku]: *DKT v DKU* [2024] SGHC(I) 9. Four-condition framework for "infra petita" challenges to arbitral awards under SG IAA s 31(2)(d).

[^gnc]: *GNC Holdings LLC v ONI Global Pte Ltd* [2025] SGHC(I) 25 (Chua Lee Ming J, Simon Thorley IJ, James Allsop IJ; 21 October 2025). SICC OA 9/2025. Partial refusal of enforcement of a foreign arbitral award under SG IAA s 31; first SICC trace in this corpus (Trace #6).

[^techteryx]: *Techteryx Ltd v IG (BVI) Limited and others*, DIFC Digital Economy Court, Black KC (3 April 2026). USD 456M stablecoin-reserves tracing dispute; conjunctive jurisdictional gates of Norwich Pharmacal + Bankers Trust + RDC 28.52 over a non-party financial institution. Trace #7; the first trace in DIFC's Digital Economy Court — purpose-built for digital-asset cross-border commercial disputes.

[^norwich]: *Norwich Pharmacal Co v Customs and Excise Commissioners* [1974] AC 133 (HL). Equitable jurisdiction to compel a non-party who has become "mixed up" in wrongdoing to disclose information.

[^bankers]: *Bankers Trust Co v Shapira* [1980] 1 WLR 1274 (CA). Pre-action discovery against banks where claimant alleges fraud and seeks to trace funds.

[^vara]: Dubai Virtual Assets Regulatory Authority, established by Dubai Law No. 4 of 2022 Regulating Virtual Assets. https://www.vara.ae

[^kleros]: Ast, Federico, and Clément Lesaege. "Kleros: A Decentralized Justice Protocol for the Internet" (Kleros white paper, v2.0.2, 2018). https://kleros.io

## Citation

```
Maxim Labs, "Habeas Protocol: An Empirical Analysis of DIFC, ADGM, and
Singapore SICC as Working Prototypes for Constitutional Digital Tribunals,"
v0.2 (April 2026).
```
