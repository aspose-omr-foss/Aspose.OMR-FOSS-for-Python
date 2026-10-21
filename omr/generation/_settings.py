"""Page-level generation settings: layout offsets, reference points and the
document-wide ``GlobalPageSettings`` defaults.

Re-exported from ``omr.generation`` (import them from there, not this private
module).
"""
from __future__ import annotations

import typing

from omr.generation._enums import (
    BubbleSize,
    Color,
    FontStyle,
    Orientation,
    PaperSize,
    RotationPointPosition,
)
from omr.generation.config.enums import LongWordHandling
from omr.generation.overflowactions import NoClip, OverflowAction
from omr.generation.writingsystems import Western, WritingSystem


class BaseOffset:
    """Base class for generation layout offsets.

    (The .NET source names the type without enumerating members; the per-edge
    integer fields below are the project's concrete, documented representation.)
    """

    def __init__(self) -> None:
        self.Top: int = 0
        self.Bottom: int = 0
        self.Left: int = 0
        self.Right: int = 0


class PixelOffset(BaseOffset):
    """Pixel-unit layout offset (per-edge integer pixel values)."""

    def __init__(self, Top: int = 0, Bottom: int = 0, Left: int = 0, Right: int = 0) -> None:
        super().__init__()
        self.Top = Top
        self.Bottom = Bottom
        self.Left = Left
        self.Right = Right


class ReferencePointsSettings:
    """Corner reference marks + rotation-marker rectangle used for de-skew during
    recognition. ``Offset`` nudges the corner marks inward per edge;
    ``RotationMarkerPosition`` chooses where the asymmetric rotation marker sits.
    """

    def __init__(self) -> None:
        self.Offset: PixelOffset = PixelOffset()
        self.RotationMarkerPosition: RotationPointPosition = RotationPointPosition.TopRight1


class GlobalPageSettings:
    """Document-wide defaults applicable to all page elements; per-element overridable."""

    def __init__(self) -> None:
        self.PaperSize: PaperSize = PaperSize.A4
        self.Orientation: Orientation = Orientation.Vertical
        self.PageMarginLeft: int = 210
        self.PageMarginRight: int = 210
        self.FontFamily: str = "Segoe UI"
        self.FontSize: int = 12
        self.FontStyle: FontStyle = FontStyle.Regular
        self.BubbleSize: BubbleSize = BubbleSize.Normal
        self.BubbleColor: Color = Color.Black
        self.Multiselect: bool = True
        self.ImagesPaths: list[str] = []
        self.Overflow: OverflowAction = NoClip()
        self.LongWordHandling: LongWordHandling = LongWordHandling.DrawOver
        self.WritingSystem: WritingSystem = Western()
        self.ReferencePoints: ReferencePointsSettings = ReferencePointsSettings()
        self.BatchBarcode: typing.Any = None
