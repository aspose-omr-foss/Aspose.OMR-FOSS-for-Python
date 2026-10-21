"""Draw a single answer bubble and report its box for the ``.omr`` descriptor.

The box this returns is the bubble's full bounding rectangle (outline included).
The recognizer does not sample that rectangle directly: it insets it
(``geometry.sample_roi`` trims ``SAMPLE_INSET_RATIO`` off each side) so the
printed outline is never counted as ink. Because the drawer records the box and
the sampler derives its ROI from that same box through the shared ``geometry``
module, the sampled region always lands inside the drawn bubble by construction
-- the two cannot drift apart.
"""
from __future__ import annotations

from omr._internal import fonts
from omr._internal.renderer import support
from omr._internal.renderer.constants import GLYPH_GRAY
from omr._internal.renderer.context import RenderContext
from omr.generation import FontStyle
from omr.generation.config.enums import BubbleType


def draw_bubble(ctx: RenderContext, cx: float, cy: float, diameter: int,
                bubble_type: BubbleType, color: tuple[int, int, int],
                glyph: str = "") -> list[float]:
    """Draw an empty bubble (outline only) centred at ``(cx, cy)``.

    A round bubble is an ellipse, a square bubble a rectangle. An optional light
    guide ``glyph`` (e.g. the option letter) is drawn centred inside; it is
    deliberately light grey so the recognizer never counts it as a mark.

    Returns the ``[x, y, w, h]`` bounding box (top-left origin) recorded in the
    descriptor.
    """
    radius = diameter / 2.0
    x0, y0 = cx - radius, cy - radius
    x1, y1 = cx + radius, cy + radius
    outline_width = max(2, diameter // 22)

    if bubble_type == BubbleType.Square:
        ctx.draw.rectangle([x0, y0, x1, y1], outline=color, width=outline_width)
    else:
        ctx.draw.ellipse([x0, y0, x1, y1], outline=color, width=outline_width)

    if glyph:
        glyph_font = fonts.get_font(ctx.settings.FontFamily, max(10, int(diameter * 0.46)),
                                    int(FontStyle.Regular))
        glyph_w, glyph_h = support.text_size(glyph_font, glyph)
        glyph_bbox = glyph_font.getbbox(glyph)
        glyph_x = cx - glyph_w / 2.0 - glyph_bbox[0]
        glyph_y = cy - glyph_h / 2.0 - glyph_bbox[1]
        ctx.draw.text((glyph_x, glyph_y), glyph, font=glyph_font, fill=GLYPH_GRAY)

    return [x0, y0, float(diameter), float(diameter)]
