#!/usr/bin/env bash
# Regenerate spike/trace-*/output.json from each Catala rule file.
#
# These files are committed (so the dashboard's static-fallback view
# works on GitHub Pages without an interpreter), but they must stay in
# sync with the rule files and event facts. CI re-runs this script and
# checks `git diff` is empty — any drift fails the build.
#
# Usage:
#     eval $(opam env --switch=catala)   # or whatever your switch is
#     bash scripts/build_trace_outputs.sh

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"

if ! command -v catala >/dev/null 2>&1; then
  echo "catala not on PATH. Activate an opam switch with catala installed:" >&2
  echo "  eval \$(opam env --switch=catala)" >&2
  exit 1
fi

cd "$ROOT"

PYSCRIPT='
import json, sys
out_path = sys.argv[1]
raw = sys.stdin.read()
chunks, buf, depth = [], "", 0
for ch in raw:
    buf += ch
    if ch == "{":
        depth += 1
    elif ch == "}":
        depth -= 1
        if depth == 0:
            chunks.append(buf.strip())
            buf = ""
if not chunks:
    sys.exit(f"catala produced no JSON; raw={raw!r}")
parsed = [json.loads(c) for c in chunks]
final = parsed[0] if len(parsed) == 1 else parsed
with open(out_path, "w") as f:
    json.dump(final, f, indent=2)
    f.write("\n")
'

for d in spike/trace-*/; do
  rule="$d/rule.catala_en"
  out="$d/output.json"
  [ -f "$rule" ] || continue

  # Multiple #[test] scopes emit one JSON object each; concatenate
  # them into a JSON list so `output.json` is always one valid value.
  catala interpret -F json --no-stdlib "$rule" | python3 -c "$PYSCRIPT" "$out"
  echo "  wrote $out"
done
