"""The render / layout engine.

Walks a ``TemplateConfig`` tree, draws every element onto a page raster (Pillow)
and records every bubble's region into the ``.omr`` descriptor. Generation
drawing and recognition sampling share ``_internal.geometry``, so the sampled ROI
is, by construction, the inset of the drawn bubble box -- the drawer and sampler
cannot drift apart.

Scope: the Layer 0-2 "core bubble-sheet slice" -- layout (page/container/block/
positioned_block/text/content/empty_line/image) plus the bubble elements
(answer_sheet, choicebox/option, checkbox, grid, composite_grid). Unsupported
element types raise ``InvalidConfigurationException``.

The engine is split into focused modules:

  * ``constants``        -- shared small constants (auto letters, glyph grey),
  * ``context``          -- the per-page ``RenderContext`` + child dispatch,
  * ``support``          -- font / colour / size resolution and text measurement,
  * ``text``             -- the text / content handlers + paragraph drawer,
  * ``bubbles``          -- the single-bubble drawer,
  * ``layout``           -- container and non-bubble-leaf handlers,
  * ``questions``        -- the bubble-bearing element handlers,
  * ``reference_marks``  -- corner fiducials + rotation marker, and
  * ``engine``           -- type dispatch and the per-page render loop.

``render`` is the only public entry point.
"""
from __future__ import annotations

from omr._internal.renderer.engine import render

__all__ = ["render"]
