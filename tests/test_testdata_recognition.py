"""Recognition exercised on the ported Aspose corpus via a self-consistent round trip.

For each recognition fixture (markup + ``_SAMPLE.csv`` answer key) we:

1. generate our own sheet (PNG + ``.omr``) from the real Aspose markup;
2. mark bubbles — using the Aspose answer key wherever it maps cleanly onto our fields,
   synthesizing otherwise (see ``_testdata.build_fill_plan``);
3. recognize our own filled image with the auto threshold;
4. assert we recover exactly what we marked.

Why not recognize Aspose's own ``_SAMPLE.png`` scans directly? This build renders
pragmatically (different default paper size, non-pixel-faithful layout — see the
README), so a regenerated template's ROIs do not line up with Aspose's scans. The round
trip instead validates the whole shared pipeline — ``.omr`` contract, bubble geometry,
reference-point registration, fill sampling, threshold calibration, result assembly and
export — against real-world markup and, for the clean cases, real answer keys.

Comparisons are by *name multiset* (``_testdata.answers_by_name``): some grid fixtures
reuse an element name across variants, so collapsing to a name-keyed dict would drop a
real answer and hide a regression in all but the last same-named element.
"""
from __future__ import annotations

import json
import os

import pytest

from omr.api import FormValidationLogic, OmrEngine

from . import _testdata as td

RECOG = td.recognition_fixtures()

# Execution floors — the number of fixtures that must actually run (not skip) each path.
# Measured counts are higher; these are conservative so a genuine coverage loss fails the
# build instead of silently turning into skips.
MIN_ROUNDTRIP_RUNS = 37      # measured: 39 in-scope, single-page, field-bearing fixtures
MIN_PURE_CSV_RUNS = 5        # measured: 5 fixtures whose answer key maps 1:1 onto our fields


@pytest.fixture(scope="module")
def engine():
    return OmrEngine()


def _generate_in_scope(engine, rel, tmp_path):
    """Generate ``rel`` and skip unless it is a single-page, recognizable, in-scope sheet.
    Returns ``(descriptor, omr_path, png_path)``."""
    gen = engine.Generate(td.abspath(rel))
    if gen.ErrorCode != 0:
        pytest.skip(f"out-of-scope markup: {gen.ErrorMessage}")
    desc = td.load_descriptor(gen)
    if len(desc["Pages"]) != 1:
        pytest.skip("multi-page fixture; round trip recognizes a single image")
    if not any(e["Fields"] for e in desc["Pages"][0]["Elements"]):
        pytest.skip("no recognizable elements (content/image only)")
    gen.Save(str(tmp_path), "tpl")
    return desc, os.path.join(str(tmp_path), "tpl.omr"), os.path.join(str(tmp_path), "tpl.png")


def test_recognition_corpus_is_discovered():
    assert len(RECOG) > 50, f"expected many recognition fixtures, found {len(RECOG)}"


@pytest.mark.parametrize("rel", RECOG, ids=lambda r: r)
def test_roundtrip_exact_recovery(engine, tmp_path, rel):
    """Generate -> mark -> recognize -> recover exactly the marked answers."""
    desc, omr_path, png_path = _generate_in_scope(engine, rel, tmp_path)
    rows = td.parse_sample_csv(td.sample_csv_for(rel))
    boxes, plan, _source = td.build_fill_plan(desc, rows)
    assert boxes, f"{rel}: plan marked no bubbles"  # never a blank-to-blank no-op

    filled = td.fill_image(png_path, boxes)
    proc = engine.GetTemplateProcessor(omr_path, FormValidationLogic.Ignore)
    got = td.recognized_pairs(proc.Recognize(filled))  # auto threshold (-100)

    want_ms = td.answers_by_name(plan)
    got_ms = td.answers_by_name(got)
    assert got_ms == want_ms, (
        f"{rel}: recovered answers differ from what was marked\n"
        f"  planned: {want_ms}\n  got:     {got_ms}")


@pytest.mark.parametrize("rel", RECOG, ids=lambda r: r)
def test_pure_csv_answer_key_recovery(engine, tmp_path, rel):
    """Where the Aspose answer key maps 1:1 onto our fields, mark strictly that key and
    recover it exactly — the recovered answers are compared directly against the CSV
    (not against the plan derived from it), blanks and multiselect included."""
    desc, omr_path, png_path = _generate_in_scope(engine, rel, tmp_path)
    rows = td.parse_sample_csv(td.sample_csv_for(rel))
    boxes, _plan, source = td.build_fill_plan(desc, rows)
    if source != "csv":
        pytest.skip("answer key does not map 1:1 onto generated fields")
    assert boxes, f"{rel}: pure-csv plan marked no bubbles"

    filled = td.fill_image(png_path, boxes)
    proc = engine.GetTemplateProcessor(omr_path, FormValidationLogic.Ignore)
    got = td.recognized_pairs(proc.Recognize(filled))

    # Independent ground truth: the recognized elements must match the CSV answer key
    # exactly (as a per-name multiset over the recognizable elements).
    recognized_names = {n for n, _ in got}
    csv_truth = [(n, v) for n, v in rows if n in recognized_names]
    assert td.answers_by_name(got) == td.answers_by_name(csv_truth), (
        f"{rel}: recognition disagrees with the Aspose answer key")


