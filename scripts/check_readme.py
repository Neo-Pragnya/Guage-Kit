#!/usr/bin/env python3
"""Lint a showcase README (and its PyPI copy) for the things that silently break on GitHub or PyPI.

    python check_readme.py README.md [--pypi python/README.md] [--max-svg-kb 400]

GitHub README:
  * every relative link and image exists in the repository;
  * every in-page anchor (#-why-it) matches a heading, using GitHub's slug rules (emoji and punctuation dropped,
    spaces → hyphens, so "## ✨ Why ESHANA?" is #-why-eshana);
  * every <picture> keeps an <img> fallback with alt text; every <img> has alt text;
  * every local SVG: has a <title>, no <script> or external resources (GitHub's image proxy blocks them), animations
    honour prefers-reduced-motion, and the file stays under the size budget.
PyPI copy (--pypi):
  * no relative links or images remain, no Mermaid fences, no > [!NOTE] alerts, no <picture>;
  * every image URL is https and not raw.githubusercontent.com for SVG (served as text/plain, so it will not render);
  * when `readme_renderer` is installed (pip install readme-renderer), the text renders as PyPI would.
Exits 1 when anything fails; prints one line per problem.
"""
from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from pathlib import Path


def slug(heading: str) -> str:
    """GitHub's heading anchor: lowercase, drop everything but letters, digits, spaces, hyphens and underscores,
    spaces to hyphens (emoji vanish but the space after them stays, giving a leading hyphen)."""
    h = re.sub(r"<[^>]+>", "", heading).strip().lower()
    h = re.sub(r"`|\*\*|\*|~~", "", h)
    h = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", h)
    out = []
    for ch in h:
        cat = unicodedata.category(ch)
        if ch in " -_" or cat[0] in "LN" or cat == "Mn":
            out.append(ch)
    return "".join(out).replace(" ", "-")


def anchors(text: str) -> set[str]:
    seen: dict[str, int] = {}
    out = set()
    body = re.sub(r"```.*?```", "", text, flags=re.S)
    for m in re.finditer(r"^#{1,6}\s+(.+?)\s*#*\s*$", body, flags=re.M):
        s = slug(m.group(1))
        n = seen.get(s, 0)
        out.add(s if n == 0 else f"{s}-{n}")
        seen[s] = n + 1
    for m in re.finditer(r'<a\s+(?:name|id)="([^"]+)"', body):
        out.add(m.group(1))
    return out


def links(text: str):
    body = re.sub(r"```.*?```", "", text, flags=re.S)
    for m in re.finditer(r"!?\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)", body):
        yield m.group(1)
    for m in re.finditer(r'(?:src|href|srcset)="([^"]+)"', body):
        yield m.group(1)


def check_github(path: Path, max_kb: int) -> list[str]:
    root, text, bad = path.parent, path.read_text(encoding="utf-8"), []
    names = anchors(text)
    for url in links(text):
        if url.startswith("#"):
            if url[1:] not in names:
                bad.append(f"anchor {url} matches no heading")
        elif not re.match(r"^(https?:|mailto:|data:)", url):
            target = root / url.split("#", 1)[0].split("?", 1)[0]
            if not target.exists():
                bad.append(f"missing file: {url}")
    for pic in re.findall(r"<picture>.*?</picture>", text, flags=re.S):
        if not re.search(r"<img [^>]*alt=\"[^\"]+\"", pic):
            bad.append("a <picture> has no <img alt=…> fallback")
    for img in re.findall(r"<img [^>]*>", text):
        if not re.search(r'alt="[^"]+"', img):
            bad.append(f"image without alt text: {img[:80]}")
    for url in set(links(text)):
        if url.endswith(".svg") and not re.match(r"^https?:", url):
            f = root / url
            if not f.exists():
                continue
            svg = f.read_text(encoding="utf-8", errors="replace")
            kb = f.stat().st_size / 1024
            if kb > max_kb:
                bad.append(f"{url}: {kb:.0f} KB (budget {max_kb} KB)")
            if "<title" not in svg:
                bad.append(f"{url}: no <title> (screen readers and tooltips)")
            if "<script" in svg:
                bad.append(f"{url}: <script> is stripped by GitHub; use CSS keyframes")
            if re.search(r'(?:href|src)="https?:|@import|url\(https?:', svg):
                bad.append(f"{url}: external resource (blocked inside an <img>); inline it")
            if re.search(r"@keyframes|<animate", svg) and "prefers-reduced-motion" not in svg:
                bad.append(f"{url}: animated but ignores prefers-reduced-motion")
    return bad


def check_pypi(path: Path) -> list[str]:
    text, bad = path.read_text(encoding="utf-8"), []
    for url in links(text):
        if not re.match(r"^(https?:|mailto:|#|data:)", url):
            bad.append(f"PyPI: relative link {url}")
        if url.endswith(".svg") and "raw.githubusercontent.com" in url:
            bad.append(f"PyPI: {url} is served as text/plain; host SVGs on Pages")
        if re.match(r"^http:", url):
            bad.append(f"PyPI: insecure URL {url}")
    if "```mermaid" in text:
        bad.append("PyPI: Mermaid does not render; replace with a link or an image")
    if re.search(r"^> \[!\w+\]", text, flags=re.M):
        bad.append("PyPI: GitHub alerts do not render")
    if "<picture>" in text:
        bad.append("PyPI: <picture> is stripped; keep only the <img>")
    try:
        import readme_renderer.markdown as rm
        if rm.render(text, variant="GFM") is None:
            bad.append("PyPI: readme_renderer could not render the text")
    except ImportError:
        pass
    return bad


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("readme")
    ap.add_argument("--pypi")
    ap.add_argument("--max-svg-kb", type=int, default=400)
    a = ap.parse_args()
    bad = check_github(Path(a.readme), a.max_svg_kb)
    if a.pypi:
        bad += check_pypi(Path(a.pypi))
    for b in bad:
        print("✗", b)
    print("readme ok" if not bad else f"{len(bad)} problem(s)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
