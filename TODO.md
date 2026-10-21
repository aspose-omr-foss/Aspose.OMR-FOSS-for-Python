# TODO — bugs for further analysis

Correctness defects found in the **implemented** Layer 0-2 code (see
[AGENTS.md](AGENTS.md) §4 for the scope boundary). These are **bugs**, not missing
features — deferred features live in [ROADMAP.md](ROADMAP.md), not here.

**How these were found.** The full `pytest` suite passes (**436 passed, 264 skipped, 0
failed**), so none of these is caught by the current tests. They came from an adversarial
multi-agent code audit (2026-10-07): parallel finders over each subsystem →
independent skeptical verification of every candidate → 4 confirmed, 0 rejected. The
`recognizer` and `enums/config` subsystems audited clean. Each item below was reproduced
by the verifier and cross-checked against the code in context; line numbers are from the
audited revision — re-confirm before fixing.

**Suggested next step:** add a failing regression test for each (the suite currently has
none covering these paths), then apply the fix, then make the test pass.

---

## 1. Multi-page merged recognition interleaves questions across pages — MEDIUM

- **Where:** `omr/api/__init__.py` — `TemplateProcessor._recognize_merged` (~line 263);
  root cause spans `omr/_internal/renderer.py` (`_Ctx.sort_weight` reset per page, ~line
  56 + `_next_sw` ~600) and `omr/model/__init__.py` (`_sorted_elements` sorts by
  `SortWeight`, ~line 73).
- **What's wrong:** the renderer builds a fresh `_Ctx` **per page** with `sort_weight = 0`,
  so field `SortWeight`s restart at 1 on every page and **collide across pages** in the
  `.omr`. `_recognize_merged` concatenates the per-page elements, then every exporter sorts
  the merged list purely by `SortWeight` (a stable sort), so pages get **interleaved**.
- **Repro:** a 2-page form — page 1 `answer_sheet` `Q` (3 lines), page 2 `answer_sheet`
  `R` (3 lines). `Q1..Q3` and `R1..R3` all carry `SortWeight` 1/2/3, so
  `proc.Recognize([img1, img2]).GetCsv()` emits rows in order `Q1, R1, Q2, R2, Q3, R3`
  instead of `Q1, Q2, Q3, R1, R2, R3`. `GetJson`/`GetXml` share `_sorted_elements` and
  are affected identically. The wrong order also survives `Recalculate` (it rebuilds from
  the still-page-local cached `SortWeight`).
- **Why it matters:** multi-page generation **and** merged recognition are both in the
  implemented slice, so this is a silent result-reordering bug on a mainstream path.
- **Suggested fix:** make `SortWeight` globally monotonic across pages. Cleanest single
  point is `recognizer.build_elements_from_cache` (used by both the initial merged
  `Recognize` and `Recalculate`), where each cache element already carries `_page`:
  precompute `page_offset[pg] = Σ (max SortWeight of earlier pages)` and add it when
  building each `_OmrElement` (use `min + offset` for the `GROUPING_ELEMENT` branch).
  Alternatively store `_page` on `_OmrElement` and key `_sorted_elements` on
  `(page, SortWeight)`. Note: rebasing only inside `_recognize_merged` would fix the
  initial export but **not** `Recalculate`.

## 2. `composite_grid` `ExtraRow` `None` entry draws a phantom null-valued bubble — MEDIUM

- **Where:** `omr/_internal/renderer.py` — `_layout_composite_grid`, the `ExtraRow`
  present-flag computation (~lines 552–554), with fallout at `new_bubble(sym, box)` (~579)
  and in `omr/_internal/recognizer.py` `build_elements_from_cache` (~329).
- **What's wrong:** the present flag is `syms.append((sym, sym != ""))`. Only `""` is
  treated as "no bubble"; a `None` entry yields `None != ""` → `True`, so the slot is
  **not** skipped. A bubble box is recorded as `{"Value": None}` in the `.omr`. This
  contradicts the documented contract that a `None`/null entry means **no bubble**
  (`omr/generation/config/elements/__init__.py:164` "None entry = no bubble"; also
  `../python_api.md:1933`, `../aspose-omr-for-.net-API.md:2575`).
