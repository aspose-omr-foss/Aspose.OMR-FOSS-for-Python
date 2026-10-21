"""Draw the page's reference marks and record them into the descriptor.

Every page carries four solid corner fiducial squares plus one asymmetric
rotation marker. The recognizer uses the four corner centroids to de-skew the
scan and the rotation marker to resolve orientation, so the exact rectangles are
computed by ``geometry`` (shared with recognition) and stored in the descriptor.
"""
from __future__ import annotations

from omr._internal import geometry
from omr._internal.renderer.context import RenderContext
from omr.generation import GlobalPageSettings


def draw_reference_marks(ctx: RenderContext, width: int, height: int,
                         settings: GlobalPageSettings) -> None:
    """Draw the 4 corner squares + rotation marker and store their geometry in
    the page descriptor (``ReferenceCenters`` and ``RotationMarker``)."""
    marks = geometry.reference_marks(width, height, settings.ReferencePoints)
    black = (0, 0, 0)

    for corner_x, corner_y, corner_w, corner_h in marks["corners"]:
        ctx.draw.rectangle(
            [corner_x, corner_y, corner_x + corner_w, corner_y + corner_h], fill=black)

    rot_x, rot_y, rot_w, rot_h = marks["rotation"]
    ctx.draw.rectangle([rot_x, rot_y, rot_x + rot_w, rot_y + rot_h], fill=black)

    ctx.page_desc["ReferenceCenters"] = marks["corner_centers"]
    ctx.page_desc["RotationMarker"] = marks["rotation"]
