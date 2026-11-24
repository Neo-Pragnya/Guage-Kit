"""The generated metric catalogue matches the registry, and every docs page has frontmatter for the site."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_metric_catalogue_is_current() -> None:
    r = subprocess.run(
        [sys.executable, "scripts/gen_metric_docs.py", "--check"],
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


def test_readme_renders_on_pypi() -> None:
    """PyPI shows the README without the repository: relative links and images break there, and the dynamic
    pyversions badge is unreliable, so links must be absolute and the Python badge static."""
    import re

    text = (ROOT / "README.md").read_text(encoding="utf-8")
    relative = re.findall(r"\]\((?!https?://|#)([^)]+)\)", text) + re.findall(
        r'src="(?!https?://)([^"]+)"', text
    )
    assert not relative, f"relative links break on PyPI: {relative}"
    assert "img.shields.io/pypi/pyversions" not in text
