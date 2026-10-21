"""Warp a scanned page back into template pixel space.

Registration is what makes recognition robust: it takes a scan that may be
rotated by a quarter turn, skewed, photographed at an angle, missing a torn
corner, or streaked by a scanner, and maps it onto the exact pixel grid the
template was drawn on -- so a bubble drawn at (x, y) is sampled at (x, y).

The method is a *perspective transform* driven by the four corner fiducials:

  * ``cv2.getPerspectiveTransform(src, dst)`` solves for the 3x3 homography that
    maps the four detected source corners ``src`` onto the four known template
    corners ``dst``. A homography (not just an affine) is needed because a photo
    taken at an angle is a genuine projective distortion, not merely a
    rotation+scale.
  * ``cv2.warpPerspective`` then resamples the whole image through that matrix.

The orientation (0/90/180/270 deg) is resolved by a *search*: we do not know
which detected corner is the template's top-left, so we try all four cyclic
labelings and keep the one whose warp lands the asymmetric rotation marker back
on its template position (where it reads darkest). This is why a single
rotation-marker ROI is the registration objective.

Note / documented limit: trusting one marker ROI is reliable for each
degradation handled on its own, but it can be fooled when a *missing* corner
coincides with gross misalignment (a torn corner combined with skew/perspective).
That stacked case is a known limit (see ROADMAP.md), not a supported one.
"""
from __future__ import annotations

import itertools

import cv2
import numpy as np

from omr._internal.recognizer.constants import ALIGNED_STRONG, MARKER_OK, WARP_MARGIN
from omr._internal.recognizer.fiducials import solid_square_candidates
from omr._internal.recognizer.quad import (
    complete_rectangle,
    order_clockwise,
    select_corner_quad,
    template_src_points,
)

# Scoring warps run at this longest-side pixel size. Trying four orientations per
# quad over many quads would be slow at full resolution, so candidates are scored
# on a small warp and only the winner is warped at full size.
_SCORING_MAX_SIDE = 800.0

# The valid fiducial quad spans the candidate cloud, so a real quad must cover at
# least this fraction of the cloud's bounding box. Rejects small/degenerate quads
# built from interior points.
_MIN_QUAD_AREA_FRACTION = 0.4

# Cap on how many candidate points enter the brute-force subset search, to bound
# the combinatorics on pathologically busy scans (the farthest-from-centre points
# are kept, since fiducials are outermost).
_MAX_SEARCH_CANDIDATES = 12

# A 180 flip is applied when the marker reads this much darker at its mirrored
# (bottom) position than at the expected (top) position.
_FLIP_MARGIN = 25.0


def marker_darkness(warped: np.ndarray, rotation_box, width: int, height: int) -> float:
    """Mean intensity inside the template rotation-marker box (lower = more
    marker-like). Returns 0.0 when there is no marker box and 255.0 (maximally
    un-marker-like) when the box falls outside the image."""
    if not rotation_box or len(rotation_box) != 4:
        return 0.0
    x, y, box_w, box_h = rotation_box
    x0 = max(0, int(x))
    x1 = min(width, int(x + box_w))
    y0 = max(0, int(y))
    y1 = min(height, int(y + box_h))
    if x1 <= x0 or y1 <= y0:
        return 255.0
    return float(warped[y0:y1, x0:x1].mean())


def warp_quad(gray: np.ndarray, quad, rotation: int, dst: np.ndarray,
              width: int, height: int) -> np.ndarray:
    """Perspective-warp ``gray`` so ``quad`` (at the given cyclic orientation)
    maps onto the template corners ``dst``, producing a ``width`` x ``height``
    image. Pixels outside the source map to white (``borderValue=255``)."""
    clockwise = order_clockwise(quad)
    matrix = cv2.getPerspectiveTransform(template_src_points(clockwise, rotation), dst)
    return cv2.warpPerspective(gray, matrix, (width, height),
                               flags=cv2.INTER_LINEAR, borderValue=255)


