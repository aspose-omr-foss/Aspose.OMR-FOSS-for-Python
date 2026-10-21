"""Name-fidelity checks on the ported enums (exact casing + integer values)."""
from omr.generation import BubbleSize, Color, FontStyle, Orientation, PaperSize, RotationPointPosition
from omr.generation.config.enums import (
    BarcodeType,
    BorderType,
    BubbleType,
    ConfigType,
    QRVersion,
    ScoreHeaderType,
    TableType,
)
from omr.recognition.enums import FormValidationLogic


def test_papersize_values():
    assert PaperSize.undefined == 0
    assert PaperSize.A4 == 1
    assert PaperSize.Legal == 2
    assert PaperSize.Tabloid == 3
    assert PaperSize.p8519 == 4
    assert PaperSize.p8521 == 5
    assert PaperSize.A3 == 6
    assert PaperSize.Letter == 7


def test_bubblesize_casing_and_values():
    # Source quirk: Extrasmall / Extralarge (NOT ExtraSmall / ExtraLarge).
    assert BubbleSize.Extrasmall == 10
    assert BubbleSize.Small == 20
    assert BubbleSize.Normal == 30
    assert BubbleSize.Large == 40
    assert BubbleSize.Extralarge == 50
    assert not hasattr(BubbleSize, "ExtraSmall")


def test_fontstyle_flags():
    assert FontStyle.undefined == 0
    assert FontStyle.Bold == 1
    assert FontStyle.Italic == 2
    assert FontStyle.Underline == 4
    assert FontStyle.Strikeout == 8
    assert FontStyle.Regular == 16
    assert int(FontStyle.Bold | FontStyle.Italic) == 3


def test_color_set():
    assert Color.undefined == 0
    assert Color.Black == 35
    assert Color.Blue == 37
    assert Color.Red == 141
    assert Color.White == 164
    assert Color.Yellow == 166
    assert Color.YellowGreen == 167
    # undefined + 140 named colors.
    assert len(list(Color)) == 141


def test_orientation():
    assert Orientation.undefined == 0
    assert Orientation.Vertical == 1
    assert Orientation.Horizontal == 2


def test_rotationpointposition():
    assert RotationPointPosition.TopLeft1 == 10
    assert RotationPointPosition.BottomRight1 == 40


def test_reserved_none_members():
    assert BorderType["None"] == 0
    assert BorderType.Square == 1
    assert BorderType.Rounded == 2
    assert TableType["None"] == 0
    assert TableType.EqualCells == 2


def test_configtype_aliases_and_blocks():
    assert ConfigType.Text == 0
    assert ConfigType.AnswerSheet == 3
    assert ConfigType.PositionedBlock == 210
    # Value 2 is unpublished.
    assert 2 not in [int(m) for m in ConfigType]


def test_bubbletype_and_scoreheader():
    assert BubbleType.Round == 0
    assert BubbleType.Square == 1
    assert ScoreHeaderType.Positive == 0
    assert ScoreHeaderType.Content == 4


def test_barcode_and_qr():
    assert BarcodeType.QR == 0
    assert BarcodeType.Code128 == 7
    assert BarcodeType.GS1CodablockF == 66
    assert len(list(BarcodeType)) == 67
    assert QRVersion.Auto == 0
    assert QRVersion.Version40 == 40
    assert QRVersion.VersionM1 == 101
    assert QRVersion.VersionM4 == 104


def test_formvalidationlogic():
    assert FormValidationLogic.undefined == 0
    assert FormValidationLogic.Ignore == 1
    assert FormValidationLogic.Exception == 2
