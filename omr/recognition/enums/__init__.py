"""Recognition enums.

Port of ``Aspose.OMR.Recognition.Enums``. ``FormValidationLogic`` is the only enum
in this namespace as of 26.1. Member names/values copied verbatim from the source.
"""
from __future__ import annotations

import enum

__all__ = ["FormValidationLogic"]


class FormValidationLogic(enum.IntEnum):
    """Controls engine behavior when a template validation rule is broken during
    recognition. Passed to ``OmrEngine.GetTemplateProcessor(...)``."""

    undefined = 0  # No logic specified -> the default (Ignore) is used.
    Ignore = 1     # Engine ignores all errors against template validation logic.
    Exception = 2  # Engine throws an OMRException-derived exception on a violation.
