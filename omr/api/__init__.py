"""The engine + recognition API.

Port of ``Aspose.OMR.Api``: ``OmrEngine`` (the stateless factory/entry point),
``TemplateProcessor`` (recognition), ``ImageCollection`` (in-memory images for
generation) and the ``FormValidationLogic`` enum (re-exported from
``omr.recognition.enums``). Public method/property names/casing are copied verbatim
from the .NET source (intentionally non-PEP8). Heavy CV / rendering modules are
imported lazily so ``import omr.api`` stays cheap and generation needs no OpenCV.
"""
from __future__ import annotations

import os
import typing

from omr.exceptions import OMRException, RuntimeExceptionOMR
from omr.generation import GenerationResult
from omr.generation.config import TemplateConfig
from omr.recognition.enums import FormValidationLogic

__all__ = ["OmrEngine", "TemplateProcessor", "ImageCollection", "FormValidationLogic"]

_IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".gif")


# ── ImageCollection ──────────────────────────────────────────────────────────

class ImageCollection:
    """Append-only, case-sensitive name -> image-bytes map for in-memory images
    referenced by markup (``?image=<name>``). Duplicate names raise."""

    def __init__(self) -> None:
        self._items: dict[str, bytes] = {}

    def Add(self, name: str, image: typing.Any) -> None:
        if name in self._items:
            raise OMRException(f"ImageCollection already contains an image named {name!r}.")
        self._items[name] = _coerce_image_bytes(image)

    def Contains(self, name: str) -> bool:
        return name in self._items

    @property
    def Count(self) -> int:
        return len(self._items)

    def as_dict(self) -> dict[str, bytes]:
        return dict(self._items)


def _coerce_image_bytes(image: typing.Any) -> bytes:
    if isinstance(image, (bytes, bytearray)):
        return bytes(image)
    if isinstance(image, str):  # file path
        with open(image, "rb") as fh:
            return fh.read()
    if hasattr(image, "read"):
        return image.read()
    # PIL / numpy -> encode to PNG
    try:
        from PIL import Image as _PILImage
        if isinstance(image, _PILImage.Image):
            import io as _io
            buf = _io.BytesIO()
            image.save(buf, format="PNG")
            return buf.getvalue()
    except ImportError:  # pragma: no cover
        pass
    try:
        import io as _io

        import numpy as _np
        from PIL import Image as _PILImage
        if isinstance(image, _np.ndarray):
            arr = image if image.ndim == 2 else image[:, :, ::-1]
            buf = _io.BytesIO()
            _PILImage.fromarray(arr).save(buf, format="PNG")
            return buf.getvalue()
    except ImportError:  # pragma: no cover
        pass
    raise OMRException(f"Unsupported image type for ImageCollection: {type(image)!r}")


def _images_to_dict(third: typing.Any, settings) -> dict[str, bytes]:
    """Build a name->bytes image map from a third arg (ImageCollection or list of
    image paths) plus ``settings.ImagesPaths``."""
    images: dict[str, bytes] = {}
    paths: list[str] = []
    if settings is not None and getattr(settings, "ImagesPaths", None):
        paths.extend(settings.ImagesPaths)
    if isinstance(third, ImageCollection):
        images.update(third.as_dict())
    elif isinstance(third, dict):
        images.update(third)
    elif isinstance(third, (list, tuple)):
        paths.extend(third)
    for p in paths:
        base = os.path.basename(p)
        if base in images and p in images:
            continue
        try:
            with open(p, "rb") as fh:
                data = fh.read()
        except OSError:
            continue
        images.setdefault(base, data)
        images.setdefault(p, data)
    return images


# ── OmrEngine ────────────────────────────────────────────────────────────────

