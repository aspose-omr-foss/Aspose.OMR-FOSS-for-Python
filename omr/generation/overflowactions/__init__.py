"""Overflow actions.

Port of ``Aspose.OMR.Generation.OverflowActions``. ``OverflowAction`` is a class
hierarchy (NOT an enum); instantiate and assign to ``BlockConfig.Overflow`` /
``GlobalPageSettings.Overflow`` (e.g. ``Overflow = Clip()``).
"""
from __future__ import annotations

__all__ = ["OverflowAction", "Clip", "NoClip", "Wrap"]


class OverflowAction:
    """Base class for child-overflow handling algorithms."""

    def __init__(self) -> None:
        ...


class Clip(OverflowAction):
    """Truncate overflowing content at the parent's border."""

    def __init__(self) -> None:
        ...


class NoClip(OverflowAction):
    """Do nothing; overflowing content is drawn past the parent's border (default)."""

    def __init__(self) -> None:
        ...


class Wrap(OverflowAction):
    """Relocate an overflowing child (column reflow / element splitting)."""

    def __init__(self) -> None:
        ...
