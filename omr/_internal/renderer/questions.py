"""Bubble-bearing element handlers.

These draw the recognizable elements -- ``answer_sheet``, ``choicebox``,
``checkbox``, ``grid`` and ``composite_grid`` -- and, as a side effect, record
each one into the page descriptor in the uniform element/field/bubble shape the
recognizer later samples.

Pixel arithmetic here is load-bearing: the box ``draw_bubble`` returns is the
exact rectangle the recognizer samples, so the step/spacing expressions must not
drift. Each handler returns the new vertical cursor; absolutely-positioned grids
return the incoming ``y`` so they do not advance the flow.
"""
from __future__ import annotations

from omr._internal import omr_format
from omr._internal.renderer import support
from omr._internal.renderer.bubbles import draw_bubble
from omr._internal.renderer.constants import AUTO_LETTERS
from omr._internal.renderer.context import RenderContext
from omr._internal.renderer.text import draw_paragraph
from omr.generation import Color, Orientation
from omr.generation.config.enums import (
    AlignmentEnum,
    BubbleType,
    ConfigType,
    GridHeaderTypeEnum,
)


def _answers_values(element) -> list[str]:
    """The per-line answer glyphs for an answer sheet: the explicit
    ``AnswersValues`` if given, else auto letters A, B, C ... of length
    ``AnswersCount``."""
    values = list(getattr(element, "AnswersValues", []) or [])
    count = getattr(element, "AnswersCount", len(values))
    if not values:
        values = AUTO_LETTERS[:count]
    return values


