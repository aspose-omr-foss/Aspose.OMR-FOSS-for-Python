"""Build config objects from markup element openers and option lines.

Two kinds of markup line create elements:

  * an opener ``?keyword=value`` -> one ``*Config`` node (``make_element``), and
  * an inline option line such as ``(A) Yes  (B) No`` inside a choicebox, which
    expands to one ``ChoiceBoxAnswerConfig`` per ``(char) label`` pair
    (``parse_option_line``).

Only the Layer 0-2 core elements are recognised; any other keyword is reported
as unsupported.
"""
from __future__ import annotations

import re

from omr.exceptions import InvalidConfigurationException
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
from omr._internal.markup_parser.values import bubble_value

# Keywords whose element can contain children, so an opener pushes a new scope
# that stays open until the matching ``&keyword`` close line.
BLOCK_OPENERS = {
    "page",
    "container",
    "block",
    "positioned_block",
    "choicebox",
    "checkbox",
}

# One "(char) label" option on an inline option line. ``([^)]*)`` captures the
# bubble character inside the parens; ``([^(]*)`` captures the label text up to
# the next "(" (or end of line).
OPTION_RE = re.compile(r"\(([^)]*)\)\s*([^(]*)")

# Markup keyword -> the config class it builds. ``choicebox`` is constructed from
# this table too, then given its question text in ``make_element``.
_ELEMENT_CLASSES = {
    "page": PageConfig,
    "container": ContainerConfig,
    "block": BlockConfig,
    "positioned_block": PositionedBlockConfig,
    "choicebox": ChoiceBoxConfig,
    "checkbox": CheckBoxConfig,
    "option": ChoiceBoxAnswerConfig,
    "text": TextConfig,
    "content": ContentConfig,
    "empty_line": EmptyLineConfig,
    "image": ImageConfig,
    "answer_sheet": AnswerSheetConfig,
    "grid": GridConfig,
    "composite_grid": CompositeGridConfig,
}


def make_element(keyword: str, value: str):
    """Create the config node for a ``?keyword=value`` opener.

    ``value`` becomes the element's ``Name`` (its displayed text / recognition
    id, depending on the element). A ``choicebox`` additionally keeps ``value``
    as its ``QuestionText``. An unknown keyword is outside the core slice and is
    reported as unsupported.
    """
    config_class = _ELEMENT_CLASSES.get(keyword)
    if config_class is None:
        raise InvalidConfigurationException(
            f"Markup element '?{keyword}=' is not supported by the Layer 0-2 core build."
        )
    element = config_class()
    if keyword == "choicebox":
        element.QuestionText = value
    element.Name = value
    return element


def parse_option_line(text: str) -> list[ChoiceBoxAnswerConfig]:
    """Expand an inline option line into ``ChoiceBoxAnswerConfig`` objects.

    Example::

        "(A) Apple (B) Banana"  ->  [option A "Apple", option B "Banana"]

    The character inside the parens becomes the bubble value (normalised via
    ``bubble_value``); the text after it becomes the label. When a pair has no
    label the character is reused as the label (so ``(1)`` labels its bubble
    "1").
    """
    options: list[ChoiceBoxAnswerConfig] = []
    for match in OPTION_RE.finditer(text):
        char = match.group(1).strip()
        label = match.group(2).strip()
        option = ChoiceBoxAnswerConfig()
        option.BubbleValue = bubble_value(char) if char else ""
        option.Name = label if label else char
        options.append(option)
    return options
