# Habeas Protocol -- arXiv paper build
# Single-file LaTeX, all figures TikZ-native, no external images.

TEX      := pdflatex
TEXFLAGS := -interaction=nonstopmode -halt-on-error -file-line-error
SRC      := main.tex
PDF      := main.pdf
AUX_EXTS := aux log out toc lof lot bbl blg synctex.gz fls fdb_latexmk

.PHONY: all clean cleanall watch arxiv view

all: $(PDF)

# Two-pass build is enough since the bibliography is inline (thebibliography env).
$(PDF): $(SRC)
	$(TEX) $(TEXFLAGS) $(SRC)
	$(TEX) $(TEXFLAGS) $(SRC)

# Live rebuild on save (requires latexmk).
watch:
	latexmk -pdf -pvc -interaction=nonstopmode $(SRC)

# Open the produced PDF in the default viewer (macOS / Linux).
view: $(PDF)
	@if command -v open >/dev/null 2>&1; then open $(PDF); \
	elif command -v xdg-open >/dev/null 2>&1; then xdg-open $(PDF); \
	else echo "Open $(PDF) manually."; fi

# Clean intermediate artefacts but keep the PDF.
clean:
	@for ext in $(AUX_EXTS); do rm -f main.$$ext; done

# Clean everything including the PDF.
cleanall: clean
	@rm -f $(PDF)

# Bundle a tarball ready for arXiv upload.
# arXiv accepts a single .tex (compiles on their TeX Live) or a tarball with
# all sources. We ship a tarball so they can rebuild from source.
arxiv: $(PDF)
	@mkdir -p _arxiv
	@cp $(SRC) _arxiv/
	@cd _arxiv && tar czf ../habeas-protocol-arxiv.tar.gz $(SRC)
	@rm -rf _arxiv
	@echo "Bundle ready: habeas-protocol-arxiv.tar.gz"
