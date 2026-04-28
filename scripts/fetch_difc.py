#!/usr/bin/env python3
"""Phase 0 spike scraper. Pull listing pages, extract judgment URLs, download HTML."""
import os
import re
import sys
import time
import urllib.request
from html.parser import HTMLParser

UA = "Mozilla/5.0 (compatible; habeas-spike/0.1)"
BASE = "https://www.difccourts.ae"
LISTING = BASE + "/rules-decisions/judgments-orders?ccm_paging_p={p}&ccm_order_by=ak_date&ccm_order_by_direction=desc"
OUT = os.path.dirname(os.path.abspath(__file__)) + "/../data/raw/judgments"

DIVISIONS = (
    "court-first-instance", "court-appeal", "arbitration", "small-claims-tribunal",
    "technology-and-construction-division", "digital-economy-court", "enforcement",
    "joint-judicial-committee", "court-administrative-orders",
)

def fetch(url, dest):
    if os.path.exists(dest):
        return
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = r.read()
    with open(dest, "wb") as f:
        f.write(data)
    time.sleep(0.5)

def extract_judgment_urls(listing_html):
    """Pull only links that match a real judgment slug (not division index pages)."""
    urls = set()
    pattern = re.compile(
        r'href="(https://www\.difccourts\.ae/rules-decisions/judgments-orders/(?:'
        + "|".join(DIVISIONS)
        + r')/[a-z0-9][^"]+)"'
    )
    for m in pattern.finditer(listing_html):
        urls.add(m.group(1))
    return sorted(urls)

def slug(url):
    return url.rsplit("/", 1)[-1]

def main():
    os.makedirs(OUT, exist_ok=True)
    pages = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    all_urls = []
    for p in range(1, pages + 1):
        listing_path = f"{OUT}/_listing_p{p}.html"
        fetch(LISTING.format(p=p), listing_path)
        with open(listing_path) as f:
            html = f.read()
        urls = extract_judgment_urls(html)
        print(f"page {p}: {len(urls)} judgments")
        all_urls.extend(urls)

    # Dedupe, preserve order
    seen = set()
    deduped = []
    for u in all_urls:
        if u not in seen:
            seen.add(u)
            deduped.append(u)
    print(f"total unique: {len(deduped)}")

    for u in deduped:
        dest = f"{OUT}/{slug(u)}.html"
        try:
            fetch(u, dest)
            print(f"  saved {slug(u)[:60]}")
        except Exception as e:
            print(f"  FAIL {slug(u)[:60]}: {e}")

if __name__ == "__main__":
    main()
