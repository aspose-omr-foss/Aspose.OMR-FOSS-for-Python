"""Text markup (txt DSL) parser.

Turns Aspose-style OMR text markup into a ``TemplateConfig`` tree for the render
engine. A line beginning with ``?`` opens an element (``?name=value``);
tab-prefixed lines are that element's attributes; ``&name`` closes a block
element. The ``#`` question shorthand and ``(char) Answer`` option lines desugar
into a choicebox/option tree. Markup tokens (``?``/``&``/attribute keys/value
keywords) are byte-identical to the source DSL; only the supported Layer 0-2
core elements are recognised.

JSON markup is not handled here (use the code-first ``TemplateConfig`` path for
structured authoring).

The parser is split into focused modules:

  * ``values``     -- turn attribute strings into typed / enum values,
  * ``elements``   -- build config objects from openers and option lines,
  * ``attributes`` -- apply ``key=value`` attributes per element type, and
  * ``parser``     -- the line scanner that ties them together.

``parse_markup`` is the only public entry point.
"""
from __future__ import annotations

from omr._internal.markup_parser.parser import parse_markup

__all__ = ["parse_markup"]
