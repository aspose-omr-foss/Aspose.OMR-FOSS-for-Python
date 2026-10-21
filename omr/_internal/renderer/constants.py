"""Small constants shared across the render handlers."""
from __future__ import annotations

# Auto-generated bubble glyphs A, B, C, ... used when an element does not supply
# its own answer values (e.g. an answer_sheet with only a count).
AUTO_LETTERS = [chr(code) for code in range(ord("A"), ord("Z") + 1)]

# The in-bubble guide glyph is drawn this light on purpose: light enough that the
# recognizer's ink test (fill < FILL_DARK_CUTOFF, ~175) never counts it as a
# mark, even after light-shade gamma, so an unmarked bubble reads ~0% fill.
GLYPH_GRAY = (210, 210, 210)
