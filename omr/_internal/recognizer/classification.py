"""Turn a fill cache into recognized elements (pixel-free classification).

Given each bubble's fill percentage, decide which bubbles are *marked* and
assemble the answers. This stage never touches the image, so it is shared by the
initial recognition pass and by ``TemplateProcessor.Recalculate`` (re-scoring at
a new threshold without re-reading pixels).

The core idea is *gap finding*. Within one question the filled bubbles cluster
high and the blanks cluster low, leaving a wide gap in between. The cut is placed
in the middle of that gap, per question when the evidence is strong enough,
otherwise falling back to a page-global cut computed the same way. This adapts to
faint pencil vs. bold pen without a fixed threshold.
"""
from __future__ import annotations

from omr._internal.recognizer.constants import (
    CONFIDENT_SURPLUS,
    GLOBAL_DEFAULT,
    MIN_GAP,
    MIN_JUMP,
)
from omr._internal.omr_format import GROUPING_ELEMENT


def largest_gap_cutoff(sorted_fills: list[float]) -> tuple[float, float | None]:
    """Find the widest gap between sorted fills and a cut in the middle of it.

    A 2-wide window is used (as OMRChecker does): the gap at position ``i`` is
    ``fills[i+1] - fills[i-1]``, so a single intermediate value cannot by itself
    define the cut. The returned cutoff is the midpoint of the widest such span.

    Worked example for ``[0, 0, 2, 88, 90]``: the window gaps are
    ``2-0 = 2`` (i=1), ``88-0 = 88`` (i=2) and ``90-2 = 88`` (i=3); the first
    widest is i=2, giving cutoff ``(88 + 0) / 2 = 44`` -- comfortably between the
    blanks (<= 2) and the filled (>= 88). Returns ``(88.0, 44.0)``.

    For exactly two values the only possible gap/cut is returned directly.
    """
    n = len(sorted_fills)
    if n == 2:
        gap = sorted_fills[1] - sorted_fills[0]
        return gap, (sorted_fills[0] + sorted_fills[1]) / 2.0

    best_gap = -1.0
    cutoff: float | None = None
    for i in range(1, n - 1):
        gap = sorted_fills[i + 1] - sorted_fills[i - 1]
        if gap > best_gap:
            best_gap = gap
            cutoff = (sorted_fills[i + 1] + sorted_fills[i - 1]) / 2.0
    return best_gap, cutoff


def global_threshold(all_fills: list[float]) -> float:
    """A page-global cut from every bubble's fill on the page.

    Used as the fallback when an individual question has too little contrast to
    decide on its own. Only trusted if the widest gap clears ``MIN_JUMP``;
    otherwise the page is treated as having no clear boundary and
    ``GLOBAL_DEFAULT`` (50%) is used.
    """
    if not all_fills:
        return GLOBAL_DEFAULT
    ordered = sorted(all_fills)
    gap, cutoff = largest_gap_cutoff(ordered)
    if cutoff is not None and gap > MIN_JUMP:
        return cutoff
    return GLOBAL_DEFAULT


def local_cutoff(field_fills: list[float], global_thr: float) -> float:
    """A per-question cut, deferring to the global threshold when unsure.

    * 0-1 bubbles: nothing to compare -> use the global threshold.
    * 2 bubbles: split them only if they differ by at least ``MIN_GAP``,
      otherwise they are probably both blank or both filled -> global.
    * 3+ bubbles: use the gap cut when it is *confident*
      (gap >= ``MIN_JUMP + CONFIDENT_SURPLUS``); otherwise, if the whole field
      spans less than ``MIN_GAP`` it has no real boundary -> global; else fall
      back to the gap cut if one exists, or the global threshold.
    """
    ordered = sorted(field_fills)
    if len(ordered) < 2:
        return global_thr
    if len(ordered) < 3:
        if (ordered[-1] - ordered[0]) < MIN_GAP:
            return global_thr
        return (ordered[0] + ordered[-1]) / 2.0

    gap, cutoff = largest_gap_cutoff(ordered)
    confident = MIN_JUMP + CONFIDENT_SURPLUS
    if cutoff is not None and gap >= confident:
        return cutoff
    if (ordered[-1] - ordered[0]) < MIN_GAP:
        return global_thr
    return cutoff if cutoff is not None else global_thr


