"""Check the licences of everything Guage Kit installs at runtime.

Walks the dependency tree of the installed ``guage-kit`` (optionally with extras) through package metadata and
classifies each distribution's declared licence. Copyleft licences (GPL, AGPL, LGPL, SSPL, EUPL, OSL, CC-BY-SA) fail
the check; permissive ones pass; MPL-2.0 (file-level, weak copyleft) is allowed and listed. Anything without a
recognisable licence is reported for review and fails with ``--strict``.

Usage: python scripts/check_licenses.py [--extras anthropic,embeddings] [--strict] [--json out.json]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from importlib import metadata

from packaging.requirements import Requirement

PERMISSIVE = re.compile(r"\b(MIT|BSD|Apache|ISC|PSF|Python Software Foundation|Unlicense|0BSD|Zlib|HPND|CC0|Public Domain|MIT-CMU)\b", re.I)
WEAK = re.compile(r"\b(MPL|Mozilla Public License)\b", re.I)
COPYLEFT = re.compile(r"\b(A?GPL|LGPL|GNU (?:Affero |Lesser )?General Public|SSPL|EUPL|OSL|CC-BY-SA)\b", re.I)


def licence_of(dist: metadata.Distribution) -> str:
    md = dist.metadata
    expr = md.get("License-Expression")
    if expr:
        return expr
    classifiers = [c.split("::")[-1].strip() for c in md.get_all("Classifier") or [] if c.startswith("License ::")]
    if classifiers:
        return " AND ".join(classifiers)
    lic = (md.get("License") or "").strip()
    return lic.splitlines()[0][:80] if lic else "UNKNOWN"


def classify(text: str) -> str:
    if COPYLEFT.search(text) and not re.search(r"\bOR\b", text):
        return "copyleft"
    if PERMISSIVE.search(text):
        return "permissive"
    if WEAK.search(text):
        return "weak-copyleft"
    return "unknown"


def walk(root: str, extras: set[str]) -> dict[str, metadata.Distribution]:
    seen: dict[str, metadata.Distribution] = {}
    todo: list[tuple[str, set[str]]] = [(root, extras)]
    while todo:
        name, ex = todo.pop()
        key = name.lower().replace("_", "-")
        try:
            dist = metadata.distribution(name)
        except metadata.PackageNotFoundError:
            continue
        if key in seen and not ex:
            continue
        seen[key] = dist
        for raw in dist.requires or []:
            req = Requirement(raw)
            if req.marker is not None:
                envs = [{"extra": e} for e in ex] or [{"extra": ""}]
                if not any(req.marker.evaluate(env) for env in envs):
                    continue
            if req.name.lower().replace("_", "-") not in seen:
                todo.append((req.name, set(req.extras)))
    return seen


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--package", default="guage-kit")
    ap.add_argument("--extras", default="")
    ap.add_argument("--strict", action="store_true", help="fail on unknown licences too")
    ap.add_argument("--json", dest="json_out")
    args = ap.parse_args()
    extras = {e.strip() for e in args.extras.split(",") if e.strip()}
    dists = walk(args.package, extras)
    rows = []
    for key, dist in sorted(dists.items()):
        lic = licence_of(dist)
        rows.append({"name": key, "version": dist.version, "licence": lic, "class": classify(lic)})
    width = max(len(r["name"]) for r in rows)
    for r in rows:
        print(f"{r['name']:<{width}}  {r['version']:<12} {r['class']:<14} {r['licence']}")
    bad = [r for r in rows if r["class"] == "copyleft"]
    unknown = [r for r in rows if r["class"] == "unknown"]
    print(f"\n{len(rows)} distributions: {len(bad)} copyleft, {len(unknown)} unknown, " f"{sum(r['class'] == 'weak-copyleft' for r in rows)} weak copyleft (allowed)")
    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as fh:
            json.dump(rows, fh, indent=2)
    if bad:
        print("FAIL: copyleft licences: " + ", ".join(r["name"] for r in bad))
        return 1
    if unknown and args.strict:
        print("FAIL (--strict): unknown licences: " + ", ".join(r["name"] for r in unknown))
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
