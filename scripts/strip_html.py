#!/usr/bin/env python3
"""Strip judgment HTML files to plain text. Heuristic — keep main content area."""
import os
import re
import sys
from html.parser import HTMLParser

class TextExtractor(HTMLParser):
    SKIP = {"script", "style", "nav", "header", "footer", "form", "aside"}
    def __init__(self):
        super().__init__()
        self.parts = []
        self.skip_depth = 0
    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self.skip_depth += 1
        if tag in ("p", "br", "div", "h1", "h2", "h3", "h4", "li", "tr"):
            self.parts.append("\n")
    def handle_endtag(self, tag):
        if tag in self.SKIP and self.skip_depth > 0:
            self.skip_depth -= 1
        if tag in ("p", "div", "h1", "h2", "h3", "h4", "li", "tr"):
            self.parts.append("\n")
    def handle_data(self, data):
        if self.skip_depth == 0:
            self.parts.append(data)
    def text(self):
        raw = "".join(self.parts)
        raw = re.sub(r"[ \t]+", " ", raw)
        raw = re.sub(r"\n[ \t]+", "\n", raw)
        raw = re.sub(r"\n{3,}", "\n\n", raw)
        return raw.strip()

def main():
    src = os.path.dirname(os.path.abspath(__file__)) + "/../data/raw/judgments"
    dst = os.path.dirname(os.path.abspath(__file__)) + "/../data/raw/text"
    os.makedirs(dst, exist_ok=True)
    files = sorted(f for f in os.listdir(src) if f.endswith(".html") and not f.startswith("_"))
    for fn in files:
        with open(f"{src}/{fn}") as f:
            html = f.read()
        ex = TextExtractor()
        ex.feed(html)
        text = ex.text()
        out = f"{dst}/{fn[:-5]}.txt"
        with open(out, "w") as f:
            f.write(text)
        print(f"{fn[:-5]:60s} {len(text):6d} chars")

if __name__ == "__main__":
    main()
