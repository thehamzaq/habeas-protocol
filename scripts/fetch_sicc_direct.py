"""
Direct (no-Firecrawl) SICC judgment fetcher for elitigation.sg.

Walks the SICC listing pages, extracts case URLs, downloads each
judgment HTML, and strips to plain text. Output mirrors what the
existing Firecrawl-based fetcher produces, so triage_sicc.py picks
it up unchanged.

Output:
  data/raw/sicc/html/<slug>.html
  data/raw/sicc/text/<slug>.txt

Idempotent — already-cached files are skipped.

Usage:
  python3 scripts/fetch_sicc_direct.py [--max-pages N] [--target-n N]
"""

import argparse
import html as html_module
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
HTML_DIR = ROOT / "data" / "raw" / "sicc" / "html"
TXT_DIR = ROOT / "data" / "raw" / "sicc" / "text"

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36")

LISTING_BASE = (
    "https://www.elitigation.sg/gd/Home/Index"
    "?Filter=SICC&YearOfDecision=All&SortBy=DateOfDecision"
    "&CurrentPage={page}&SortAscending=False&PageSize=0"
    "&Verbose=False&SearchQueryTime=0&SearchTotalHits=0"
    "&SearchMode=True&SpanMultiplePages=False"
)

# Each /gd/sic/<slug> is a SICC judgment page. elitigation uses single
# quotes for href in the listing, double in the case body — match both.
CASE_URL_RE = re.compile(r'href=[\'"](/gd/sic/[^\'"#?]+)[\'"]', re.IGNORECASE)
NEUTRAL_CITE_RE = re.compile(
    r"\[(20\d{2})\]\s+SGHC\(I\)\s+(\d+)", re.IGNORECASE)


def fetch(url: str, timeout: int = 30) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA,
                                                "Accept": "text/html"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def list_page(page: int):
    """Return list of /gd/sic/<slug> case URLs from one listing page."""
    url = LISTING_BASE.format(page=page)
    try:
        body = fetch(url).decode("utf-8", errors="replace")
    except urllib.error.URLError as e:
        print(f"  page {page}: ERR {e}")
        return []
    paths = list(dict.fromkeys(CASE_URL_RE.findall(body)))
    return [f"https://www.elitigation.sg{p}" for p in paths]


def slug_for(case_url: str) -> str:
    """Convert /gd/sic/2025_SGHCI_25 → '2025_SGHCI_25'."""
    return urllib.parse.urlparse(case_url).path.rstrip("/").split("/")[-1]


def strip_html(html: str) -> str:
    """Light HTML→text conversion — mirrors what the Firecrawl markdown
    output looks like for the existing 13 cached files."""
    # remove scripts and styles
    html = re.sub(r"<script[^>]*>.*?</script>", " ", html,
                  flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<style[^>]*>.*?</style>", " ", html,
                  flags=re.DOTALL | re.IGNORECASE)
    # turn block tags into newlines
    html = re.sub(r"</(?:p|div|h\d|li|tr|br)\s*>", "\n", html, flags=re.IGNORECASE)
    html = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
    # strip remaining tags
    text = re.sub(r"<[^>]+>", "", html)
    # decode entities
    text = html_module.unescape(text)
    # collapse whitespace, preserve paragraph breaks
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def fetch_case(case_url: str) -> bool:
    """Download one judgment. Return True if newly fetched."""
    slug = slug_for(case_url)
    html_path = HTML_DIR / f"{slug}.html"
    txt_path = TXT_DIR / f"{slug}.txt"
    if html_path.exists() and txt_path.exists() and txt_path.stat().st_size > 1000:
        return False
    try:
        body = fetch(case_url).decode("utf-8", errors="replace")
    except urllib.error.URLError as e:
        print(f"  FAIL {slug}: {e}")
        return False
    if "[" not in body and "SGHC" not in body:
        print(f"  THIN {slug}: page returned no judgment content")
        return False

    html_path.write_text(body)
    text = strip_html(body)
    txt_path.write_text(text)
    print(f"  pulled {slug}  ({len(text):>6} chars)")
    return True


def already_have_count() -> int:
    if not HTML_DIR.exists():
        return 0
    return sum(1 for f in HTML_DIR.iterdir() if f.suffix == ".html")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-pages", type=int, default=20,
                    help="walk listing pages 1..N (default 20)")
    ap.add_argument("--target-n", type=int, default=75,
                    help="stop once this many SICC HTML files are on disk")
    ap.add_argument("--delay", type=float, default=0.6,
                    help="seconds between page fetches (be polite)")
    args = ap.parse_args()

    HTML_DIR.mkdir(parents=True, exist_ok=True)
    TXT_DIR.mkdir(parents=True, exist_ok=True)

    have = already_have_count()
    print(f"have {have} HTML files; target {args.target_n}")

    seen = set()
    new = 0
    for page in range(1, args.max_pages + 1):
        if already_have_count() >= args.target_n:
            print(f"reached target n={args.target_n}; stopping")
            break
        urls = list_page(page)
        if not urls:
            print(f"  page {page}: empty listing, stopping")
            break
        urls = [u for u in urls if u not in seen]
        seen.update(urls)
        print(f"page {page}: {len(urls)} case URLs")
        for u in urls:
            if already_have_count() >= args.target_n:
                break
            if fetch_case(u):
                new += 1
                time.sleep(args.delay)
        time.sleep(args.delay)

    final = already_have_count()
    print(f"\ndone. {new} newly fetched. total HTML files: {final}")
    if final < args.target_n:
        print(f"WARN: did not reach target n={args.target_n}. "
              f"Try --max-pages with a higher value.")


if __name__ == "__main__":
    main()
