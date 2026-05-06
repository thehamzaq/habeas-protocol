"""
Idempotently insert the reliance disclaimer banner and footer note into
every dashboard/*.html page.

- Top banner: standard yellow warning on most pages; strong (red) on the
  playground because it actually executes rule predicates.
- Bottom footer note: uniform across all pages.

Re-runnable: skips a file if the banner sentinel is already present.
"""

from pathlib import Path

DASH = Path(__file__).resolve().parent.parent / "dashboard"

BANNER_STD = (
    '<div class="hp-disclaimer" role="note">\n'
    '  <strong>Research artifact</strong> — not legal advice, not court-endorsed.\n'
    '  Source judgments remain the property of the issuing court.\n'
    '  See <a href="../data/tos_audit.md">data/tos_audit.md</a> and\n'
    '  <a href="../LICENSE">LICENSE</a>.\n'
    '</div>\n'
)
BANNER_STRONG = (
    '<div class="hp-disclaimer hp-disclaimer-strong" role="note">\n'
    '  <strong>Research artifact — not legal advice, not court-endorsed.</strong>\n'
    '  Outputs of this playground are reproductions of rule structure for academic study only.\n'
    '  Do not rely on them as a legal determination. Source judgments remain the property of the\n'
    '  issuing court (DIFC / ADGM / Singapore Courts) — see\n'
    '  <a href="../data/tos_audit.md">data/tos_audit.md</a>.\n'
    '</div>\n'
)
FOOTER = (
    '<div class="hp-footer-note">\n'
    '  Habeas Protocol v0.2 — research artifact. Code: MIT. Data: structured-metadata licence (see\n'
    '  <a href="../LICENSE">LICENSE</a>). Outputs computed against rule modules pinned in\n'
    '  <code>rules/&lt;module&gt;_source.yaml</code>; not a legal determination. Takedown:\n'
    '  see <code>SECURITY.md</code>.\n'
    '</div>\n'
)

SENTINEL = "hp-disclaimer"
FOOTER_SENTINEL = "hp-footer-note"

STRONG_PAGES = {"playground.html", "simulator.html", "authoring.html"}


def patch(path: Path) -> None:
    text = path.read_text()
    changed = False
    if SENTINEL not in text:
        banner = BANNER_STRONG if path.name in STRONG_PAGES else BANNER_STD
        text = text.replace("<body>\n", "<body>\n" + banner, 1)
        changed = True
    if FOOTER_SENTINEL not in text:
        text = text.replace("</body>\n", FOOTER + "</body>\n", 1)
        changed = True
    if changed:
        path.write_text(text)
        print(f"  patched {path.name}")
    else:
        print(f"  skip    {path.name}  (already has banner + footer)")


def main():
    print(f"dashboard dir: {DASH}")
    for p in sorted(DASH.glob("*.html")):
        patch(p)


if __name__ == "__main__":
    main()
