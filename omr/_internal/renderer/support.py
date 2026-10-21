"""Shared styling and text-measurement helpers for the render handlers.

These are the small, pure-ish primitives every handler reuses: resolving an
element's effective font / colour / bubble size against the page defaults, and
measuring / aligning / wrapping text. Keeping them here lets each element
handler read as layout logic rather than bookkeeping.
"""
from __future__ import annotations

from omr._internal import colors, fonts, geometry
from omr.generation import BubbleSize, Color, FontStyle, GlobalPageSettings
from omr.generation.config.enums import AlignmentEnum


def resolve_font(element, settings: GlobalPageSettings):
    """Resolve an element's effective font, falling back to the page defaults.

    An element's own ``FontFamily`` / ``FontSize`` / ``FontStyle`` win when set;
    an empty / zero / ``undefined`` value means "inherit from GlobalPageSettings".
    Returns ``(pil_font, resolved_FontStyle)`` -- the style is returned too so
    the caller can draw underline / strikeout decorations.
    """
    family = getattr(element, "FontFamily", "") or settings.FontFamily
    size = getattr(element, "FontSize", 0) or settings.FontSize
    style = getattr(element, "FontStyle", FontStyle.undefined)
    if not style or style == FontStyle.undefined:
        style = settings.FontStyle
    return fonts.get_font(family, size, int(style)), FontStyle(int(style))


def resolve_color(color_value: Color, default: Color = Color.Black) -> tuple[int, int, int]:
    """Resolve a ``Color`` enum to an ``(R, G, B)`` triple.

    ``None`` / ``undefined`` falls back to ``default``; an unknown name falls
    back to black.
    """
    if color_value is None or color_value == Color.undefined:
        color_value = default
    return colors.COLOR_RGB.get(color_value.name, (0, 0, 0))


def resolve_bubble_diameter(element, settings: GlobalPageSettings) -> int:
    """Resolve an element's bubble diameter in pixels, inheriting the page
    default when the element's ``BubbleSize`` is ``undefined``."""
    bubble_size = getattr(element, "BubbleSize", BubbleSize.undefined)
    if not bubble_size or bubble_size == BubbleSize.undefined:
        bubble_size = settings.BubbleSize
    return geometry.bubble_diameter(bubble_size)


def text_size(font, text: str) -> tuple[int, int]:
    """Measure the ``(width, height)`` of ``text`` in ``font`` (0x0 for empty)."""
    if not text:
        return (0, 0)
    bbox = font.getbbox(text)
    return (bbox[2] - bbox[0], bbox[3] - bbox[1])


def line_height(font) -> int:
    """One line's height for ``font`` (ascent + descent), with a fallback for
    the rare default font that exposes no metrics."""
    try:
        ascent, descent = font.getmetrics()
        return ascent + descent
    except Exception:  # pragma: no cover - some default fonts lack metrics
        return text_size(font, "Ag")[1] + 4


def align_x(align: AlignmentEnum, x: int, width: int, content_w: int) -> int:
    """Left edge for ``content_w``-wide content inside ``[x, x + width]`` for the
    given horizontal alignment (Left / undefined keep ``x``)."""
    if align == AlignmentEnum.Center:
        return x + max(0, (width - content_w) // 2)
    if align == AlignmentEnum.Right:
        return x + max(0, width - content_w)
    return x  # Left / undefined


def wrap_text(font, text: str, max_width: int) -> list[str]:
    """Greedy word-wrap ``text`` to ``max_width`` pixels in ``font``.

    Explicit ``\\n`` breaks are preserved (an empty paragraph yields an empty
    line). A single word wider than ``max_width`` is kept on its own line rather
    than split. ``max_width <= 0`` disables wrapping.
    """
    if max_width <= 0:
        return [text]
    out: list[str] = []
    for paragraph in text.split("\n"):
        if paragraph == "":
            out.append("")
            continue
        words = paragraph.split(" ")
        line = ""
        for word in words:
            trial = word if not line else line + " " + word
            if text_size(font, trial)[0] <= max_width or not line:
                line = trial
            else:
                out.append(line)
                line = word
        out.append(line)
    return out
