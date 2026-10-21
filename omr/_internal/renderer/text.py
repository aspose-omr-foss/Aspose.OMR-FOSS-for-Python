"""Text layout handlers (the ``text`` / ``content`` elements) and the shared
paragraph drawer used by bubble elements for their labels.

Each handler returns the new vertical cursor (the y just below what it drew),
which is how the engine stacks elements down the page.
"""
from __future__ import annotations

from omr._internal.renderer import support
from omr._internal.renderer.context import RenderContext
from omr.generation import Color, FontStyle
from omr.generation.config.enums import AlignmentEnum, ContentType


def layout_text(ctx: RenderContext, element, x: int, y: int, width: int) -> int:
    """Draw a ``text`` / ``content`` element (the handler for both config types).

    Normal content is word-wrapped and drawn line by line, honouring alignment
    and underline / strikeout decorations. ``content_type=cells`` draws each
    character in its own box instead (see ``layout_cells``).
    """
    font, style = support.resolve_font(element, ctx.settings)
    color = support.resolve_color(getattr(element, "Color", Color.undefined))
    align = getattr(element, "TextAlignment", None) or getattr(
        element, "Alignment", AlignmentEnum.undefined)
    content_type = getattr(element, "ContentType", ContentType.Normal)
    text = element.Name or ""

    if content_type == ContentType.Cells and text:
        return layout_cells(ctx, text, x, y, width, font, color, align)

    height = support.line_height(font)
    cursor = y
    for line in support.wrap_text(font, text, width):
        line_w = support.text_size(font, line)[0]
        line_x = support.align_x(align, x, width, line_w)
        ctx.draw.text((line_x, cursor), line, font=font, fill=color)
        if int(style) & int(FontStyle.Underline):
            ctx.draw.line([line_x, cursor + height - 2, line_x + line_w, cursor + height - 2],
                          fill=color, width=2)
        if int(style) & int(FontStyle.Strikeout):
            ctx.draw.line([line_x, cursor + height // 2, line_x + line_w, cursor + height // 2],
                          fill=color, width=2)
        cursor += height
    return cursor


def layout_cells(ctx: RenderContext, text: str, x: int, y: int, width: int, font,
                 color: tuple[int, int, int], align: AlignmentEnum) -> int:
    """Draw one boxed cell per character (``content_type=cells``).

    Every character sits centred in a square cell; the whole run is aligned as a
    block within ``width``. Blank characters leave their cell empty.
    """
    cell = max(support.line_height(font) + 10, 36)
    total = len(text) * cell
    start_x = support.align_x(align, x, width, total)
    for index, char in enumerate(text):
        cell_x = start_x + index * cell
        ctx.draw.rectangle([cell_x, y, cell_x + cell, y + cell], outline=color, width=2)
        if char.strip():
            char_w, char_h = support.text_size(font, char)
            bbox = font.getbbox(char)
            ctx.draw.text(
                (cell_x + cell / 2 - char_w / 2 - bbox[0], y + cell / 2 - char_h / 2 - bbox[1]),
                char, font=font, fill=color)
    return y + cell + 6


def draw_paragraph(ctx: RenderContext, text: str, x: int, y: int, width: int, font,
                   color: tuple[int, int, int], align: AlignmentEnum) -> int:
    """Draw wrapped, aligned text with no font decorations.

    Used by bubble elements to render their question text / labels above the
    bubbles. Returns the cursor below the last line.
    """
    height = support.line_height(font)
    cursor = y
    for line in support.wrap_text(font, text, width):
        line_w = support.text_size(font, line)[0]
        line_x = support.align_x(align, x, width, line_w)
        ctx.draw.text((line_x, cursor), line, font=font, fill=color)
        cursor += height
    return cursor
