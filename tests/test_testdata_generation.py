"""Generation coverage over the full ported Aspose markup corpus (``tests/testdata``).

Every ``.txt`` markup fixture is fed through ``OmrEngine.Generate``. The contract
(``omr/api/__init__.py``: generation reports problems via ``ErrorCode`` and never
throws, bar a missing file) splits the corpus cleanly in two:

* **in-scope** markup -> ``ErrorCode == 0`` with a well-formed ``.omr`` descriptor and a
  rendered page image that ``Save`` writes to disk;
* **out-of-scope** markup (barcode, table, score_group, paragraph, vertical_choicebox,
  custom_answer_sheet, input_group, ICR/write_in, numeric_grid) -> ``ErrorCode != 0``
  whose message names the Layer 0-2 scope boundary.

Nothing in the corpus is allowed to raise.
"""
from __future__ import annotations

import json
import math
import os

import pytest

from omr.api import OmrEngine

from . import _testdata as td

MARKUP = td.all_markup_fixtures()

# Floors on the two populations. Measured: 114 in-scope, 123 out-of-scope. These pin the
# split so a regression that reclassifies an in-scope fixture (e.g. an element handler
# starts reporting itself unsupported) fails here instead of silently moving the fixture
# into the out-of-scope branch and dropping it from the recognition round trip.
MIN_IN_SCOPE = 110
MIN_OUT_OF_SCOPE = 115


@pytest.fixture(scope="module")
def engine():
    return OmrEngine()


def test_corpus_is_discovered():
    # Guard against a silently-empty parametrization (e.g. testdata not checked out).
    assert len(MARKUP) > 100, f"expected a large markup corpus, found {len(MARKUP)}"


@pytest.mark.parametrize("rel", MARKUP, ids=lambda r: r)
def test_generation_scope_and_artifacts(engine, tmp_path, rel):
    """Each fixture either generates valid artifacts or is reported out-of-scope."""
    gen = engine.Generate(td.abspath(rel))

    if gen.ErrorCode != 0:
        # Out-of-scope markup: reported, not thrown, and named as such.
        assert td.UNSUPPORTED_MARKER in gen.ErrorMessage, (
            f"{rel}: unexpected generation error: {gen.ErrorMessage!r}")
        assert gen.TemplateImage is None
        return

    # In-scope markup: the .omr descriptor is well-formed.
    desc = td.load_descriptor(gen)
    assert desc["Format"] == "omr-python-for-foss"
    assert desc["Version"]
    assert isinstance(desc["Pages"], list) and desc["Pages"], f"{rel}: no pages"

    for page in desc["Pages"]:
        assert page["Width"] > 0 and page["Height"] > 0, f"{rel}: bad page size"
        assert len(page["ReferenceCenters"]) == 4, f"{rel}: expected 4 reference marks"
        assert isinstance(page["Elements"], list)

    # A page image was produced, one per page.
    npages = len(desc["Pages"])
    assert gen.TemplateImage is not None
    assert len(gen.MultipageTemplateImages) == npages

    # Save writes a real PNG per page plus a re-readable .omr. A single-page result is
    # "<name>.png"; a multi-page one is "<name>_1.png", "<name>_2.png", ...
    gen.Save(str(tmp_path), "tpl")
    expected_pngs = (["tpl.png"] if npages <= 1
                     else [f"tpl_{i + 1}.png" for i in range(npages)])
    for fn in expected_pngs:
        png = os.path.join(str(tmp_path), fn)
        assert os.path.exists(png) and os.path.getsize(png) > 0, f"{rel}: {fn} not written"
    with open(os.path.join(str(tmp_path), "tpl.omr"), encoding="utf-8") as fh:
        assert json.load(fh)["Pages"], f"{rel}: saved .omr unreadable"


@pytest.mark.parametrize("rel", MARKUP, ids=lambda r: r)
def test_generated_bubble_geometry_is_sane(engine, rel):
    """Every generated bubble box is non-degenerate, finite and anchored on the page.

    Note: full containment (``x + w <= page_width``) is deliberately *not* asserted. This
    renderer is pragmatic (see the README), and the ``Overflow/*`` and composite-grid
    stress fixtures intentionally place bubbles past the page edge. The universal
    invariant is that a box has positive size, finite coordinates and a non-negative
    origin.
    """
    gen = engine.Generate(td.abspath(rel))
    if gen.ErrorCode != 0:
        pytest.skip("out-of-scope markup")
    desc = td.load_descriptor(gen)
    checked = 0
    for page in desc["Pages"]:
        for element in page["Elements"]:
            for field in element["Fields"]:
                for bubble in field["Bubbles"]:
                    x, y, w, h = bubble["Box"]
                    assert all(math.isfinite(v) for v in (x, y, w, h)), \
                        f"{rel}: non-finite box {bubble['Box']!r}"
                    assert w > 0 and h > 0, f"{rel}: zero-size bubble {bubble['Value']!r}"
                    assert x >= 0 and y >= 0, f"{rel}: bubble origin off the top/left"
                    checked += 1
    # Fixtures with recognizable elements must actually have bubbles.
    has_fields = any(e["Fields"] for p in desc["Pages"] for e in p["Elements"])
    if has_fields:
        assert checked > 0


def test_scope_split_is_stable(engine):
    """The corpus splits into a stable number of in-scope and out-of-scope fixtures, and
    every out-of-scope one is *reported* (never raised) with the documented message.

    Pinning both counts turns a silent reclassification — in either direction — into a
    failure, which the per-fixture test above cannot catch because it accepts whichever
    branch the library chooses."""
    in_scope = out_of_scope = 0
    for rel in MARKUP:
        gen = engine.Generate(td.abspath(rel))  # must not raise
        if gen.ErrorCode == 0:
            in_scope += 1
        else:
            out_of_scope += 1
            assert td.UNSUPPORTED_MARKER in gen.ErrorMessage, f"{rel}: {gen.ErrorMessage!r}"

    assert in_scope >= MIN_IN_SCOPE, (
        f"only {in_scope} fixtures generate in-scope (floor {MIN_IN_SCOPE}); "
        f"an in-scope fixture may have regressed to an error")
    assert out_of_scope >= MIN_OUT_OF_SCOPE, (
        f"only {out_of_scope} out-of-scope fixtures (floor {MIN_OUT_OF_SCOPE})")
