"""The render engine: walk a ``TemplateConfig`` tree into page rasters + the
``.omr`` descriptor.

This module owns element-type dispatch (the one ``HANDLERS`` table and
``layout_element``) and the per-page setup loop. Individual element drawing
lives in the sibling handler modules; containers recurse back here through
``ctx.layout_child`` (the context carries ``layout_element`` as its dispatcher),
which keeps the handler modules free of any import back into this engine.
"""
from __future__ import annotations

from omr._internal import geometry, omr_format
from omr._internal.renderer import layout, questions, text
from omr._internal.renderer.context import RenderContext
from omr._internal.renderer.reference_marks import draw_reference_marks
from omr.exceptions import InvalidConfigurationException
from omr.generation import GlobalPageSettings, Orientation, PaperSize
from omr.generation.config import TemplateConfig
from omr.generation.config.enums import ConfigType

# ConfigType -> the handler that draws it. ``Text`` and ``Content`` share one
# handler; the rest map one-to-one.
HANDLERS = {
    ConfigType.Container: layout.layout_container,
    ConfigType.Block: layout.layout_block,
    ConfigType.PositionedBlock: layout.layout_positioned_block,
    ConfigType.Text: text.layout_text,
    ConfigType.Content: text.layout_text,
    ConfigType.EmptyLine: layout.layout_empty_line,
    ConfigType.Image: layout.layout_image,
    ConfigType.AnswerSheet: questions.layout_answer_sheet,
    ConfigType.ChoiceBox: questions.layout_choicebox,
    ConfigType.CheckBox: questions.layout_checkbox,
    ConfigType.Grid: questions.layout_grid,
    ConfigType.CompositeGrid: questions.layout_composite_grid,
}


def layout_element(ctx: RenderContext, element, x: int, y: int, width: int) -> int:
    """Dispatch one element to its handler and return the new vertical cursor.

    An element type with no handler is outside the Layer 0-2 core slice and
    raises ``InvalidConfigurationException``.
    """
    handler = HANDLERS.get(element.Type)
    if handler is None:
        type_name = element.Type.name if element.Type is not None else type(element).__name__
        raise InvalidConfigurationException(
            f"Element type '{type_name}' is not supported by the Layer 0-2 core build."
        )
    return handler(ctx, element, x, y, width)


def _page_layout(page, settings: GlobalPageSettings, page_number: int):
    """Resolve one page's paper/orientation/margins/name and its content list.

    ``page`` is either a ``PageConfig`` (explicit page) or ``None`` (the single
    implicit page carrying all top-level children, supplied by the caller).
    Undefined paper/orientation and zero margins inherit the global settings.
    """
    if page is not None:
        paper = page.PaperSize if page.PaperSize != PaperSize.undefined else settings.PaperSize
        orientation = page.Orientation if page.Orientation != Orientation.undefined else settings.Orientation
        margin_left = page.LeftMargin or settings.PageMarginLeft
        margin_right = page.RightMargin or settings.PageMarginRight
        page_name = page.Name or f"Page{page_number}"
        content = list(getattr(page, "Children", []) or [])
    else:
        paper = settings.PaperSize
        orientation = settings.Orientation
        margin_left = settings.PageMarginLeft
        margin_right = settings.PageMarginRight
        page_name = f"Page{page_number}"
        content = None  # caller fills in the top-level children
    return paper, orientation, margin_left, margin_right, page_name, content


def render(template: TemplateConfig, settings: GlobalPageSettings | None,
           images: dict[str, bytes] | None):
    """Render a template to ``(list[PIL.Image], descriptor dict)``."""
    from PIL import Image, ImageDraw

    settings = settings or GlobalPageSettings()
    images = images or {}

    descriptor = omr_format.new_descriptor(getattr(template, "Name", "") or "")

    # Pages come from explicit PageConfig children, or a single implicit page
    # carrying all top-level children.
    children = list(getattr(template, "Children", []) or [])
    page_children = [child for child in children if child.Type == ConfigType.Page]
    pages = page_children if page_children else [None]

    page_images: list = []
    for page_index, page in enumerate(pages):
        (paper, orientation, margin_left, margin_right, page_name,
         content) = _page_layout(page, settings, page_index + 1)
        if content is None:  # implicit single page
            content = children

        width, height = geometry.page_dimensions(paper, orientation)
        image = Image.new("RGB", (width, height), (255, 255, 255))
        draw = ImageDraw.Draw(image)
        page_desc = omr_format.new_page(page_name, width, height)
        ctx = RenderContext(draw, image, settings, images, page_desc, layout_element)

        draw_reference_marks(ctx, width, height, settings)

        left = margin_left
        content_w = width - margin_left - margin_right
        cursor = geometry.CONTENT_TOP
        for element in content:
            cursor = layout_element(ctx, element, left, cursor, content_w)

        descriptor["Pages"].append(page_desc)
        page_images.append(image)

    return page_images, descriptor
