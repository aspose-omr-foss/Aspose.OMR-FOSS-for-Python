"""Font resolution for the render engine.

Resolves a ``PIL.ImageFont`` from an Aspose-style (FontFamily, FontSize, FontStyle)
triple, trying platform font files for the named family and degrading gracefully to
DejaVu / the Pillow default so rendering never fails for a missing typeface.
"""
from __future__ import annotations

import functools
import os

from omr.generation import FontStyle

# Common family -> (regular, bold, italic, bold-italic) base filenames. Looked up on
# the font search path; unknown families fall through to the DejaVu fallbacks.
_FAMILY_FILES: dict[str, tuple[str, str, str, str]] = {
    "segoe ui": ("segoeui.ttf", "segoeuib.ttf", "segoeuii.ttf", "segoeuiz.ttf"),
    "arial": ("arial.ttf", "arialbd.ttf", "ariali.ttf", "arialbi.ttf"),
    "calibri": ("calibri.ttf", "calibrib.ttf", "calibrii.ttf", "calibriz.ttf"),
    "times new roman": ("times.ttf", "timesbd.ttf", "timesi.ttf", "timesbi.ttf"),
    "courier new": ("cour.ttf", "courbd.ttf", "couri.ttf", "courbi.ttf"),
    "verdana": ("verdana.ttf", "verdanab.ttf", "verdanai.ttf", "verdanaz.ttf"),
    "tahoma": ("tahoma.ttf", "tahomabd.ttf", "tahoma.ttf", "tahomabd.ttf"),
}

_DEJAVU = ("DejaVuSans.ttf", "DejaVuSans-Bold.ttf", "DejaVuSans-Oblique.ttf",
           "DejaVuSans-BoldOblique.ttf")

_SEARCH_DIRS = [
    os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts"),
    "/usr/share/fonts",
    "/usr/local/share/fonts",
    "/Library/Fonts",
    os.path.expanduser("~/.fonts"),
]


def _find_file(filename: str) -> str | None:
    for d in _SEARCH_DIRS:
        candidate = os.path.join(d, filename)
        if os.path.isfile(candidate):
            return candidate
    return None


def _variant_index(style: FontStyle) -> int:
    bold = bool(int(style) & int(FontStyle.Bold))
    italic = bool(int(style) & int(FontStyle.Italic))
    if bold and italic:
        return 3
    if italic:
        return 2
    if bold:
        return 1
    return 0


@functools.lru_cache(maxsize=256)
def get_font(font_family: str, font_size: int, style_value: int):
    """Return a PIL font object for the requested family/size/style (cached)."""
    from PIL import ImageFont

    size = max(1, int(font_size))
    style = FontStyle(style_value) if style_value else FontStyle.Regular
    idx = _variant_index(style)
    family = (font_family or "").strip().lower()

    candidates: list[str] = []
    if family in _FAMILY_FILES:
        files = _FAMILY_FILES[family]
        candidates.append(files[idx])
        candidates.append(files[0])
    elif family:
        # Try the raw family name as a file / fontconfig name.
        candidates.extend([f"{font_family}.ttf", font_family])
    candidates.extend([_DEJAVU[idx], _DEJAVU[0]])

    for name in candidates:
        # Direct path or bare name (Pillow can resolve some bare names itself).
        path = _find_file(name) or name
        try:
            return ImageFont.truetype(path, size)
        except (OSError, IOError):
            continue

    # Last resort: Pillow's built-in default (sized on Pillow >= 10).
    try:
        return ImageFont.load_default(size)
    except TypeError:  # older Pillow: no size parameter
        return ImageFont.load_default()
