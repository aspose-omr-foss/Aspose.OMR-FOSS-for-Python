"""Tuning constants for the recognition pipeline, in one auditable place.

These values are *finely balanced*: they were tuned together so recognition
survives the real-world degradations the distortion tests throw at it, while
still reading a clean scan correctly. Treat them as a unit -- changing one in
isolation can quietly regress a degradation case. Every constant below is
documented with the reasoning and, where it helps, a worked number.

Two different numeric scales appear here:

  * **Intensity (0-255)** -- a pixel's grey level, 0 = black, 255 = white. Used
    by the ink test and the rotation-marker darkness checks.
  * **Fill percentage (0-100)** -- the share of a bubble's ROI that counts as
    ink. Used by the gap/threshold classification.
"""
from __future__ import annotations

# ── classification: gap / threshold constants (fill-percentage scale, 0-100) ──
#
# These mirror OMRChecker's 0-255 defaults, linearly rescaled by 100/255:
#   MIN_JUMP          25/255*100 = 9.8  -> 10.0
#   MIN_GAP           30/255*100 = 11.8 -> 12.0
#   CONFIDENT_SURPLUS  5/255*100 =  2.0 ->  2.0
#
# The idea: within one question the filled bubbles read much darker than the
# blank ones, leaving a wide "gap" in the sorted fill values. The cut goes in
# that gap. These constants say how wide a gap must be to trust it.

MIN_JUMP = 10.0
"""Smallest fill gap (0-100) that counts as a real jump between blank and filled.
A gap narrower than this is noise, not a blank/filled boundary."""

MIN_GAP = 12.0
"""Smallest spread (max - min fill) a field must show before a *local* decision
is trusted. A field whose bubbles are all similar (all blank, or all faint) has
no real boundary, so it defers to the page-global threshold instead."""

CONFIDENT_SURPLUS = 2.0
"""Added to ``MIN_JUMP`` to define a *confident* gap (= 12.0). A field whose gap
clears this higher bar is classified on its own; otherwise ``MIN_GAP`` / the
global threshold act as tie-breakers."""

GLOBAL_DEFAULT = 50.0
"""Fallback cut (0-100) when no convincing gap exists anywhere on the page --
e.g. a page where every bubble is blank. 50% sits safely between a blank
bubble's ~0% and a filled bubble's ~90%+."""

# ── sampling / line suppression: ink test (intensity scale, 0-255) ────────────

FILL_DARK_CUTOFF = 175.0
"""A page pixel counts as *ink* when its normalized intensity is below this.

Chosen so the light in-bubble guide glyph (drawn near 210, and still ~195 after
light-shade gamma) is NOT counted, while genuine -- even faint -- pencil marks
are. A bubble's "fill" is then the percentage of its ROI pixels below this
cutoff. The line suppressor uses the same cutoff so that any faint banding that
would be *counted as fill* is also eligible for *removal*."""

# ── fiducial detection: square-vs-everything-else shape gates ─────────────────
#
# A corner fiducial is a SOLID square. These three gates separate it from the
# two shapes it could be confused with: a hollow outline box (cells / checkbox /
# grid header) and a filled round answer bubble. They are rotation-invariant, so
# they hold at any page orientation or perspective.

FIDUCIAL_INK = 0.62
"""Minimum fraction of a candidate's ``minAreaRect`` that must be inked.

A solid square fills its own bounding rectangle almost completely (~1.0); a
hollow outline box is mostly empty inside (~0.1-0.3). Requiring >= 0.62 rejects
hollow boxes while leaving headroom for a fiducial whose far edge is slightly
foreshortened in a photo."""

FIDUCIAL_ASPECT = 1.6
"""Maximum long/short side ratio of a candidate's ``minAreaRect``.

A square is ~1.0. The allowance up to 1.6 tolerates a photo's perspective
foreshortening of the far corner; anything more elongated is a rule, a bar, or a
stray streak, not a fiducial."""

FIDUCIAL_CIRC = 0.83
"""Maximum circularity ``4*pi*Area / Perimeter^2`` of a candidate.

Circularity is 1.0 for a perfect circle and pi/4 ~= 0.785 for a square. A filled
round bubble sits near 0.9+, a square near 0.785. The 0.83 cut is the decisive
square-vs-circle test: it keeps squares (<= 0.83) and rejects round marks
(> 0.83). This survives perspective, where vertex count and ink fraction alone
start to overlap between the two shapes."""

# ── registration: rotation-marker darkness decision points (intensity 0-255) ──
#
# After a candidate warp, the mean intensity inside the template's rotation-marker
# box tells us whether the warp put the page back in template space: a correctly
# registered marker is near-black, blank/foreign content reads ~200+.

ALIGNED_STRONG = 60.0
"""If a plain resize already makes the marker at least this dark, the scan is
already upright and correctly sized -- use it directly, with no detection or
warp. This is the common case (flatbed scan / digital fill) and the whole
round-trip corpus."""

MARKER_OK = 120.0
"""A warp whose marker ends up at most this dark is accepted as a valid
registration. Above this the marker is not convincingly restored."""

WARP_MARGIN = 20.0
"""A warp must beat the plain-resize marker darkness by at least this much to be
used, so a merely-equal warp never displaces a good resize. This keeps
registration robust when the marker is partly occluded by overlapping content."""
