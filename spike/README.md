# Habeas Protocol — Phase 0 Spike

Half-day validation spike for the Habeas Protocol demo build plan.
Tested whether the DIFC Courts corpus is scrapable, whether judgments
contain crisply codable rules, and whether at least one rule can be
expressed as an executable predicate matching the human ruling.

## Result

**Go.** See `notes/go-nogo.md`.

One trace working end-to-end (`trace-01/`); it incidentally surfaced a
6 AED arithmetic discrepancy in the operative court order versus the
Schedule of Reasons.

## Layout

```
spike/
├── README.md                # this file
├── scrape.py                # listing-page scraper
├── strip.py                 # HTML → text
├── judgments/               # 24 raw judgment HTML files + 2 listing pages
├── text/                    # 24 stripped plaintext judgments
├── trace-01/                # CFI 058/2024 Dhawan — arithmetic trace
│   ├── rule.catala_en       # Catala source (syntactic only — runtime deferred)
│   ├── events.json          # case facts as event log
│   └── evaluate.py          # Python predicate evaluator
└── notes/
    ├── trace-picks.md       # 3 trace candidates + reasoning
    └── go-nogo.md           # Phase 0 memo
```

## Reproduce

```
cd spike
python3 scrape.py 2          # pulls listing pages 1-2 + 24 judgments
python3 strip.py             # HTML → text in spike/text/
python3 trace-01/evaluate.py # runs the predicate, reports match + flag
```
