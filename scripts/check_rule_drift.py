"""
Check whether the official source of each rule module has drifted from
the version pinned in <module>_source.yaml.

For each rule with drift_check.method == 'http_get':
  - Fetch the URL.
  - Canonicalise (strip HTML, collapse whitespace, lowercase).
  - sha256.
  - Compare against the pinned retrieved_sha256.

Modes:
  --bootstrap   populate retrieved_sha256 fields that are currently null.
  --check       (default) compare current hash to pinned hash. Non-zero
                exit if any drift detected; 0 if all match (or all are
                manual-review modules).
  --soft        like --check but never returns non-zero; logs only.

For drift_check.method == 'manual' (case-law doctrines): print a reminder
that human review is required and the URL to inspect.

The canonicalisation deliberately drops markup, scripts, styles, and
whitespace because the official source pages are HTML wrappers around
the actual rule text — a cosmetic change to navigation should NOT count
as drift, but a substantive amendment to the rule text should.

Usage:
    python3 scripts/check_rule_drift.py            # --check
    python3 scripts/check_rule_drift.py --bootstrap
    python3 scripts/check_rule_drift.py --soft     # CI-friendly
"""

import argparse
import hashlib
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path


HERE = Path(__file__).resolve().parent.parent
RULES = HERE / "rules"

UA = "Mozilla/5.0 (compatible; HabeasProtocolDriftCheck/0.2; +contact via SECURITY.md)"
TIMEOUT = 30


# --- minimal YAML reader/writer (no external dependency) ------------------
# The source.yaml files are deliberately written in a flat, predictable
# subset of YAML so we can avoid pulling in PyYAML.

def parse_simple_yaml(text):
    """Parse the constrained YAML that bootstrap_rule_sources.py writes.

    Supports: top-level scalars; one level of nesting (two-space indent);
    block scalar with `|` for the notes field. Returns a nested dict.
    """
    out = {}
    cur_top = None
    in_block = None
    block_buf = []
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if in_block is not None:
            if line.startswith("  ") or line.startswith("\t"):
                block_buf.append(line.lstrip())
                continue
            else:
                _, key = in_block
                cur_top[key] = "\n".join(block_buf).strip()
                in_block = None
                block_buf = []
        if line.startswith("  "):
            # nested
            assert cur_top is not None
            k, _, v = line.lstrip().partition(":")
            v = v.strip()
            if v.endswith(":") or v == "":
                # nested-deeper not supported; treat as null
                cur_top[k] = None
            elif v == "|":
                in_block = (cur_top, k)
                block_buf = []
            else:
                cur_top[k] = strip_yaml_value(v)
        else:
            k, _, v = line.partition(":")
            v = v.strip()
            if v == "" or v.endswith(":"):
                out[k] = {}
                cur_top = out[k]
            elif v == "|":
                out[k] = ""
                in_block = (out, k)
                block_buf = []
            else:
                out[k] = strip_yaml_value(v)
                cur_top = out[k] if isinstance(out[k], dict) else None
    if in_block is not None:
        cur_top_final, key = in_block
        cur_top_final[key] = "\n".join(block_buf).strip()
    return out


def strip_yaml_value(v):
    # Strip inline comments. For a quoted string, find the closing quote and
    # discard everything after it; otherwise split on `\s+#`.
    if v and v[0] in ('"', "'"):
        q = v[0]
        end = v.find(q, 1)
        if end != -1:
            v = v[: end + 1]
    else:
        v = re.split(r"\s+#", v, maxsplit=1)[0].strip()
    if v == "null" or v == "~" or v == "":
        return None
    if v == "true":
        return True
    if v == "false":
        return False
    if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
        return v[1:-1]
    return v


def write_sha256(path, sha):
    """Replace the `retrieved_sha256: null` line with the computed value."""
    text = path.read_text()
    new = re.sub(
        r"(retrieved_sha256:\s*)(null|\"[a-f0-9]+\")",
        rf'\g<1>"{sha}"',
        text,
        count=1,
    )
    if new == text:
        raise RuntimeError(f"failed to update retrieved_sha256 in {path}")
    path.write_text(new)


