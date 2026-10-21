"""Apply a single ``key=value`` attribute to the element it belongs to.

The markup for every element type accepts a different set of attribute keys.
Rather than one long ``isinstance`` ladder, each element type has its own small
applier function, and ``apply_attr`` dispatches to it by the element's concrete
type (the element config classes are mutually exclusive leaf types, so an exact
``type(...)`` match reproduces the original ``isinstance`` behaviour precisely).

Unknown keys for an element are silently ignored: generation reports problems
via ``ErrorCode`` rather than throwing, and an unrecognised attribute should not
abort an otherwise valid form.
"""
from __future__ import annotations

from omr.generation import (
    BubbleSize,
    Color,
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
from omr.generation.config.elements import (
    AnswerSheetConfig,
    ChoiceBoxAnswerConfig,
    ChoiceBoxConfig,
    CompositeGridConfig,
    ContentConfig,
    EmptyLineConfig,
    GridConfig,
    ImageConfig,
    TextConfig,
)
from omr.generation.config.elements.parents import (
    BlockConfig,
    CheckBoxConfig,
    ContainerConfig,
    PageConfig,
    PositionedBlockConfig,
)
from omr._internal.markup_parser import values
from omr._internal.markup_parser.values import (
    as_bool,
    as_int,
    as_font_style,
    as_paren_list,
    as_proportions,
    bubble_value,
)


def _apply_common_font(element, key: str, value: str) -> bool:
    """Apply a font / colour attribute shared by all text-bearing elements.

    Returns ``True`` if ``key`` was one of the shared attributes (and was
    applied), ``False`` otherwise so the caller can try element-specific keys.
    """
    if key == "font_family":
        element.FontFamily = value
    elif key == "font_size":
        element.FontSize = as_int(value)
    elif key == "font_style":
        element.FontStyle = as_font_style(value)
    elif key == "color":
        element.Color = values.COLOR_LUT.get(value.strip().lower(), Color.Black)
    else:
        return False
    return True


def _apply_page(element: PageConfig, key: str, value: str) -> None:
    if key == "orientation":
        element.Orientation = values.ORIENTATION_LUT.get(value.lower(), Orientation.undefined)
    elif key == "paper_size":
        element.PaperSize = values.PAPER_LUT.get(value.lower(), PaperSize.undefined)
    elif key == "left_margin":
        element.LeftMargin = as_int(value)
    elif key == "right_margin":
        element.RightMargin = as_int(value)
    elif key == "rotation_point_position":
        element.RotationPointPosition = values.ROTATION_LUT.get(
            value.lower(), RotationPointPosition.TopRight1)


def _apply_container(element: ContainerConfig, key: str, value: str) -> None:
    if key == "columns_count":
        element.ColumnsCount = as_int(value, 1)
    elif key == "columns_proportions":
        element.Proportions = as_proportions(value)
    elif key == "type":
        element.ContainerType = values.CONTAINER_LUT.get(value.lower(), ContainerTypeEnum.Normal)
    elif key == "block_right_margin":
        element.BlockRightMargin = as_int(value)
    elif key == "block_bottom_margin":
        element.BlockBottomMargin = as_int(value)
    elif key == "block_top_padding":
        element.BlockTopPadding = as_int(value)
    elif key == "sync_children_height":
        element.SyncBlockHeight = as_bool(value)


def _apply_block(element: BlockConfig, key: str, value: str) -> None:
    if key == "column":
        element.Column = as_int(value, 1)
    elif key == "border":
        element.BorderType = values.BORDER_LUT.get(value.lower(), BorderType["None"])
    elif key == "border_size":
        element.BorderSize = as_int(value)
    elif key == "border_color":
        element.BorderColor = values.COLOR_LUT.get(value.lower(), Color.Black)
    elif key == "is_clipped":
        element.IsClipped = as_bool(value)
    elif key == "background_color":
        element.BackgroundColor = values.COLOR_LUT.get(value.lower(), Color.undefined)
    elif key == "height":
        element.Height = as_int(value)
    elif key == "horizontal_padding":
        element.HorizontalPadding = as_int(value)
    elif key == "vertical_padding":
        element.VerticalPadding = as_int(value)
    elif key == "overflow":
        overflow_factory = values.OVERFLOW_LUT.get(value.lower(), values.NoClip)
        element.Overflow = overflow_factory()


def _apply_positioned_block(element: PositionedBlockConfig, key: str, value: str) -> None:
    if key == "x":
        element.XPosition = as_int(value)
    elif key == "y":
        element.YPosition = as_int(value)
    elif key == "width":
        element.Width = as_int(value)
    elif key == "height":
        element.Height = as_int(value)


def _apply_text_like(element, key: str, value: str) -> None:
    """Attributes shared by ``TextConfig`` and ``ContentConfig``.

    They differ only in where ``align`` lands (content uses ``Alignment``, text
    uses ``TextAlignment``) and in that ``content_type`` applies to content only.
    """
    if _apply_common_font(element, key, value):
        return
    if key == "align":
        alignment = values.ALIGN_LUT.get(value.lower(), AlignmentEnum.undefined)
        if isinstance(element, ContentConfig):
            element.Alignment = alignment
        else:
            element.TextAlignment = alignment
    elif key == "content_type" and isinstance(element, ContentConfig):
        element.ContentType = values.CONTENT_LUT.get(value.lower(), ContentType.Normal)


def _apply_empty_line(element: EmptyLineConfig, key: str, value: str) -> None:
    if key == "height":
        element.Height = as_int(value)


def _apply_image(element: ImageConfig, key: str, value: str) -> None:
    if key == "width":
        element.Width = as_int(value)
    elif key == "height":
        element.Height = as_int(value)
    elif key == "x":
        element.XPosition = as_int(value)
    elif key == "y":
        element.YPosition = as_int(value)
    elif key == "align":
        element.ImageAlign = values.ALIGN_LUT.get(value.lower(), AlignmentEnum.undefined)


def _apply_choicebox(element: ChoiceBoxConfig, key: str, value: str) -> None:
    if _apply_common_font(element, key, value):
        return
    if key == "align":
        element.TextAlignment = values.ALIGN_LUT.get(value.lower(), AlignmentEnum.undefined)
    elif key == "display_number":
        element.DisplayQuestionNumber = as_bool(value)
    elif key == "multiselect":
        element.Multiselect = as_bool(value)


def _apply_choicebox_answer(element: ChoiceBoxAnswerConfig, key: str, value: str) -> None:
    if _apply_common_font(element, key, value):
        return
    if key == "bubble_value":
        element.BubbleValue = bubble_value(value)
    elif key == "align":
        element.TextAlignment = values.ALIGN_LUT.get(value.lower(), AlignmentEnum.undefined)
    elif key == "row_index":
        element.RowIndex = as_int(value)


def _apply_checkbox(element: CheckBoxConfig, key: str, value: str) -> None:
    if _apply_common_font(element, key, value):
        return
    if key == "threshold":
        element.Threshold = as_int(value, 3)
    elif key == "hide_name":
        element.HideName = as_bool(value)
    elif key == "bubble_size":
        element.BubbleSize = values.BUBBLE_SIZE_LUT.get(value.lower(), BubbleSize.undefined)
    elif key == "bubble_type":
        element.BubbleType = values.BUBBLE_TYPE_LUT.get(value.lower(), BubbleType.Square)
    elif key == "multiselect":
        element.Multiselect = as_bool(value)


def _apply_answer_sheet(element: AnswerSheetConfig, key: str, value: str) -> None:
    if key == "elements_count":
        element.ElementsCount = as_int(value)
    elif key == "columns_count":
        element.ColumnsCount = as_int(value, 4)
    elif key == "answers_count":
        element.AnswersCount = as_int(value, 4)
    elif key == "start_id":
        element.StartId = as_int(value)
    elif key == "vertical_margin":
        element.VerticalMargin = as_int(value)
    elif key == "bubble_size":
        element.BubbleSize = values.BUBBLE_SIZE_LUT.get(value.lower(), BubbleSize.undefined)
    elif key == "bubble_type":
        element.BubbleType = values.BUBBLE_TYPE_LUT.get(value.lower(), BubbleType.Round)
    elif key == "answers_list":
        element.AnswersValues = as_paren_list(value)
        element.AnswersCount = len(element.AnswersValues)
    elif key == "column":
        element.Column = as_int(value, 1)
    elif key == "multiselect":
        element.Multiselect = as_bool(value)


def _apply_grid(element: GridConfig, key: str, value: str) -> None:
    if key == "sections_count":
        element.SectionsCount = as_int(value, 8)
    elif key == "options_count":
        element.OptionsCount = as_int(value, 10)
    elif key == "align":
        element.GridAlignment = values.ALIGN_LUT.get(value.lower(), AlignmentEnum.undefined)
    elif key == "orientation":
        element.GridOrientation = values.ORIENTATION_LUT.get(value.lower(), Orientation.Horizontal)
    elif key == "header_type":
        element.HeaderType = values.GRID_HEADER_LUT.get(value.lower(), GridHeaderTypeEnum.Underline)
    elif key == "header_border_size":
        element.HeaderBorderSize = as_int(value)
    elif key == "header_border_color":
        element.HeaderBorderColor = values.COLOR_LUT.get(value.lower(), Color.Black)
    elif key == "vertical_margin":
        element.VerticalMargin = as_int(value)
    elif key == "bubble_size":
        element.BubbleSize = values.BUBBLE_SIZE_LUT.get(value.lower(), BubbleSize.undefined)
    elif key == "bubble_type":
        element.BubbleType = values.BUBBLE_TYPE_LUT.get(value.lower(), BubbleType.Round)
    elif key == "x":
        element.XPosition = as_int(value)
    elif key == "y":
        element.YPosition = as_int(value)
    elif key == "column":
        element.Column = as_int(value, 1)


def _apply_composite_grid(element: CompositeGridConfig, key: str, value: str) -> None:
    if key == "columns_count":
        element.ColumnsCount = as_int(value, 5)
    elif key == "values":
        element.Values = as_paren_list(value)
    elif key == "extra_row":
        element.ExtraRow.append(as_paren_list(value))
    elif key == "align":
        element.GridAlignment = values.ALIGN_LUT.get(value.lower(), AlignmentEnum.undefined)
    elif key == "orientation":
        element.GridOrientation = values.ORIENTATION_LUT.get(value.lower(), Orientation.Horizontal)
    elif key == "rotate":
        element.RotationAngle = as_int(value)
    elif key == "header_type":
        element.HeaderType = values.GRID_HEADER_LUT.get(value.lower(), GridHeaderTypeEnum.Underline)
    elif key == "header_border_size":
        element.HeaderBorderSize = as_int(value)
    elif key == "header_border_color":
        element.HeaderBorderColor = values.COLOR_LUT.get(value.lower(), Color.Black)
    elif key == "vertical_margin":
        element.VerticalMargin = as_int(value)
    elif key == "bubble_size":
        element.BubbleSize = values.BUBBLE_SIZE_LUT.get(value.lower(), BubbleSize.undefined)
    elif key == "bubble_type":
        element.BubbleType = values.BUBBLE_TYPE_LUT.get(value.lower(), BubbleType.Round)
    elif key == "x":
        element.XPosition = as_int(value)
    elif key == "y":
        element.YPosition = as_int(value)
    elif key == "column":
        element.Column = as_int(value, 1)
    elif key == "display_hint":
        element.DisplayHint = as_bool(value)


# Concrete element type -> its attribute applier. ``TextConfig`` and
# ``ContentConfig`` share one applier that branches internally.
_APPLIERS = {
    PageConfig: _apply_page,
    ContainerConfig: _apply_container,
    BlockConfig: _apply_block,
    PositionedBlockConfig: _apply_positioned_block,
    TextConfig: _apply_text_like,
    ContentConfig: _apply_text_like,
    EmptyLineConfig: _apply_empty_line,
    ImageConfig: _apply_image,
    ChoiceBoxConfig: _apply_choicebox,
    ChoiceBoxAnswerConfig: _apply_choicebox_answer,
    CheckBoxConfig: _apply_checkbox,
    AnswerSheetConfig: _apply_answer_sheet,
    GridConfig: _apply_grid,
    CompositeGridConfig: _apply_composite_grid,
}


def apply_attr(element, key: str, value: str) -> None:
    """Apply one ``key=value`` attribute line to ``element`` (in place)."""
    key = key.strip()
    applier = _APPLIERS.get(type(element))
    if applier is not None:
        applier(element, key, value)
