#!/usr/bin/env python3
"""Fill generated sections of a README from the real program, so reference tables and galleries cannot drift.

The README marks each generated section:

    <!-- OPS:START -->
    (anything here is replaced)
    <!-- OPS:END -->

and a JSON spec says how to produce each one, either a command whose stdout is Markdown or a Python callable:

    {
      "readme": "README.md",
      "sections": {
        "OPS":     {"cmd": ["python", "tools/ops_table.py"]},
        "CLI":     {"cmd": ["mytool", "--help"], "fence": "text"},
        "GALLERY": {"python": "tools/gallery.py:render"}
      }
    }

    python readme_sections.py spec.json           # rewrite every section
    python readme_sections.py spec.json --check   # exit 1 when any section is stale (CI / make docs-check)

Use it for anything a reader trusts as complete: every operation/command/flag, error codes, supported methods, the
screenshot gallery. A table written by hand goes out of date the day a feature lands; a generated one fails the check.
"""
from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path


def produce(root: Path, spec: dict) -> str:
    if "cmd" in spec:
        out = subprocess.run(spec["cmd"], cwd=root, check=True, capture_output=True, text=True).stdout.rstrip()
    elif "python" in spec:
        path, fn = spec["python"].split(":")
        mod_spec = importlib.util.spec_from_file_location("section_mod", root / path)
        mod = importlib.util.module_from_spec(mod_spec)
        mod_spec.loader.exec_module(mod)
        out = getattr(mod, fn)().rstrip()
    else:
        raise SystemExit(f"section needs 'cmd' or 'python': {spec}")
    if spec.get("fence"):
        out = f"```{spec['fence']}\n{out}\n```"
    return out


def fill(text: str, name: str, body: str) -> str:
    pat = re.compile(rf"(<!-- {re.escape(name)}:START -->\n).*?(<!-- {re.escape(name)}:END -->)", re.S)
    if not pat.search(text):
        raise SystemExit(f"README has no {name}:START/END markers")
    return pat.sub(lambda m: m.group(1) + body + "\n" + m.group(2), text)


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    spec_path = Path(sys.argv[1]).resolve()
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    root = spec_path.parent if "root" not in spec else (spec_path.parent / spec["root"]).resolve()
    readme = root / spec.get("readme", "README.md")
    old = readme.read_text(encoding="utf-8")
    new = old
    for name, sec in spec["sections"].items():
        new = fill(new, name, produce(root, sec))
    if "--check" in sys.argv:
        if new != old:
            print(f"{readme.name}: generated sections are stale: run readme_sections.py {spec_path.name}")
            return 1
        print("readme sections ok")
        return 0
    readme.write_text(new, encoding="utf-8")
    print(f"wrote {len(spec['sections'])} generated section(s) in {readme.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
