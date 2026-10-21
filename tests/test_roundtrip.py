"""End-to-end round trip: generate -> fill bubbles -> recognize -> verify answers.

This exercises every shared primitive at once: the .omr contract, the bubble geometry
single-source-of-truth, reference-point registration and fill-ratio classification.
"""
import json
import os

import pytest

from omr.api import FormValidationLogic, OmrEngine
from omr.exceptions import MultiselectException

from ._util import build_sample_template, descriptor_of, fill_bubbles


def _generate(tmp_path, multiselect=True):
    engine = OmrEngine()
    tpl, settings = build_sample_template(multiselect_answer_sheet=multiselect)
    result = engine.Generate(tpl, settings)
    assert result.ErrorCode == 0, result.ErrorMessage
    result.Save(str(tmp_path), "quiz")
    return engine, result


def test_full_round_trip(tmp_path):
    engine, gen = _generate(tmp_path)
    desc = descriptor_of(gen.Template)
    targets = [
        ("MainQuestions", "MainQuestions1", "A"),
        ("MainQuestions", "MainQuestions2", "C"),
        ("MainQuestions", "MainQuestions3", "B"),
        ("MainQuestions", "MainQuestions4", "D"),
        ("capital", "capital", "Paris"),
        ("agree", "agree", "Terms"),
        ("agree", "agree", "News"),
        ("StudentID", "StudentID_1", "1"),
        ("StudentID", "StudentID_2", "2"),
        ("StudentID", "StudentID_3", "3"),
    ]
    filled = fill_bubbles(os.path.join(str(tmp_path), "quiz.png"), desc, targets)

    proc = engine.GetTemplateProcessor(os.path.join(str(tmp_path), "quiz.omr"))
    result = proc.Recognize(filled)  # auto threshold

    answers = {e.QuestionName: e.GetAnswer() for e in result.OmrElements}
    assert answers["MainQuestions1"] == "A"
    assert answers["MainQuestions2"] == "C"
    assert answers["MainQuestions3"] == "B"
    assert answers["MainQuestions4"] == "D"
    assert answers["MainQuestions5"] == ""
    assert answers["capital"] == "Paris"
    assert answers["agree"] == "Terms,News"
    assert answers["StudentID"] == "123"


def test_exports(tmp_path):
    engine, gen = _generate(tmp_path)
    desc = descriptor_of(gen.Template)
    filled = fill_bubbles(os.path.join(str(tmp_path), "quiz.png"), desc,
                          [("capital", "capital", "Paris")])
    proc = engine.GetTemplateProcessor(os.path.join(str(tmp_path), "quiz.omr"))
    result = proc.Recognize(filled)

    csv = result.GetCsv()
    assert "capital,Paris" in csv
    assert isinstance(result.GetCsv("utf-8"), bytes)
    assert result.GetCsvAsStream("utf-8").read()

    data = json.loads(result.GetJson())
    assert data["TemplateName"] == "quiz"
    assert any(el["QuestionName"] == "capital" and el["Answer"] == "Paris"
               for el in data["Elements"])
    assert isinstance(result.GetJson("utf-8"), bytes)

    xml = result.GetXml()
    assert "RecognitionResult" in xml and "Paris" in xml


def test_recalculate_changes_classification(tmp_path):
    engine, gen = _generate(tmp_path)
    desc = descriptor_of(gen.Template)
    filled = fill_bubbles(os.path.join(str(tmp_path), "quiz.png"), desc,
                          [("MainQuestions", "MainQuestions1", "A")])
    proc = engine.GetTemplateProcessor(os.path.join(str(tmp_path), "quiz.omr"))
    result = proc.Recognize(filled, -100)
    first = {e.QuestionName: e.GetAnswer() for e in result.OmrElements}
    assert first["MainQuestions1"] == "A"

    # Impossibly strict threshold -> nothing passes; Recalculate re-scores in place.
    proc.Recalculate(result, 100)
    after = {e.QuestionName: e.GetAnswer() for e in result.OmrElements}
    assert after["MainQuestions1"] == ""


def test_multiselect_exception(tmp_path):
    engine = OmrEngine()
    tpl, settings = build_sample_template(multiselect_answer_sheet=False)
    gen = engine.Generate(tpl, settings)
    gen.Save(str(tmp_path), "quiz")
    desc = descriptor_of(gen.Template)
    # Two marks on one single-select line.
    filled = fill_bubbles(os.path.join(str(tmp_path), "quiz.png"), desc, [
        ("MainQuestions", "MainQuestions1", "A"),
        ("MainQuestions", "MainQuestions1", "B"),
    ])
    proc = engine.GetTemplateProcessor(os.path.join(str(tmp_path), "quiz.omr"),
                                       FormValidationLogic.Exception)
    with pytest.raises(MultiselectException):
        proc.Recognize(filled, 50)


def test_multiselect_ignore_joins(tmp_path):
    engine = OmrEngine()
    tpl, settings = build_sample_template(multiselect_answer_sheet=False)
    gen = engine.Generate(tpl, settings)
    gen.Save(str(tmp_path), "quiz")
    desc = descriptor_of(gen.Template)
    filled = fill_bubbles(os.path.join(str(tmp_path), "quiz.png"), desc, [
        ("MainQuestions", "MainQuestions1", "A"),
        ("MainQuestions", "MainQuestions1", "B"),
    ])
    proc = engine.GetTemplateProcessor(os.path.join(str(tmp_path), "quiz.omr"),
                                       FormValidationLogic.Ignore)
    result = proc.Recognize(filled, 50)
    answers = {e.QuestionName: e.GetAnswer() for e in result.OmrElements}
    assert answers["MainQuestions1"] in ("A,B", "B,A")


def test_recognize_from_stream_and_ndarray(tmp_path):
    import cv2

    engine, gen = _generate(tmp_path)
    desc = descriptor_of(gen.Template)
    filled = fill_bubbles(os.path.join(str(tmp_path), "quiz.png"), desc,
                          [("capital", "capital", "Berlin")])
    proc = engine.GetTemplateProcessor(os.path.join(str(tmp_path), "quiz.omr"))

    with open(filled, "rb") as fh:
        from_stream = proc.Recognize(fh)
    arr = cv2.imread(filled, cv2.IMREAD_GRAYSCALE)
    from_arr = proc.Recognize(arr)

    for r in (from_stream, from_arr):
        ans = {e.QuestionName: e.GetAnswer() for e in r.OmrElements}
        assert ans["capital"] == "Berlin"
