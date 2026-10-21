"""Shared helpers for the ``tests/testdata`` corpus (ported Aspose.OMR fixtures).

The corpus under ``tests/testdata/api`` is the Aspose.OMR for .NET test suite:

* ``Generation/`` and ``Recognition/`` each hold ``<name>.txt`` markup fixtures.
* A recognition fixture also carries ``<name>_SAMPLE.csv`` — the answer key Aspose
  recognized from its own filled scan (``<name>_SAMPLE.png``) — plus a reference
  ``<name>_SAMPLE.omr`` descriptor in Aspose's own JSON shape.

Two facts about this build shape how the data is used (both documented in the README):

1. Rendering is *pragmatic*, not pixel-faithful to Aspose, and the default paper size
   differs (A4 vs Aspose's Letter). So the Aspose ``_SAMPLE.png`` scans cannot be
   recognized through a template we regenerate — the geometry does not line up.
   Recognition is therefore exercised as a **self-consistent round trip**: we generate
   our own sheet from the real markup, mark bubbles, and recognize our own image.
2. ``#`` begins a comment (not the inline choicebox shorthand), so a few fixtures'
   inline ``#question / () option`` blocks are intentionally dropped. The round trip
   only asserts over the elements our generator actually emits.

The *answer key* in ``_SAMPLE.csv`` still drives the fill wherever it maps cleanly onto
our generated fields, so the recovered answers are checked against real Aspose data for
every field that structurally matches.

Element names are **not unique**: a handful of grid fixtures (e.g. ``GridOrientation``,
``bubbleSize``) reuse one name across orientation/size variants, and the CSV carries one
row per occurrence. Everything here therefore preserves order and compares by name as a
*multiset* rather than collapsing same-named elements into a dict (which would drop a
real answer key and hide a regression in all but the last occurrence).
"""
from __future__ import annotations

import csv
import json
import os
from collections import Counter, defaultdict

TESTDATA_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "testdata", "api")

# Markup element the Layer 0-2 core reports as unsupported (the scope boundary).
UNSUPPORTED_MARKER = "not supported by the Layer 0-2 core build"


# ── fixture discovery ──────────────────────────────────────────────────────────

def _rel(path: str) -> str:
    return os.path.relpath(path, TESTDATA_ROOT).replace("\\", "/")


def all_markup_fixtures() -> list[str]:
    """Every ``.txt`` markup fixture, as a path relative to ``TESTDATA_ROOT``."""
    out = []
    for dirpath, _dirs, files in os.walk(TESTDATA_ROOT):
        for fn in files:
            if fn.endswith(".txt"):
                out.append(_rel(os.path.join(dirpath, fn)))
    return sorted(out)


def recognition_fixtures() -> list[str]:
    """Markup fixtures that ship an expected-answer ``_SAMPLE.csv`` beside them."""
    out = []
    for rel in all_markup_fixtures():
        if os.path.exists(os.path.join(TESTDATA_ROOT, rel[:-4] + "_SAMPLE.csv")):
            out.append(rel)
    return out


def abspath(rel: str) -> str:
    return os.path.join(TESTDATA_ROOT, rel)


def sample_csv_for(rel: str) -> str:
    return os.path.join(TESTDATA_ROOT, rel[:-4] + "_SAMPLE.csv")


# ── expected-answer parsing ─────────────────────────────────────────────────────

def parse_sample_csv(path: str) -> list[tuple[str, str]]:
    """Aspose ``_SAMPLE.csv`` -> ordered ``[(ElementName, Value), ...]``.

    Order and duplicate names are preserved on purpose (some grid fixtures list the same
    element name more than once); callers compare by multiset, not by last-wins dict.
    """
    rows: list[tuple[str, str]] = []
    with open(path, newline="", encoding="utf-8-sig") as fh:
        for i, row in enumerate(csv.reader(fh)):
            if i == 0 or not row or not row[0].strip():
                continue
            rows.append((row[0].strip(), row[1].strip() if len(row) > 1 else ""))
    return rows


def normalize_answer(value: str) -> str:
    """Order-insensitive form for comparison. Multiselect answers are comma-joined, so
    sorting the tokens makes ``"C,A"`` and ``"A,C"`` compare equal; a grid/element
    digit string carries no comma and is left intact."""
    if not value:
        return ""
    return ",".join(sorted(t for t in value.split(",") if t))


