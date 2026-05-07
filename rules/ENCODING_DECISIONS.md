# Rule encoding decisions

This file records, per rule module, the interpretive choices the
encoder made and the reasons for them. Going-forward, every new rule
gets a paragraph in this file *before* the Catala predicate is written
(see `PREREGISTRATION.md` §4).

The 12 retrospectives below are written from the encoding logs and
the rule-module source files; they document choices that were made
during the original encoding and that a future reader (or
practitioner reviewer) must be able to inspect before treating the
encoding as authoritative.

All 12 modules currently ship at state `draft` per
`rules/_certification.yaml`; the `lawyer_of_record` field is empty
for all 12. Practitioner review is open work.

---

## difc_rdc_part_38 (DIFC RDC Part 38 — standard-basis costs)

**Source pinned:** DIFC RDC Part 38 (the costs-assessment regime), as
in force in 2024. URL + SHA in `difc_rdc_part_38_source.yaml`.

**Interpretive choices:**
- The predicate computes a pure `(hours × hourly_rate) +
  disbursements` sum applied to the claimant's costs schedule.
  Trace #1 (Dhawan v El Jaouhari) exercises this against a
  specific case where the schedule arithmetic sums to AED
  7,121.75.
- "Reasonably incurred" is treated as an externally-determined input,
  not a computed property. The predicate sums and applies the
  schedule; it does not assess reasonableness.
- The 80% practice convention (the court awards roughly 80% of
  claimed reasonable costs absent specific objection) is *not*
  encoded in this module; it lives in `difc_practice_direction_4_2017`
  alongside the 14-day deadline + 9% interest structure that recurs
  across DIFC arbitration costs orders.

**Test scenarios:** baseline assessment summing a hours-rate-fee
schedule.

**Practitioner review:** open. Reviewers should confirm that
"reasonably incurred" is never a computed property in DIFC standard-
basis assessment in practice.

---

## difc_rdc_38_19_indemnity (DIFC RDC 38.17 + 38.19 — indemnity-basis costs)

**Source pinned:** DIFC RDC 38.17 (indemnity basis defined) and 38.19
(application). Pinned in `difc_rdc_38_19_indemnity_source.yaml`.

**Interpretive choices:**
- Per Cooke J. in *Taylor v Yao Affi* (ENF 271/2025), indemnity basis
  *strips proportionality* and leaves only reasonableness. The
  predicate accordingly disposes objections via four buckets (no-named-
  element / held-to-zero / deterministic-reduction / requires-human-
  judgment) and surfaces the residue as the irreducible
  human-judgment region.
- "Reasonableness" is a black-box input: the predicate does not
  compute reasonableness; it composes the objections-bucket logic
  around it.

**Test scenarios:** trace #3 (real case) + synthetic counter-branches.

**Practitioner review:** open. Specifically: is the four-bucket
classification an accurate description of indemnity-basis review in
DIFC practice, or is there a fifth class (e.g. "settlement-driven
adjustment") that should be modelled?

---

## difc_practice_direction_4_2017 (DIFC PD 4/2017 — Interest on Judgments)

**Source pinned:** DIFC Practice Direction No. 4 of 2017. URL + SHA
in `difc_practice_direction_4_2017_source.yaml`.

**Interpretive choices:**
- The 14-day window suppresses interest entirely; missing the window
  activates retroactive accrual at 9% from the date of the order, not
  from the deadline. This is the structural asymmetry the predicate
  captures.
- The 80% practice convention (the court awards roughly 80% of
  claimed reasonable costs absent specific objection) is encoded as
  a parameterised `discount_rate` so the predicate can be tested
  under alternative rates if a future practice direction modifies it.
  The 80% recurs verbatim across the adjacent DIFC arbitration costs
  orders coded in the corpus.
- Pre-judgment interest convention (calendar daycount) is encoded as
  the default; trace #4's daycount convention divergence (court used
  inclusive endpoint = 610 days, predicate used 609) is recorded as a
  predicate scope limitation, not as a court error
  (`spike/trace-04/discrepancy.json`).

**Test scenarios:** five payment-timing scenarios (on-time, at-deadline,
1-day-late, 61-days-late, 92-days-late); all five reproduce the
implicit schedule.

**Practitioner review:** open. Specifically: is the 9% rate stable
across DIFC arbitration costs orders, or does it vary by Practice
Direction edition?

---

## difc_third_party_disclosure (Norwich Pharmacal + Bankers Trust + RDC 28.52)

**Source pinned:** *Norwich Pharmacal Co v Customs and Excise
Commissioners* [1974] AC 133 (HL); *Bankers Trust Co v Shapira*
[1980] 1 WLR 1274 (CA); DIFC RDC 28.52. The doctrines are
common-law; drift = higher-court overrule. Manual drift check.

