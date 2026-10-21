"""Writing systems (directionality + native digit sets).

Port of ``Aspose.OMR.Generation.WritingSystems``. The Layer 0-2 core renders LTR
Western only; the RTL / native-digit systems are present for API fidelity but the
core render engine treats them as Western (LTR). Assign to
``GlobalPageSettings.WritingSystem`` (e.g. ``WritingSystem = Arabic(True)``).
"""
from __future__ import annotations

__all__ = [
    "WritingSystem",
    "Western",
    "Arabic",
    "Bengali",
    "Hebrew",
    "Persian",
    "Urdu",
]


class WritingSystem:
    """Base writing system (LTR, Western digits)."""

    def __init__(self) -> None:
        ...


class Western(WritingSystem):
    """Default writing system: left-to-right, Western (0-9) digits."""

    def __init__(self) -> None:
        ...


class Arabic(WritingSystem):
    """Right-to-left; optionally Eastern-Arabic digits."""

    def __init__(self, useNativeNumber: bool) -> None:
        self.useNativeNumber = useNativeNumber


class Bengali(WritingSystem):
    """Left-to-right; optionally Bengali digits."""

    def __init__(self, useNativeNumber: bool) -> None:
        self.useNativeNumber = useNativeNumber


class Hebrew(WritingSystem):
    """Right-to-left; optionally Hebrew numbering."""

    def __init__(self, useNativeNumber: bool) -> None:
        self.useNativeNumber = useNativeNumber


class Persian(WritingSystem):
    """Right-to-left; optionally Persian digits."""

    def __init__(self, useNativeNumber: bool) -> None:
        self.useNativeNumber = useNativeNumber


class Urdu(WritingSystem):
    """Right-to-left; optionally Urdu digits."""

    def __init__(self, useNativeNumber: bool) -> None:
        self.useNativeNumber = useNativeNumber