def format_answer(marked: list[str]) -> str:
    """Format a field's marked values: empty, the single value, or a
    comma-joined list for a multi-mark answer."""
    if not marked:
        return ""
    if len(marked) == 1:
        return marked[0]
    return ",".join(marked)


def _page_global_thresholds(cache: list[dict]) -> dict[int, float]:
    """Compute the global threshold PER source page.

    Doing this per page (keyed by the ``_page`` stamp) means ``Recalculate`` on a
    merged multi-page result reproduces the per-page global that was used at
    initial recognition, rather than mixing fills across pages.
    """
    page_fills: dict[int, list[float]] = {}
    for element in cache:
        page = element.get("_page", 0)
        page_fills.setdefault(page, [])
        for field in element["Fields"]:
            for bubble in field["Bubbles"]:
                page_fills[page].append(bubble["Fill"])
    return {page: global_threshold(fills) for page, fills in page_fills.items()}


def _field_cutoff(field_fills: list[float], element_threshold, recognition_threshold,
                  use_fixed: bool, global_thr: float) -> float:
    """Pick the cutoff for one field, in priority order:

    1. the element's own ``Threshold`` when set (>= 0), e.g. a checkbox's fill %;
    2. the fixed ``recognitionThreshold`` when the caller gave a 0..100 value;
    3. otherwise the adaptive per-field local cutoff.
    """
    if element_threshold is not None and element_threshold >= 0:
        return float(element_threshold)
    if use_fixed:
        return float(recognition_threshold)
    return local_cutoff(field_fills, global_thr)


def build_elements_from_cache(cache: list[dict], threshold: int, validation):
    """Pure (pixel-free) classification: turn a fill cache into recognized
    elements.

    Shared by the initial recognition pass and ``TemplateProcessor.Recalculate``.
    ``threshold`` is the ``recognitionThreshold`` (``0..100`` fixed, or ``-100`` =
    auto-calibrate). An element's own ``Threshold`` (>= 0) overrides it (e.g. the
    ``checkbox`` fill threshold).

    Grouping decides how fields become elements:

    * ``GROUPING_ELEMENT`` -- all fields' marks are concatenated into one element
      (a grid's digit string); its sort weight is the smallest field weight.
    * otherwise (field grouping) -- each field becomes its own element.
    """
    from omr.exceptions import MultiselectException
    from omr.model import _OmrElement
    from omr.recognition.enums import FormValidationLogic

    page_global = _page_global_thresholds(cache)
    use_fixed = threshold is not None and 0 <= threshold <= 100
    elements: list[_OmrElement] = []

    for element in cache:
        grouping = element["ResultGrouping"]
        multiselect = element["Multiselect"]
        element_threshold = element["Threshold"]
        global_thr = page_global.get(element.get("_page", 0), GLOBAL_DEFAULT)

        # Determine the marked values for each field.
        field_marks: list[tuple[dict, list[str]]] = []
        for field in element["Fields"]:
            fills = [bubble["Fill"] for bubble in field["Bubbles"]]
            cutoff = _field_cutoff(
                fills, element_threshold, threshold, use_fixed, global_thr)
            marked = [bubble["Value"] for bubble in field["Bubbles"] if bubble["Fill"] >= cutoff]
            field_marks.append((field, marked))

        # Optional strict validation: a single-select question with >1 mark.
        if not multiselect and validation == FormValidationLogic.Exception:
            for field, marked in field_marks:
                if len(marked) > 1:
                    raise MultiselectException(
                        f"Question '{field['Name']}' has {len(marked)} marks but "
                        f"multiselect is disabled."
                    )

        if grouping == GROUPING_ELEMENT:
            answer = "".join("".join(marked) for _field, marked in field_marks)
            sort_weight = min((field["SortWeight"] for field in element["Fields"]), default=0)
            elements.append(_OmrElement(element["Name"], sort_weight, answer))
        else:
            for field, marked in field_marks:
                elements.append(
                    _OmrElement(field["Name"], field["SortWeight"], format_answer(marked)))

    return elements