**Interpretive choices:**
- Three conjunctive jurisdictional gates: (i) constructive-trust
  threshold (Bankers Trust), (ii) innocent-mixed-up-party gate
  (Norwich Pharmacal), (iii) procedural route under RDC 28.52. The
  predicate composes all three; failure at any gate denies the
  disclosure jurisdiction.
- The "innocent" requirement is treated as a tribunal finding, not a
  computed property.

**Test scenarios:** trace #7 (Techteryx v IG) + synthetic single-gate-
fails counter-branches.

**Practitioner review:** open. The Bankers Trust pre-action discovery
threshold and the Norwich Pharmacal "mixed up" requirement have
evolved since their original formulations; a DIFC equity practitioner
should verify the gate structure is current.

---

## adgm_cpr_admissions (ADGM Court Procedure Rules 2016 — admissions and set-off)

**Source pinned:** ADGM CPR 2016 Rule 42 (admissions). PDF + binary
SHA pinned in `adgm_cpr_admissions_source.yaml`.

**Interpretive choices:**
- The current `AdmissionsAndSetOff` scope encodes the **set-off
  arithmetic only**: liquidated damages + counterclaim → net
  principal, where each input is a tribunal finding.
- Set-off is computed against named counterclaim items only; the
  predicate does not infer additional set-off heads.
- Rule 42(4) withdrawal-of-admission is *not* yet encoded as a
  separate gate. Trace #4 (Projeco v Ideacrate) supplies the
  withdrawal-refused outcome as an upstream tribunal input. A
  future revision should add a `WithdrawalGate` scope encoding the
  Rule 42(4) "such terms as it thinks just" test.

**Test scenarios:** trace #4 (Projeco v Ideacrate) set-off
arithmetic.

**Practitioner review:** open. Specifically: confirm the
withdrawal-of-admission gate belongs in this module or in a
separate `adgm_cpr_admissions_withdrawal` module.

---

## adgm_cpr_summary_judgment (ADGM CPR Rule 68 — summary judgment)

**Source pinned:** ADGM CPR 2016 Rule 68 (summary judgment).

**Interpretive choices:**
- Two-limb conjunctive test: no real prospect of success + no other
  compelling reason for trial. Both limbs must be satisfied.
- Each limb is a tribunal finding, not a computed property; the
  predicate composes them.

**Test scenarios:** synthetic single-limb-fails counter-branches.

**Practitioner review:** open.

---

## adgm_arbitration_regulations_2015 (ADGM Arbitration Regulations 2015 — recognition + adjournment)

**Source pinned:** ADGM Arbitration Regulations 2015. URL + SHA
in `adgm_arbitration_regulations_2015_source.yaml`.

**Interpretive choices:**
- Recognition and enforcement of foreign arbitral awards under the
  ADGM regime parallels the NY Convention Article V grounds. The
  predicate reuses the SG IAA s 31 enumerated-grounds structure where
  the operative grounds match.
- The adjournment power in s 62(2) is encoded as a separate scope
  (`ADGM_S62_2_Adjournment`) with the discretionary triggers
  enumerated.

**Test scenarios:** synthetic counter-branches per ground.

**Practitioner review:** open. ADGM arbitration practice has been
relatively young; an ADGM-admitted practitioner should validate
whether the ground structure tracks the actual ADGM CFI line of
authority.

---

## english_contract_interpretation (Wood v Capita / Rainy Sky / Arnold v Britton)

**Source pinned:** *Wood v Capita Insurance Services Ltd* [2017]
UKSC 24; *Rainy Sky SA v Kookmin Bank* [2011] UKSC 50; *Arnold v
Britton* [2015] UKSC 36. Manual drift check.

**Interpretive choices:**
- The unitary contractual-interpretation test is encoded as a
  black-box: the predicate takes the court's contractual construction
  as an input, not a computed property. The predicate's role is to
  audit the *structure* of the construction (clause-alignment count,
  business-common-sense check) rather than to substitute for it.
- Trace #5 (Xetech v Pulsar) stipulates the construction; the
  predicate audits its conjunctive-test structure.

**Test scenarios:** trace #5 + synthetic branches.

**Practitioner review:** open. The Wood/Rainy/Arnold line is itself
under continued refinement (e.g. by *Sara & Hossein* [2022]); an
English contracts practitioner should verify the encoding still
tracks the current unitary test.

---

## ladd_v_marshall (Ladd v Marshall — fresh evidence on appeal)

**Source pinned:** *Ladd v Marshall* [1954] EWCA Civ 1. Manual drift
check (the doctrine has been re-affirmed in modern English appellate
practice).

