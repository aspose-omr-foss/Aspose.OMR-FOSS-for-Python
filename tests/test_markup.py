"""Text-markup DSL parsing + generation round trip."""
import json
import os

from omr.api import OmrEngine
from omr.generation import GlobalPageSettings, PaperSize

from ._util import fill_bubbles

MARKUP = [
    "# A simple exam sheet authored in the txt DSL",
    "?text=Markup Exam",
    "\tfont_size=24",
    "\tfont_style=bold",
    "?container=body",
    "\tcolumns_count=2",
    "?block=left",
    "\tcolumn=1",
    "\tborder=square",
    "?content=Name:______________",
    "\tfont_size=12",
    "?answer_sheet=Q",
    "\telements_count=4",
    "\tanswers_count=4",
    "\tcolumns_count=1",
    "\tstart_id=1",
    "\tanswers_list=(A)(B)(C)(D)",
    "&block",
    "?block=right",
    "\tcolumn=2",
    "?grid=ID",
    "\tsections_count=3",
    "\toptions_count=10",
    "\torientation=vertical",
    "&block",
    "&container",
    "?choicebox=Pick one",
    "\tdisplay_number=false",
    "?option=Alpha",
    "\tbubble_value=A",
    "?option=Beta",
    "\tbubble_value=B",
    "&choicebox",
]


def test_markup_parses_and_generates(tmp_path):
    engine = OmrEngine()
    settings = GlobalPageSettings()
    settings.PaperSize = PaperSize.A4
    result = engine.Generate(MARKUP, settings)
    assert result.ErrorCode == 0, result.ErrorMessage

    desc = json.loads(result.Template)
    page = desc["Pages"][0]
    names = {e["Name"]: e for e in page["Elements"]}

    assert "Q" in names
    assert len(names["Q"]["Fields"]) == 4  # elements_count
    assert len(names["Q"]["Fields"][0]["Bubbles"]) == 4  # answers_list
    assert names["Q"]["Fields"][0]["Name"] == "Q1"

    assert "ID" in names
    assert names["ID"]["ResultGrouping"] == "Element"
    assert len(names["ID"]["Fields"]) == 3  # sections

    assert "Pick one" in names
    opt_values = [b["Value"] for b in names["Pick one"]["Fields"][0]["Bubbles"]]
    assert opt_values == ["Alpha", "Beta"]


def test_markup_inline_option_lines(tmp_path):
    markup = [
        "?choicebox=Rate it",
        "(1) Poor (2) Fair (3) Good",
        "&choicebox",
    ]
    engine = OmrEngine()
    result = engine.Generate(markup)
    assert result.ErrorCode == 0, result.ErrorMessage
    desc = json.loads(result.Template)
    cb = desc["Pages"][0]["Elements"][0]
    assert [b["Value"] for b in cb["Fields"][0]["Bubbles"]] == ["Poor", "Fair", "Good"]


def test_markup_round_trip(tmp_path):
    engine = OmrEngine()
    result = engine.Generate(MARKUP)
    result.Save(str(tmp_path), "exam")
    desc = json.loads(result.Template)
    filled = fill_bubbles(os.path.join(str(tmp_path), "exam.png"), desc, [
        ("Q", "Q1", "C"),
        ("Q", "Q2", "A"),
        ("ID", "ID_1", "4"),
        ("ID", "ID_2", "0"),
        ("ID", "ID_3", "7"),
        ("Pick one", "Pick one", "Beta"),
    ])
    proc = engine.GetTemplateProcessor(os.path.join(str(tmp_path), "exam.omr"))
    result2 = proc.Recognize(filled)
    answers = {e.QuestionName: e.GetAnswer() for e in result2.OmrElements}
    assert answers["Q1"] == "C"
    assert answers["Q2"] == "A"
    assert answers["ID"] == "407"
    assert answers["Pick one"] == "Beta"