class OmrEngine:
    """The OMR engine: a stateless factory producing generation results and
    recognizers."""

    def __init__(self) -> None:
        """Create a stateless engine."""

    # ── Generation ──

    def Generate(self, source: typing.Any, settings: typing.Any = None,
                 third: typing.Any = None, fourth: typing.Any = None) -> GenerationResult:
        """Build a template -> ``GenerationResult`` (dispatches on the source type:
        markup file path, markup ``list[str]`` lines, markup stream, or a
        ``TemplateConfig``). Generation problems are reported via
        ``GenerationResult.ErrorCode``/``ErrorMessage``; a missing markup file still
        raises ``FileNotFoundError``."""
        from omr._internal import omr_format, renderer

        if source is None:  # analogue of .NET ArgumentNullException; must not be swallowed
            raise TypeError("Generate: markup/config source must not be None.")

        result = GenerationResult()
        try:
            if isinstance(source, TemplateConfig):
                template = source
                images = _images_to_dict(third, settings)
            elif isinstance(source, str):
                encoding = fourth or "utf-8"
                with open(source, "r", encoding=encoding) as fh:  # may raise FileNotFoundError
                    lines = fh.read().splitlines()
                from omr._internal.markup_parser import parse_markup
                template = parse_markup(lines, settings)
                images = _images_to_dict(third, settings)
            elif isinstance(source, (list, tuple)):
                from omr._internal.markup_parser import parse_markup
                template = parse_markup([str(x) for x in source], settings)
                images = _images_to_dict(third, settings)
            elif hasattr(source, "read"):
                encoding = fourth or "utf-8"
                data = source.read()
                if isinstance(data, (bytes, bytearray)):
                    data = data.decode(encoding)
                from omr._internal.markup_parser import parse_markup
                template = parse_markup(data.splitlines(), settings)
                images = _images_to_dict(third, settings)
            else:
                raise RuntimeExceptionOMR(f"Unsupported markup source: {type(source)!r}")

            page_images, descriptor = renderer.render(template, settings, images)
            result.MultipageTemplateImages = page_images
            result.TemplateImage = page_images[0] if page_images else None
            result.Template = omr_format.to_json(descriptor)
            result.ErrorCode = 0
        except FileNotFoundError:
            raise
        except Exception as ex:  # report, do not throw (per the generation contract)
            result.ErrorCode = 1
            result.ErrorMessage = str(ex)
        return result

    # ── Recognition factory ──

    def GetTemplateProcessor(self, templateSource: typing.Any,
                             arg2: typing.Any = None, arg3: typing.Any = None) -> "TemplateProcessor":
        """Load a ``.omr`` template (path ``str`` or memory stream) and return a
        ``TemplateProcessor`` bound to it.

        - ``GetTemplateProcessor(path, logic=FormValidationLogic.Ignore)``
        - ``GetTemplateProcessor(stream, textEncoding, logic=FormValidationLogic.Ignore)``
        """
        from omr._internal import omr_format

        if isinstance(templateSource, str):
            logic = arg2 if arg2 is not None else FormValidationLogic.Ignore
            with open(templateSource, "r", encoding="utf-8") as fh:  # may raise FileNotFoundError
                text = fh.read()
        elif hasattr(templateSource, "read"):
            encoding = arg2 or "utf-8"
            logic = arg3 if arg3 is not None else FormValidationLogic.Ignore
            data = templateSource.read()
            text = data.decode(encoding) if isinstance(data, (bytes, bytearray)) else data
        else:
            raise RuntimeExceptionOMR(
                f"Unsupported template source: {type(templateSource)!r}")

        descriptor = omr_format.parse(text)
        return TemplateProcessor(descriptor, logic)


# ── TemplateProcessor ────────────────────────────────────────────────────────

class TemplateProcessor:
    """Processes OMR images against the template it was created from. Obtain only via
    ``OmrEngine.GetTemplateProcessor(...)``; no public constructor."""

    def __init__(self, descriptor: dict, logic: FormValidationLogic = FormValidationLogic.Ignore) -> None:
        self._descriptor = descriptor
        self._logic = logic if logic is not None else FormValidationLogic.Ignore
        self.ApplyLightShadeProcessing: bool = False  # public field

    def Recognize(self, source: typing.Any, recognitionThreshold: int = -100):
        """Recognize one scanned form -> ``RecognitionResult``. A ``list`` source is
        treated as a single multi-page form and MERGED into one result."""
        from omr._internal import recognizer

        if isinstance(source, (list, tuple)):
            return self._recognize_merged(list(source), recognitionThreshold)
        path = source if isinstance(source, str) else ""
        return recognizer.recognize(
            self._descriptor, source, recognitionThreshold, self._logic,
            image_path=path, apply_light_shade=self.ApplyLightShadeProcessing,
            page_index=0,
        )

    def _recognize_merged(self, items: list, recognitionThreshold: int):
        from omr._internal import recognizer
        from omr.model import RecognitionResult

        merged = RecognitionResult()
        merged.TemplateName = self._descriptor.get("TemplateName", "")
        merged._validation = self._logic
        for i, item in enumerate(items):
            path = item if isinstance(item, str) else ""
            res = recognizer.recognize(
                self._descriptor, item, recognitionThreshold, self._logic,
                image_path=path, apply_light_shade=self.ApplyLightShadeProcessing,
                page_index=i,
            )
            if i == 0:
                merged.ImagePath = res.ImagePath
                merged.PageName = res.PageName
            merged.OmrElements.extend(res.OmrElements)
            merged._fill_cache.extend(res._fill_cache)
            merged.Images.extend(res.Images)
        return merged

    def RecognizeFolder(self, folderPath: str, recognitionThreshold: int = -100) -> list:
        """Recognize every supported image in a folder, each as an INDEPENDENT form."""
        results = []
        names = sorted(os.listdir(folderPath))
        for name in names:
            if name.lower().endswith(_IMAGE_EXTS):
                full = os.path.join(folderPath, name)
                results.append(self.Recognize(full, recognitionThreshold))
        return results

    def Recalculate(self, result, recognitionThreshold: int = -100) -> None:
        """Re-score a prior ``RecognitionResult`` at a new threshold, in place,
        WITHOUT re-reading pixels (uses the cached per-bubble fill ratios)."""
        from omr._internal import recognizer

        validation = getattr(result, "_validation", None) or self._logic
        result.OmrElements = recognizer.build_elements_from_cache(
            result._fill_cache, recognitionThreshold, validation)
