"""Parent / grouping element configs (supported Layer 0-2 core subset).

Port of ``Aspose.OMR.Generation.Config.Elements.Parents``. Only the containers the
core slice renders are defined: ``page``, ``container``, ``block``,
``positioned_block`` and the bubble-bearing ``checkbox``.
"""
from __future__ import annotations

from omr.generation import (
    BubbleSize,
    Color,
    FontStyle,
    Orientation,
    PaperSize,
    RotationPointPosition,
)
from omr.generation.config import BorderStyle, ParentConfig
from omr.generation.config.enums import (
    BorderType,
    BubbleType,
    ConfigType,
    ContainerTypeEnum,
)
from omr.generation.overflowactions import NoClip, OverflowAction

__all__ = [
    "PageConfig",
    "BlockConfig",
    "ContainerConfig",
    "PositionedBlockConfig",
    "CheckBoxConfig",
]


class PageConfig(ParentConfig):
    """One per physical page. Zero margins / undefined paper/orientation mean
    "inherit from GlobalPageSettings"."""

    def __init__(self) -> None:
        super().__init__()
        self.LeftMargin: int = 0
        self.Orientation: Orientation = Orientation.undefined
        self.PaperSize: PaperSize = PaperSize.undefined
        self.RightMargin: int = 0
        self.RotationPointPosition: RotationPointPosition = RotationPointPosition.TopRight1
        self.Type = ConfigType.Page


class BlockConfig(ParentConfig):
    """Bordered/padded box; lays out its non-block children with overflow handling.
    ``Border*Style`` default ``None`` (use the uniform ``BorderType``/``BorderColor``/
    ``BorderSize``)."""

    def __init__(self) -> None:
        super().__init__()
        self.BackgroundColor: Color = Color.undefined
        self.BorderBottomStyle: BorderStyle | None = None
        self.BorderLeftStyle: BorderStyle | None = None
        self.BorderRightStyle: BorderStyle | None = None
        self.BorderTopStyle: BorderStyle | None = None
        self.BorderColor: Color = Color.Black
        self.BorderSize: int = 3
        self.BorderType: BorderType = BorderType["None"]
        self.Column: int = 1
        self.Height: int = 0
        self.HorizontalPadding: int = 20
        self.IsClipped: bool = False
        self.Overflow: OverflowAction = NoClip()
        self.VerticalPadding: int = 20
        self.Type = ConfigType.Block


class ContainerConfig(ParentConfig):
    """Invisible layout element arranging child blocks into columns or a footer.
    Child blocks are arranged into columns via ``Proportions`` (percentages)."""

    def __init__(self) -> None:
        super().__init__()
        self.BlockBottomMargin: int = 20
        self.BlockRightMargin: int = 40
        self.BlockTopPadding: int = 20
        self.ContainerType: ContainerTypeEnum = ContainerTypeEnum.Normal
        self.Proportions: list[int] = []
        self.SyncBlockHeight: bool = False
        self.Type = ConfigType.Container


class PositionedBlockConfig(ParentConfig):
    """Places children at absolute ``XPosition``/``YPosition`` with optional size."""

    def __init__(self) -> None:
        super().__init__()
        self.Height: int = 0
        self.Width: int = 0
        self.XPosition: int = 0
        self.YPosition: int = 0
        self.Type = ConfigType.PositionedBlock


class CheckBoxConfig(ParentConfig):
    """Labeled group of blank boxes accepting any mark, with a tunable fill
    ``Threshold`` (default 3%). ``BubbleType`` defaults to ``Square``. Children are
    ``ContentConfig`` labels."""

    def __init__(self) -> None:
        super().__init__()
        self.BubbleSize: BubbleSize = BubbleSize.undefined
        self.BubbleType: BubbleType = BubbleType.Square
        self.FontFamily: str = ""
        self.FontSize: int = 0
        self.FontStyle: FontStyle = FontStyle.undefined
        self.HideName: bool = False
        self.Multiselect: bool | None = None
        self.Orientation: Orientation = Orientation.undefined
        self.Threshold: int = 3
        self.Type = ConfigType.CheckBox
