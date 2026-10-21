"""Shared test helpers: build a sample template and fill bubbles programmatically."""
from __future__ import annotations

import json

from PIL import Image, ImageDraw

from omr.generation import BubbleSize, GlobalPageSettings, Orientation, PaperSize
from omr.generation.config import TemplateConfig
from omr.generation.config.elements import (
    AnswerSheetConfig,
    ChoiceBoxAnswerConfig,
    ChoiceBoxConfig,
    ContentConfig,
    GridConfig,
    TextConfig,
)
from omr.generation.config.elements.parents import CheckBoxConfig, PageConfig
from omr.generation.config.enums import BubbleType


def build_sample_template(multiselect_answer_sheet: bool = True) -> tuple[TemplateConfig, GlobalPageSettings]:
    """A template exercising answer_sheet, choicebox, checkbox and grid."""
    tpl = TemplateConfig()
    tpl.Name = "quiz"
    page = PageConfig()

    title = TextConfig()
    title.Name = "Sample Sheet"
    title.FontSize = 26

    ans = AnswerSheetConfig()
    ans.Name = "MainQuestions"
    ans.ElementsCount = 5
    ans.AnswersValues = ["A", "B", "C", "D"]
    ans.AnswersCount = 4
    ans.ColumnsCount = 1
    ans.StartId = 1
    ans.BubbleType = BubbleType.Round
    ans.BubbleSize = BubbleSize.Normal
    ans.VerticalMargin = 12
    ans.Multiselect = multiselect_answer_sheet

    cb = ChoiceBoxConfig()
    cb.Name = "capital"
    cb.QuestionText = "Capital of France?"
    for nm, bv in [("Paris", "A"), ("Berlin", "B"), ("Rome", "C")]:
        o = ChoiceBoxAnswerConfig()
        o.Name = nm
        o.BubbleValue = bv
        cb.Children.append(o)

    chk = CheckBoxConfig()
    chk.Name = "agree"
    for lab in ["Terms", "Privacy", "News"]:
        c = ContentConfig()
        c.Name = lab
        chk.Children.append(c)

    grid = GridConfig()
    grid.Name = "StudentID"
    grid.SectionsCount = 3
    grid.OptionsCount = 10
    grid.GridOrientation = Orientation.Vertical
    grid.BubbleSize = BubbleSize.Small

    page.Children = [title, ans, cb, chk, grid]
    tpl.Children = [page]

    settings = GlobalPageSettings()
    settings.PaperSize = PaperSize.A4
    return tpl, settings


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


def fill_bubbles(png_path: str, descriptor: dict, targets: list[tuple[str, str | None, str]]) -> str:
    """Fill the given (element, field, value) bubbles on a copy of the PNG. Returns
    the path to the filled image."""
    img = Image.open(png_path).convert("RGB")
    draw = ImageDraw.Draw(img)
    for elem, field, value in targets:
        box = find_box(descriptor, elem, field, value)
        if box is None:
            raise AssertionError(f"bubble not found: {elem}/{field}/{value}")
        x, y, w, h = box
        r = w * 0.40
        cx, cy = x + w / 2, y + h / 2
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(10, 10, 10))
    out = png_path.replace(".png", "_filled.png")
    img.save(out)
    return out


def descriptor_of(result_template_json: str) -> dict:
    return json.loads(result_template_json)