- **Repro:** `CompositeGridConfig(Name="ID", ColumnsCount=3, Values=["0","1"],
  ExtraRow=[["1", None, "3"]])` renders column `ID_2` (the `None` slot) with **3** bubbles
  `[None, "0", "1"]` instead of **2** `["0", "1"]`. Because `composite_grid` uses
  `GROUPING_ELEMENT`, recognition runs `"".join("".join(marked) ...)`; if that
  null-valued bubble is ever classified as filled, `"".join([None])` raises `TypeError`
  and **crashes recognition**.
- **Reachability:** via the documented code-first API only (the markup parser's
  `_as_paren_list` only ever yields strings), but `ExtraRow` accepting `None` is an
  explicitly documented first-class input.
- **Suggested fix:** treat `None` like the empty sentinel:
  ```python
  for er in extra:
      sym = er[c] if c < len(er) else ""
      present = sym is not None and sym != ""
      syms.append((sym if present else "", present))
  ```
  Then the slot is skipped (no bubble drawn, no null `Value` written), matching the
  contract and removing the downstream crash.

## 3. Markup multi-line `text` continuation lines are silently dropped — MEDIUM

- **Where:** `omr/_internal/markup_parser.py` — `parse_markup` main loop; a column-0,
  non-special line falls through to the final "Any other line: ignore." no-op (~line 506).
- **What's wrong:** `../python_api.md:1152` documents the `text` element as
  "`?text=<first line>` then raw continuation lines until a blank line / new element /
  attribute." The renderer already supports multi-line text (`_wrap` splits `el.Name` on
  `\n`), but the parser never appends continuation lines to the current element's `Name`,
  so everything after the first line is **silently discarded** (`ErrorCode` stays 0).
- **Repro:** `parse_markup(["?text=Line one", "Line two continuation", "?content=X"])`
  yields a `TextConfig` with `Name == "Line one"` only; "Line two continuation" is lost.
- **Why it matters:** genuine fidelity / silent-data-loss defect for an implemented
  element and a documented DSL feature; not a deferred feature or documented deviation.
- **Suggested fix:** just before the final ignore at ~line 506, append the line to the
  current text block:
  ```python
  if isinstance(current, TextConfig):
      current.Name = (current.Name + "\n" + line) if current.Name else line
      continue
  ```
  The earlier branches already `continue` on blank/tab/`&`/`(`/`?` lines, so only genuine
  continuation lines reach here, and the existing blank-line skip already terminates a
  paragraph per the spec. (Consider whether `content` should behave likewise.)

## 4. `_coerce_image_bytes` swaps channels of 4-channel (RGBA) numpy arrays — LOW

- **Where:** `omr/api/__init__.py` — `_coerce_image_bytes` (~line 75).
- **What's wrong:** `arr = image if image.ndim == 2 else image[:, :, ::-1]` reverses **all**
  channels. For a 3-channel array this is the intended BGR→RGB swap, but for a 4-channel
  RGBA array it turns `[R,G,B,A]` into `[A,B,G,R]` (alpha into the red slot). The sibling
  coercion `_to_pil` (`omr/generation/__init__.py:183`) guards the reverse with
  `arr.shape[2] == 3`, so the two paths disagree.
- **Repro:** RGBA pixel `(10,20,30,40)` → `_coerce_image_bytes` round-trips to
  `(40,30,20,10)`; `_to_pil` leaves it `(10,20,30,40)`. A referenced `?image=` added to an
  `ImageCollection` as an RGBA `ndarray` then renders with swapped colors and a
  near-transparent alpha (pasted via the alpha mask in `_layout_image`).
- **Why it matters:** low severity (niche input: an RGBA numpy array handed to
  `ImageCollection.Add`), but it is silent image corruption on an implemented path.
- **Suggested fix:** guard the reverse like `_to_pil`:
  ```python
  arr = image if image.ndim == 2 else (image[:, :, ::-1] if image.shape[2] == 3 else image)
  ```

---

## Notes

- No defects were confirmed in the **recognizer** (registration, fill sampling,
  threshold calibration, `Recalculate`, multiselect) or in **enum/config fidelity**
  (names, integer values, `ConfigType` aliases, the 67-member `BarcodeType`, the Color
  table) — those subsystems audited clean.
- The audit targeted correctness within the implemented slice only. Gaps that are
  *absence of a deferred feature* (PDF export, tables, barcode, RTL, robust multi-page
  merge, etc.) are tracked in [ROADMAP.md](ROADMAP.md), not here.
