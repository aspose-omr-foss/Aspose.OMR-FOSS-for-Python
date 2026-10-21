"""100%-accuracy recognition under real-world scan / photo / handling degradation.

Generates the advanced exam sheet (the full Layer 0-2 element set -- image, styled text,
proportional container, bordered block with character cells, an 8-digit ID grid, a
10-question A-D answer sheet, a 6-digit composite grid, a choicebox and a checkbox), inks
a fixed answer key, then recovers it EXACTLY from a battery of degraded images:

  * cardinal rotations (90 / 180 / 270) and arbitrary skew (+-3 .. +-20 deg),
  * an angled "phone photo" on a textured desk, with perspective, uneven lighting,
    blur and sensor noise,
  * scanner banding (horizontal bands + vertical roller streaks),
  * ink smudges, pen scribbles, and torn paper corners (one fiducial destroyed).

Every degradation is built to keep the answer marks and the registration fiducials
legible (damage is kept out of the bubble sampling ROIs -- see the note in
``smudges_scribbles`` on why damage on an answer mark is excluded), so demanding exact
recovery is a fair, well-defined bar. The degradation library lives in
``tests/_distortions.py`` and the fixture / answer key in ``tests/_advanced.py``.

Scope of each category (asserted):
  * rotation / skew / phone / scanner / smudge: the degradation applied to an otherwise
    clean sheet, across a wide parameter range.
  * **torn corner**: the sheet is torn but laid FLAT (upright), the realistic flatbed
    case. Such a scan is already in template space, so it recovers via the aligned
    path and the missing corner is irrelevant -- these assertions therefore validate
    *correct recovery of a torn sheet*, not the fiducial-reconstruction code specifically
    (which the misaligned search exercises on the phone/skew cases instead).

Known limits -- NOT asserted here, documented in ROADMAP.md:
  * extreme oblique perspective (phone keystone beyond a firm hand-held angle);
  * a torn corner COMBINED with significant skew/perspective, or the worst-case stacking
    of skew + heavy banding + a smudge that lands on a fiducial. The registration
    objective is a single rotation-marker ROI, which a stray mark can satisfy while the
    page is misaligned, so those combinations can be silently misregistered.
"""
from __future__ import annotations

import pytest

from . import _distortions as D
from ._advanced import (
    diff_answers,
    generate_advanced,
    mark_sheet,
    recognized_answers,
)


@pytest.fixture(scope="module")
def sheet(tmp_path_factory):
    """Generate the advanced sheet once and ink the fixed answer key -> (desc, clean, proc)."""
    out = tmp_path_factory.mktemp("advanced")
    engine, desc, png, omr = generate_advanced(str(out))
    clean = mark_sheet(png, desc)
    proc = engine.GetTemplateProcessor(omr)
    return desc, clean, proc


def _assert_exact(proc, img):
    diffs = diff_answers(recognized_answers(proc.Recognize(img)))
    assert not diffs, "recovered answers differ from the answer key:\n  " + "\n  ".join(diffs)


def test_clean_baseline(sheet):
    """The inked sheet, undistorted, recovers the full answer key."""
    _desc, clean, proc = sheet
    _assert_exact(proc, clean)


def test_canonical_distortions(sheet):
    """Every degradation in the demo battery (one representative per category, plus a
    stacked 'combined' case) recovers 100%."""
    desc, clean, proc = sheet
    for name, fn in D.all_distortions(desc).items():
        diffs = diff_answers(recognized_answers(proc.Recognize(fn(clean))))
        assert not diffs, f"[{name}] mismatches:\n  " + "\n  ".join(diffs)


@pytest.mark.parametrize("turns", [1, 2, 3], ids=["rot90", "rot180", "rot270"])
def test_cardinal_rotation(sheet, turns):
    _desc, clean, proc = sheet
    _assert_exact(proc, D.rotate_exact(clean, turns))


@pytest.mark.parametrize("angle", [-20, -15, -12, -9, -6, -3, 3, 6, 9, 12, 15, 20])
def test_skew(sheet, angle):
    _desc, clean, proc = sheet
    _assert_exact(proc, D.rotate_skew(clean, float(angle)))


@pytest.mark.parametrize("seed", range(1, 9))
def test_scanner_lines(sheet, seed):
    _desc, clean, proc = sheet
    _assert_exact(proc, D.scanner_lines(clean, seed=seed))


@pytest.mark.parametrize("seed", range(1, 9))
def test_smudges_scribbles(sheet, seed):
    desc, clean, proc = sheet
    _assert_exact(proc, D.smudges_scribbles(clean, desc, seed=seed))


@pytest.mark.parametrize("corner", ["br", "bl", "tr", "tl"])
@pytest.mark.parametrize("seed", [1, 2, 3])
def test_torn_corner(sheet, corner, seed):
    desc, clean, proc = sheet
    _assert_exact(proc, D.torn_corner(clean, desc, corner, seed=seed))


@pytest.mark.parametrize("strength", [0.6, 1.0])
@pytest.mark.parametrize("seed", range(1, 7))
def test_phone_shot(sheet, strength, seed):
    _desc, clean, proc = sheet
    _assert_exact(proc, D.perspective_phone(clean, seed=seed, strength=strength))


@pytest.mark.parametrize("angle", [0.0, 10.0, -8.0])
def test_markerless_template_deskews(sheet, tmp_path_factory, angle):
    """A descriptor WITHOUT a rotation marker (e.g. hand-authored; the library always
    emits one) still de-skews from the fiducials rather than only resizing."""
    import json
    import os

    from omr.api import OmrEngine

    desc, clean, _proc = sheet
    d2 = json.loads(json.dumps(desc))
    for pg in d2["Pages"]:
        pg["RotationMarker"] = []
    out = tmp_path_factory.mktemp("nomarker")
    omr2 = os.path.join(str(out), "nomarker.omr")
    with open(omr2, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(d2))
    proc2 = OmrEngine().GetTemplateProcessor(omr2)
    _assert_exact(proc2, D.rotate_skew(clean, angle))
