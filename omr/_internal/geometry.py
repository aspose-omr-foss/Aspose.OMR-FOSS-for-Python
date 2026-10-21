"""Shared bubble / page / reference-point geometry.

This module is the SINGLE SOURCE OF TRUTH for every pixel convention shared between
the generation drawer and the recognition sampler. A mismatch here would silently
break recognition, so both pipelines import these helpers rather than hard-coding
any dimension.
"""
from __future__ import annotations

from omr.generation import (
    BubbleSize,
    Orientation,
    PaperSize,
    ReferencePointsSettings,
)

# Rendering resolution. Paper pixel dimensions below are quoted at this DPI.
DPI = 300

# Portrait pixel dimensions per paper size @ 300 DPI (verbatim from the .NET source).
PAPER_SIZE_PX: dict[PaperSize, tuple[int, int]] = {
    PaperSize.A4: (2480, 3508),
    PaperSize.Legal: (2551, 4205),
    PaperSize.Tabloid: (3295, 5102),
    PaperSize.p8519: (2551, 5702),
    PaperSize.p8521: (2551, 6302),
    PaperSize.A3: (3508, 4961),
    PaperSize.Letter: (2551, 3295),
}

# BubbleSize -> drawn bubble diameter in pixels (the source maps the enum to internal
# physical sizes 40/50/60/80/100). The drawn bubble's bounding box is what the
# recognizer samples FROM: it measures the inset ROI of that box (see
# SAMPLE_INSET_RATIO below), not the full box.
BUBBLE_PX: dict[BubbleSize, int] = {
    BubbleSize.Extrasmall: 40,
    BubbleSize.Small: 50,
    BubbleSize.Normal: 60,
    BubbleSize.Large: 80,
    BubbleSize.Extralarge: 100,
}

# Reference-mark geometry (corner fiducial squares + an asymmetric rotation marker).
REF_MARGIN = 70   # px from the page edge to the OUTER edge of each corner square
REF_SQUARE = 56   # side length (px) of each corner fiducial square
ROT_MARKER_W = 90  # rotation marker width (px)
ROT_MARKER_H = 34  # rotation marker height (px)

# Default content region insets (px) when a page/element does not override margins.
CONTENT_TOP = 230
CONTENT_BOTTOM = 210

# Fraction trimmed off each side of a bubble's bounding box before measuring fill,
# so the drawn outline / cell border does not inflate an empty bubble's reading.
SAMPLE_INSET_RATIO = 0.18


def page_dimensions(paper_size: PaperSize, orientation: Orientation) -> tuple[int, int]:
    """Return (width, height) in pixels for a paper size + orientation."""
    base = PAPER_SIZE_PX.get(paper_size)
    if base is None:  # undefined / unknown -> A4
        base = PAPER_SIZE_PX[PaperSize.A4]
    w, h = base
    if orientation == Orientation.Horizontal:
        return (h, w)
    return (w, h)


def bubble_diameter(bubble_size: BubbleSize) -> int:
    """Drawn bubble diameter (px) for a bubble size (undefined -> Normal)."""
    return BUBBLE_PX.get(bubble_size, BUBBLE_PX[BubbleSize.Normal])


def reference_marks(
    width: int, height: int, settings: ReferencePointsSettings | None = None
) -> dict[str, list[float]]:
    """Compute the reference-mark rectangles for a page of the given pixel size.

    Returns a dict with:
      - ``"corners"``: a list of 4 ``[x, y, w, h]`` corner-square boxes in TL, TR,
        BL, BR order (top-left origin of each square).
      - ``"corner_centers"``: the 4 corresponding ``[cx, cy]`` centroids, same order
        (these are the points used for the perspective transform).
      - ``"rotation"``: the ``[x, y, w, h]`` box of the asymmetric rotation marker.
    """
    off = settings.Offset if settings is not None else None
    o_top = off.Top if off else 0
    o_bottom = off.Bottom if off else 0
    o_left = off.Left if off else 0
    o_right = off.Right if off else 0

    left_x = REF_MARGIN + o_left
    right_x = width - REF_MARGIN - REF_SQUARE - o_right
    top_y = REF_MARGIN + o_top
    bottom_y = height - REF_MARGIN - REF_SQUARE - o_bottom

    corners = [
        [left_x, top_y, REF_SQUARE, REF_SQUARE],      # TL
        [right_x, top_y, REF_SQUARE, REF_SQUARE],     # TR
        [left_x, bottom_y, REF_SQUARE, REF_SQUARE],   # BL
        [right_x, bottom_y, REF_SQUARE, REF_SQUARE],  # BR
    ]
    centers = [[c[0] + c[2] / 2.0, c[1] + c[3] / 2.0] for c in corners]

    # Rotation marker: a horizontal bar centered at the top, below the top edge.
    # It breaks top/bottom symmetry so a 180-degree flip is detectable.
    rot_x = (width - ROT_MARKER_W) / 2.0
    rot_y = REF_MARGIN
    rotation = [rot_x, rot_y, ROT_MARKER_W, ROT_MARKER_H]

    return {"corners": corners, "corner_centers": centers, "rotation": rotation}


def sample_roi(box: list[float] | tuple[float, float, float, float]) -> tuple[int, int, int, int]:
    """Convert a bubble's drawn bounding box ``[x, y, w, h]`` into the inset
    integer ``(x0, y0, x1, y1)`` region used for fill measurement."""
    x, y, w, h = box
    dx = w * SAMPLE_INSET_RATIO
    dy = h * SAMPLE_INSET_RATIO
    x0 = int(round(x + dx))
    y0 = int(round(y + dy))
    x1 = int(round(x + w - dx))
    y1 = int(round(y + h - dy))
    if x1 <= x0:
        x1 = x0 + 1
    if y1 <= y0:
        y1 = y0 + 1
    return x0, y0, x1, y1
