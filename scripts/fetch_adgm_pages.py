#!/usr/bin/env python3
"""ADGM Courts judgment fetcher — plain HTTP, no API key.

`scripts/fetch_adgm.py` only fetches page 1 of the judgment listing,
relying on the manual observation that the listing is JS-paginated. That
turns out to be wrong: the ADGM site *does* honour `?page=N` server-side
and returns a fully rendered HTML page for each value of N. The earlier
Firecrawl-based variant (`scripts/fetch_adgm_firecrawl.py`) was therefore
spending credits on something plain `urllib` can do.

This script does the same job with no external API key:

  * fetches `?page=1` with a browser User-Agent,
  * reads `total-items` / `items-per-page` from the markup,
  * loops `?page=N` for N=2..total_pages,
  * regexes `assets.adgm.com/.../*.pdf/<hash>` URLs out of each page,
  * downloads anything not already on disk (idempotent),
  * runs pypdf text extraction (matching `fetch_adgm.py`).

Output paths match the existing scrapers so the migration script picks
up new files automatically:
  - data/raw/adgm/pdfs/<slug>.pdf
  - data/raw/adgm/text/<slug>.txt
  - data/raw/adgm/pages/_summary.json   (per-page stats, useful for diffs)
"""
from __future__ import annotations

import html
import json
import math
import os
import re
import sys
import time
import urllib.parse
import urllib.request

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
LISTING_URL = "https://www.adgm.com/adgm-courts/judgments"

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(HERE + "/..")
PDF_DIR = ROOT + "/data/raw/adgm/pdfs"
TXT_DIR = ROOT + "/data/raw/adgm/text"
PAGE_DIR = ROOT + "/data/raw/adgm/pages"

# pypdf may be installed at the user-site path used by the other scrapers
sys.path.insert(0, "/Users/hamzaqureshi/Library/Python/3.9/lib/python/site-packages")

ASSET_RE = re.compile(
    r"https://assets\.adgm\.com/download/assets/[^\"'\s<>)]+\.pdf/[a-f0-9]+",
    re.IGNORECASE,
)
TOTAL_RE = re.compile(r'total-items="(\d+)"')
PER_RE = re.compile(r'items-per-page="(\d+)"')

NON_JUDGMENT_SLUGS = {"ADGM_Brand_Book_2025"}


def http_get(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8", errors="replace")


def http_get_bytes(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def extract_pdf_urls(page_html: str) -> list[str]:
    return sorted({html.unescape(u) for u in ASSET_RE.findall(page_html)})


def extract_page_count(page_html: str) -> int | None:
    t = TOTAL_RE.search(page_html)
    p = PER_RE.search(page_html)
    if t and p and int(p.group(1)) > 0:
        return math.ceil(int(t.group(1)) / int(p.group(1)))
    return None


def case_slug(url: str) -> str:
    name = url.split("/assets/", 1)[1]
    name = urllib.parse.unquote(name).split("/")[0]
    name = name.replace(".pdf", "")
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name)
    return name[:120]


def extract_text(pdf_path: str) -> str:
    from pypdf import PdfReader
    reader = PdfReader(pdf_path)
    parts = []
    for page in reader.pages:
        try:
            parts.append(page.extract_text() or "")
        except Exception as e:
            parts.append(f"[page extraction error: {e}]")
    return "\n\n".join(parts)


def main() -> None:
    os.makedirs(PDF_DIR, exist_ok=True)
    os.makedirs(TXT_DIR, exist_ok=True)
    os.makedirs(PAGE_DIR, exist_ok=True)

    # Page 1 — also gives us the page count
    page1 = http_get(LISTING_URL + "?page=1")
    with open(f"{PAGE_DIR}/page_01.html", "w") as f:
        f.write(page1)
    total_pages = extract_page_count(page1) or 1
    urls_p1 = extract_pdf_urls(page1)
    all_urls: set[str] = set(urls_p1)
    page_results = [{"page": 1, "urls": len(urls_p1)}]
    print(f"page 1: {len(urls_p1)} PDF URLs (total pages reported: {total_pages})")

    for n in range(2, total_pages + 1):
        url = f"{LISTING_URL}?page={n}"
        try:
            page_html = http_get(url)
            with open(f"{PAGE_DIR}/page_{n:02d}.html", "w") as f:
                f.write(page_html)
            urls = extract_pdf_urls(page_html)
            new = [u for u in urls if u not in all_urls]
            all_urls.update(urls)
            page_results.append({"page": n, "urls": len(urls), "new": len(new)})
            print(f"page {n}: {len(urls)} PDF URLs ({len(new)} new)")
            time.sleep(0.4)  # gentle on the origin
        except Exception as e:
            page_results.append({"page": n, "error": repr(e)})
            print(f"page {n} FAILED: {e}")

    print(f"\nUnique PDF URLs across {total_pages} pages: {len(all_urls)}")

    new_slugs: list[str] = []
    skipped: list[str] = []
    skipped_non_judgment: list[str] = []
    failed: list[dict] = []

    for url in sorted(all_urls):
        slug = case_slug(url)
        if slug in NON_JUDGMENT_SLUGS:
            skipped_non_judgment.append(slug)
            continue
        pdf_dest = f"{PDF_DIR}/{slug}.pdf"
        txt_dest = f"{TXT_DIR}/{slug}.txt"
        if os.path.exists(pdf_dest) and os.path.getsize(pdf_dest) > 0:
            skipped.append(slug)
            # ensure text exists even if PDF was downloaded by an earlier run
            if not os.path.exists(txt_dest):
                try:
                    text = extract_text(pdf_dest)
                    with open(txt_dest, "w") as f:
                        f.write(text)
                    print(f"  re-extracted text for existing pdf {slug}")
                except Exception as e:
                    failed.append({"slug": slug, "stage": "extract", "err": str(e)})
            continue
        try:
            data = http_get_bytes(url)
            with open(pdf_dest, "wb") as f:
                f.write(data)
            time.sleep(0.4)
            try:
                text = extract_text(pdf_dest)
                with open(txt_dest, "w") as f:
                    f.write(text)
            except Exception as e:
                failed.append({"slug": slug, "stage": "extract", "err": str(e)})
            new_slugs.append(slug)
            print(f"  + {slug}")
        except Exception as e:
            failed.append({"slug": slug, "stage": "download", "err": str(e), "url": url})
            print(f"  ! {slug} FAILED: {e}")

    summary = {
        "total_pages": total_pages,
        "page_results": page_results,
        "total_pdf_urls_unique": len(all_urls),
        "new_pdfs_added": new_slugs,
        "already_present": skipped,
        "skipped_non_judgment": skipped_non_judgment,
        "failed": failed,
    }
    with open(f"{PAGE_DIR}/_summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    print()
    print(f"Added {len(new_slugs)} new PDFs, skipped {len(skipped)} already on disk, {len(failed)} failed.")
    print(f"Summary: {PAGE_DIR}/_summary.json")
    if new_slugs:
        print("\nNext step: re-run scripts/migrate_to_postgres.py to load new files into Postgres.")


if __name__ == "__main__":
    main()