# --- fetch + canonicalise -----------------------------------------------

def fetch(url):
    """Returns (bytes, content_type)."""
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        ct = resp.headers.get("Content-Type", "").lower()
        return resp.read(), ct


def canonicalise(html: str) -> str:
    text = re.sub(r"<script[^>]*>.*?</script>", " ", html,
                  flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style[^>]*>.*?</style>", " ", text,
                  flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&nbsp;", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text)
    return text.strip().lower()


def sha256_of(s) -> str:
    if isinstance(s, str):
        s = s.encode("utf-8")
    return hashlib.sha256(s).hexdigest()


def hash_content(body: bytes, content_type: str, url: str) -> str:
    """Hash the official source.

    For HTML: strip markup, collapse whitespace, lowercase, then sha256.
    For PDF / other binary: sha256 the bytes directly.
    """
    is_pdf = (
        "pdf" in content_type
        or url.lower().endswith(".pdf")
        or body[:4] == b"%PDF"
    )
    if is_pdf:
        return sha256_of(body)
    text = body.decode("utf-8", errors="replace")
    return sha256_of(canonicalise(text))


# --- main checker --------------------------------------------------------

def check_one(yaml_path, mode):
    src = parse_simple_yaml(yaml_path.read_text())
    name = src.get("module", yaml_path.stem.removesuffix("_source"))
    drift = src.get("drift_check", {}) or {}
    method = drift.get("method")

    if method == "manual":
        url = drift.get("url") or src.get("source_authority", {}).get("url")
        print(f"  MANUAL  {name:<40}  doctrine — review at {url}")
        return "manual"

    if method != "http_get":
        print(f"  SKIP    {name:<40}  drift_check.method = {method!r}")
        return "skip"

    url = drift.get("url") or src.get("source_authority", {}).get("url")
    if not url:
        print(f"  ERROR   {name:<40}  no URL")
        return "error"

    try:
        body, content_type = fetch(url)
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        print(f"  NETERR  {name:<40}  {type(e).__name__}: {e}")
        return "neterr"

    sha = hash_content(body, content_type, url)
    pinned = src.get("source_authority", {}).get("retrieved_sha256")

    if mode == "bootstrap":
        if pinned in (None, ""):
            write_sha256(yaml_path, sha)
            print(f"  PIN     {name:<40}  {sha[:16]}…  (was null)")
            return "bootstrap"
        else:
            print(f"  KEEP    {name:<40}  already pinned to {pinned[:16]}…")
            return "keep"

    if pinned in (None, ""):
        print(f"  UNPINNED{name:<40}  no retrieved_sha256 — run --bootstrap")
        return "unpinned"
    if pinned == sha:
        print(f"  OK      {name:<40}  {sha[:16]}…")
        return "ok"
    print(f"  DRIFT   {name:<40}  pinned {pinned[:16]}… now {sha[:16]}…")
    return "drift"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bootstrap", action="store_true",
                    help="populate retrieved_sha256 where currently null")
    ap.add_argument("--soft", action="store_true",
                    help="never exit non-zero (log only)")
    args = ap.parse_args()
    mode = "bootstrap" if args.bootstrap else "check"

    yamls = sorted(RULES.glob("*_source.yaml"))
    if not yamls:
        print("no rules/*_source.yaml found — run scripts/bootstrap_rule_sources.py")
        sys.exit(2)

    results = []
    for y in yamls:
        results.append(check_one(y, mode))

    drift = sum(1 for r in results if r == "drift")
    unpinned = sum(1 for r in results if r == "unpinned")
    ok = sum(1 for r in results if r in ("ok", "bootstrap", "keep"))
    print(f"\n{ok} ok, {drift} drift, {unpinned} unpinned, "
          f"{sum(1 for r in results if r == 'manual')} manual, "
          f"{sum(1 for r in results if r == 'neterr')} neterr")

    if args.soft:
        sys.exit(0)
    if drift or unpinned:
        sys.exit(1)


if __name__ == "__main__":
    main()
