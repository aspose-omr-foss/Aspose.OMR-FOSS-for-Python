"""Template generation surface.

Port of ``Aspose.OMR.Generation``: the generation enums (``PaperSize``,
``Orientation``, ``BubbleSize``, ``FontStyle``, ``Color``, ``RotationPointPosition``),
page settings (``GlobalPageSettings``, ``ReferencePointsSettings``, offsets) and the
result holders (``GenerationResult``, ``MemoryGenerationResult``).

Identifier names/casing and enum integer values are copied verbatim from the .NET
source (intentionally non-PEP8). ``TemplateConfig`` lives in ``omr.generation.config``
and is re-exported here for convenience, matching the ``OmrEngine`` import examples.

The surface is assembled from focused private submodules and re-exported here so
the public import paths (``from omr.generation import GenerationResult``, etc.)
stay unchanged:

  * ``_enums``    -- the generation enums (and the named ``Color``),
  * ``_settings`` -- offsets, reference points, ``GlobalPageSettings``, and
  * ``_results`` -- ``GenerationResult`` / ``MemoryGenerationResult``.
"""
from __future__ import annotations

from omr.generation._enums import (
    BubbleSize,
    Color,
    FontStyle,
    Orientation,
    PaperSize,
    RotationPointPosition,
)
from omr.generation._settings import (
    BaseOffset,
    GlobalPageSettings,
    PixelOffset,
    ReferencePointsSettings,
)
from omr.generation._results import GenerationResult, MemoryGenerationResult

# Re-exports: LongWordHandling's canonical home is the config enums, and
# TemplateConfig's is the config package; both are surfaced here because the
# OmrEngine docs import them from omr.generation.
from omr.generation.config.enums import LongWordHandling as LongWordHandling
from omr.generation.config import TemplateConfig as TemplateConfig

__all__ = [
    "PaperSize",
    "Orientation",
    "BubbleSize",
    "FontStyle",
    "Color",
    "RotationPointPosition",
    "LongWordHandling",
    "BaseOffset",
    "PixelOffset",
    "ReferencePointsSettings",
    "GlobalPageSettings",
    "GenerationResult",
    "MemoryGenerationResult",
    "TemplateConfig",
]
