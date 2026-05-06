# Falsification analysis — v0.2 rubric

## Per-ruling primitive means

| Group / class                       |    n |  PR1 |  PR2 |  PR3 |  PR4 |  PR5 |  PR6 | Mean |
|--------------------------------------|-----:|-----:|-----:|-----:|-----:|-----:|-----:|-----:|
| DIFC Courts                         |   32 | 1.81 | 1.78 | 1.69 | 1.75 | 1.88 | 1.44 | 1.72 |
| ADGM Courts                         |   76 | 1.97 | 2.00 | 1.93 | 2.00 | 1.96 | 1.62 | 1.91 |
| Singapore International Commercial Court |   80 | 1.82 | 2.00 | 1.96 | 1.55 | 1.96 | 1.81 | 1.85 |
| (separator)                         |    0 |    — |    — |    — |    — |    — |    — |    — |
| A. Sealed arbitral awards           |    6 | 0.00 | 0.00 | 1.00 | 1.00 | 0.00 | 2.00 | 0.67 |
| B. On-chain / DAO tribunals         |    6 | 0.33 | 1.00 | 0.00 | 1.00 | 1.00 | 0.00 | 0.56 |
| C. Regulator enforcement            |    6 | 1.83 | 1.83 | 2.00 | 1.83 | 2.00 | 2.00 | 1.92 |
| D. Platform adjudicators            |    6 | 1.17 | 0.50 | 1.17 | 0.67 | 1.17 | 0.17 | 0.81 |
| E. Specialised panels (positive ctl) |    6 | 1.83 | 1.83 | 2.00 | 2.00 | 1.83 | 1.17 | 1.78 |

## System properties (per-class mean)

| Class                                | SP1  | SP2  |
|--------------------------------------|------|------|
| A. Sealed arbitral awards            | 2.00 | 1.00 |
| B. On-chain / DAO tribunals          | 0.33 | 0.00 |
| C. Regulator enforcement             | 1.00 | 1.17 |
| D. Platform adjudicators             | 0.33 | 0.17 |
| E. Specialised panels (positive ctl) | 2.00 | 1.17 |

## Diagnostic checks

- Operating courts (DIFC+ADGM+SICC) per-ruling mean: 1.83
  - vs A. Sealed arbitral awards            gap = +1.16  → RUBRIC SEPARATES
  - vs B. On-chain / DAO tribunals          gap = +1.27  → RUBRIC SEPARATES
  - vs C. Regulator enforcement             gap = -0.09  → rubric does not separate
  - vs D. Platform adjudicators             gap = +1.02  → RUBRIC SEPARATES
  - vs E. Specialised panels (positive ctl) gap = +0.05  → rubric does not separate

Expected pattern:
  A: gap ≥ 0.6   (sealed → low PR1/PR2/PR5)
  B: gap ≥ 1.0   (on-chain → low across the board)
  C: gap ≤ 0.2   (regulator → high per-ruling; SP1 fails)
  D: gap mixed   (Meta OB high; consumer programmes low)
  E: gap ≤ 0.2   (positive control — rubric should NOT mark down)
