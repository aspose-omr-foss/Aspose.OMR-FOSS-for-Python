"""Generation result holders: ``GenerationResult`` (page image(s) + ``.omr`` JSON)
and ``MemoryGenerationResult`` (the same outputs as in-memory streams).

Re-exported from ``omr.generation`` (import them from there, not this private
module). Returned by ``OmrEngine.Generate``; not constructed directly by callers.
"""
from __future__ import annotations

import io
import os
import typing


def _to_pil(image: typing.Any):
    """Coerce a page image (``numpy.ndarray`` or ``PIL.Image.Image``) to PIL RGB."""
    import PIL.Image

    if isinstance(image, PIL.Image.Image):
        return image
    # numpy.ndarray path (grayscale or RGB); avoid importing numpy eagerly.
    try:
        import numpy as _np

        if isinstance(image, _np.ndarray):
            arr = image
            if arr.ndim == 2:
                return PIL.Image.fromarray(arr).convert("RGB")
            return PIL.Image.fromarray(arr[:, :, ::-1] if arr.shape[2] == 3 else arr)
    except ImportError:  # pragma: no cover
        pass
    raise TypeError(f"Unsupported image type: {type(image)!r}")


class GenerationResult:
    """The result of template generation: the page image(s) plus the ``.omr``
    template JSON describing element locations. Returned by ``OmrEngine.Generate``;
    not constructed directly by callers.
    """

    def __init__(self) -> None:
        self.ErrorCode: int = 0
        self.ErrorMessage: str = ""
        self.Template: str = ""
        self.TemplateImage: typing.Any = None
        self.MultipageTemplateImages: list[typing.Any] = []
        self.Warnings: list[str] = []

    def _page_filename(self, name: str, index: int, count: int) -> str:
        if count <= 1:
            return f"{name}.png"
        return f"{name}_{index + 1}.png"

    def Save(self, folder: str, name: str) -> None:
        """Write PNG image(s) PLUS the ``.omr`` template file. Produces
        ``<name>.png`` (one per page; multi-page numbered ``<name>_1.png`` ...) and
        ``<name>.omr``. ``folder=""`` => current working directory."""
        if folder:
            os.makedirs(folder, exist_ok=True)
        images = self.MultipageTemplateImages or ([self.TemplateImage] if self.TemplateImage is not None else [])
        count = len(images)
        for i, img in enumerate(images):
            path = os.path.join(folder, self._page_filename(name, i, count))
            _to_pil(img).save(path, format="PNG")
        omr_path = os.path.join(folder, f"{name}.omr")
        with open(omr_path, "w", encoding="utf-8") as fh:
            fh.write(self.Template)

    def SaveAsPdf(self, folder: str, name: str) -> None:
        """Compose page images into one flat multi-page PDF (+ ``.omr``).

        Not implemented in the Layer 0-2 core (PNG + .omr only)."""
        raise NotImplementedError(
            "SaveAsPdf is not implemented in the Layer 0-2 core build (PNG + .omr only)."
        )


class MemoryGenerationResult:
    """Wrapper around ``GenerationResult`` exposing outputs as in-memory streams."""

    def __init__(self, generationResult: GenerationResult) -> None:
        self._result = generationResult

    def GetImages(self) -> list[typing.BinaryIO]:
        """PNG page image(s) as in-memory byte streams."""
        result = self._result
        images = result.MultipageTemplateImages or (
            [result.TemplateImage] if result.TemplateImage is not None else []
        )
        streams: list[typing.BinaryIO] = []
        for img in images:
            buf = io.BytesIO()
            _to_pil(img).save(buf, format="PNG")
            buf.seek(0)
            streams.append(buf)
        return streams

    def GetOmr(self, encoding: str = "utf-8") -> typing.BinaryIO:
        """The ``.omr`` template JSON as an in-memory byte stream."""
        buf = io.BytesIO(self._result.Template.encode(encoding or "utf-8"))
        buf.seek(0)
        return buf

    def GetPDF(self) -> typing.BinaryIO:
        """The form as a single (multi-page) PDF stream.

        Not implemented in the Layer 0-2 core (PNG + .omr only)."""
        raise NotImplementedError(
            "GetPDF is not implemented in the Layer 0-2 core build (PNG + .omr only)."
        )
