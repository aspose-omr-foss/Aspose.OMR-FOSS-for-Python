"""Regression tests locking in the adversarial-review fixes."""
import json
import os

import cv2
import pytest

from omr.api import OmrEngine
from omr.generation import BubbleSize, GlobalPageSettings, Orientation
from omr.generation.config import TemplateConfig
from omr.generation.config.elements import AnswerSheetConfig, CompositeGridConfig, GridConfig
from omr.generation.config.elements.parents import PageConfig

from ._util import build_sample_template, fill_bubbles


def _gen(tmp_path, tpl, settings=None):
    engine = OmrEngine()
    gen = engine.Generate(tpl, settings or GlobalPageSettings())
    assert gen.ErrorCode == 0, gen.ErrorMessage
    gen.Save(str(tmp_path), "f")
    return engine, gen, json.loads(gen.Template)


def test_empty_glyph_bubbles_read_near_zero(tmp_path):
    # The light in-bubble guide glyph must NOT register as fill, even with light-shade
    # on and a very low fixed threshold -> a blank sheet yields no false positives.
    engine, gen, desc = _gen(tmp_path, *build_sample_template())
    proc = engine.GetTemplateProcessor(os.path.join(str(tmp_path), "f.omr"))
    proc.ApplyLightShadeProcessing = True
    result = proc.Recognize(os.path.join(str(tmp_path), "f.png"), 5)  # strict low threshold
    for e in result.OmrElements:
        assert e.GetAnswer() == "", f"{e.QuestionName} false-positive: {e.GetAnswer()!r}"


def test_startid_advances_autoid(tmp_path):
    tpl = TemplateConfig()
    tpl.Name = "t"
    page = PageConfig()
    a1 = AnswerSheetConfig()
    a1.Name = "Q"
    a1.ElementsCount = 3
    a1.StartId = 5  # explicit -> ids 5,6,7
    a2 = AnswerSheetConfig()
    a2.Name = "Q"
    a2.ElementsCount = 2  # auto -> must continue at 8,9 (not restart/collide)
    page.Children = [a1, a2]
    tpl.Children = [page]
    _, _, desc = _gen(tmp_path, tpl)
    field_names = [f["Name"] for e in desc["Pages"][0]["Elements"] for f in e["Fields"]]
    assert field_names == ["Q5", "Q6", "Q7", "Q8", "Q9"]
    assert len(field_names) == len(set(field_names))  # no collisions


def test_composite_grid_extra_row_renders(tmp_path):
    tpl = TemplateConfig()
    tpl.Name = "t"
    page = PageConfig()
    cg = CompositeGridConfig()
    cg.Name = "cg"
    cg.ColumnsCount = 3
    cg.Values = ["X", "Y"]
    cg.ExtraRow = [["A", "B", "C"]]  # one extra leading row of custom symbols
    page.Children = [cg]
    tpl.Children = [page]
    _, _, desc = _gen(tmp_path, tpl)
    elem = desc["Pages"][0]["Elements"][0]
    # Each column should carry its extra symbol plus the 2 common values.
    col1 = [b["Value"] for b in elem["Fields"][0]["Bubbles"]]
    assert col1 == ["A", "X", "Y"]
    col3 = [b["Value"] for b in elem["Fields"][2]["Bubbles"]]
    assert col3 == ["C", "X", "Y"]


def test_grid_default_orientation_is_column_per_digit(tmp_path):
    tpl = TemplateConfig()
    tpl.Name = "t"
    page = PageConfig()
    g = GridConfig()
    g.Name = "ID"
    g.SectionsCount = 3
    g.OptionsCount = 10  # default (horizontal) -> each section is a vertical column
    page.Children = [g]
    tpl.Children = [page]
    _, _, desc = _gen(tmp_path, tpl)
    sec0 = desc["Pages"][0]["Elements"][0]["Fields"][0]["Bubbles"]
    xs = [b["Box"][0] for b in sec0]
    ys = [b["Box"][1] for b in sec0]
    assert max(xs) - min(xs) < 2       # all bubbles in a section share one x (a column)
    assert ys == sorted(ys) and ys[-1] - ys[0] > 100  # stacked vertically


def test_none_source_raises():
    engine = OmrEngine()
    with pytest.raises(TypeError):
        engine.Generate(None)


def test_180_rotation_corrected(tmp_path):
    engine, gen, desc = _gen(tmp_path, *build_sample_template())
    filled = fill_bubbles(os.path.join(str(tmp_path), "f.png"), desc, [
        ("MainQuestions", "MainQuestions1", "A"),
        ("capital", "capital", "Paris"),
    ])
    img = cv2.imread(filled, cv2.IMREAD_GRAYSCALE)
    flipped = cv2.rotate(img, cv2.ROTATE_180)
    flipped_path = os.path.join(str(tmp_path), "flipped.png")
    cv2.imwrite(flipped_path, flipped)

    proc = engine.GetTemplateProcessor(os.path.join(str(tmp_path), "f.omr"))
    result = proc.Recognize(flipped_path)
    answers = {e.QuestionName: e.GetAnswer() for e in result.OmrElements}
    assert answers["MainQuestions1"] == "A"
    assert answers["capital"] == "Paris"
