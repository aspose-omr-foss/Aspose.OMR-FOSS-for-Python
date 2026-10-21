"""Decode any supported image input to grayscale, and the two whole-image
intensity transforms the pipeline uses (min-max normalize, light-shade gamma).

Grayscale is the right working space for OMR: a mark's *darkness* is the only
signal that matters, so colour is discarded up front. OpenCV decodes most
formats; Pillow is the fallback for anything OpenCV cannot read.
"""
from __future__ import annotations

import typing

import cv2
import numpy as np


def _decode_grayscale(data: bytes) -> np.ndarray:
    """Decode encoded image ``bytes`` (PNG/JPEG/...) to a 2-D uint8 grayscale
    array, falling back to Pillow when OpenCV cannot decode the format."""
    buffer = np.frombuffer(data, dtype=np.uint8)
    gray = cv2.imdecode(buffer, cv2.IMREAD_GRAYSCALE)
    if gray is None:
        import io

        from PIL import Image
        gray = np.array(Image.open(io.BytesIO(data)).convert("L"))
    return gray


def to_gray(image: typing.Any) -> np.ndarray:
    """Decode any supported image input to a 2-D uint8 grayscale array.

    Accepts a file path, a ``PIL.Image``, encoded ``bytes``, a readable
    file-like object, or an existing numpy array (BGR colour -> grey, or already
    grey). Anything else is a ``TypeError``.
    """
    if isinstance(image, str):
        gray = cv2.imread(image, cv2.IMREAD_GRAYSCALE)
        if gray is None:
            from PIL import Image
            gray = np.array(Image.open(image).convert("L"))
        return gray

    try:
        from PIL import Image as PILImage
        if isinstance(image, PILImage.Image):
            return np.array(image.convert("L"))
    except ImportError:  # pragma: no cover
        pass

    if isinstance(image, (bytes, bytearray)):
        return _decode_grayscale(bytes(image))

    if hasattr(image, "read"):
        return _decode_grayscale(image.read())

    if isinstance(image, np.ndarray):
        if image.ndim == 3:
            return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        return image

    raise TypeError(f"Unsupported image input: {type(image)!r}")


def normalize(gray: np.ndarray) -> np.ndarray:
    """Stretch intensities to the full 0-255 range (min-max normalization).

    A scan is often low-contrast: its darkest ink might be 40 and its paper 220
    rather than 0 and 255. ``cv2.NORM_MINMAX`` linearly remaps the actual
    [min, max] to [0, 255], so the subsequent ink test compares against a
    consistent scale regardless of exposure. A flat image (max == min, e.g. a
    blank page) is returned unchanged to avoid dividing by a zero range.

    Example: pixels spanning [40, 220] map as ``(v - 40) * 255 / 180`` -- 40 -> 0,
    130 -> ~127, 220 -> 255.
    """
    if gray.max() > gray.min():
        return cv2.normalize(gray, None, 0, 255, cv2.NORM_MINMAX)
    return gray


def apply_light_shade(gray: np.ndarray) -> np.ndarray:
    """Boost faint pencil marks via a gamma darken + re-normalize (off by default).

    A gamma < 1 applied as ``out = (in/255) ** (1/gamma) * 255`` pushes
    mid-tones downward (darker): with ``gamma = 0.7`` the exponent is ~1.43, so a
    faint mark at intensity 180 (180/255 = 0.706) becomes ``0.706**1.43 * 255 =
    ~155`` -- now below the ink cutoff. The lookup table applies this to all 256
    levels in one pass; a final normalize restores full contrast. Mirrors the
    OMRChecker light-shade handling.
    """
    gamma = 0.7
    lookup = np.array([((i / 255.0) ** (1.0 / gamma)) * 255 for i in range(256)],
                      dtype=np.uint8)
    return normalize(cv2.LUT(gray, lookup))
