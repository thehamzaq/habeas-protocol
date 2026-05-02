# `paper/` — arXiv submission source

Single-file LaTeX paper with TikZ-native figures (no external images).

## Build

```bash
make            # two-pass pdflatex -> main.pdf
make view       # open the PDF
make clean      # remove .aux/.log/etc, keep PDF
make cleanall   # remove everything including PDF
```

Live rebuild while editing (requires `latexmk`):

```bash
make watch
```

## Compile requirements

- TeX Live 2022 or later (or MacTeX). The paper uses standard CTAN packages: `lmodern`, `microtype`, `geometry`, `enumitem`, `xcolor`, `titlesec`, `booktabs`, `mdframed`, `tikz`, `pgfplots` (≥ 1.18), `hyperref`. All ship with a full TeX Live install.
- No external image files — all figures are TikZ / pgfplots.

## arXiv submission

```bash
make arxiv      # produces habeas-protocol-arxiv.tar.gz
```

Upload the tarball to arXiv at <https://arxiv.org/submit>. Suggested primary category: **cs.CY** (Computers and Society). Secondary: **cs.PL** (Programming Languages).

The paper is self-contained: bibliography is inline (`thebibliography`), so no `.bib` file or `bibtex`/`biber` pass is needed.

## Companion artefacts

The paper references but does not include:

- the public dashboard at <https://thehamzaq.github.io/habeas-protocol/dashboard/>
- the source repository at <https://github.com/thehamzaq/habeas-protocol>
- the markdown working paper at `../paper.md` (longer-form, with rule-by-rule reasoning)

## Versioning

Each arXiv revision should bump the date on the title page (`\date{...}`) and add a one-line note to a `% revision history` block at the top of `main.tex`.
