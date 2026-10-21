"""Leaf / primitive element configs (supported Layer 0-2 core subset).

Port of ``Aspose.OMR.Generation.Config.Elements``. Only the elements the core
bubble-sheet slice renders and recognizes are defined here: text/content/empty
line/image layout leaves and the bubble-bearing ``answer_sheet``, ``choicebox``
(+ ``option``), ``grid`` and ``composite_grid`` elements. Property names/casing are
copied verbatim from the .NET source; ``undefined`` / ``0`` / ``""`` defaults mean
"inherit from GlobalPageSettings".
"""
from __future__ import annotations

from omr.generation import BubbleSize, Color, FontStyle, Orientation
from omr.generation.config import BaseConfig, ParentConfig
from omr.generation.config.enums import (
    AlignmentEnum,
    BubbleType,
    ConfigType,
    ContentType,
    GridHeaderTypeEnum,
)

__all__ = [
    "TextConfig",
    "ContentConfig",
    "EmptyLineConfig",
    "ImageConfig",
    "AnswerSheetConfig",
    "ChoiceBoxConfig",
    "ChoiceBoxAnswerConfig",
    "GridConfig",
    "CompositeGridConfig",
]


class TextConfig(BaseConfig):
    """Top-level multi-line raw text block. ``Name`` holds the displayed text."""

    def __init__(self) -> None:
        super().__init__()
        self.Color: Color = Color.undefined
        self.FontFamily: str = ""
        self.FontSize: int = 0
        self.FontStyle: FontStyle = FontStyle.undefined
        self.TextAlignment: AlignmentEnum = AlignmentEnum.undefined
        self.Type = ConfigType.Text


class ContentConfig(BaseConfig):
    """One styled text line inside a parent. ``Name`` holds the displayed text.
    Base of ``ScoreAnswerConfig`` / ``ScoreHeaderConfig`` / ``TableContentConfig``
    (those higher elements are out of the core slice)."""

    def __init__(self) -> None:
        super().__init__()
        self.Alignment: AlignmentEnum = AlignmentEnum.undefined
        self.Color: Color = Color.undefined
        self.ContentType: ContentType = ContentType.Normal
        self.FontFamily: str = ""
        self.FontSize: int = 0
        self.FontStyle: FontStyle = FontStyle.undefined
        self.Type = ConfigType.Content


class EmptyLineConfig(BaseConfig):
    """Vertical spacer. ``Height`` = 0 means one line of the default font."""

    def __init__(self) -> None:
        super().__init__()
        self.Height: int = 0
        self.Type = ConfigType.EmptyLine


class ImageConfig(BaseConfig):
    """Picture referenced by name. ``XPosition``/``YPosition`` = -1 means not
    absolutely positioned (use ``ImageAlign`` instead)."""

    def __init__(self) -> None:
        super().__init__()
        self.Height: int = 0
        self.Path: str = ""
        self.Width: int = 0
        self.XPosition: int = -1
        self.YPosition: int = -1
        self.ImageAlign: AlignmentEnum = AlignmentEnum.undefined  # FIELD
        self.Type = ConfigType.Image


class AnswerSheetConfig(BaseConfig):
    """Numbered question/answer bubble matrix. Returns ``<Name><id>`` per line.
    ``ElementsCount`` = 0 means the element is not rendered."""

    def __init__(self) -> None:
        super().__init__()
        self.AnswersCount: int = 4
        self.AnswersValues: list[str] = []
        self.BubbleType: BubbleType = BubbleType.Round
        self.Column: int = 1
        self.ColumnsCount: int = 4
        self.ElementsCount: int = 0
        self.Multiselect: bool | None = None
        self.StartId: int = 0
        self.VerticalMargin: int = 0
        self.BubbleSize: BubbleSize = BubbleSize.undefined  # FIELD
        self.Type = ConfigType.AnswerSheet


class ChoiceBoxConfig(ParentConfig):
    """A single question with a fixed set of option bubbles. ``Name`` is the
    recognition id; ``QuestionText`` is the displayed question."""

    def __init__(self) -> None:
        super().__init__()
        self.Color: Color = Color.undefined
        self.DisplayQuestionNumber: bool = True
        self.FontFamily: str = ""
        self.FontSize: int = 0
        self.FontStyle: FontStyle = FontStyle.undefined
        self.QuestionText: str = ""
        self.TextAlignment: AlignmentEnum = AlignmentEnum.undefined
        self.Multiselect: bool | None = None
        self.Type = ConfigType.ChoiceBox


class ChoiceBoxAnswerConfig(BaseConfig):
    """One answer bubble + label. ``BubbleValue`` sets the glyph (else auto A, B,
    C...); ``Name`` is displayed and returned. ``RowIndex`` packs options onto a row."""

    def __init__(self) -> None:
        super().__init__()
        self.BubbleValue: str = ""
        self.Color: Color = Color.undefined
        self.FontFamily: str = ""
        self.FontSize: int = 0
        self.FontStyle: FontStyle = FontStyle.undefined
        self.RowIndex: int = 0
        self.TextAlignment: AlignmentEnum = AlignmentEnum.undefined
        self.Type = ConfigType.ChoiceBoxAnswer


class GridConfig(BaseConfig):
    """Digit matrix (``SectionsCount`` sections x ``OptionsCount`` 0-9 bubbles)
    merged into one value. ``XPosition``/``YPosition`` = -1 means not absolute."""

    def __init__(self) -> None:
        super().__init__()
        self.BubbleSize: BubbleSize = BubbleSize.undefined
        self.BubbleType: BubbleType = BubbleType.Round
        self.Column: int = 1
        self.GridAlignment: AlignmentEnum = AlignmentEnum.undefined
        self.GridOrientation: Orientation = Orientation.Horizontal
        self.HeaderBorderColor: Color = Color.Black
        self.HeaderBorderSize: int = 3
        self.HeaderType: GridHeaderTypeEnum = GridHeaderTypeEnum.Underline
        self.OptionsCount: int = 10
        self.SectionsCount: int = 8
        self.VerticalMargin: int = 0
        self.XPosition: int = -1
        self.YPosition: int = -1
        self.Type = ConfigType.Grid


class CompositeGridConfig(BaseConfig):
    """Flexible grid with custom symbols; marks merge into one value.
    ``ExtraRow`` is ``[row][column]`` (None entry = no bubble)."""

    def __init__(self) -> None:
        super().__init__()
        self.BubbleType: BubbleType = BubbleType.Round
        self.Column: int = 1
        self.ColumnsCount: int = 5
        self.DisplayHint: bool = True
        self.ExtraRow: list[list[str]] = []
        self.GridAlignment: AlignmentEnum = AlignmentEnum.undefined
        self.GridOrientation: Orientation = Orientation.Horizontal
        self.HeaderBorderColor: Color = Color.Black
        self.HeaderBorderSize: int = 3
        self.HeaderType: GridHeaderTypeEnum = GridHeaderTypeEnum.Underline
        self.RotationAngle: int = 0
        self.Values: list[str] = []
        self.XPosition: int = -1
        self.YPosition: int = -1
        self.BubbleSize: BubbleSize = BubbleSize.undefined  # FIELD
        self.VerticalMargin: int = 0  # FIELD
        self.Type = ConfigType.CompositeGrid
