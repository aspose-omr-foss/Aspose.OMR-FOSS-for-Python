"""Shared fixtures for the advanced-template distortion tests.

Builds the advanced exam sheet (generated from the committed ``examples/advanced-exam.txt``
markup), fills a fixed answer key with realistic pen marks, and exposes the exact
``EXPECTED`` answer dict the recognizer must recover. The distortion library in
``_distortions.py`` perturbs the filled sheet; every perturbation must still yield
``EXPECTED`` exactly (100% accuracy).
"""
from __future__ import annotations

import json
import os

import cv2
import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
EXAMPLES = os.path.normpath(os.path.join(_HERE, "..", "examples"))
MARKUP = os.path.join(EXAMPLES, "advanced-exam.txt")
LOGO = os.path.join(EXAMPLES, "advanced_logo.png")

# ── the answer key ────────────────────────────────────────────────────────────
# Grid / composite_grid are concatenated per element; answer_sheet is per line;
# choicebox/checkbox return option/box names.
_STUDENT_ID = "20260137"          # 8 sections
_EXAM_CODE = "428193"             # 6 columns
_MAIN = {1: "A", 2: "C", 3: "B", 4: "D", 5: "", 6: "A", 7: "B", 8: "C", 9: "D", 10: "A"}
_CHOICE = "Mars"
_CHECK = ["The answers are my own work", "I have read the exam rules"]  # mark first 2 of 3

_CHOICE_FIELD = "Section C - Which planet is the Red Planet?"
_CHECK_FIELD = "Section D - Declaration (tick all that apply)"

# (element, field, bubble-value) triples to ink.
FILL_TARGETS: list[tuple[str, str, str]] = []
for i, dgt in enumerate(_STUDENT_ID, start=1):
    FILL_TARGETS.append(("StudentID", f"StudentID_{i}", dgt))
for i, dgt in enumerate(_EXAM_CODE, start=1):
    FILL_TARGETS.append(("ExamCode", f"ExamCode_{i}", dgt))
for qid, ans in _MAIN.items():
    if ans:
        FILL_TARGETS.append(("MainQuestions", f"MainQuestions{qid}", ans))
FILL_TARGETS.append((_CHOICE_FIELD, _CHOICE_FIELD, _CHOICE))
for name in _CHECK:
    FILL_TARGETS.append((_CHECK_FIELD, _CHECK_FIELD, name))

# ── the expected recovered answers (QuestionName -> answer string) ────────────
EXPECTED: dict[str, str] = {}
EXPECTED["StudentID"] = _STUDENT_ID
EXPECTED["ExamCode"] = _EXAM_CODE
for qid, ans in _MAIN.items():
    EXPECTED[f"MainQuestions{qid}"] = ans
EXPECTED[_CHOICE_FIELD] = _CHOICE
EXPECTED[_CHECK_FIELD] = ",".join(_CHECK)


# ── generation + filling ──────────────────────────────────────────────────────

def generate_advanced(out_dir: str):
    """Generate the advanced sheet into ``out_dir``; return (engine, descriptor,
    png_path, omr_path)."""
    from omr.api import OmrEngine
    from omr.generation import GlobalPageSettings, PaperSize

    settings = GlobalPageSettings()
    settings.PaperSize = PaperSize.A4
    settings.ImagesPaths = [LOGO]
    engine = OmrEngine()
    res = engine.Generate(MARKUP, settings, [LOGO])
    assert res.ErrorCode == 0, res.ErrorMessage
    res.Save(out_dir, "advanced-exam")
    desc = json.loads(res.Template)
    return (engine, desc,
            os.path.join(out_dir, "advanced-exam.png"),
            os.path.join(out_dir, "advanced-exam.omr"))


def find_box(descriptor: dict, elem_name: str, field_name: str | None, value: str):
    for page in descriptor["Pages"]:
        for e in page["Elements"]:
            if e["Name"] != elem_name:
                continue
            for f in e["Fields"]:
                if field_name is not None and f["Name"] != field_name:
                    continue
                for b in f["Bubbles"]:
                    if b["Value"] == value:
                        return b["Box"]
    return None


def mark_sheet(png_path: str, descriptor: dict) -> np.ndarray:
    """Ink the answer key onto the clean sheet with solid pen-like discs.
    Returns a BGR uint8 image (cv2 convention), the clean filled baseline that all
    distortions start from."""
    img = cv2.imread(png_path, cv2.IMREAD_COLOR)
    if img is None:
        raise AssertionError(f"could not read {png_path}")
    for elem, field, value in FILL_TARGETS:
        box = find_box(descriptor, elem, field, value)
        if box is None:
            raise AssertionError(f"bubble not found: {elem}/{field}/{value}")
        x, y, w, h = box
        cx, cy = int(x + w / 2), int(y + h / 2)
        r = int(w * 0.42)
        cv2.circle(img, (cx, cy), r, (28, 28, 28), -1)
    return img


def recognized_answers(result) -> dict[str, str]:
    return {e.QuestionName: e.GetAnswer() for e in result.OmrElements}


def diff_answers(got: dict[str, str]) -> list[str]:
    """Return a list of human-readable mismatches vs EXPECTED ([] == perfect)."""
    out = []
    for name, exp in EXPECTED.items():
        g = got.get(name, "<missing>")
        if g != exp:
            out.append(f"{name!r}: expected {exp!r} got {g!r}")
    extra = set(got) - set(EXPECTED)
    for name in sorted(extra):
        if got[name]:  # a spurious non-empty answer for an unexpected element
            out.append(f"{name!r}: unexpected {got[name]!r}")
    return out
