"""Render the homepage terminal as an animated SVG: commands type out, output appears, and the session loops.

Pure CSS animation (no script), so it plays on the website and in the GitHub README. The output lines are real:
copied from runs of the acceptance fixture project and of ``guage demo`` (see the "In your terminal" section of
website/src/pages/index.astro).

Usage: python scripts/gen_terminal_svg.py [--check]
"""

from __future__ import annotations

import sys
from html import escape
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "website" / "public" / "terminal.svg"

# (kind, text): "cmd" lines are typed; "out" lines appear; "gap" is a pause. Markup: [ok]..[/], [dim]..[/], [bad]..[/].
SESSION: list[tuple[str, str]] = [
    ("cmd", "pip install guage-kit"),
    ("out", "[dim]Successfully installed guage-kit[/]"),
    ("gap", ""),
    ("cmd", "guage run --gate faithfulness:min=0.85 --gate recall@3:min=0.8:warn"),
    ("out", "[dim] metric           value   95% CI          n[/]"),
    ("out", " faithfulness ↑   1.000   1.000 – 1.000   24"),
    ("out", " recall@3 ↑       0.958   0.875 – 1.000   24"),
    ("out", " mrr ↑            0.882   0.750 – 0.979   24"),
    ("out", " token_f1 ↑       0.413   0.288 – 0.529   24"),
    ("out", "Gate: [ok]PASS[/]"),
    ("out", "  [ok]✓[/] faithfulness: 1 meets ≥ 0.85"),
    ("out", "  [ok]✓[/] recall@3: 0.9583 meets ≥ 0.8"),
    ("gap", ""),
    ("cmd", "guage compare runs/rag_v1_run.json runs/rag_v2_run.json"),
    ("out", "[dim] metric             before   after    Δ       p (Holm)[/]"),
    ("out", " faithfulness       0.549    0.822    0.273   0.009    [ok]improved[/]"),
    ("out", " context_precision  0.586    0.829    0.243   0.009    [ok]improved[/]"),
    ("out", " recall@3           0.681    0.875    0.194   0.065    [dim]inconclusive[/]"),
    ("out", " mrr                0.636    0.845    0.208   0.009    [ok]improved[/]"),
]

W, PAD, LINE_H, CHAR_W, FONT = 860, 18, 20, 7.8, 13
TYPE_S, OUT_S, GAP_S, ENTER_S, HOLD_S = 0.035, 0.07, 0.5, 0.35, 5.0  # seconds per char / line / pause / hold


def _spans(text: str) -> str:
    out, i = [], 0
    while i < len(text):
        if text.startswith("[", i) and "]" in text[i:]:
            tag = text[i + 1 : text.index("]", i)]
            if tag in ("ok", "dim", "bad"):
                end = text.index("[/]", i)
                inner = text[text.index("]", i) + 1 : end]
                out.append(f'<tspan class="{tag}">{escape(inner)}</tspan>')
                i = end + 3
                continue
        j = text.find("[", i + 1)
        j = len(text) if j == -1 else j
        out.append(escape(text[i:j]))
        i = j
    return "".join(out)


