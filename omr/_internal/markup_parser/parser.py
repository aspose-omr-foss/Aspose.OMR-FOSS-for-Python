"""The text-markup line parser: markup lines -> ``TemplateConfig`` tree.

Line grammar (Aspose-style OMR text markup):

  * ``?keyword=value``      -- open an element; block elements stay open and
                               nest until their ``&keyword`` close line.
  * ``<tab>key=value``      -- an attribute of the most recently opened element.
  * ``&keyword``            -- close the innermost open block element.
  * ``(A) label (B) ...``   -- inline option line inside a choicebox.
  * ``# ...``               -- a comment line (ignored).

The scanning here stays deliberately thin: element creation lives in
``elements.py`` and attribute parsing in ``attributes.py``, so this file only
tracks the open-block stack and routes each line to the right place.
"""
from __future__ import annotations

from omr.exceptions import InvalidConfigurationException
from omr.generation.config import TemplateConfig
from omr.generation.config.elements import ChoiceBoxConfig
from omr._internal.markup_parser.attributes import apply_attr
from omr._internal.markup_parser.elements import (
    BLOCK_OPENERS,
    make_element,
    parse_option_line,
)


def _reject_json_markup(lines: list[str]) -> None:
    """Raise if the markup is actually JSON (handled by the code-first path).

    Only the first non-comment, non-blank line is inspected: a leading ``{`` or
    ``[`` means a JSON document, which the core build does not parse.
    """
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            if stripped.startswith("{") or stripped.startswith("["):
                raise InvalidConfigurationException(
                    "JSON markup is not supported in the Layer 0-2 core build; "
                    "use the code-first TemplateConfig overload instead."
                )
            break


def parse_markup(lines: list[str], settings=None) -> TemplateConfig:
    """Parse text-markup lines into a ``TemplateConfig``.

    Note: ``#`` begins a comment line (matching the reference ``final-exam.txt``
    sample). Choiceboxes are authored with ``?choicebox=`` + ``?option=`` or
    inline ``(char) Answer`` option lines; the ``#`` question shorthand is
    treated as a comment to avoid the documented ``#``-comment / ``#``-shorthand
    conflict.

    ``settings`` is accepted for call-site symmetry with the generation entry
    point but is not consulted here (markup has no global-settings line).
    """
    _reject_json_markup(lines)

    template = TemplateConfig()
    open_blocks: list = []   # stack of open block elements (innermost last)
    current = None           # most recent element, for attribute attachment

    def active_parent():
        """The element new children are added to: the innermost open block, or
        the template root when no block is open."""
        return open_blocks[-1] if open_blocks else template

    def enclosing_choicebox():
        """The nearest open choicebox, if any (option lines attach to it)."""
        for block in reversed(open_blocks):
            if isinstance(block, ChoiceBoxConfig):
                return block
        return None

    def add_inline_options(text: str) -> None:
        choicebox = enclosing_choicebox()
        if choicebox is None:
            return
        choicebox.Children.extend(parse_option_line(text))

    for raw_line in lines:
        line = raw_line.rstrip("\n").rstrip("\r")
        if line.strip() == "":
            continue
        stripped = line.strip()

        # Comment line.
        if stripped.startswith("#"):
            continue

        # Attribute line (tab-prefixed) applies to the current element.
        if line[:1] == "\t":
            body = stripped
            if body.startswith("(") and enclosing_choicebox() is not None:
                add_inline_options(body)
                continue
            if "=" in body and current is not None:
                key, _, value = body.partition("=")
                apply_attr(current, key, value)
            continue

        # Block close.
        if stripped.startswith("&"):
            if open_blocks:
                open_blocks.pop()
            current = open_blocks[-1] if open_blocks else None
            continue

        # Option line at column 0 (e.g. "(A) Yes (B) No") inside a choicebox.
        if stripped.startswith("(") and enclosing_choicebox() is not None:
            add_inline_options(stripped)
            continue

        # Element opener.
        if stripped.startswith("?"):
            body = stripped[1:]
            keyword, _, value = body.partition("=")
            keyword = keyword.strip()
            element = make_element(keyword, value)

            if keyword == "option":
                choicebox = enclosing_choicebox()
                target = choicebox if choicebox is not None else active_parent()
                target.Children.append(element)
            else:
                active_parent().Children.append(element)
                if keyword in BLOCK_OPENERS:
                    open_blocks.append(element)
            current = element
            continue

        # Any other line: ignore.

    return template
