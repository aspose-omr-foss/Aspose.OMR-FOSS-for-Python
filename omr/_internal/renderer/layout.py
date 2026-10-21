"""Layout containers and non-bubble leaves.

Handlers here arrange *other* elements (``container``, ``block``,
``positioned_block``) or draw a simple leaf (``empty_line``, ``image``).
Containers recurse into their children through ``ctx.layout_child`` so the
engine stays the single owner of type dispatch.

Every handler takes ``(ctx, element, x, y, width)`` and returns the new vertical
cursor. Absolutely-positioned elements return the *incoming* ``y`` unchanged, so
they do not advance the normal top-to-bottom flow.
"""
from __future__ import annotations

from omr._internal.renderer import support
from omr._internal.renderer.context import RenderContext
from omr.generation import Color
from omr.generation.config.enums import AlignmentEnum, BorderType


def layout_container(ctx: RenderContext, element, x: int, y: int, width: int) -> int:
    """Arrange child blocks into columns.

    Column widths come from ``Proportions`` (percent-like weights) when given,
    otherwise an even split across ``ColumnsCount`` columns. Each child drops
    into the column named by its 1-based ``Column`` attribute. The container's
    height is the tallest column plus the bottom margin.
    """
    children = getattr(element, "Children", []) or []
    proportions = getattr(element, "Proportions", []) or []
    columns = len(proportions) if proportions else max(1, getattr(element, "ColumnsCount", 1))

    if proportions:
        total = sum(proportions) or 100
        fractions = [p / total for p in proportions]
    else:
        fractions = [1.0 / columns] * columns

    gap = getattr(element, "BlockRightMargin", 40)
    top_pad = getattr(element, "BlockTopPadding", 20)
    bottom_margin = getattr(element, "BlockBottomMargin", 20)

    available = width - gap * (columns - 1)
    column_widths = [max(1, int(available * fraction)) for fraction in fractions]

    # Left edge of each column, laid out left to right with ``gap`` between.
    column_x: list[int] = []
    cursor_x = x
    for column_width in column_widths:
        column_x.append(cursor_x)
        cursor_x += column_width + gap

    # Independent vertical cursor per column; children stack within their column.
    start_y = y + top_pad
    column_y = [start_y] * columns
    for child in children:
        column_index = max(1, getattr(child, "Column", 1)) - 1
        column_index = min(column_index, columns - 1)
        column_y[column_index] = ctx.layout_child(
            child, column_x[column_index], column_y[column_index], column_widths[column_index])
    return max(column_y) + bottom_margin


def layout_block(ctx: RenderContext, element, x: int, y: int, width: int) -> int:
    """A padded, optionally bordered box that stacks its children vertically.

    The block's height is the larger of its explicit ``Height`` and the measured
    content height (plus padding). Only the border is drawn here.
    """
    h_pad = getattr(element, "HorizontalPadding", 20)
    v_pad = getattr(element, "VerticalPadding", 20)
    inner_x = x + h_pad
    inner_w = width - 2 * h_pad
    inner_y = y + v_pad

    cursor = inner_y
    for child in getattr(element, "Children", []) or []:
        cursor = ctx.layout_child(child, inner_x, cursor, inner_w)
    content_h = cursor - inner_y
    block_h = max(getattr(element, "Height", 0) or 0, content_h + 2 * v_pad)

    # Note: BlockConfig.BackgroundColor is accepted for API fidelity but not
    # painted in the core slice (filling behind auto-height content would need a
    # pre-measure pass). Only the border is drawn below.
    border_type = getattr(element, "BorderType", None)
    try:
        is_bordered = border_type is not None and border_type != BorderType["None"]
    except Exception:
        is_bordered = False
    if is_bordered:
        border_color = support.resolve_color(getattr(element, "BorderColor", Color.Black))
        border_size = max(1, getattr(element, "BorderSize", 3))
        ctx.draw.rectangle([x, y, x + width, y + block_h], outline=border_color, width=border_size)
    return y + block_h


def layout_positioned_block(ctx: RenderContext, element, x: int, y: int, width: int) -> int:
    """Place children at an absolute ``(XPosition, YPosition)``.

    Absolute placement does not advance the outer flow, so the incoming ``y`` is
    returned unchanged.
    """
    pos_x = getattr(element, "XPosition", 0)
    pos_y = getattr(element, "YPosition", 0)
    pos_w = getattr(element, "Width", 0) or (width - (pos_x - x) if pos_x >= x else width)
    cursor = pos_y
    for child in getattr(element, "Children", []) or []:
        cursor = ctx.layout_child(child, pos_x, cursor, pos_w)
    return y  # absolute placement: do not advance the outer cursor


def layout_empty_line(ctx: RenderContext, element, x: int, y: int, width: int) -> int:
    """Advance the cursor by ``Height`` px, or one default line when unset."""
    from omr._internal import fonts
    from omr.generation import FontStyle

    height = getattr(element, "Height", 0)
    if not height:
        default_font = fonts.get_font(ctx.settings.FontFamily, ctx.settings.FontSize,
                                      int(FontStyle.Regular))
        height = support.line_height(default_font)
    return y + int(height)


def layout_image(ctx: RenderContext, element, x: int, y: int, width: int) -> int:
    """Paste a named image, scaling to ``Width`` / ``Height`` (aspect-preserving
    when only one is given). A missing image draws a placeholder box instead.

    With an absolute ``XPosition`` the image is pasted there and the flow cursor
    is left unchanged; otherwise it is aligned within ``width`` and the cursor
    advances below it.
    """
    import io

    from PIL import Image

    data = resolve_image_bytes(ctx, element.Name)
    if data is None:
        # Missing image: draw a placeholder box, advance.
        placeholder_h = element.Height or 160
        ctx.draw.rectangle([x, y, x + (element.Width or 160), y + placeholder_h],
                           outline=(0, 0, 0), width=2)
        return y + placeholder_h + 10

    picture = Image.open(io.BytesIO(data)).convert("RGBA")
    draw_w = element.Width or picture.width
    draw_h = element.Height or picture.height
    if element.Width and not element.Height:
        draw_h = int(picture.height * (draw_w / picture.width))
    elif element.Height and not element.Width:
        draw_w = int(picture.width * (draw_h / picture.height))
    picture = picture.resize((max(1, int(draw_w)), max(1, int(draw_h))))

    is_absolute = getattr(element, "XPosition", -1) is not None and element.XPosition >= 0
    if is_absolute:
        paste_x = element.XPosition
        paste_y = element.YPosition if element.YPosition >= 0 else y
        ctx.image.paste(picture, (int(paste_x), int(paste_y)), picture)
        return y  # absolute placement does not advance the cursor

    paste_x = support.align_x(getattr(element, "ImageAlign", AlignmentEnum.undefined),
                              x, width, int(draw_w))
    ctx.image.paste(picture, (int(paste_x), int(y)), picture)
    return y + int(draw_h) + 10


def resolve_image_bytes(ctx: RenderContext, name: str) -> bytes | None:
    """Find an image's bytes by name: first the in-memory image map, then any
    file on ``settings.ImagesPaths`` whose basename (or full path) matches."""
    import os

    if name in ctx.images:
        return ctx.images[name]
    for path in ctx.settings.ImagesPaths or []:
        if os.path.basename(path) == name or path == name:
            try:
                with open(path, "rb") as handle:
                    return handle.read()
            except OSError:
                return None
    return None
