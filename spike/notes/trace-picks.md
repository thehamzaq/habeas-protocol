# Phase 0 — Trace Candidates

Three judgments picked from the 24-judgment sample. They form a progression:
**pure arithmetic → temporal logic → bounded discretion.** That sequence is a
better demonstration of the protocol's range than three different subject
domains, because each pick is intentionally *more* judgment-laden than the
last — letting us show where executable rules land cleanly, and where they
gracefully degrade into a structured human decision.

## Trace #1 — Pure arithmetic
**CFI 058/2024 Dhawan v El Jaouhari** (31 Mar 2026, Stewart KC)
- **Rule**: costs = (hours × rate) + court_fee
- **Inputs**: 3 hours, AED 2,000/hr, AED 1,121.75 filing fee
- **Output**: AED 7,121.75 (judgment rounds/states AED 7,127.75 — minor reconciliation point worth flagging)
- **Why this trace**: zero discretion. The court literally awards "as claimed."
  This is the easiest possible compile target and proves the predicate path end-to-end.

## Trace #2 — Temporal logic
**ARB 008/2026 Oberlin v Ovidiu** (26 Mar 2026, Al Sawalehi)
- **Rule**: if !paid(amount, by=order_date+14d) then interest_accrues(rate=9%, from=order_date)
- **Inputs**: AED 76,785.81 due, order issued 26 Mar 2026, 14-day window, 9% p.a. per Practice Direction No. 4 of 2017
- **Output**: pay full amount within 14d, else interest from order date
- **Why this trace**: deadline + consequence is the canonical "smart contract"
  shape. Encodable as a state machine over an event log; the predicate is
  unambiguous; demonstrates the protocol's *temporal* primitive.

## Trace #3 — Bounded discretion
**ENF 271/2025 Taylor v Yao Affi** (1 Apr 2026, Cooke)
- **Rule**: on indemnity-basis costs, court reviews itemised bill for *reasonableness only* (proportionality not in play); may reduce specific lines
- **Inputs**: claimed AED 128,914.80; court found senior-associate hours excessive; reduced to AED 120,000
- **Output**: AED 120,000 (specific delta not formula-derived)
- **Why this trace**: this is the **honest** case. Indemnity-basis review has
  a *bounded* but non-formula judgment step. The protocol can encode
  everything *up to* the reduction (which lines were reviewed, what rule
  governs, what the standard is); the actual delta is a structured human
  call. Showing this is the strongest move — it lets us say what executable
  rules *can't* do, not just what they can.

## What we're explicitly not picking (and why)

- **CFI 110/2025 Karthi Keyan v Ahmed** — refusal to vary trial mode from
  in-person to remote. Reasoning is policy-driven (witness credibility,
  Middle East security context). Not formula-shaped; would force an
  unconvincing compile.
- **CFI 011/2025 Five Holding v Patel** — permission-to-appeal application,
  44-paragraph reasons, jurisdictional argument under Article 14. Too much
  interpretive reasoning to fit a Phase 0 trace cleanly.
- **CFI 067/2025 Coinmena v Foloosi** (digital-payments dispute) — initially
  attractive as a contract-formation candidate, but a single judgment isn't
  available with a clean offer/acceptance/consideration structure in the
  sample. Good candidate for Phase 1 expansion.

## Coverage check against the Habeas Protocol primitives

| Primitive | Trace #1 | Trace #2 | Trace #3 |
|---|---|---|---|
| 1. Versioned signed rules | RDC 38.7-38.23 cited | RDC 38.40 + PD No. 4/2017 | indemnity-basis rule |
| 2. Executable predicates | ✓ pure formula | ✓ deadline + interest | partial — discretion bounded |
| 3. Due-process trace | written submissions on both sides | ✓ statement of costs filed | ✓ submissions + reply |
| 4. Separation of powers | RDC = legislature; judge = adjudicator | same | same |
| 5. Precedent chain | n/a | PD No. 4/2017 governs | indemnity-basis line of authority |
| 6. External tribunal | DIFC Courts itself enforceable abroad via NY Convention | same | same |
| 7. Preventive minimums | n/a (not safety domain) | n/a | n/a |

Three traces cover primitives 1–6. Primitive 7 (preventive minimums) is
inherently a different domain (child safety, real-time detection) — best
demonstrated by a parallel Roblox-MDL-style proof, which the existing
roblox-forensics repo already provides. The Habeas demo therefore *cites*
roblox-forensics for primitive 7 rather than re-deriving it.
