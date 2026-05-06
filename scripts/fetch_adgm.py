#!/usr/bin/env python3
"""ADGM Courts judgment fetcher.

ADGM Courts publishes judgments at https://www.adgm.com/adgm-courts/judgments.
Listing is JS-paginated; the first page is server-rendered with ~10-15 PDFs.
This script extracts those URLs, downloads the PDFs, and extracts text.

For deeper pulls beyond page 1, a headless browser pass is required —
deferred to Phase 2.
"""
import html
import os
import re
import sys
import time
import urllib.parse
import urllib.request

UA = "Mozilla/5.0 (compatible; habeas-spike/0.1)"
INDEX_URL = "https://www.adgm.com/adgm-courts/judgments"
HERE = os.path.dirname(os.path.abspath(__file__))
PDF_DIR = HERE + "/../data/raw/adgm/pdfs"
TXT_DIR = HERE + "/../data/raw/adgm/text"

# Note: site-packages is on sys.path by default; no manual insertion needed.


def fetch(url, dest):
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        return False
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = r.read()
    with open(dest, "wb") as f:
        f.write(data)
    time.sleep(0.6)
    return True


def extract_pdf_urls(index_html):
    pattern = re.compile(r'href="(https://assets\.adgm\.com/download/assets/[^"]+\.pdf/[a-f0-9]+)"')
    raw = pattern.findall(index_html)
    return sorted(set(html.unescape(u) for u in raw))


def case_slug(url):
    """Extract a filesystem-safe slug from the asset URL."""
    name = url.split("/assets/", 1)[1]
    name = urllib.parse.unquote(name).split("/")[0]
    name = name.replace(".pdf", "")
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name)
    return name[:120]


def extract_text(pdf_path):
    from pypdf import PdfReader
    reader = PdfReader(pdf_path)
    parts = []
    for page in reader.pages:
        try:
            parts.append(page.extract_text() or "")
        except Exception as e:
            parts.append(f"[page extraction error: {e}]")
    return "\n\n".join(parts)


def main():
    os.makedirs(PDF_DIR, exist_ok=True)
    os.makedirs(TXT_DIR, exist_ok=True)

    index_path = f"{PDF_DIR}/_index.html"
    fetch(INDEX_URL, index_path)
    with open(index_path) as f:
        index_html = f.read()

    pdf_urls = extract_pdf_urls(index_html)
    print(f"found {len(pdf_urls)} PDF URLs on landing page")

    for url in pdf_urls:
        slug = case_slug(url)
        pdf_dest = f"{PDF_DIR}/{slug}.pdf"
        try:
            downloaded = fetch(url, pdf_dest)
            print(f"  {'pulled' if downloaded else 'cached'} {slug[:60]}")
        except Exception as e:
            print(f"  FAIL {slug[:60]}: {e}")
            continue

    print("\nExtracting text...")
    for fn in sorted(os.listdir(PDF_DIR)):
        if not fn.endswith(".pdf"):
            continue
        pdf_path = f"{PDF_DIR}/{fn}"
        txt_path = f"{TXT_DIR}/{fn[:-4]}.txt"
        if os.path.exists(txt_path) and os.path.getsize(txt_path) > 100:
            continue
        try:
            text = extract_text(pdf_path)
            with open(txt_path, "w") as f:
                f.write(text)
            print(f"  text {fn[:-4][:60]:60s} {len(text):6d} chars")
        except Exception as e:
            print(f"  FAIL text {fn[:-4][:60]}: {e}")


if __name__ == "__main__":
    main()
