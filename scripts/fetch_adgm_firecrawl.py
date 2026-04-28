#!/usr/bin/env python3
"""ADGM Courts judgment fetcher via Firecrawl.

The listing at https://www.adgm.com/adgm-courts/judgments is JS-paginated in
the rendered DOM, but the server actually honours `?page=N` and returns a
fully server-rendered page-N HTML. We use Firecrawl /v1/scrape to fetch
each page (raw scrape responses saved as JSON), regex out the
assets.adgm.com PDF asset URLs, then download any PDFs not already on
disk and run pypdf text extraction (matching scripts/fetch_adgm.py).

Total pages is read from `total-items` / `items-per-page` in the markup.
"""
import html
import json
import math
import os
import re
import sys
import time
import urllib.parse
import urllib.request

UA = "Mozilla/5.0 (compatible; habeas-spike/0.2)"
FIRECRAWL_KEY = os.environ.get("FIRECRAWL_KEY") or sys.exit("set FIRECRAWL_KEY env var")
FIRECRAWL_URL = "https://api.firecrawl.dev/v1/scrape"
LISTING_URL = "https://www.adgm.com/adgm-courts/judgments"

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(HERE + "/..")
PDF_DIR = ROOT + "/data/raw/adgm/pdfs"
TXT_DIR = ROOT + "/data/raw/adgm/text"
FC_DIR = ROOT + "/data/raw/adgm/firecrawl"

sys.path.insert(0, "/Users/hamzaqureshi/Library/Python/3.9/lib/python/site-packages")

ASSET_PATTERN = re.compile(
    r"https://assets\.adgm\.com/download/assets/[^\"'\s<>)]+\.pdf/[a-f0-9]+",
    re.IGNORECASE,
)
TOTAL_ITEMS_RE = re.compile(r'total-items="(\d+)"')
ITEMS_PER_RE = re.compile(r'items-per-page="(\d+)"')

# Ignore non-judgment marketing PDFs that appear in site footer/header.
NON_JUDGMENT_SLUGS = {"ADGM_Brand_Book_2025"}


def firecrawl_scrape(url):
    body = {
        "url": url,
        "formats": ["markdown", "links", "html"],
        "waitFor": 2500,
    }
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        FIRECRAWL_URL,
        data=data,
        method="POST",
        headers={
            "Authorization": f"Bearer {FIRECRAWL_KEY}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read())


def html_unescape_ref(s):
    """Some HTML returned encodes '+' as '&#x2B;'. Normalise."""
    return html.unescape(s)


def extract_pdf_urls(payload):
    found = set()
    blob = json.dumps(payload)
    for u in ASSET_PATTERN.findall(blob):
        found.add(html_unescape_ref(u))
    # Also check decoded HTML field (json.dumps keeps escapes intact, but be safe).
    data = payload.get("data") or {}
    if isinstance(data, dict):
        for field in ("html", "markdown"):
            text = data.get(field) or ""
            if not isinstance(text, str):
                continue
            text = html_unescape_ref(text)
            for u in ASSET_PATTERN.findall(text):
                found.add(u)
    return sorted(found)


def page_count(payload):
    data = payload.get("data") or {}
    h = data.get("html", "") if isinstance(data, dict) else ""
    if not isinstance(h, str):
        return None
    t = TOTAL_ITEMS_RE.search(h)
    p = ITEMS_PER_RE.search(h)
    if t and p and int(p.group(1)) > 0:
        return math.ceil(int(t.group(1)) / int(p.group(1)))
    return None


def case_slug(url):
    name = url.split("/assets/", 1)[1]
    name = urllib.parse.unquote(name).split("/")[0]
    name = name.replace(".pdf", "")
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name)
    return name[:120]


def download(url, dest):
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        return False
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120) as r:
        data = r.read()
    with open(dest, "wb") as f:
        f.write(data)
    time.sleep(0.5)
    return True


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


def save_payload(name, payload):
    path = f"{FC_DIR}/{name}.json"
    with open(path, "w") as f:
        json.dump(payload, f, indent=2)
    return path


def scrape_all_pages():
    os.makedirs(FC_DIR, exist_ok=True)
    all_urls = set()
    page_results = []

    # Page 1
    try:
        payload = firecrawl_scrape(LISTING_URL + "?page=1")
        save_payload("page_01", payload)
        urls = extract_pdf_urls(payload)
        total_pages = page_count(payload) or 15
        page_results.append({"page": 1, "url_count": len(urls), "total_pages": total_pages, "error": None})
        all_urls.update(urls)
        print(f"page 1: {len(urls)} PDF URLs (total pages reported: {total_pages})")
    except Exception as e:
        page_results.append({"page": 1, "url_count": 0, "total_pages": None, "error": repr(e)})
        print(f"page 1 FAILED: {e}")
        return [], page_results

    for n in range(2, total_pages + 1):
        url = f"{LISTING_URL}?page={n}"
        try:
            payload = firecrawl_scrape(url)
            save_payload(f"page_{n:02d}", payload)
            urls = extract_pdf_urls(payload)
            new = [u for u in urls if u not in all_urls]
            page_results.append({"page": n, "url_count": len(urls), "new_count": len(new), "error": None})
            all_urls.update(urls)
            print(f"page {n}: {len(urls)} PDF URLs ({len(new)} new)")
            time.sleep(0.4)  # gentle on Firecrawl
        except Exception as e:
            page_results.append({"page": n, "url_count": 0, "new_count": 0, "error": repr(e)})
            print(f"page {n} FAILED: {e}")

    return sorted(all_urls), page_results


def main():
    os.makedirs(PDF_DIR, exist_ok=True)
    os.makedirs(TXT_DIR, exist_ok=True)

    pdf_urls, page_results = scrape_all_pages()
    print(f"\nTotal unique PDF URLs across all pages: {len(pdf_urls)}")

    new_slugs = []
    skipped_slugs = []
    skipped_non_judgment = []
    failed = []

    for url in pdf_urls:
        slug = case_slug(url)
        if slug in NON_JUDGMENT_SLUGS:
            skipped_non_judgment.append(slug)
            continue
        pdf_dest = f"{PDF_DIR}/{slug}.pdf"
        if os.path.exists(pdf_dest) and os.path.getsize(pdf_dest) > 0:
            skipped_slugs.append(slug)
            continue
        try:
            download(url, pdf_dest)
            new_slugs.append(slug)
            print(f"  pulled {slug[:80]}")
        except Exception as e:
            failed.append({"slug": slug, "stage": "download", "error": repr(e)})
            print(f"  FAIL download {slug[:80]}: {e}")

    print("\nExtracting text for new PDFs...")
    for slug in new_slugs:
        pdf_path = f"{PDF_DIR}/{slug}.pdf"
        txt_path = f"{TXT_DIR}/{slug}.txt"
        if os.path.exists(txt_path) and os.path.getsize(txt_path) > 100:
            continue
        try:
            text = extract_text(pdf_path)
            with open(txt_path, "w") as f:
                f.write(text)
            print(f"  text {slug[:60]:60s} {len(text):6d} chars")
        except Exception as e:
            failed.append({"slug": slug, "stage": "text", "error": repr(e)})
            print(f"  FAIL text {slug[:60]}: {e}")

    summary = {
        "page_results": page_results,
        "total_pdf_urls_unique": len(pdf_urls),
        "new_pdfs_added": new_slugs,
        "already_present": skipped_slugs,
        "skipped_non_judgment": skipped_non_judgment,
        "failed": failed,
    }
    with open(f"{FC_DIR}/_summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    print("\n=== summary ===")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
