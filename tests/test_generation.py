"""Generation surface: results, .omr structure, saving, memory results, stubs."""
import io
import json
import os

import pytest

from omr.api import ImageCollection, OmrEngine
from omr.generation import MemoryGenerationResult

from ._util import build_sample_template


def test_generate_sets_result_fields(tmp_path):
    engine = OmrEngine()
    tpl, settings = build_sample_template()
    result = engine.Generate(tpl, settings)
    assert result.ErrorCode == 0
    assert result.ErrorMessage == ""
    assert result.Template.strip().startswith("{")
    assert result.TemplateImage is not None
    assert len(result.MultipageTemplateImages) == 1

    desc = json.loads(result.Template)
    assert desc["Format"] == "omr-python-for-foss"
    assert desc["TemplateName"] == "quiz"
    page = desc["Pages"][0]
    assert page["Width"] == 2480 and page["Height"] == 3508  # A4 @ 300 DPI
    assert len(page["ReferenceCenters"]) == 4
    assert page["RotationMarker"]


def test_save_writes_png_and_omr(tmp_path):
    engine = OmrEngine()
    tpl, settings = build_sample_template()
    result = engine.Generate(tpl, settings)
    result.Save(str(tmp_path), "quiz")
    assert os.path.isfile(os.path.join(str(tmp_path), "quiz.png"))
    assert os.path.isfile(os.path.join(str(tmp_path), "quiz.omr"))


def test_memory_generation_result(tmp_path):
    engine = OmrEngine()
    tpl, settings = build_sample_template()
    result = engine.Generate(tpl, settings)
    mem = MemoryGenerationResult(result)
    imgs = mem.GetImages()
    assert len(imgs) == 1 and imgs[0].read()
    omr_stream = mem.GetOmr("utf-8")
    assert b"Pages" in omr_stream.read()
    with pytest.raises(NotImplementedError):
        mem.GetPDF()


def test_pdf_stubs_raise(tmp_path):
    engine = OmrEngine()
    tpl, settings = build_sample_template()
    result = engine.Generate(tpl, settings)
    with pytest.raises(NotImplementedError):
        result.SaveAsPdf(str(tmp_path), "quiz")


def test_generate_missing_markup_raises():
    engine = OmrEngine()
    with pytest.raises(FileNotFoundError):
        engine.Generate("does_not_exist_12345.txt")


def test_unsupported_element_reports_error():
    # A score group is out of the core slice: the markup opener is rejected and the
    # failure surfaces via ErrorCode (not an exception).
    engine = OmrEngine()
    result = engine.Generate(["?score_group=sg", "&score_group"])
    assert result.ErrorCode != 0
    assert "score_group" in result.ErrorMessage


def test_image_collection_duplicate_raises():
    from PIL import Image

    coll = ImageCollection()
    buf = io.BytesIO()
    Image.new("RGB", (10, 10), (255, 0, 0)).save(buf, format="PNG")
    coll.Add("logo.png", buf.getvalue())
    assert coll.Contains("logo.png")
    assert coll.Count == 1
    with pytest.raises(Exception):
        coll.Add("logo.png", buf.getvalue())
