"""Measure each bubble's fill ratio and build the per-page fill cache.

"Fill" is the percentage (0-100) of ink pixels inside a bubble's region of
interest. The ROI is *inset* from the drawn box (via ``geometry.sample_roi``) so
the bubble's own printed outline does not count as ink -- only a mark inside does.

The output mirrors the descriptor's element/field/bubble structure but replaces
each bubble's geometry with its measured ``Fill``. Classification then works
purely from these numbers (no pixels), which is what lets ``Recalculate`` re-score
at a new threshold without re-reading the image.
"""
from __future__ import annotations

import numpy as np

from omr._internal import geometry
from omr._internal.recognizer.constants import FILL_DARK_CUTOFF
from omr._internal.recognizer.image_io import normalize


def _bubble_fill(norm: np.ndarray, box, width: int, height: int) -> float:
    """Fill percentage (0-100, rounded to 2 dp) for one bubble.

    The inset ROI is clamped to the image bounds (and forced to be at least 1x1)
    so a bubble near the edge still samples a valid region. Fill is the mean of
    the boolean "is this pixel darker than the ink cutoff?" over the ROI, times
    100 -- e.g. an ROI where 90% of pixels are ink reads 90.0.
    """
    x0, y0, x1, y1 = geometry.sample_roi(box)
    x0 = max(0, min(x0, width - 1))
    x1 = max(x0 + 1, min(x1, width))
    y0 = max(0, min(y0, height - 1))
    y1 = max(y0 + 1, min(y1, height))
    roi = norm[y0:y1, x0:x1]
    if roi.size == 0:
        return 0.0
    return round(float((roi < FILL_DARK_CUTOFF).mean()) * 100.0, 2)


def sample_fills(warped: np.ndarray, page: dict, page_index: int = 0) -> list[dict]:
    """Measure every bubble's fill and return a fill cache mirroring the page's
    element/field/bubble structure.

    ``page_index`` is stamped onto each element (as ``_page``) so that
    classification can compute a per-page global threshold even for a merged
    multi-page result.
    """
    norm = normalize(warped)
    height, width = norm.shape

    cache: list[dict] = []
    for element in page["Elements"]:
        cached_element = {
            "Type": element["Type"],
            "Name": element["Name"],
            "ResultGrouping": element["ResultGrouping"],
            "Multiselect": element["Multiselect"],
            "Threshold": element["Threshold"],
            "_page": page_index,
            "Fields": [],
        }
        for field in element["Fields"]:
            cached_field = {
                "Name": field["Name"],
                "SortWeight": field["SortWeight"],
                "Bubbles": [],
            }
            for bubble in field["Bubbles"]:
                fill = _bubble_fill(norm, bubble["Box"], width, height)
                cached_field["Bubbles"].append({"Value": bubble["Value"], "Fill": fill})
            cached_element["Fields"].append(cached_field)
        cache.append(cached_element)
    return cache