def score_quad(gray: np.ndarray, quad, dst_small: np.ndarray, rotation_box_small,
               width_small: int, height_small: int):
    """Best ``(marker_darkness, orientation)`` for ``quad`` over its 4 cyclic
    orientations, scored on a small (fast) warp.

    When there is no rotation marker only one orientation is tried (there is
    nothing to disambiguate against).
    """
    clockwise = order_clockwise(quad)
    best_darkness = None
    best_rotation = 0
    orientation_count = 4 if (rotation_box_small is not None) else 1
    for rotation in range(orientation_count):
        matrix = cv2.getPerspectiveTransform(
            template_src_points(clockwise, rotation), dst_small)
        warped = cv2.warpPerspective(gray, matrix, (width_small, height_small),
                                     flags=cv2.INTER_LINEAR, borderValue=255)
        darkness = marker_darkness(warped, rotation_box_small, width_small, height_small)
        if best_darkness is None or darkness < best_darkness:
            best_darkness = darkness
            best_rotation = rotation
    return best_darkness, best_rotation


def _warp_without_marker(gray: np.ndarray, dst: np.ndarray,
                         width: int, height: int, resize_full: np.ndarray) -> np.ndarray:
    """Register a marker-less template (guards a hand-authored .omr; templates
    this library generates always carry a marker).

    De-skew from the fiducials anyway -- better than a plain resize for a
    skewed/photographed scan -- assuming a roughly upright page (0/90/270 cannot
    be disambiguated without the marker; ``fix_180`` still catches a flip
    downstream).
    """
    quad = select_corner_quad([c["center"] for c in solid_square_candidates(gray)])
    if quad is None:
        return resize_full
    return warp_quad(gray, quad, 0, dst, width, height)