def layout_answer_sheet(ctx: RenderContext, element, x: int, y: int, width: int) -> int:
    """Draw a numbered question/answer bubble matrix.

    ``ElementsCount`` numbered lines are laid out across ``ColumnsCount``
    columns; each line gets a number label and one bubble per answer value, and
    becomes one field (``<Name><id>``) in the descriptor. The running auto id is
    advanced past the highest number used so a later auto-numbered sheet does not
    collide.
    """
    line_count = getattr(element, "ElementsCount", 0)
    if not line_count:
        return y
    values = _answers_values(element)
    columns = max(1, getattr(element, "ColumnsCount", 4))
    diameter = support.resolve_bubble_diameter(element, ctx.settings)
    bubble_type = BubbleType(getattr(element, "BubbleType", BubbleType.Round))
    bubble_color = support.resolve_color(ctx.settings.BubbleColor)
    v_margin = getattr(element, "VerticalMargin", 0)
    font, _ = support.resolve_font(element, ctx.settings)

    start_id = getattr(element, "StartId", 0) or ctx.auto_id
    multiselect = element.Multiselect if element.Multiselect is not None else ctx.settings.Multiselect

    step = diameter + max(14, int(diameter * 0.55))
    line_h = max(diameter, support.line_height(font)) + v_margin + int(diameter * 0.25)
    label_w = support.text_size(font, f"{start_id + line_count - 1}.")[0] + 16
    column_gap = 50
    column_w = (width - column_gap * (columns - 1)) / columns
    per_column = -(-line_count // columns)  # ceil division

    descriptor_element = omr_format.new_element(
        ConfigType.AnswerSheet.name, element.Name, omr_format.GROUPING_FIELD, multiselect, -1)

    max_bottom = y
    for index in range(line_count):
        question_id = start_id + index
        column = index // per_column
        row = index % per_column
        line_x = x + column * (column_w + column_gap)
        line_y = y + row * line_h

        # Number label at the left of the line.
        label = f"{question_id}."
        _, label_h = support.text_size(font, label)
        ctx.draw.text((line_x, line_y + (diameter - label_h) / 2), label, font=font, fill=(0, 0, 0))

        field = omr_format.new_field(f"{element.Name}{question_id}", ctx.next_sort_weight())
        bubbles_x = line_x + label_w
        for answer_index, value in enumerate(values):
            cx = bubbles_x + answer_index * step + diameter / 2
            cy = line_y + diameter / 2
            box = draw_bubble(ctx, cx, cy, diameter, bubble_type, bubble_color, glyph=value)
            field["Bubbles"].append(omr_format.new_bubble(value, box))
        descriptor_element["Fields"].append(field)
        max_bottom = max(max_bottom, line_y + line_h)

    ctx.page_desc["Elements"].append(descriptor_element)
    # Always advance the running id past the highest number used, so a later
    # auto-numbered answer_sheet continues instead of colliding with these ids.
    ctx.auto_id = max(ctx.auto_id, start_id + line_count)
    return max_bottom + 10


def layout_choicebox(ctx: RenderContext, element, x: int, y: int, width: int) -> int:
    """Draw one question with a row (wrapping to more rows) of option bubbles.

    The question text is drawn first, then each option as a bubble + label,
    flowing left to right and wrapping when the next option would exceed
    ``width``. The whole choicebox is one field in the descriptor.
    """
    font, _ = support.resolve_font(element, ctx.settings)
    color = support.resolve_color(getattr(element, "Color", Color.undefined))
    diameter = support.resolve_bubble_diameter(element, ctx.settings)
    bubble_color = support.resolve_color(ctx.settings.BubbleColor)
    multiselect = element.Multiselect if element.Multiselect is not None else ctx.settings.Multiselect

    # DisplayQuestionNumber is accepted for API fidelity but not acted on here:
    # the question text is expected to carry its own number in the markup.
    question = element.QuestionText or element.Name
    cursor = draw_paragraph(ctx, question, x, y, width, font, color,
                            getattr(element, "TextAlignment", AlignmentEnum.undefined))
    cursor += 6

    options = [child for child in (getattr(element, "Children", []) or [])
               if child.Type == ConfigType.ChoiceBoxAnswer]
    label_pad = 14
    line_h = max(diameter, support.line_height(font)) + 14
    row_start_x = x + 20
    row_y = cursor
    cursor_x = row_start_x

    descriptor_element = omr_format.new_element(
        ConfigType.ChoiceBox.name, element.Name, omr_format.GROUPING_FIELD, multiselect, -1)
    field = omr_format.new_field(element.Name, ctx.next_sort_weight())

    for index, option in enumerate(options):
        if option.BubbleValue:
            glyph = option.BubbleValue
        elif index < len(AUTO_LETTERS):
            glyph = AUTO_LETTERS[index]
        else:
            glyph = "?"
        label = option.Name
        label_w = support.text_size(font, label)[0]
        cell_w = diameter + label_pad + label_w + 40
        # Wrap to the next row when this option would run past the right edge.
        if cursor_x + cell_w > x + width and cursor_x > row_start_x:
            cursor_x = row_start_x
            row_y += line_h
        cx = cursor_x + diameter / 2
        cy = row_y + diameter / 2
        box = draw_bubble(ctx, cx, cy, diameter, BubbleType.Round, bubble_color, glyph=glyph)
        _, label_h = support.text_size(font, label)
        ctx.draw.text((cursor_x + diameter + label_pad, row_y + (diameter - label_h) / 2),
                      label, font=font, fill=color)
        field["Bubbles"].append(omr_format.new_bubble(option.Name, box))
        cursor_x += cell_w

    descriptor_element["Fields"].append(field)
    ctx.page_desc["Elements"].append(descriptor_element)
    return row_y + line_h + 6


def layout_checkbox(ctx: RenderContext, element, x: int, y: int, width: int) -> int:
    """Draw a labelled column of blank boxes, each accepting any mark.

    A checkbox carries a low fill ``Threshold`` (default 3%) so even a tick is
    detected. The whole group is one field in the descriptor.
    """
    font, _ = support.resolve_font(element, ctx.settings)
    diameter = support.resolve_bubble_diameter(element, ctx.settings)
    bubble_type = BubbleType(getattr(element, "BubbleType", BubbleType.Square))
    bubble_color = support.resolve_color(ctx.settings.BubbleColor)
    multiselect = element.Multiselect if element.Multiselect is not None else ctx.settings.Multiselect
    threshold = getattr(element, "Threshold", 3)

    cursor = y
    if not getattr(element, "HideName", False) and element.Name:
        cursor = draw_paragraph(ctx, element.Name, x, cursor, width, font, (0, 0, 0),
                                AlignmentEnum.undefined) + 6

    boxes = [child for child in (getattr(element, "Children", []) or [])
             if child.Type == ConfigType.Content]
    line_h = max(diameter, support.line_height(font)) + 14
    descriptor_element = omr_format.new_element(
        ConfigType.CheckBox.name, element.Name, omr_format.GROUPING_FIELD, multiselect, threshold)
    field = omr_format.new_field(element.Name, ctx.next_sort_weight())
    for box_option in boxes:
        cx = x + 20 + diameter / 2
        cy = cursor + diameter / 2
        box = draw_bubble(ctx, cx, cy, diameter, bubble_type, bubble_color, glyph="")
        _, label_h = support.text_size(font, box_option.Name)
        ctx.draw.text((x + 20 + diameter + 14, cursor + (diameter - label_h) / 2),
                      box_option.Name, font=font, fill=(0, 0, 0))
        field["Bubbles"].append(omr_format.new_bubble(box_option.Name, box))
        cursor += line_h
    descriptor_element["Fields"].append(field)
    ctx.page_desc["Elements"].append(descriptor_element)
    return cursor + 6


def _grid_start(element, ctx: RenderContext, x: int, y: int, width: int, span_w: float,
                font, name: str):
    """Resolve where a grid-like element starts drawing.

    Returns ``(start_x, cursor_after_name, is_absolute)``. An absolute
    ``XPosition``/``YPosition`` wins; otherwise the grid is aligned within
    ``width`` by ``GridAlignment``. When ``name`` is non-empty it is drawn as a
    hint above the grid and the cursor advances past it.
    """
    is_absolute = getattr(element, "XPosition", -1) is not None and element.XPosition >= 0
    if is_absolute:
        start_x = element.XPosition
        start_y = element.YPosition if getattr(element, "YPosition", -1) >= 0 else y
    else:
        start_x = support.align_x(getattr(element, "GridAlignment", AlignmentEnum.undefined),
                                  x, width, int(span_w))
        start_y = y
    cursor = start_y
    if name:
        cursor = draw_paragraph(ctx, name, start_x, cursor, max(width, int(span_w)), font,
                                (0, 0, 0), AlignmentEnum.undefined) + 4
    return start_x, cursor, is_absolute


def _draw_grid_header(ctx: RenderContext, element, start_x: float, cursor: float,
                      span_w: float) -> float:
    """Draw a grid's header (a square box or an underline rule) and return the
    cursor below it."""
    header_type = getattr(element, "HeaderType", GridHeaderTypeEnum.Underline)
    header_color = support.resolve_color(getattr(element, "HeaderBorderColor", Color.Black))
    header_size = max(1, getattr(element, "HeaderBorderSize", 3))
    if header_type == GridHeaderTypeEnum.Square:
        ctx.draw.rectangle([start_x, cursor, start_x + span_w, cursor + 40],
                           outline=header_color, width=header_size)
    else:  # Underline (default): a hand-writing rule across the grid width
        ctx.draw.line([start_x, cursor + 38, start_x + span_w, cursor + 38],
                      fill=header_color, width=header_size)
    return cursor + 46


def layout_grid(ctx: RenderContext, element, x: int, y: int, width: int) -> int:
    """Draw a digit grid: ``SectionsCount`` digits x ``OptionsCount`` (0-9)
    bubbles, merged into one recognized value.

    Spec: horizontal orientation (the default) makes each digit a COLUMN of
    option bubbles; vertical makes each digit a ROW.
    """
    sections = max(1, getattr(element, "SectionsCount", 8))
    options = max(1, getattr(element, "OptionsCount", 10))
    diameter = support.resolve_bubble_diameter(element, ctx.settings)
    bubble_type = BubbleType(getattr(element, "BubbleType", BubbleType.Round))
    bubble_color = support.resolve_color(ctx.settings.BubbleColor)
    digit_is_column = getattr(element, "GridOrientation", Orientation.Horizontal) != Orientation.Vertical
    v_margin = max(0, getattr(element, "VerticalMargin", 0))
    font, _ = support.resolve_font(element, ctx.settings)
    values = [str(i) for i in range(options)]

    step = diameter + max(14, int(diameter * 0.5)) + v_margin
    span_w = (sections if digit_is_column else options) * step
    start_x, cursor, is_absolute = _grid_start(element, ctx, x, y, width, span_w, font, element.Name)
    cursor = _draw_grid_header(ctx, element, start_x, cursor, span_w)

    descriptor_element = omr_format.new_element(
        ConfigType.Grid.name, element.Name, omr_format.GROUPING_ELEMENT, False, -1)
    for section in range(sections):
        field = omr_format.new_field(f"{element.Name}_{section + 1}", ctx.next_sort_weight())
        for option in range(options):
            if digit_is_column:
                cx = start_x + section * step + diameter / 2
                cy = cursor + option * step + diameter / 2
            else:
                cx = start_x + option * step + diameter / 2
                cy = cursor + section * step + diameter / 2
            box = draw_bubble(ctx, cx, cy, diameter, bubble_type, bubble_color, glyph=values[option])
            field["Bubbles"].append(omr_format.new_bubble(values[option], box))
        descriptor_element["Fields"].append(field)
    ctx.page_desc["Elements"].append(descriptor_element)

    if is_absolute:
        return y
    span_h = (options if digit_is_column else sections) * step
    return cursor + span_h + 10


def layout_composite_grid(ctx: RenderContext, element, x: int, y: int, width: int) -> int:
    """Draw a flexible grid with custom symbols; marks merge into one value.

    Each column holds the (optional) prepended ``ExtraRow`` symbols followed by
    the common ``Values`` (default 0-9). An empty ``ExtraRow`` cell leaves a gap
    (no bubble). ``DisplayHint`` toggles both the name hint and the in-bubble
    glyphs.
    """
    columns = max(1, getattr(element, "ColumnsCount", 5))
    base_values = list(getattr(element, "Values", []) or [])
    if not base_values:
        base_values = [str(i) for i in range(10)]
    extra_rows = getattr(element, "ExtraRow", []) or []  # list of rows, each a list of symbols
    diameter = support.resolve_bubble_diameter(element, ctx.settings)
    bubble_type = BubbleType(getattr(element, "BubbleType", BubbleType.Round))
    bubble_color = support.resolve_color(ctx.settings.BubbleColor)
    digit_is_column = getattr(element, "GridOrientation", Orientation.Horizontal) != Orientation.Vertical
    v_margin = max(0, getattr(element, "VerticalMargin", 0))
    show_hint = getattr(element, "DisplayHint", True)
    font, _ = support.resolve_font(element, ctx.settings)

    step = diameter + max(14, int(diameter * 0.5)) + v_margin

    # Per-column slots: the extra rows (prepended) then the common Values. Each
    # slot is ``(symbol, present)``; a "" extra-row cell is absent (no bubble).
    column_symbols: list[list[tuple[str, bool]]] = []
    for column in range(columns):
        slots: list[tuple[str, bool]] = []
        for extra_row in extra_rows:
            symbol = extra_row[column] if column < len(extra_row) else ""
            slots.append((symbol, symbol != ""))
        for value in base_values:
            slots.append((value, True))
        column_symbols.append(slots)
    max_slots = max((len(slots) for slots in column_symbols), default=0)

    span_w = (columns if digit_is_column else max_slots) * step
    start_x, cursor, is_absolute = _grid_start(
        element, ctx, x, y, width, span_w, font, element.Name if show_hint else "")

    descriptor_element = omr_format.new_element(
        ConfigType.CompositeGrid.name, element.Name, omr_format.GROUPING_ELEMENT, False, -1)
    for column in range(columns):
        field = omr_format.new_field(f"{element.Name}_{column + 1}", ctx.next_sort_weight())
        for slot_index, (symbol, present) in enumerate(column_symbols[column]):
            if not present:
                continue
            if digit_is_column:
                cx = start_x + column * step + diameter / 2
                cy = cursor + slot_index * step + diameter / 2
            else:
                cx = start_x + slot_index * step + diameter / 2
                cy = cursor + column * step + diameter / 2
            box = draw_bubble(ctx, cx, cy, diameter, bubble_type, bubble_color,
                              glyph=symbol if show_hint else "")
            field["Bubbles"].append(omr_format.new_bubble(symbol, box))
        descriptor_element["Fields"].append(field)
    ctx.page_desc["Elements"].append(descriptor_element)

    if is_absolute:
        return y
    span_h = (max_slots if digit_is_column else columns) * step
    return cursor + span_h + 10
