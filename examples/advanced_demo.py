"""Advanced template end-to-end robustness demo.

Generates the advanced exam sheet, inks a fixed answer key, then runs the whole
degradation battery (rotations, angled phone shot, scanner banding, smudges/scribbles,
torn corners, and a stacked 'combined' case) through recognition -- asserting each one
recovers the answer key with 100% accuracy. Writes each degraded image, a labeled
montage, and a Markdown report under ``examples/out/advanced/``.

Run from the project root with the venv Python:

    python examples/advanced_demo.py
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
sys.path.insert(0, PROJ)

import cv2  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

from tests._advanced import (  # noqa: E402
    EXPECTED,
    diff_answers,
    generate_advanced,
    mark_sheet,
    recognized_answers,
)
from tests._distortions import all_distortions  # noqa: E402

OUT = os.path.join(HERE, "out", "advanced")
os.makedirs(OUT, exist_ok=True)


def _thumb(bgr: np.ndarray, width: int = 300) -> Image.Image:
    h, w = bgr.shape[:2]
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    im = Image.fromarray(rgb)
    return im.resize((width, max(1, int(h * width / w))))


def _font(size: int):
    for name in ("arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def main() -> int:
    engine, desc, png, omr = generate_advanced(OUT)
    clean = mark_sheet(png, desc)
    cv2.imwrite(os.path.join(OUT, "00_clean_filled.png"), clean)
    proc = engine.GetTemplateProcessor(omr)

    panels = [("clean_filled", clean, [])]
    rows = []
    for name, fn in all_distortions(desc).items():
        img = fn(clean)
        cv2.imwrite(os.path.join(OUT, f"{name}.png"), img)
        diffs = diff_answers(recognized_answers(proc.Recognize(img)))
        ok = not diffs
        n = len(EXPECTED)
        rows.append((name, ok, n - len(diffs), n, diffs))
        panels.append((name, img, diffs))

    # ---- montage ----
    cols = 4
    tw = 300
    thumbs = [( _thumb(img, tw), name, not diffs) for name, img, diffs in panels]
    th = max(t.height for t, _, _ in thumbs)
    cap_h = 34
    cell_w, cell_h = tw + 16, th + cap_h + 12
    rows_n = -(-len(thumbs) // cols)
    canvas = Image.new("RGB", (cols * cell_w, rows_n * cell_h), (245, 245, 247))
    draw = ImageDraw.Draw(canvas)
    f = _font(16)
    for i, (t, name, ok) in enumerate(thumbs):
        cx = (i % cols) * cell_w + 8
        cy = (i // cols) * cell_h + 8
        canvas.paste(t, (cx, cy + cap_h))
        tag = "PASS 100%" if ok else "FAIL"
        color = (22, 130, 60) if ok else (190, 40, 40)
        draw.rectangle([cx, cy, cx + tw, cy + cap_h - 4], fill=(255, 255, 255))
        draw.text((cx + 6, cy + 4), f"{name}", fill=(20, 20, 20), font=f)
        draw.text((cx + 6, cy + 18), tag, fill=color, font=_font(13))
    montage = os.path.join(OUT, "montage.png")
    canvas.save(montage)

    # ---- report ----
    passed = sum(1 for _n, ok, *_ in rows if ok)
    lines = [
        "# Advanced template -- degradation robustness report",
        "",
        f"Template: `examples/advanced-exam.txt` -> A4 PNG + `.omr`  |  answer-key fields: {len(EXPECTED)}",
        "",
        f"**{passed}/{len(rows)} degradations recovered the answer key with 100% accuracy.**",
        "",
        "| # | degradation | result | fields recovered |",
        "|---|-------------|--------|------------------|",
    ]
    for i, (name, ok, got, n, _d) in enumerate(rows, 1):
        lines.append(f"| {i} | `{name}` | {'PASS (100%)' if ok else 'FAIL'} | {got}/{n} |")
    lines += ["", "Images: `examples/out/advanced/<name>.png`, montage: `montage.png`."]
    report = os.path.join(OUT, "report.md")
    with open(report, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")

    print(f"{passed}/{len(rows)} degradations recovered 100%")
    print("montage:", montage)
    print("report :", report)
    return 0 if passed == len(rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
