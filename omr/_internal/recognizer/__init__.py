"""The recognition pipeline.

Stages (per scanned page): decode -> detect reference points -> perspective-warp
into template space (de-skew + orient) -> suppress scanner banding -> min-max
normalize -> sample each bubble's fill ratio -> classify filled/blank -> assemble
a ``RecognitionResult``.

Registration is robust to the real-world degradations a scan or phone photo
introduces:

  * **Any cardinal rotation (0/90/180/270).** The 4 corner fiducials are matched
    to the template corners not by "nearest image corner" (which only survives
    0/180) but by trying all four cyclic labelings of the detected quad and
    keeping the one whose warp puts the asymmetric rotation marker back at its
    template position (darkest ROI).
  * **Skew + perspective ("phone shot").** The 4 detected fiducial centroids
    drive a full perspective transform, so an angled photo on a desk is rectified
    like a flatbed scan.
  * **A torn corner / one missing fiducial.** With only 3 of 4 fiducials found
    the 4th is reconstructed by parallelogram completion before warping.
  * **Scanner banding.** Long thin horizontal/vertical dark runs are erased
    before sampling so they cannot inflate a blank bubble's fill.

Fiducials are told apart from outline boxes (cells / checkbox / grid headers)
and from filled round bubbles by a rotation-invariant *solid-ink* test: inside
its minAreaRect a corner square is ~fully inked (~1.0), a hollow box is mostly
empty, and a round mark is only pi/4 ~= 0.785 inked -- so neither is mistaken for
a fiducial at any rotation.

The classification math follows the OMRChecker reference: fill is the mean
darkness of the (inset) bubble ROI, and the filled/blank cut is found by sorting
a field's fills and taking the midpoint of the first convincing gap, falling back
to a page-global threshold derived the same way. Constants are expressed on the
0-100 fill scale.

The implementation is split into focused modules:

  * ``constants``        -- the tuning values, each documented,
  * ``image_io``         -- decode to grayscale, normalize, light-shade,
  * ``fiducials``        -- detect the solid corner squares,
  * ``quad``             -- order corners / reconstruct a missing one,
  * ``registration``     -- the perspective warp + orientation search,
  * ``line_suppression`` -- erase scanner banding / long rules,
  * ``sampling``         -- measure each bubble's fill ratio,
  * ``classification``   -- gap-based filled/blank decision + assembly, and
  * ``engine``           -- the ``recognize`` entry that sequences the stages.

``recognize`` and ``build_elements_from_cache`` are the public entry points
(the latter is reused by ``TemplateProcessor.Recalculate``).
"""
from __future__ import annotations

from omr._internal.recognizer.classification import build_elements_from_cache
from omr._internal.recognizer.engine import recognize
from omr._internal.recognizer.sampling import sample_fills

__all__ = ["recognize", "build_elements_from_cache", "sample_fills"]
