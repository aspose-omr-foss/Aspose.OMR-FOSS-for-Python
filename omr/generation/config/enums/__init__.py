"""Configuration enumerations.

Port of ``Aspose.OMR.Generation.Config.Enums``. Every enum type name and every enum
member name is copied character-for-character from the .NET source (intentionally
non-PEP8). Integer values are verbatim from the source and are what the ``.omr``
descriptor serializes.

``BorderType`` and ``TableType`` each have a ``None`` member. ``None`` is a reserved
Python keyword and cannot be a class attribute, so those two are built with the
``enum.IntEnum`` functional API, which preserves the exact member name ``"None"``
(access via ``BorderType["None"]`` / ``TableType["None"]``).
"""
from __future__ import annotations

import enum

__all__ = [
    "AlignmentEnum",
    "VerticalAlignment",
    "Directionality",
    "BorderType",
    "TableType",
    "ContainerTypeEnum",
    "ParagraphTypeEnum",
    "ContentType",
    "BubbleType",
    "BubblePositionType",
    "GridHeaderTypeEnum",
    "LongWordHandling",
    "TriggerType",
    "ScoreDisplay",
    "ScoreGroupType",
    "ScoreHeaderType",
    "ConfigType",
    "BarcodeType",
    "QRVersion",
]


class AlignmentEnum(enum.IntEnum):
    """Horizontal alignment of an element relative to its parent."""

    undefined = 0  # Alignment is not set. Default value will be used.
    Left = 10      # Align element to the left.
    Center = 20    # Align element at the center of its parent.
    Right = 30     # Align element at the right side.


class VerticalAlignment(enum.IntEnum):
    """Vertical positioning of a child element inside its parent."""

    undefined = 0  # Alignment is not set. Default value will be used.
    Top = 10       # Align element at the top of the parent.
    Center = 20    # Align element at the center of the parent.
    Bottom = 30    # Align element at the bottom of the parent.


class Directionality(enum.IntEnum):
    """Direction in which elements and text are drawn (RTL/LTR support)."""

    LeftToRight = 0  # Left-to-right directionality.
    RightToLeft = 1  # Right-to-left directionality.


# ``None`` is a reserved Python keyword -> functional API preserves the EXACT
# member name "None" (access via BorderType["None"]).
BorderType = enum.IntEnum(
    "BorderType",
    [("None", 0),     # No framing.
     ("Square", 1),   # Square frame.
     ("Rounded", 2)], # Rounded frame.
)

# ``None`` is a reserved Python keyword -> functional API (see BorderType note).
TableType = enum.IntEnum(
    "TableType",
    [("None", 0),         # Simple table.
     ("Striped", 1),      # Striped table (alternating row shading).
     ("EqualCells", 2)],  # Every column has equal width.
)


class ContainerTypeEnum(enum.IntEnum):
    """How a ContainerConfig is placed on the page.

    Note: Footer is 2, NOT 1 (value 1 is not defined)."""

    Normal = 0  # Container is drawn according to its position.
    Footer = 2  # Container is drawn in the footer - at the end of the page.


class ParagraphTypeEnum(enum.IntEnum):
    """How a ParagraphConfig arranges its children."""

    Normal = 0     # Paragraph aligns items vertically.
    Multiple = 1   # Wrap many ContentConfig around one ImageConfig (legacy dup of ImageWrap).
    ImageWrap = 2  # Wrap many ContentConfig around one ImageConfig.
    Inline = 3     # Allocate elements in one horizontal (LTR) line.


class ContentType(enum.IntEnum):
    """How text content is rendered. (Markup DSL: content_type=Normal / Cells.)"""

    Normal = 0  # Default value. Draw text as is.
    Cells = 1   # Draw cells - each symbol in a line is enclosed in a rectangle (cell).


class BubbleType(enum.IntEnum):
    """The shape of an answer bubble."""

    Round = 0   # Round bubble.
    Square = 1  # Square bubble.


class BubblePositionType(enum.IntEnum):
    """Where the bubble sits relative to its main content (answer text)."""

    undefined = 0  # Default value.
    Left = 1       # On the left side of content.
    Right = 2      # On the right side of content.


class GridHeaderTypeEnum(enum.IntEnum):
    """The style of a grid's header."""

    Underline = 0  # Underline on grid header.
    Square = 1     # Square on grid header.


class LongWordHandling(enum.IntEnum):
    """Behavior when generation meets a word wider than its parent container."""

    undefined = 0       # Setting is not set. Default value will be used.
    DrawOver = 1        # Default - word is drawn as-is, overflowing the parent's borders.
    ThrowException = 2  # Raise an exception when an overflowing word is measured.
    Hyphenation = 3     # Split the long word by letters, carrying remainder to a new line.


class TriggerType(enum.IntEnum):
    """Behavior of a trigger (used by CustomTriggerConfig). One defined behavior."""

    ReplaceValue = 0  # When recognized, change the element's value to the trigger value.


class ScoreDisplay(enum.IntEnum):
    """Controls whether/how a score value is shown. Consumed by score-group headers."""

    DontDisplay = 0           # Score hidden; still counts in recognition/total.
    DisplayAsExtraColumn = 1  # Score shown in an extra column; counts in total.
    DisplayInsideCell = 2     # Score shown inside each cell/bubble.