def render() -> str:
    rows = [r for r in SESSION if r[0] != "gap"]
    height = PAD * 2 + 34 + LINE_H * len(rows)
    # timeline
    t, events = 0.6, []
    for kind, text in SESSION:
        if kind == "gap":
            t += GAP_S
        elif kind == "cmd":
            events.append((kind, text, t, t + TYPE_S * len(text)))
            t += TYPE_S * len(text) + ENTER_S
        else:
            events.append((kind, text, t, t))
            t += OUT_S
    total = t + HOLD_S

    def pct(x: float) -> str:
        return f"{100 * x / total:.3f}%"

    css, body = [], []
    y = PAD + 34 + 14
    for i, (kind, text, start, end) in enumerate(events):
        cls = f"l{i}"
        if kind == "cmd":
            width = (len(text) + 2) * CHAR_W
            body.append(
                f'<g class="{cls}"><text x="{PAD}" y="{y}"><tspan class="p">$</tspan> {escape(text)}</text>'
                f'<rect class="cover c{i}" x="{PAD + 2 * CHAR_W}" y="{y - 14}" width="{width}" height="{LINE_H}"/>'
                f'<rect class="cursor k{i}" x="{PAD + 2 * CHAR_W}" y="{y - 13}" width="{CHAR_W}" height="16"/></g>'
            )
            n = len(text)
            css.append(
                f"@keyframes c{i}{{0%,{pct(start)}{{transform:translateX(0);animation-timing-function:steps({n},end)}}"
                f"{pct(end)},99%{{transform:translateX({n * CHAR_W:.1f}px)}}100%{{transform:translateX(0)}}}}"
                f".c{i}{{animation:c{i} {total:.2f}s infinite}}"
            )
            css.append(
                f"@keyframes k{i}{{0%{{opacity:0;transform:translateX(0)}}"
                f"{pct(start - 0.01)}{{opacity:0;transform:translateX(0)}}"
                f"{pct(start)}{{opacity:1;transform:translateX(0);animation-timing-function:steps({n},end)}}"
                f"{pct(end)}{{opacity:1;transform:translateX({n * CHAR_W:.1f}px)}}"
                f"{pct(end + ENTER_S * 0.8)},100%{{opacity:0;transform:translateX({n * CHAR_W:.1f}px)}}}}"
                f".k{i}{{animation:k{i} {total:.2f}s infinite}}"
            )
        else:
            body.append(f'<text class="{cls}" x="{PAD}" y="{y}">{_spans(text)}</text>')
        css.append(
            f"@keyframes v{i}{{0%,{pct(start - 0.001)}{{opacity:0}}{pct(start)},99%{{opacity:1}}100%{{opacity:0}}}}"
            f".{cls}{{animation:v{i} {total:.2f}s infinite}}"
        )
        y += LINE_H
    style = (
        "text{font:" + str(FONT) + "px ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;fill:#d8e3e0;"
        "white-space:pre}.p{fill:#f59e0b}.ok{fill:#5eead4}.dim{fill:#7b8b91}.bad{fill:#f87171}"
        ".cover{fill:#0f1a1f}.cursor{fill:#5eead4}"
        "@media (prefers-reduced-motion:reduce){*{animation:none!important}.cover,.cursor{display:none}}"
        + "".join(css)
    )
    dots = "".join(
        f'<circle cx="{PAD + 6 + k * 18}" cy="{PAD + 6}" r="6" fill="{c}"/>'
        for k, c in enumerate(("#f2643d", "#f59e0b", "#14b8a6"))
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {height}" width="{W}" height="{height}" '
        f'role="img" aria-labelledby="t d">'
        "<title id=\"t\">Guage Kit in a terminal</title>"
        "<desc id=\"d\">guage run gates faithfulness and recall@3 and passes; guage compare shows which metrics "
        "improved between two versions with Holm-corrected p-values.</desc>"
        f"<style>{style}</style>"
        f'<rect width="{W}" height="{height}" rx="12" fill="#0f1a1f"/>{dots}'
        f'<text x="{W / 2}" y="{PAD + 10}" text-anchor="middle" class="dim" style="font-size:12px">guage</text>'
        + "".join(body)
        + "</svg>\n"
    )


if __name__ == "__main__":
    svg = render()
    if "--check" in sys.argv:
        if not OUT.exists() or OUT.read_text(encoding="utf-8") != svg:
            print("website/public/terminal.svg is out of date: run python scripts/gen_terminal_svg.py")
            sys.exit(1)
        print("terminal.svg is up to date")
    else:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(svg, encoding="utf-8")
        print(f"wrote {OUT} ({len(svg) // 1024} KB)")
