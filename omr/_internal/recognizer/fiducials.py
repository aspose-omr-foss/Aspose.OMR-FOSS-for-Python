"""Detect the four solid corner fiducial squares on a scanned page.

The fiducials are the registration anchors: their centroids drive the
perspective transform that maps the scan back into template space. The hard part
is telling a fiducial apart from everything else dark on the page -- outline
boxes (cells, checkbox squares, grid headers) and filled round answer bubbles.

A fiducial is defined, rotation-invariantly, as a SOLID SQUARE:

  1. sized like a corner mark (area within a sensible band),
  2. roughly square (``minAreaRect`` aspect ~1),
  3. four-sided (``approxPolyDP`` yields a quadrilateral, not a 6+-gon disc),
  4. low circularity (a square's ``4*pi*A/P^2`` ~= 0.785, well under a disc's ~1),
  5. actually filled (its bounding rect is mostly ink, unlike a hollow box).

Because every test is on a rotation-invariant shape descriptor, it holds at any
page orientation and under moderate perspective.
"""
from __future__ import annotations

import cv2
import numpy as np

from omr._internal.recognizer.constants import (
    FIDUCIAL_ASPECT,
    FIDUCIAL_CIRC,
    FIDUCIAL_INK,
)

# Area band, as a fraction of the whole image. A fiducial is small but not tiny:
# below ~0.003% it is noise/dust, above ~5% it is a large graphic or a merged
# blob, not a corner mark.
_MIN_AREA_FRACTION = 3e-5
_MAX_AREA_FRACTION = 0.05


def _binarize_for_fiducials(gray: np.ndarray) -> np.ndarray:
    """Produce a clean binary (ink = 255) image in which each solid fiducial is
    an isolated blob.

    Steps:

    * **Gaussian blur (5x5)** removes speckle so thresholding is stable.
    * **Adaptive (local) threshold**, *not* global Otsu: a phone photo has
      uneven lighting (a bright spot plus vignette) under which no single global
      cut separates the dark fiducials from the sheet everywhere. A local block
      several fiducials wide marks each pixel "darker than its neighbourhood",
      which is invariant to a slow light gradient. The block size is tied to the
      image (``min(h, w)//15``, forced odd, floor 31); with
      ``ADAPTIVE_THRESH_GAUSSIAN_C`` each pixel's threshold is a Gaussian-weighted
      local mean (nearer neighbours weigh more) minus the bias constant ``12``
      (the standard adaptive-threshold bias). ``THRESH_BINARY_INV`` makes ink
      white (255) on black, which is what ``findContours`` expects.
    * **Morphological open (5x5 ellipse)** erodes then dilates, snapping thin
      connections (scanner banding, form rules, bubble outlines) so a solid
      fiducial stays a separate blob; anything >= ~5 px wide survives.
    """
    height, width = gray.shape
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    block = max(31, (min(height, width) // 15) | 1)  # odd, >= 31
    binary = cv2.adaptiveThreshold(
        blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, block, 12)

    open_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    return cv2.morphologyEx(binary, cv2.MORPH_OPEN, open_kernel)


def _inked_fraction(binary: np.ndarray, rotated_rect) -> float:
    """Fraction of a candidate's rotated rectangle that is ink (0..1).

    The candidate's ``minAreaRect`` is converted to its four corner points, a
    polygon mask of exactly that quadrilateral is filled, and we measure how much
    of the binary image inside that mask is ink. A solid square scores ~1.0; a
    hollow outline box, whose interior is background, scores low. Using the
    rotated rect (not an axis-aligned crop) keeps the measurement tight at any
    angle.
    """
    box = cv2.boxPoints(rotated_rect).astype(np.int32)
    bx, by, bw, bh = cv2.boundingRect(box)
    bx0, by0 = max(0, bx), max(0, by)
    region = binary[by0:by0 + bh, bx0:bx0 + bw]
    if region.size == 0:
        return 0.0
    mask = np.zeros(region.shape, np.uint8)
    cv2.fillConvexPoly(mask, box - [bx0, by0], 255)
    inside = region[mask == 255]
    if inside.size == 0:
        return 0.0
    return float((inside == 255).mean())


def _as_fiducial(contour, binary: np.ndarray, image_area: float) -> dict | None:
    """Return ``{"center", "area"}`` if ``contour`` passes every fiducial gate,
    else ``None``. Gates run cheap-to-expensive so most contours are rejected
    before the ink-fill measurement."""
    area = cv2.contourArea(contour)
    if area < image_area * _MIN_AREA_FRACTION or area > image_area * _MAX_AREA_FRACTION:
        return None

    (cx, cy), (rect_w, rect_h), angle = cv2.minAreaRect(contour)
    if rect_w < 2.0 or rect_h < 2.0:
        return None
    if max(rect_w, rect_h) / min(rect_w, rect_h) > FIDUCIAL_ASPECT:
        return None

    perimeter = cv2.arcLength(contour, True)
    if perimeter <= 0:
        return None

    # Square, not circle. A polygon approximation at 4.5% of the perimeter keeps
    # a square's 4 corners but collapses a disc to 6+ vertices, so != 4 rejects
    # round marks. Circularity 4*pi*A/P^2 is the decisive follow-up: a square is
    # ~0.785 (kept), a filled bubble ~0.9+ (rejected).
    if len(cv2.approxPolyDP(contour, 0.045 * perimeter, True)) != 4:
        return None
    circularity = 4.0 * np.pi * area / (perimeter * perimeter)
    if circularity > FIDUCIAL_CIRC:
        return None

    if _inked_fraction(binary, ((cx, cy), (rect_w, rect_h), angle)) < FIDUCIAL_INK:
        return None

    return {"center": (float(cx), float(cy)), "area": float(area)}


def solid_square_candidates(gray: np.ndarray) -> list[dict]:
    """Detect solid square blobs rotation-invariantly.

    Returns one ``{"center": (cx, cy), "area": a}`` dict per detected fiducial
    candidate. Hollow outline boxes and round marks are rejected by the shape
    gates in ``_as_fiducial``.
    """
    binary = _binarize_for_fiducials(gray)
    # RETR_LIST (not RETR_EXTERNAL): in a phone photo the dark desk encloses the
    # white sheet as a background hole, so the fiducials sit INSIDE that hole and
    # RETR_EXTERNAL -- which only returns top-level contours -- would miss them.
    contours, _ = cv2.findContours(binary, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

    image_area = float(gray.shape[1] * gray.shape[0])
    candidates: list[dict] = []
    for contour in contours:
        candidate = _as_fiducial(contour, binary, image_area)
        if candidate is not None:
            candidates.append(candidate)
    return candidates
