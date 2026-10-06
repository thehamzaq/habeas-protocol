"""Locate the catala binary for the conformance scripts.

Catala usually lives in an opam switch that is not on PATH, so a bare
`shutil.which("catala")` misses it and every conformance script used to
print "CATALA SKIP" and still exit 0. Order: $HABEAS_CATALA, PATH, then
the default opam switch.

Set HABEAS_REQUIRE_CATALA=1 (CI does) to make a missing binary an error
instead of a skip.
"""

import glob
import os
import shutil
import sys


def find_catala():
    explicit = os.environ.get("HABEAS_CATALA")
    if explicit:
        if not os.path.exists(explicit):
            sys.exit(f"HABEAS_CATALA={explicit} does not exist")
        return explicit
    found = shutil.which("catala")
    if not found:
        candidates = sorted(glob.glob(os.path.expanduser("~/.opam/*/bin/catala")))
        found = candidates[0] if candidates else None
    if not found and os.environ.get("HABEAS_REQUIRE_CATALA") == "1":
        sys.exit("catala not found and HABEAS_REQUIRE_CATALA=1. "
                 "Install with `opam install catala.1.1.0` or set HABEAS_CATALA.")
    return found
