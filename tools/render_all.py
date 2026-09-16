#!/usr/bin/env python3
"""Regenerate every module's static/description/index.html from tools/specs/.

One command, nineteen pages, one shared template. Edit the spec, never the
generated HTML: hand-editing one copy of a shared block is how listings drift
apart.

    python3 tools/render_all.py [--check]

``--check`` writes nothing and exits non-zero if any page is out of date.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_index import render  # noqa: E402

TOOLS = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(TOOLS)
SPECS = os.path.join(TOOLS, "specs")


def main(check=False):
    stale = []
    for name in sorted(os.listdir(SPECS)):
        if not name.endswith(".json"):
            continue
        spec = json.load(open(os.path.join(SPECS, name)))
        module = spec["module"]
        page = os.path.join(REPO, module, "static", "description", "index.html")
        out = render(**spec)
        current = open(page).read() if os.path.exists(page) else None
        if out == current:
            continue
        stale.append(module)
        if not check:
            open(page, "w").write(out)
    if check:
        print("out of date: " + ", ".join(stale) if stale else "all pages current")
        return 1 if stale else 0
    print("rewrote %d page(s)" % len(stale))
    return 0


if __name__ == "__main__":
    sys.exit(main("--check" in sys.argv[1:]))
