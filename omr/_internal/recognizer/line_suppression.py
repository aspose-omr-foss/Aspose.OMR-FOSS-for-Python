"""Erase long thin dark runs (scanner banding, roller streaks, the form's own
long rules) before fill sampling.

Why it matters: a dark band crossing a bubble inflates that bubble's fill and
can flip a blank bubble to "marked" -- especially for a low-threshold checkbox.
A line is distinguished from a mark by *length*: a mark is compact, a band or
rule spans a large fraction of the page. So we detect dark pixels that survive a
morphological OPEN with a kernel far longer than any bubble, and whiten them.

The kernel is a 1-px line rotated through many angles, so banding that
registration could not restore to exactly horizontal/vertical (a few degrees
off) is still caught.
"""
from __future__ import annotations

import cv2
import numpy as np

from omr._internal.recognizer.constants import FILL_DARK_CUTOFF

# Line kernel length as a fraction of the page's short side (forced odd, floor
# 31). A run must be about this long to be treated as a line, which is far longer
# than any bubble or mark, so marks are left intact.
_LINE_KERNEL_DIVISOR = 12

# Orientation step (degrees) for the rotated line kernel. 0..180 in 15-degree
# steps covers every line direction (a line and its 180 reflection are the same).
_ANGLE_STEP = 15


def suppress_lines(gray: np.ndarray) -> np.ndarray:
    """Return ``gray`` with long thin dark runs whitened.

    The dark cutoff matches the fill sampler's (``FILL_DARK_CUTOFF``) so that any
    faint banding that would be *counted as fill* is also eligible for *removal*:
    a line at intensity 160 counts toward a bubble's fill but is lighter than a
    150 cutoff, so matching the cutoffs keeps the two tests consistent.
    """
    height, width = gray.shape
    dark = (gray < FILL_DARK_CUTOFF).astype(np.uint8) * 255

    # A horizontal 1-px line kernel; rotating it sweeps all orientations.
    length = max(31, (min(height, width) // _LINE_KERNEL_DIVISOR) | 1)
    horizontal = np.zeros((length, length), np.uint8)
    cv2.line(horizontal, (0, length // 2), (length - 1, length // 2), 255, 1)

    # OPEN(dark, line-kernel) keeps only dark pixels that lie along a run as long
    # as the kernel at that angle; OR across angles accumulates every line.
    lines = np.zeros_like(dark)
    for angle in range(0, 180, _ANGLE_STEP):
        rotate = cv2.getRotationMatrix2D((length / 2.0, length / 2.0), angle, 1.0)
        kernel = (cv2.warpAffine(horizontal, rotate, (length, length),
                                 flags=cv2.INTER_NEAREST) > 0).astype(np.uint8)
        if kernel.sum() == 0:
            continue
        lines = cv2.bitwise_or(lines, cv2.morphologyEx(dark, cv2.MORPH_OPEN, kernel))

    # Dilate slightly so a line's full width (not just its 1-px core) is cleared.
    lines = cv2.dilate(lines, cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3)))

    out = gray.copy()
    out[lines > 0] = 255
    return out
