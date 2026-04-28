#!/usr/bin/env python3
"""Singapore International Commercial Court (SICC) judgment fetcher.

Fetches the SICC judgment listing via Firecrawl, extracts judgment URLs and
metadata, downloads judgment HTML pages, then extracts plain text. Mirrors
the structure of fetch_adgm_firecrawl.py but adapted for the
elitigation.sg / judiciary.gov.sg layout.

SICC judgments are surfaced at:
  https://www.judiciary.gov.sg/judgments/sicc-judgments
which is a paginated listing that links into elitigation.sg case pages.
"""
import html as html_module
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

UA = "Mozilla/5.0 (compatible; habeas-spike/0.2)"
FIRECRAWL_KEY = os.environ.get("FIRECRAWL_KEY") or sys.exit("set FIRECRAWL_KEY env var")
FIRECRAWL_URL = "https://api.firecrawl.dev/v1/scrape"
LISTING_URL = "https://www.judiciary.gov.sg/singapore-international-commercial-court/hearings-judgments/judgments"

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(HERE + "/..")
HTML_DIR = ROOT + "/data/raw/sicc/html"
TXT_DIR = ROOT + "/data/raw/sicc/text"
FC_DIR = ROOT + "/data/raw/sicc/firecrawl"


def firecrawl_scrape(url, formats=None, wait_for=2500):
    formats = formats or ["markdown", "links", "html"]
    body = {"url": url, "formats": formats, "waitFor": wait_for}
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


def save_payload(name, payload):
    os.makedirs(FC_DIR, exist_ok=True)
    path = f"{FC_DIR}/{name}.json"
    with open(path, "w") as f:
        json.dump(payload, f, indent=2)
    return path


# Pattern for SICC neutral citations: [YYYY] SGHC(I) NN  or  [YYYY] SGHCR NN  or  [YYYY] SGCA NN
NEUTRAL_CITE_RE = re.compile(r"\[(20\d{2})\]\s+SGHC\(I\)\s+(\d+)", re.IGNORECASE)
# elitigation.sg case detail URLs
ELIT_CASE_RE = re.compile(
    r"https?://www\.elitigation\.sg/gd/sic/(?:20\d{2})_(?:SGHCI|SGCAI)_\d+",
    re.IGNORECASE,
)


def extract_links(payload):
    """Pull elitigation.sg URLs and any neutral citations out of the payload."""
    blob = json.dumps(payload)
    blob = html_module.unescape(blob)
    links = set()
    for m in ELIT_CASE_RE.findall(blob):
        # strip trailing punctuation
        u = m.rstrip(".,);")
        links.add(u)
    cites = set(f"[{y}] SGHC(I) {n}" for y, n in NEUTRAL_CITE_RE.findall(blob))
    data = payload.get("data") or {}
    if isinstance(data, dict):
        for L in data.get("links", []) or []:
            if not isinstance(L, str):
                continue
            if "elitigation.sg/gd/sic/" in L and "#" not in L and "Index" not in L:
                links.add(L.split("?")[0].rstrip(".,);"))
    return sorted(links), sorted(cites)


def slug_for_case(url, citation=None):
    if citation:
        s = citation.replace("[", "").replace("]", "").replace("(", "").replace(")", "")
        s = re.sub(r"\s+", "_", s.strip())
        return s
    name = url.rstrip("/").split("/")[-1]
    name = urllib.parse.unquote(name)
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name)
    return name[:120]


def main():
    os.makedirs(HTML_DIR, exist_ok=True)
    os.makedirs(TXT_DIR, exist_ok=True)
    os.makedirs(FC_DIR, exist_ok=True)

    print(f"Scraping listing: {LISTING_URL}")
    try:
        payload = firecrawl_scrape(LISTING_URL)
        save_payload("listing_p1", payload)
    except Exception as e:
        print(f"FAIL listing: {e}")
        return

    links, cites = extract_links(payload)
    print(f"  found {len(links)} elitigation links, {len(cites)} SGHC(I) citations on listing page")

    # The elitigation listing is paginated; we already get the most recent
    # ~10 cases on the first listing fetch. Try one more direct elitigation
    # listing fetch for safety.
    try:
        p = firecrawl_scrape("https://www.elitigation.sg/gd/Home/Index?filter=SICC")
        save_payload("listing_elit_p1", p)
        l2, c2 = extract_links(p)
        new = [x for x in l2 if x not in links]
        print(f"  elit page1: +{len(new)} new links")
        links.extend(new)
        for c in c2:
            if c not in cites:
                cites.append(c)
    except Exception as e:
        print(f"  elit page1 FAIL: {e}")

    # Dedupe
    links = list(dict.fromkeys(links))
    cites = list(dict.fromkeys(cites))

    # If we still have very few elitigation links, fall back to scraping by citation:
    # the elitigation site canonical URL pattern is
    # https://www.elitigation.sg/gd/sicc/<year>_SGHC(I)_<n>/
    # but actual format uses no parentheses and is
    # https://www.elitigation.sg/gd/s/[YEAR]_SGHCI_<n> (varies). We will rely
    # on Firecrawl's listing extraction primarily and hand-curate fallback.

    print(f"\nTotal {len(links)} unique elitigation links queued.")

    # Prefer 2024-2026 SGHCI cases (skip Court of Appeal SGCAI to keep
    # apples-to-apples first-instance comparison with DIFC/ADGM CFI).
    def keep(u):
        if "SGCAI" in u:
            return False
        for y in ("2026", "2025", "2024", "2023"):
            if f"/{y}_SGHCI_" in u or f"_{y}_SGHCI_" in u:
                return True
        return False
    preferred = [u for u in links if keep(u)]
    target = preferred[:12] if preferred else links[:12]

    saved = []
    failed = []
    for url in target:
        slug = slug_for_case(url)
        html_path = f"{HTML_DIR}/{slug}.html"
        if os.path.exists(html_path) and os.path.getsize(html_path) > 1000:
            saved.append(slug)
            continue
        try:
            p = firecrawl_scrape(url, formats=["html", "markdown"], wait_for=3500)
            save_payload(f"case_{slug}", p)
            data = p.get("data") or {}
            html_text = data.get("html") or ""
            md_text = data.get("markdown") or ""
            with open(html_path, "w") as f:
                f.write(html_text)
            # Use markdown as text source — cleaner than stripping HTML
            txt_path = f"{TXT_DIR}/{slug}.txt"
            with open(txt_path, "w") as f:
                f.write(md_text or html_module.unescape(re.sub(r"<[^>]+>", " ", html_text)))
            saved.append(slug)
            print(f"  pulled {slug[:80]}  ({len(md_text)} md chars)")
            time.sleep(0.5)
        except Exception as e:
            failed.append({"url": url, "error": repr(e)})
            print(f"  FAIL {url}: {e}")

    summary = {
        "listing_links_found": len(links),
        "saved": saved,
        "failed": failed,
        "citations_seen": cites,
    }
    with open(f"{FC_DIR}/_summary.json", "w") as f:
        json.dump(summary, f, indent=2)
    print("\n=== summary ===")
    print(json.dumps(summary, indent=2)[:2000])


if __name__ == "__main__":
    main()
