"""The recognition entry point: one scanned page -> one ``RecognitionResult``.

This sequences the pipeline stages (each implemented in its own module):

    decode -> register (de-skew / orient) -> fix 180 -> suppress lines
           -> [optional light-shade] -> sample fills -> classify

Keeping each stage separate makes the data flow legible: a grayscale image goes
in, a warped template-space image comes out of registration, a fill cache comes
out of sampling, and recognized elements come out of classification.
"""
from __future__ import annotations

import typing

import numpy as np

from omr._internal.recognizer import image_io, registration
from omr._internal.recognizer.classification import build_elements_from_cache
from omr._internal.recognizer.line_suppression import suppress_lines
from omr._internal.recognizer.sampling import sample_fills


def _select_page(descriptor: dict, page_index: int) -> dict:
    """The descriptor page for this scan, falling back to the first page when
    the index is out of range (e.g. a single-page template recognizing extra
    scans)."""
    pages = descriptor["Pages"]
    if page_index < len(pages):
        return pages[page_index]
    return pages[0]


def recognize(descriptor: dict, image: typing.Any, threshold: int, validation,
              image_path: str, apply_light_shade: bool, page_index: int = 0):
    """Recognize one scanned page against one descriptor page -> RecognitionResult."""
    from omr.model import RecognitionResult

    gray = image_io.to_gray(image)
    page = _select_page(descriptor, page_index)

    # Register into template space, then correct a residual 180 flip.
    warped: np.ndarray = registration.register(gray, page)
    warped = registration.fix_180(warped, page)

    # Suppress scanner banding / roller streaks / the form's own long rules in
    # template space (now axis-aligned, kernel template-sized) so they cannot
    # inflate a bubble's fill -- important for a low-threshold checkbox. Done
    # after registration so a band crossing a corner fiducial never erases part
    # of it before detection.
    warped = suppress_lines(warped)
    if apply_light_shade:
        warped = image_io.apply_light_shade(warped)

    cache = sample_fills(warped, page, page_index)

    result = RecognitionResult()
    result.ImagePath = image_path or ""
    result.PageName = page.get("PageName", "")
    result.TemplateName = descriptor.get("TemplateName", "")
    result._fill_cache = cache
    result._validation = validation
    result.OmrElements = build_elements_from_cache(cache, threshold, validation)
    return result
