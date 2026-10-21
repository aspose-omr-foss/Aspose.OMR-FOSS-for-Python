"""Library error types raised by generation / recognition.

Port of ``Aspose.OMR.Exceptions``. Every class name is copied character-for-character
from the .NET source (intentionally non-PEP8).
"""
from __future__ import annotations

__all__ = [
    "OMRException",
    "RuntimeExceptionOMR",
    "InvalidConfigurationException",
    "ChildOverflowException",
    "MultiselectException",
]


class OMRException(Exception):
    """Base class for every exception raised by the OMR library."""


class RuntimeExceptionOMR(OMRException):
    """Raised on an internal, unrecoverable generation/recognition failure."""


class InvalidConfigurationException(OMRException):
    """Raised when a template / element configuration is invalid or unsupported."""


class ChildOverflowException(OMRException):
    """Raised when a child element overflows its parent and overflow handling is
    configured to throw (see ``OverflowActions`` / ``LongWordHandling``)."""


class MultiselectException(OMRException):
    """Raised when more than one bubble is marked for a question that does not
    allow multi-select, and ``FormValidationLogic.Exception`` is active."""
