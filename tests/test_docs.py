"""The generated references (metrics, API, terminal SVG) match the code, and every docs page has frontmatter for the site."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]


@pytest.mark.parametrize("script", ["gen_metric_docs.py", "gen_api_docs.py", "gen_terminal_svg.py"])
def test_generated_docs_are_current(script: str) -> None:
    r = subprocess.run(
        [sys.executable, f"scripts/{script}", "--check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0, r.stdout + r.stderr


def test_docs_pages_have_frontmatter() -> None:
    for p in (ROOT / "docs").rglob("*.md"):
        text = p.read_text(encoding="utf-8")
        assert text.startswith("---\n") and "\ntitle:" in text.split("---", 2)[1], p


def test_no_package_file_is_git_ignored() -> None:
    """Hatch builds from what git doesn't ignore: an ignored file under src/ silently drops out of the wheel."""
    import shutil

    if shutil.which("git") is None or not (ROOT / ".git").exists():
        return
    files = [
        str(p.relative_to(ROOT))
        for p in (ROOT / "src").rglob("*")
        if p.is_file() and "__pycache__" not in p.parts
    ]
    r = subprocess.run(
        ["git", "check-ignore", "--no-index", *files],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.stdout.strip() == "", f"ignored package files: {r.stdout}"


def test_readme_renders_on_github_and_pypi() -> None:
    """README.md is written for GitHub (relative links, <picture>, alerts, Mermaid); README.pypi.md, the PyPI long
    description, is generated from it with absolute links and images served from GitHub Pages. Both are linted, and
    the generated sections and the PyPI copy must be current."""
    for args in (
        ["scripts/check_readme.py", "README.md", "--pypi", "README.pypi.md"],
        ["scripts/pypi_readme.py", "--check"],
        ["scripts/readme_sections.py", "readme_sections.json", "--check"],
    ):
        r = subprocess.run(
            [sys.executable, *args], cwd=ROOT, capture_output=True, text=True, check=False
        )
        assert r.returncode == 0, (args, r.stdout + r.stderr)
    pypi = (ROOT / "README.pypi.md").read_text(encoding="utf-8")
    assert "img.shields.io/pypi/pyversions" not in pypi  # that dynamic badge often fails to load
    assert "](assets/" not in pypi and 'src="assets/' not in pypi