**Interpretive choices:**
- Three-prong conjunctive test: (i) reasonable diligence,
  (ii) important influence, (iii) presumably credible. Failure of any
  one prong defeats admission; the predicate short-circuits.

**Test scenarios:** trace #5 admissibility check + synthetic
single-prong-fails branches.

**Practitioner review:** open.

---

## sg_iaa_s_31 (Singapore IAA s 31 — NY Convention Article V refusal grounds)

**Source pinned:** Singapore International Arbitration Act 1994
(2020 Rev Ed), s 31. URL + SHA in `sg_iaa_s_31_source.yaml`.

**Interpretive choices:**
- Four scopes encode the s 31 structure:
  - `IAA_S31_Refusal` (the main enumerated-grounds gate)
  - `DKTvDKUChallenge` (the four-condition framework for "infra
    petita" challenges from *DKT v DKU* [2025] SGCA 23, [2025] 1 SLR 806)
  - `IAA_S31_5_Adjournment` (the adjournment power under
    s 31(5))
  - `IAA_S31_2_c_InfraPetita` (sub-paragraph excision under partial
    refusal)
- Trace #6 (GNC Holdings v ONI Global) is the canonical partial-
  refusal case; the predicate reproduces the disposition at
  para 185(a)–(c) exactly.

**Test scenarios:** trace #6 + synthetic single-ground-allowed,
multi-ground-refused branches.

**Practitioner review:** open. *DKT v DKU* [2025] SGCA 23 is recent and
the four-condition framework as restated by the Court of Appeal may
evolve in subsequent jurisprudence; a Singapore-admitted arbitration
practitioner should verify the current encoding.

---

## caparo_three_stage_test (Caparo v Dickman — duty of care)

**Source pinned:** *Caparo Industries plc v Dickman* [1990] UKHL 2,
[1990] 2 AC 605. Manual drift check.

**Interpretive choices:**
- Three-stage test: foreseeability + proximity + fair-just-and-
  reasonable. All three are tribunal findings; the predicate
  composes them on the *novel-duty* path.
- *Robinson v Chief Constable of West Yorkshire* [2018] UKSC 4
  narrowing IS implemented as a guarded short-circuit in the
  predicate: an `is_established_category` input gates an
  `EstablishedCategory_DutyByPrecedent` path that bypasses the
  three-stage test entirely. On that path, `n_stages_satisfied`
  reports `-1` as a sentinel so downstream consumers cannot
  misread it as "passed N of 3 stages." Tests cover both
  established-category and novel-duty paths plus stage-fall-
  through.

**Test scenarios:** established-category short-circuit; novel-duty
all three stages met; novel-duty fails at stages 1 / 2 / 3.

**Practitioner review:** open. Specifically: confirm the
`is_established_category` input is the right level of abstraction
(an *English-law-via-ADGM* practitioner would know whether
ADGM courts have an internal list of established categories
distinct from the English line).

---

## uae_civil_code_art_390 (UAE Civil Transactions Law Art 390 — agreed-compensation variation)

**Source pinned:** UAE Federal Law No. 5 of 1985, Article 390
(judicial variation of agreed compensation). MoJ index page pinned
(the official Arabic text is the authoritative source; the English
translation is a working translation). URL + SHA in
`uae_civil_code_art_390_source.yaml`.

**Interpretive choices:**
- Article 390 lets the court vary an agreed-compensation clause
  (liquidated damages) on application of either party. The predicate
  composes the cap structure (`min(daily_rate * days, X% of
  contract_value)`) and the variation gate.
- Where the agreed compensation is itself capped at a percentage of
  contract value, the predicate enforces the cap before computing
  the variation.

**Test scenarios:** trace #4 (Projeco v Ideacrate, where the 10% cap
binds) + synthetic uncapped + synthetic court-varies counter-
branches.

**Practitioner review:** open. UAE civil-law practice diverges from
common-law liquidated-damages doctrine in important respects; a
UAE-admitted civil practitioner should verify the variation gate
matches Article 390 application in modern UAE federal courts.

---

## Going-forward template (per `PREREGISTRATION.md` §4)

For each *new* rule:

```markdown
## <module_name> (<short doctrinal label>)

**Source pinned:** <full citation>. URL: <pinned URL>.
**Pre-encoding date:** <YYYY-MM-DD, before the Catala source is written>

**Source-text excerpt:** (verbatim copy of the operative provision)

**Interpretive choices:**
- <each choice + rationale, before any test data is consulted>

**Intended test scenarios:**
- <each input vector + expected disposition, written before the
  predicate>

**Encoded:** (after Catala source is committed; this section is
edited *only* in the encoding commit, not later)

**Test results:** (after `clerk test --no-stdlib` runs green)

**Practitioner review:** open / submitted / reviewed / certified.
```