def register(gray: np.ndarray, page: dict) -> np.ndarray:
    """Warp the scan into template pixel space using the detected corner
    fiducials, choosing the orientation (0/90/180/270 + skew/perspective) that
    restores the rotation marker.

    Strategy, cheapest first:

      1. **Already aligned?** If a plain resize already makes the marker dark
         (<= ``ALIGNED_STRONG``), the page is upright and correctly sized -- use
         the resize directly. This is the common path (flatbed scan / digital
         fill) and the whole round-trip corpus.
      2. **Fast path.** Otherwise reduce the fiducial candidates to their outer
         quad and score it; if its warp restores the marker, take it.
      3. **Search.** If the fast quad fails (a stray square displaced a true
         corner, or a corner is lost under overlapping content), score every
         large 4-subset of candidates, plus every 3-subset with its 4th corner
         reconstructed, and keep the hypothesis that best restores the marker.

    Scoring uses small warps, so the search is cheap and only runs for the hard
    cases.
    """
    width = int(page["Width"])
    height = int(page["Height"])
    centers = page.get("ReferenceCenters")
    rotation_box = page.get("RotationMarker")

    resize_full = cv2.resize(gray, (width, height), interpolation=cv2.INTER_AREA)
    # No reference geometry to work with -> nothing to warp against.
    if not centers or len(centers) != 4:
        return resize_full

    # Template corners, at full size and at the small scoring scale.
    scale = min(1.0, _SCORING_MAX_SIDE / max(width, height))
    dst = np.array(centers, dtype=np.float32)
    dst_small = (dst * scale).astype(np.float32)
    width_small = max(1, int(width * scale))
    height_small = max(1, int(height * scale))

    if not rotation_box:
        return _warp_without_marker(gray, dst, width, height, resize_full)

    rotation_box_small = [value * scale for value in rotation_box]

    # (1) Is the scan already in template space? A plain resize that already puts
    # the marker back (dark) means the page is upright and correctly sized --
    # warping cannot improve it and could only misfire on a busy form.
    resize_small = cv2.resize(gray, (width_small, height_small), interpolation=cv2.INTER_AREA)
    resize_score = marker_darkness(resize_small, rotation_box_small, width_small, height_small)
    if resize_score <= ALIGNED_STRONG:
        return resize_full

    # Misaligned (rotated / skewed / photographed): collect fiducial candidates.
    candidates = [c["center"] for c in solid_square_candidates(gray)]
    if len(candidates) < 3:
        return resize_full

    # A valid quad must cover a large part of the candidate cloud's bounding box.
    _, _, cloud_w, cloud_h = cv2.boundingRect(np.array(candidates, dtype=np.float32))
    min_quad_area = _MIN_QUAD_AREA_FRACTION * float(cloud_w * cloud_h)

    best = None  # (marker_darkness, quad, orientation)

    def consider(quad) -> None:
        """Score ``quad`` and remember it if it beats the current best. Skips a
        quad that is too small to be the real fiducial rectangle."""
        nonlocal best
        if quad is None:
            return
        quad_area = cv2.contourArea(cv2.convexHull(np.array(quad, dtype=np.float32)))
        if quad_area < min_quad_area:
            return
        darkness, rotation = score_quad(
            gray, quad, dst_small, rotation_box_small, width_small, height_small)
        if best is None or darkness < best[0]:
            best = (darkness, quad, rotation)

    def is_good(candidate_best) -> bool:
        """A registration is accepted when its marker is convincingly dark AND it
        beats the plain resize by the safety margin."""
        return (candidate_best is not None
                and candidate_best[0] <= MARKER_OK
                and candidate_best[0] + WARP_MARGIN < resize_score)

    # (2) Fast path: the hull-reduced quad (fiducials are the cloud's outer corners).
    consider(select_corner_quad(candidates))

    # (3) Search: large subsets, reconstructing the 4th corner for each 3-subset,
    # so a corner lost under a smudge/band is reconstructed rather than replaced
    # by a stray mark.
    if not is_good(best):
        search_points = candidates
        if len(search_points) > _MAX_SEARCH_CANDIDATES:
            cx = sum(p[0] for p in search_points) / len(search_points)
            cy = sum(p[1] for p in search_points) / len(search_points)
            search_points = sorted(
                search_points,
                key=lambda p: -((p[0] - cx) ** 2 + (p[1] - cy) ** 2),
            )[:_MAX_SEARCH_CANDIDATES]
        for combo in itertools.combinations(range(len(search_points)), 4):
            consider([search_points[i] for i in combo])
        for combo in itertools.combinations(range(len(search_points)), 3):
            consider(complete_rectangle([search_points[i] for i in combo]))

    if is_good(best):
        return warp_quad(gray, best[1], best[2], dst, width, height)
    return resize_full


def fix_180(warped: np.ndarray, page: dict) -> np.ndarray:
    """Secondary net: rotate 180 deg if the marker still reads darker at its
    mirrored (bottom) position than at the expected (top) position.

    After marker-aware ``register`` this is normally a no-op; it still corrects a
    180 flip for legacy templates that carry a marker but were registered with
    the plain-resize fallback.
    """
    rotation_box = page.get("RotationMarker")
    if not rotation_box or len(rotation_box) != 4:
        return warped
    height, width = warped.shape
    x, y, box_w, box_h = rotation_box
    x0 = max(0, int(x))
    x1 = min(width, int(x + box_w))
    y0 = max(0, int(y))
    y1 = min(height, int(y + box_h))
    if x1 <= x0 or y1 <= y0:
        return warped

    top = warped[y0:y1, x0:x1]
    mirror_y0 = max(0, height - y1)
    mirror_y1 = min(height, height - y0)
    bottom = warped[mirror_y0:mirror_y1, x0:x1]
    if top.size == 0 or bottom.size == 0:
        return warped
    if float(bottom.mean()) + _FLIP_MARGIN < float(top.mean()):
        return cv2.rotate(warped, cv2.ROTATE_180)
    return warped