class ScoreGroupType(enum.IntEnum):
    """Drawing mode of a score-group element. Only one member defined."""

    Table = 0  # Position each question as a table, with each answer as a row.


class ScoreHeaderType(enum.IntEnum):
    """Role of a column header inside a score group."""

    Positive = 0  # If the bubble under this column is marked, the score value is added.
    Negative = 1  # If the bubble under this column is marked, nothing happens.
    Amount = 2    # Column header stores the score value. Only with DisplayAsExtraColumn.
    Question = 3  # In this column: header = question text; rows = answers.
    Content = 4   # Custom content column. Header = header text; rows = Content element.


class ConfigType(enum.IntEnum):
    """Discriminator identifying which *Config element a node is.

    Values are NOT contiguous: a first block 0-24, then a second block 200+.
    Value 2 is not a published member.
    """

    Text = 0
    Grid = 1
    AnswerSheet = 3
    Table = 4
    Barcode = 5
    Block = 6
    ChoiceBox = 7
    Container = 8
    Image = 9
    Paragraph = 10
    WriteIn = 11
    Page = 12
    Template = 13
    EmptyLine = 14
    Question = 15
    TableTitle = 16
    Content = 17
    TableAnswer = 18
    TableHeader = 19
    Answer = 20
    VerticalChoiceBox = 21
    InputGroup = 22
    CustomAnswerSheet = 23
    CustomRow = 24
    BubbleArray = 200
    ScoreGroup = 201
    ScoreQuestion = 202
    ScoreHeader = 203
    CustomTrigger = 204
    ScoreAnswer = 205
    CheckBox = 206
    TableContent = 207
    CompositeGrid = 208
    ChoiceBoxAnswer = 209
    PositionedBlock = 210


class BarcodeType(enum.IntEnum):
    """The symbology used by a BarcodeConfig. Default QR (0). 67 members, 0-66."""

    QR = 0
    Codabar = 1
    Code11 = 2
    Code39Standard = 3
    Code39Extended = 4
    Code93Standard = 5
    Code93Extended = 6
    Code128 = 7
    GS1Code128 = 8
    EAN8 = 9
    EAN13 = 10
    EAN14 = 11
    SCC14 = 12
    SSCC18 = 13
    UPCA = 14
    UPCE = 15
    ISBN = 16
    ISSN = 17
    ISMN = 18
    Standard2of5 = 19
    Interleaved2of5 = 20
    Matrix2of5 = 21
    ItalianPost25 = 22
    IATA2of5 = 23
    ITF14 = 24
    ITF6 = 25
    MSI = 26
    VIN = 27
    DeutschePostIdentcode = 28
    DeutschePostLeitcode = 29
    OPC = 30
    PZN = 31
    Code16K = 32
    Pharmacode = 33
    DataMatrix = 34
    Aztec = 35
    Pdf417 = 36
    MacroPdf417 = 37
    AustraliaPost = 38
    Postnet = 39
    Planet = 40
    OneCode = 41
    RM4SCC = 42
    Mailmark = 43
    DatabarOmniDirectional = 44
    DatabarTruncated = 45
    DatabarLimited = 46
    DatabarExpanded = 47
    SingaporePost = 48
    GS1DataMatrix = 49
    AustralianPosteParcel = 50
    SwissPostParcel = 51
    PatchCode = 52
    DatabarExpandedStacked = 53
    DatabarStacked = 54
    DatabarStackedOmniDirectional = 55
    MicroPdf417 = 56
    GS1QR = 57
    MaxiCode = 58
    Code32 = 59
    DataLogic2of5 = 60
    DotCode = 61
    DutchKIX = 62
    UpcaGs1Code128Coupon = 63
    UpcaGs1DatabarCoupon = 64
    CodablockF = 65
    GS1CodablockF = 66


class QRVersion(enum.IntEnum):
    """QR symbol version for a QR-family BarcodeConfig. Auto (0) lets the library
    pick. Standard versions 1-40; Micro QR versions use 101-104."""

    Auto = 0
    Version01 = 1
    Version02 = 2
    Version03 = 3
    Version04 = 4
    Version05 = 5
    Version06 = 6
    Version07 = 7
    Version08 = 8
    Version09 = 9
    Version10 = 10
    Version11 = 11
    Version12 = 12
    Version13 = 13
    Version14 = 14
    Version15 = 15
    Version16 = 16
    Version17 = 17
    Version18 = 18
    Version19 = 19
    Version20 = 20
    Version21 = 21
    Version22 = 22
    Version23 = 23
    Version24 = 24
    Version25 = 25
    Version26 = 26
    Version27 = 27
    Version28 = 28
    Version29 = 29
    Version30 = 30
    Version31 = 31
    Version32 = 32
    Version33 = 33
    Version34 = 34
    Version35 = 35
    Version36 = 36
    Version37 = 37
    Version38 = 38
    Version39 = 39
    Version40 = 40
    VersionM1 = 101
    VersionM2 = 102
    VersionM3 = 103
    VersionM4 = 104
