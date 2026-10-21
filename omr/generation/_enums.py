"""Generation enums (values verbatim from the .NET source).

These are the top-level ``Aspose.OMR.Generation`` enums -- paper size,
orientation, bubble size, font style, rotation-marker placement and the named
``Color``. Integer values are copied character-for-character from the source and
are what the ``.omr`` descriptor serializes, so they must not change.

Re-exported from ``omr.generation`` (import them from there, not this private
module).
"""
from __future__ import annotations

import enum

from omr._internal.colors import COLOR_ORDER


class PaperSize(enum.IntEnum):
    """Output page size. Pixel dimensions are @300 DPI (see ``PAPER_SIZE_PX``)."""

    undefined = 0
    A4 = 1       # 2480 x 3508 px
    Legal = 2    # 2551 x 4205 px
    Tabloid = 3  # 3295 x 5102 px
    p8519 = 4    # 2551 x 5702 px (8.5 x 19 in)
    p8521 = 5    # 2551 x 6302 px (8.5 x 21 in)
    A3 = 6       # 3508 x 4961 px
    Letter = 7   # 2551 x 3295 px


class Orientation(enum.IntEnum):
    undefined = 0
    Vertical = 1    # portrait (default)
    Horizontal = 2  # landscape


class BubbleSize(enum.IntEnum):
    """Answer-bubble size. Source casing is ``Extrasmall`` / ``Extralarge`` (sic)."""

    undefined = 0
    Extrasmall = 10
    Small = 20
    Normal = 30  # default
    Large = 40
    Extralarge = 50


class FontStyle(enum.IntFlag):
    """Flag-like font style; members may be combined."""

    undefined = 0
    Bold = 1
    Italic = 2
    Underline = 4
    Strikeout = 8
    Regular = 16


class RotationPointPosition(enum.IntEnum):
    """Placement of the orientation (rotation) marker relative to the page."""

    TopLeft1 = 10
    TopLeft2 = 11
    TopRight1 = 20
    TopRight2 = 21
    BottomLeft1 = 30
    BottomLeft2 = 31
    BottomRight1 = 40
    BottomRight2 = 41


# ``Color`` member values follow the .NET ``System.Drawing.Color`` known-color
# ordering (``undefined`` = 0, then 28..167). Built from the shared color table so
# the integer values stay authoritative and in one place.
Color = enum.IntEnum("Color", COLOR_ORDER)
Color.__doc__ = "Named-color enum (System.Drawing known-color ordering)."