def test_multiselect_recovered_from_real_answer_key(engine, tmp_path):
    """The answer_sheet_square key contains genuine multiselect answers (e.g. 'A,C',
    'B,D'); they must come back as the same set, and blanks must stay blank. This fixture
    has unique element names, so a plain name->value map is safe here."""
    rel = "Recognition/New/AnswerSheet/answer_sheet_square.txt"
    assert rel in RECOG
    desc, omr_path, png_path = _generate_in_scope(engine, rel, tmp_path)
    rows = td.parse_sample_csv(td.sample_csv_for(rel))
    expected = dict(rows)
    assert len(expected) == len(rows), "fixture unexpectedly has duplicate names"

    multiselect = {k: v for k, v in expected.items() if "," in v}
    blanks = [k for k, v in expected.items() if v == ""]
    assert multiselect and blanks, "fixture should have both multiselect and blank answers"

    boxes, _plan, source = td.build_fill_plan(desc, rows)
    assert source == "csv"
    filled = td.fill_image(png_path, boxes)
    proc = engine.GetTemplateProcessor(omr_path, FormValidationLogic.Ignore)
    got = dict(td.recognized_pairs(proc.Recognize(filled)))

    for k, v in multiselect.items():
        assert td.normalize_answer(got[k]) == td.normalize_answer(v), f"{k}: {got[k]!r} != {v!r}"
    for k in blanks:
        assert got[k] == "", f"{k} should be blank, got {got[k]!r}"


def test_exports_from_real_fixture(engine, tmp_path):
    """CSV / JSON / XML export of a recognized real-markup result."""
    rel = "Recognition/New/CheckBox/checkbox.txt"
    desc, omr_path, png_path = _generate_in_scope(engine, rel, tmp_path)
    expected = dict(td.parse_sample_csv(td.sample_csv_for(rel)))  # {'Sex:': 'Male'}
    boxes, _plan, _ = td.build_fill_plan(desc, td.parse_sample_csv(td.sample_csv_for(rel)))
    filled = td.fill_image(png_path, boxes)
    result = engine.GetTemplateProcessor(omr_path, FormValidationLogic.Ignore).Recognize(filled)

    (name, value), = expected.items()
    csv_text = result.GetCsv()
    assert name in csv_text and value in csv_text
    assert isinstance(result.GetCsv("utf-8"), bytes)

    data = json.loads(result.GetJson())
    assert any(el["QuestionName"] == name and el["Answer"] == value for el in data["Elements"])

    xml = result.GetXml()
    assert "RecognitionResult" in xml and value in xml


def test_recalculate_with_strict_threshold_clears_answers(engine, tmp_path):
    """Recalculate re-scores a cached result in place without re-reading pixels."""
    rel = "Recognition/New/AnswerSheet/answer_sheet_square.txt"
    desc, omr_path, png_path = _generate_in_scope(engine, rel, tmp_path)
    rows = td.parse_sample_csv(td.sample_csv_for(rel))
    boxes, _plan, _ = td.build_fill_plan(desc, rows)
    filled = td.fill_image(png_path, boxes)

    proc = engine.GetTemplateProcessor(omr_path, FormValidationLogic.Ignore)
    result = proc.Recognize(filled, -100)
    assert any(e.GetAnswer() for e in result.OmrElements), "expected some marks at auto threshold"

    proc.Recalculate(result, 100)  # impossibly strict -> nothing passes
    assert all(e.GetAnswer() == "" for e in result.OmrElements)


def test_recognition_execution_floor(engine, tmp_path):
    """Guard against silent coverage erosion: a regression that turns in-scope fixtures
    into skips (ErrorCode flips, dropped fields, answer-key labels drifting) would leave
    the parametrized tests green with everything skipped. Pin how many fixtures actually
    run each path, independently of the on-disk fixture count."""
    roundtrip_runs = pure_csv_runs = 0
    for rel in RECOG:
        gen = engine.Generate(td.abspath(rel))
        if gen.ErrorCode != 0:
            continue
        desc = td.load_descriptor(gen)
        if len(desc["Pages"]) != 1:
            continue
        if not any(e["Fields"] for e in desc["Pages"][0]["Elements"]):
            continue
        boxes, _plan, source = td.build_fill_plan(desc, td.parse_sample_csv(td.sample_csv_for(rel)))
        if not boxes:
            continue
        roundtrip_runs += 1
        if source == "csv":
            pure_csv_runs += 1

    assert roundtrip_runs >= MIN_ROUNDTRIP_RUNS, (
        f"only {roundtrip_runs} fixtures run the round trip (floor {MIN_ROUNDTRIP_RUNS}); "
        f"coverage eroded into skips")
    assert pure_csv_runs >= MIN_PURE_CSV_RUNS, (
        f"only {pure_csv_runs} fixtures run the pure-CSV check (floor {MIN_PURE_CSV_RUNS})")