def answers_by_name(pairs) -> dict:
    """``[(name, value), ...]`` -> ``{name: Counter(normalized value -> count)}``.

    Comparing two of these is a per-name multiset equality that is correct even when a
    name repeats (each occurrence keeps its own value instead of overwriting)."""
    out: dict = defaultdict(Counter)
    for name, value in pairs:
        out[name][normalize_answer(value)] += 1
    return dict(out)


# ── fill-plan construction ──────────────────────────────────────────────────────

def _sorted_fields(element: dict) -> list[dict]:
    return sorted(element["Fields"], key=lambda f: f.get("SortWeight", 0))


def build_fill_plan(descriptor: dict, csv_rows: list[tuple[str, str]]):
    """Decide which bubbles to mark on our generated sheet.

    Returns ``(boxes, plan, source)`` where ``boxes`` is a list of ``[x, y, w, h]``
    rectangles to fill, ``plan`` is an ordered ``[(QuestionName, intended answer), ...]``
    (duplicate names preserved) and ``source`` is ``"csv"`` (every value taken from the
    Aspose answer key), ``"synth"`` or ``"csv+synth"``.

    Answer-key rows are consumed **in order per name**, so the N-th element named ``X``
    is paired with the N-th CSV row named ``X``. A value is taken from the key only when
    it maps cleanly onto the generated field (all tokens are real bubble values;
    element-grouped values have one valid character per field); otherwise it is
    synthesized by marking the first bubble of each field, so there is always something
    to recover even where Aspose's read of its own scan does not match our field count.
    """
    queues: dict[str, list[str]] = {}
    for name, value in csv_rows:
        queues.setdefault(name, []).append(value)
    cursor: dict[str, int] = defaultdict(int)

    def next_value(name: str):
        vals = queues.get(name)
        if not vals or cursor[name] >= len(vals):
            return None
        value = vals[cursor[name]]
        cursor[name] += 1
        return value

    boxes: list = []
    plan: list[tuple[str, str]] = []
    source: set[str] = set()

    for page in descriptor["Pages"]:
        for element in page["Elements"]:
            grouping = element.get("ResultGrouping")
            fields = _sorted_fields(element)
            if not fields:
                continue  # nothing recognizable (pure content / image element)

            if grouping == "Field":
                for field in fields:
                    qn = field["Name"]
                    values = [b["Value"] for b in field["Bubbles"]]
                    want = next_value(qn)
                    tokens = [t.strip() for t in want.split(",")] if want else []
                    tokens = [t for t in tokens if t]
                    if want is not None and all(t in values for t in tokens):
                        plan.append((qn, want))
                        source.add("csv")
                        for t in tokens:
                            boxes.append(next(b["Box"] for b in field["Bubbles"]
                                              if b["Value"] == t))
                    else:
                        plan.append((qn, values[0]))
                        source.add("synth")
                        boxes.append(field["Bubbles"][0]["Box"])

            elif grouping == "Element":
                qn = element["Name"]
                want = next_value(qn)
                per_field = [[b["Value"] for b in f["Bubbles"]] for f in fields]
                clean = (want is not None and len(want) == len(fields)
                         and all(want[i] in per_field[i] for i in range(len(fields))))
                if clean:
                    plan.append((qn, want))
                    source.add("csv")
                    for i, field in enumerate(fields):
                        boxes.append(next(b["Box"] for b in field["Bubbles"]
                                          if b["Value"] == want[i]))
                else:
                    plan.append((qn, "".join(per_field[i][0] for i in range(len(fields)))))
                    source.add("synth")
                    for field in fields:
                        boxes.append(field["Bubbles"][0]["Box"])

    return boxes, plan, "+".join(sorted(source)) if source else "none"


def fill_image(png_path: str, boxes: list) -> str:
    """Draw a solid disc inside each box on a copy of ``png_path``; return its path."""
    from PIL import Image, ImageDraw

    img = Image.open(png_path).convert("RGB")
    draw = ImageDraw.Draw(img)
    for x, y, w, h in boxes:
        r = min(w, h) * 0.42
        cx, cy = x + w / 2, y + h / 2
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(8, 8, 8))
    out = png_path[:-4] + "_filled.png"
    img.save(out)
    return out


def recognized_pairs(result) -> list[tuple[str, str]]:
    """Ordered ``[(QuestionName, answer), ...]`` for every recognized element (duplicate
    names preserved — compare with :func:`answers_by_name`)."""
    return [(e.QuestionName, e.GetAnswer()) for e in result.OmrElements]


def load_descriptor(generation_result) -> dict:
    return json.loads(generation_result.Template)
