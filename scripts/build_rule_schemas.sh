#!/usr/bin/env bash
# Regenerate rules/*.schema.json from each rule module's primary scope.
#
# Each rule module has one or more `declaration scope X:` lines; the
# first non-test scope is treated as the public entrypoint. The
# generated schema describes the input and output JSON shapes and is
# consumed by dashboard/playground.html to render input forms.
#
# Files are committed so the GitHub Pages static build can serve them.
# CI re-runs this script and checks for drift.
#
# Usage:
#     eval $(opam env --switch=catala)
#     bash scripts/build_rule_schemas.sh

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"

if ! command -v catala >/dev/null 2>&1; then
  echo "catala not on PATH. Activate an opam switch with catala installed." >&2
  exit 1
fi

cd "$ROOT"

declare -a INDEX

for f in rules/*.catala_en; do
  name=$(basename "$f" .catala_en)
  # Pull every non-test `declaration scope X:` from the file. We skip
  # scopes whose name starts with "Test" — those are the #[test]
  # demonstrations, not the public predicate.
  while IFS= read -r scope; do
    [ -z "$scope" ] && continue
    case "$scope" in
      Test*) continue ;;
    esac
    out="rules/${name}__${scope}.schema.json"
    if catala json-schema --no-stdlib --scope="$scope" "$f" > "$out".raw 2>/dev/null; then
      # Canonicalise the schema so re-runs are deterministic. Catala
      # emits `required` arrays in OCaml-hash-table order, which drifts
      # across builds and triggers spurious CI failures. Sort every
      # `required` array, sort object keys, and strip insignificant
      # whitespace so two regens of the same rule are byte-identical.
      python3 -c "
import json, sys, pathlib
def canonicalise(node):
    if isinstance(node, dict):
        out = {}
        for k in sorted(node):
            v = canonicalise(node[k])
            if k == 'required' and isinstance(v, list):
                v = sorted(v)
            out[k] = v
        return out
    if isinstance(node, list):
        return [canonicalise(x) for x in node]
    return node
p = pathlib.Path('$out.raw')
data = json.loads(p.read_text())
out = json.dumps(canonicalise(data), indent=2, ensure_ascii=False)
pathlib.Path('$out').write_text(out + '\n')
p.unlink()
"
      echo "  wrote $out"
      INDEX+=("{\"module\":\"$name\",\"scope\":\"$scope\",\"file\":\"${name}.catala_en\",\"schema\":\"${name}__${scope}.schema.json\"}")
    else
      echo "  FAILED to schema-extract $scope from $f" >&2
      rm -f "$out" "$out".raw
    fi
  done < <(awk -F'[ :]+' '/^declaration scope [A-Za-z_][A-Za-z0-9_]*:/ {print $3}' "$f")
done

# Write an index file that the playground can fetch first.
{
  echo '['
  printf '  %s' "${INDEX[0]}"
  for i in "${!INDEX[@]}"; do
    [ "$i" = "0" ] && continue
    printf ',\n  %s' "${INDEX[$i]}"
  done
  echo
  echo ']'
} > rules/_index.json
echo "  wrote rules/_index.json (${#INDEX[@]} scopes)"
