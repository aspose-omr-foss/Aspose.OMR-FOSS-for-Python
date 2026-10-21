"""Convert raw markup attribute strings into typed Python / enum values.

A markup attribute is always ``key=value`` where ``value`` is free text (the DSL
is untyped). This module is the one place that turns that text into the typed
value a config object expects:

  * the ``*_LUT`` dictionaries map a lowercased keyword to its enum member
    (``"center"`` -> ``AlignmentEnum.Center``), and
  * the ``as_*`` helpers parse scalars (ints, booleans, flag combinations,
    proportion lists, parenthesised lists).

Keeping all of this together means the attribute-application code in
``attributes.py`` reads as plain assignments and never re-implements parsing.
"""
from __future__ import annotations

import re

from omr.generation import (
    BubbleSize,
    Color,
    FontStyle,
    Orientation,
    PaperSize,
    RotationPointPosition,
)
from omr.generation.config.enums import (
    AlignmentEnum,
    BorderType,
    BubbleType,
    ContainerTypeEnum,
    ContentType,
    GridHeaderTypeEnum,
)
from omr.generation.overflowactions import Clip, NoClip, Wrap


def _enum_lookup(enum_cls) -> dict:
    """Build a ``lowercased-member-name -> member`` map for an enum type."""
    return {member.name.lower(): member for member in enum_cls}


# ── keyword -> enum member lookup tables ─────────────────────────────────────
# Full-enum tables are generated from the enum itself so they never drift from
# the source; the short, hand-written tables only list the keywords the markup
# DSL actually accepts for that attribute.

COLOR_LUT = _enum_lookup(Color)
PAPER_LUT = _enum_lookup(PaperSize)
ROTATION_LUT = _enum_lookup(RotationPointPosition)

BUBBLE_SIZE_LUT = {
    "extrasmall": BubbleSize.Extrasmall,
    "small": BubbleSize.Small,
    "normal": BubbleSize.Normal,
    "large": BubbleSize.Large,
    "extralarge": BubbleSize.Extralarge,
}
BUBBLE_TYPE_LUT = {
    "round": BubbleType.Round,
    "square": BubbleType.Square,
}
ALIGN_LUT = {
    "left": AlignmentEnum.Left,
    "center": AlignmentEnum.Center,
    "right": AlignmentEnum.Right,
}
ORIENTATION_LUT = {
    "vertical": Orientation.Vertical,
    "horizontal": Orientation.Horizontal,
}
BORDER_LUT = {
    "none": BorderType["None"],  # "None" is a keyword -> functional-API member name
    "square": BorderType.Square,
    "rounded": BorderType.Rounded,
}
CONTENT_LUT = {
    "normal": ContentType.Normal,
    "cells": ContentType.Cells,
}
GRID_HEADER_LUT = {
    "underline": GridHeaderTypeEnum.Underline,
    "square": GridHeaderTypeEnum.Square,
}
CONTAINER_LUT = {
    "normal": ContainerTypeEnum.Normal,
    "footer": ContainerTypeEnum.Footer,
}
OVERFLOW_LUT = {
    "noclip": NoClip,
    "clip": Clip,
    "wrap": Wrap,
}
FONT_STYLE_LUT = {
    "regular": FontStyle.Regular,
    "bold": FontStyle.Bold,
    "italic": FontStyle.Italic,
    "underline": FontStyle.Underline,
    "strikeout": FontStyle.Strikeout,
}

# A parenthesised option group, e.g. ``(A)`` or ``(10)``; used for list values.
_PAREN_ITEM_RE = re.compile(r"\(([^)]*)\)")


# ── scalar coercions ─────────────────────────────────────────────────────────

def as_bool(value: str) -> bool:
    """Parse a markup boolean. True-ish keywords are ``true/1/yes/on``."""
    return value.strip().lower() in ("true", "1", "yes", "on")


def as_int(value: str, default: int = 0) -> int:
    """Parse an integer, tolerating a decimal point (``"3.0"`` -> ``3``).

    Any unparseable text falls back to ``default`` rather than raising, because
    generation reports problems instead of throwing on bad markup.
    """
    try:
        return int(float(value.strip()))
    except (ValueError, TypeError):
        return default


def as_font_style(value: str) -> FontStyle:
    """Parse a comma-separated font-style flag combination.

    ``FontStyle`` is an ``IntFlag``, so styles OR together: ``"bold,italic"``
    becomes ``FontStyle.Bold | FontStyle.Italic``. An empty / unrecognised value
    defaults to ``FontStyle.Regular``.
    """
    result = FontStyle.undefined
    for token in value.split(","):
        key = token.strip().lower()
        if key in FONT_STYLE_LUT:
            result |= FONT_STYLE_LUT[key]
    return result if result != FontStyle.undefined else FontStyle.Regular


def as_proportions(value: str) -> list[int]:
    """Parse a column-proportion list written as ``"30-30-40"`` (optional ``%``)
    into ``[30, 30, 40]``."""
    out: list[int] = []
    for part in value.split("-"):
        part = part.strip().rstrip("%").strip()
        if part:
            out.append(as_int(part))
    return out


def as_paren_list(value: str) -> list[str]:
    """Parse a list of answer tokens.

    Preferred form is parenthesised, ``"(A) (B) (C)"`` -> ``["A", "B", "C"]``.
    If no parentheses are present the value is split on whitespace instead, so
    ``"A B C"`` also works.
    """
    items = [match.strip() for match in _PAREN_ITEM_RE.findall(value)]
    if items:
        return items
    return [token for token in value.split() if token]


def bubble_value(value: str) -> str:
    """Normalise a single bubble's returned value.

    The markup keywords ``yes`` / ``no`` map to the single-character results
    ``Y`` / ``N`` (the Aspose convention); everything else is returned trimmed.
    """
    low = value.strip().lower()
    if low == "yes":
        return "Y"
    if low == "no":
        return "N"
    return value.strip()
