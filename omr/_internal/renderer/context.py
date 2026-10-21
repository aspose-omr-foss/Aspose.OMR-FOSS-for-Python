"""The per-page render context.

One ``RenderContext`` is created per page and threaded through every element
handler. It carries the Pillow drawing surface, the resolved page settings, the
image map, the page descriptor being built, and two pieces of running state
(the auto answer-sheet line number and the CSV sort weight).

It also exposes ``layout_child`` -- the recursion entry a container handler uses
to lay out its children. The dispatcher is *injected* by the engine when the
context is built, so handler modules recurse through the context and never need
to import the engine back (which would create an import cycle).
"""
from __future__ import annotations

import typing

from omr.generation import GlobalPageSettings


class RenderContext:
    """Mutable render state shared across element handlers for one page."""

    def __init__(
        self,
        draw,
        image,
        settings: GlobalPageSettings,
        images: dict[str, bytes],
        page_desc: dict[str, typing.Any],
        dispatch,
    ) -> None:
        self.draw = draw
        self.image = image
        self.settings = settings
        self.images = images
        self.page_desc = page_desc
        self.auto_id = 1       # running answer-sheet line number
        self.sort_weight = 0   # running CSV sort weight
        # ``dispatch(ctx, element, x, y, width) -> new_y``; see ``layout_child``.
        self._dispatch = dispatch

    def layout_child(self, element, x: int, y: int, width: int) -> int:
        """Lay out a nested child element and return the new vertical cursor.

        Dispatches by the child's ``ConfigType`` (via the engine's handler
        table). Container handlers call this for each of their children.
        """
        return self._dispatch(self, element, x, y, width)

    def next_sort_weight(self) -> int:
        """Return the next CSV sort weight (1, 2, 3, ...). Each recognizable
        field/line takes one, fixing the output ordering."""
        self.sort_weight += 1
        return self.sort_weight
