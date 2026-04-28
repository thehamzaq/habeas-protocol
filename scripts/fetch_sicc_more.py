#!/usr/bin/env python3
"""Fetch additional SICC judgments from page 2 of the elitigation listing."""
import json
import os
import re
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(HERE + "/..")
HTML_DIR = ROOT + "/data/raw/sicc/html"
TXT_DIR = ROOT + "/data/raw/sicc/text"
FC_DIR = ROOT + "/data/raw/sicc/firecrawl"

FIRECRAWL_KEY = os.environ.get("FIRECRAWL_KEY") or sys.exit("set FIRECRAWL_KEY env var")


def fc(url, formats=None, wait=3500):
    formats = formats or ["markdown", "links", "html"]
    body = json.dumps({"url": url, "formats": formats, "waitFor": wait}).encode()
    req = urllib.request.Request(
        "https://api.firecrawl.dev/v1/scrape",
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {FIRECRAWL_KEY}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read())


def main():
    page2 = (
        "https://www.elitigation.sg/gd/Home/Index?Filter=SICC&"
        "YearOfDecision=All&SortBy=DateOfDecision&CurrentPage=2&"
        "SortAscending=False&PageSize=0&Verbose=False&"
        "SearchQueryTime=0&SearchTotalHits=0&SearchMode=True&SpanMultiplePages=False"
    )
    p = fc(page2)
    with open(f"{FC_DIR}/listing_p2.json", "w") as f:
        json.dump(p, f)
    links = p.get("data", {}).get("links", []) or []
    sicc = [l for l in links if "elitigation.sg/gd/sic/" in l
            and "#" not in l and "Index" not in l]
    sicc = list(dict.fromkeys(sicc))
    print(f"page2 SICC links: {len(sicc)}")
    for u in sicc[:15]:
        print("  ", u)

    chosen = []
    for u in sicc:
        if "SGCAI" in u:
            continue
        if any(f"_{y}_SGHCI_" in u or f"/{y}_SGHCI_" in u
               for y in ("2024", "2025", "2023")):
            chosen.append(u)
        if len(chosen) >= 5:
            break

    print(f"\nchosen {len(chosen)}: {chosen}\n")
    for url in chosen:
        slug = url.rstrip("/").split("/")[-1]
        html_path = f"{HTML_DIR}/{slug}.html"
        txt_path = f"{TXT_DIR}/{slug}.txt"
        if os.path.exists(txt_path) and os.path.getsize(txt_path) > 1000:
            print(f"  skip (already on disk) {slug}")
            continue
        try:
            pp = fc(url, formats=["html", "markdown"])
            with open(f"{FC_DIR}/case_{slug}.json", "w") as f:
                json.dump(pp, f)
            data = pp.get("data", {})
            with open(html_path, "w") as f:
                f.write(data.get("html", "") or "")
            md = data.get("markdown", "") or ""
            with open(txt_path, "w") as f:
                f.write(md)
            print(f"  pulled {slug}  ({len(md)} chars)")
            time.sleep(0.6)
        except Exception as e:
            print(f"  FAIL {slug}: {e}")


if __name__ == "__main__":
    main()
