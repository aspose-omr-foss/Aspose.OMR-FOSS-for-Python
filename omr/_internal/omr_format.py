"""The ``.omr`` descriptor format: the frozen contract between generation and
recognition.

The descriptor is JSON. It records, per page, the pixel size, the reference-mark
centroids (template space) and every recognizable element reduced to a uniform shape:
a list of *fields* (sampling units), each with an ordered list of *bubbles* carrying
a returned value and a bounding box. Element semantics collapse to two grouping modes:

  - ``"Field"``      : each field becomes one recognized element (``answer_sheet`` ->
                       one element per numbered line; ``choicebox`` / ``checkbox`` ->
                       a single field).
  - ``"Element"``    : all fields' marked values are concatenated into one recognized
                       element (``grid`` / ``composite_grid`` digit strings).

Keeping every bubble element in this one shape lets the recognizer sample and classify
without knowing any element type.
"""
from __future__ import annotations

import json
import typing

FORMAT = "omr-python-for-foss"
VERSION = "1.0"

GROUPING_FIELD = "Field"
GROUPING_ELEMENT = "Element"


def new_descriptor(template_name: str) -> dict[str, typing.Any]:
    """Create an empty descriptor for a template."""
    return {
        "Format": FORMAT,
        "Version": VERSION,
        "TemplateName": template_name or "",
        "Pages": [],
    }


def new_page(page_name: str, width: int, height: int) -> dict[str, typing.Any]:
    """Create an empty page entry."""
    return {
        "PageName": page_name,
        "Width": int(width),
        "Height": int(height),
        "ReferenceCenters": [],
        "RotationMarker": [],
        "Elements": [],
    }


def new_element(
    type_name: str,
    name: str,
    grouping: str,
    multiselect: bool,
    threshold: int,
) -> dict[str, typing.Any]:
    """Create an empty recognizable-element entry."""
    return {
        "Type": type_name,
        "Name": name,
        "ResultGrouping": grouping,
        "Multiselect": bool(multiselect),
        "Threshold": int(threshold),
        "Fields": [],
    }


def new_field(name: str, sort_weight: int) -> dict[str, typing.Any]:
    """Create an empty field (sampling unit) entry."""
    return {"Name": name, "SortWeight": int(sort_weight), "Bubbles": []}


def new_bubble(value: str, box: typing.Sequence[float]) -> dict[str, typing.Any]:
    """Create a bubble entry with a returned value and an ``[x, y, w, h]`` box."""
    return {"Value": value, "Box": [float(box[0]), float(box[1]), float(box[2]), float(box[3])]}


def to_json(descriptor: dict[str, typing.Any]) -> str:
    """Serialize a descriptor to a pretty JSON string."""
    return json.dumps(descriptor, indent=2, ensure_ascii=False)


def parse(text: str) -> dict[str, typing.Any]:
    """Parse ``.omr`` JSON text into a descriptor dict, validating the envelope."""
    data = json.loads(text)
    if not isinstance(data, dict) or "Pages" not in data:
        raise ValueError("Not a valid .omr descriptor: missing 'Pages'.")
    return data
