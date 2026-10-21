# ROADMAP — omr-python-for-foss

**Goal:** a FOSS Python library that reproduces the **full
[Aspose.OMR for .NET v26.1.0](../aspose-omr-for-.net-API.md) public API surface**, in
Python, name-for-name (see [AGENTS.md](AGENTS.md) §3 on identifier fidelity). This
roadmap lists **every** step toward that goal — including the ones already done — and
orders them **completed → easy → hard**.

- Canonical feature inventory: [`../features_list.md`](../features_list.md).
- Intended Python surface: [`../python_api.md`](../python_api.md).

## Legend

**Status:** ✅ complete · ⚠️ partial (shipped but incomplete vs full parity) · ❌ not started.

**Difficulty** (effort in FOSS Python with numpy + opencv + Pillow):

| | | |
|---|---|---|
| `S` | Trivial | data/enum/config/holders, serialization glue; ~days |
| `M` | Easy | file/stream I/O, orchestration, CSV/JSON/XML, simple math; days–1 wk |
| `L` | Moderate | standard CV/geometry: threshold, ROI sampling, warp from known points; 1–3 wks |
| `XL` | Hard | robust algorithms under scan noise: fiducial detection, de-skew, barcode decode, multi-page merge, write-in; 1–2 mo |
| `XXL` | Very hard | pixel-faithful rendering/typesetting (fonts, RTL, tables, pagination) and the correction GUI; 2+ mo |

## Milestone status

| Milestone | Definition (from features_list.md) | Status |
|---|---|---|
| **Vertical slice** | one element (`answer_sheet`) end-to-end: author → `.omr` → PNG → recognize → CSV | ✅ done |
| **MVP v0.1** — "bubble sheets that work" | foundation; render blocks/containers/text/bubbles; `answer_sheet`, `choicebox`/`option`, `checkbox`; ref-point draw+detect; fill-ratio + threshold; single-page `Recognize`; `Save` (PNG+`.omr`); CSV/JSON/XML | ✅ done (also ships `grid`/`composite_grid`, `image`, auto-calibration, `Recalculate`, light-shade, `RecognizeFolder`, basic multi-page merge) |
| **v0.2** — "forms people author" | tables, grids, score groups, `vertical_choicebox`, `write_in`, borders/overflow, PDF export, presets | ⚠️ grids done; tables/score/vertical_choicebox/write_in/overflow/PDF/presets pending |
| **v1.0** — "parity surface" | barcode gen+decode, batch pipeline, multi-page QR merge, RTL, hyphenation | ❌ pending |

Test state at last run: **436 passed, 264 skipped, 0 failed** (skips = out-of-scope
corpus fixtures; see [AGENTS.md](AGENTS.md) §7). Known bugs, if any, are tracked in
[TODO.md](TODO.md).

---

# Phase 0 — ✅ Completed

Everything below is implemented and under test today (Layers 0–2 "core bubble-sheet
slice").

## Layer 0 — Foundation

| Step | Diff | Where |
|---|---|---|
| ✅ Packaging & module layout (`omr.*` mirrors `Aspose.OMR.*`) | S | whole `omr/` tree |
| ✅ All generation/config enums + 140-name `Color` set (names & int values verbatim) | S | `omr/generation/__init__.py`, `omr/generation/config/enums/__init__.py`, `omr/_internal/colors.py` |
| ✅ `.omr` descriptor (de)serialization — the generation↔recognition contract | S | `omr/_internal/omr_format.py` |
| ✅ Exception hierarchy (`OMRException`, `RuntimeExceptionOMR`, `InvalidConfigurationException`, `ChildOverflowException`, `MultiselectException`) | S | `omr/exceptions/__init__.py` |
| ✅ `FormValidationLogic` enum (undefined/Ignore/Exception) | S | `omr/recognition/enums/__init__.py` |
| ✅ Positioning offsets (`BaseOffset`, `PixelOffset`) | S | `omr/generation/__init__.py` |
| ✅ `OmrEngine` factory/orchestrator | S | `omr/api/__init__.py` |
| ✅ `GlobalPageSettings` holder (paper/orientation/margins/font/bubble/multiselect/ref points/…) | S | `omr/generation/__init__.py` |

## Layer 1 — Generation

| Step | Diff | Where |
|---|---|---|
| ✅ Code-first config tree (`BaseConfig`/`ParentConfig`/`TemplateConfig` + the core `*Config`s) | S | `omr/generation/config/**` |
| ✅ Text-markup (txt DSL) parser for core elements | M | `omr/_internal/markup_parser.py` |
| ✅ `Generate` dispatch — 4 overloads (path / `list[str]` / stream / `TemplateConfig`) | M | `omr/api/__init__.py` |
| ✅ Render/layout engine for the core-slice element set (pragmatic, not pixel-faithful) | XXL* | `omr/_internal/renderer.py` |
| ✅ Bubble geometry & sizing model (shared drawer↔sampler source of truth) | L | `omr/_internal/geometry.py` |
| ✅ Image embedding (`ImageCollection` + `ImagesPaths`; renderer draws images) | M | `omr/api/__init__.py`, `omr/_internal/renderer.py` |
| ✅ Reference points & rotation marker — **drawing** | L | `omr/_internal/renderer.py`, `geometry.py` |
| ✅ `GenerationResult.Save` (PNG per page + `.omr`) | M | `omr/generation/__init__.py` |
| ✅ `MemoryGenerationResult.GetImages` / `GetOmr` (streams) | S | `omr/generation/__init__.py` |

*The engine itself is an `XXL` target; the implemented **subset** (layout + core bubble
elements, LTR, fixed spacing) is shipped. Full pixel-faithful typesetting remains in later
phases.

**Elements rendered + recognized:** `page` · `container` · `block` · `positioned_block`
· `text` · `content` (+ `content_type=cells`) · `empty_line` · `image` · `answer_sheet`
· `choicebox` + `option` · `checkbox` · `grid` · `composite_grid`.

## Layer 2 — Recognition

| Step | Diff | Where |
|---|---|---|
| ✅ `GetTemplateProcessor` — `.omr` loader (path + `MemoryStream`+encoding overloads) | M | `omr/api/__init__.py` |
| ✅ Input image decode — raster JPG/PNG/TIFF/BMP/GIF (+ path/bytes/stream/`ndarray`/PIL) | M | `omr/_internal/recognizer.py` |
| ✅ Reference-point detection + perspective registration (rotation-invariant fiducial detection; skew/perspective de-warp; resize fallback) | XL | `omr/_internal/recognizer.py` |
| ✅ Full orientation (0/90/180/270°) via the asymmetric rotation marker + skew/perspective de-warp + 3-of-4 fiducial reconstruction + scanner-line suppression; pinned by `tests/test_distortion_recognition.py`. Each degradation handled individually; see the hardening row for the stacked limits. | XL | `omr/_internal/recognizer.py` |
| ✅ Bubble fill-ratio sampling + classification | L | `omr/_internal/recognizer.py`, `geometry.py` |
| ✅ `recognitionThreshold` (fixed 0–100) + auto-calibration (`-100`, gap-detection heuristic) | L | `omr/_internal/recognizer.py` |
| ✅ `TemplateProcessor.Recognize` (single page) | L | `omr/api/__init__.py` |
| ✅ `Recalculate` (re-score cached fills, no re-read) | M | `omr/api/__init__.py` |
| ✅ `ApplyLightShadeProcessing` (gamma boost for faint marks) | L | `omr/_internal/recognizer.py` |
| ✅ Multiselect validation (`MultiselectException` under strict logic) | S | `omr/_internal/recognizer.py` |
| ✅ `RecognizeFolder` (folder batch, each image independent) | M | `omr/api/__init__.py` |
| ✅ `RecognitionResult` + `IOmrElement` model | S | `omr/model/__init__.py` |
| ✅ CSV / JSON / XML export (`GetCsv`/`GetJson`/`GetXml` + `*AsStream`, `SortWeight`-ordered) | M | `omr/model/__init__.py` |

## Presets / infra enums already in place

| Step | Diff | Where |
|---|---|---|
| ✅ Presets layout config enums (`BubbleType`/`BubbleSize`/`PaperSize`) present & correct | S | `omr/generation/config/enums`, `omr/generation` |

---

# Phase 1 — ⚠️ Finish what's partially done (easy → hard)

Shipped but incomplete relative to full Aspose parity. Ordered easiest first.

| # | Step | Diff | What's done / what's missing |
|---|---|---|---|
| 1 | `MemoryGenerationResult.GetPDF` | S | Images/omr streams done; `GetPDF` raises `NotImplementedError`. Trivial once `SaveAsPdf` exists. |
| 2 | Multi-page recognition merge | XL | Generation emits multi-page `.omr`/PNGs and `Recognize(list)` concatenates per-page results. Missing: robust page ordering and the `page` QR page-id that binds scans to pages (naive concat only today). |
| 3 | Render engine → pixel-faithful | XXL | Core-slice layout works (LTR, fixed spacing). Missing: faithful typesetting/measurement, proportional tables, pagination, column proportions fidelity. |

---

# Phase 2 — ❌ Remaining, ordered easy → hard

Grouped by difficulty. Dependencies in parentheses reference prior steps/elements.

## `S` — Trivial (do these first)

| Step | What it adds | Depends on |
|---|---|---|
| ❌ `#` choicebox shorthand | desugar `#question` + `(char) Answer` into a choicebox/option tree. Currently `#` is a comment (documented conflict); needs a disambiguation decision. | markup parser, `choicebox`/`option` |
| ❌ `%index%` row templating | substitute the row ordinal so repeated names stay unique. | `custom_answer_sheet`, `custom_row` |
| ❌ Derived statistics | client-side counts (total/answered/blank, write-in count) over the element list. | `RecognitionResult` |
| ❌ Batch dataset input (`DataSet`/`DataRecord` + JSON loaders) | mail-merge field data holders. | — |
| ❌ `empty_line`/`column`/`header`/`answer_value`/`question`/`table_content` configs | the small layout/table leaf configs (names/values verbatim). | parent elements |

## `M` — Easy

| Step | What it adds | Depends on |
|---|---|---|
| ❌ PDF **input** decode for recognition | decode PDF (incl. multi-page) scans to page buffers. | input decode; `pdf2image`/PyMuPDF |
| ❌ `SaveAsPdf` | compose page images into one flat multi-page PDF (+ `.omr`). | `Save`; `reportlab`/`img2pdf` |
| ❌ Recognition value triggers (`custom_trigger` / `TriggerType.ReplaceValue`) | a control bubble that replaces a target's value when marked. | fill-ratio sampling, `custom_trigger` element |
| ❌ `text` / `content` / `image` / `positioned_block` / `input_group` / `table_title` / `table_header` authoring parity | finish attribute coverage + the remaining layout elements. | render engine, border styling |
| ❌ Batch recognition (`BatchTemplateProcessor` → `BatchRecognitionResult` + bulk export) | recognize folder/file/stream against a `.domr`. | single-page recognize, CSV/JSON/XML, `.domr` |
| ❌ Batch generation output + per-form/page stream export (`BatchGenerationResult`, `TemplateExporter`) | persist the batch; forward-only exporter. | personalized batch pipeline |

## `L` — Moderate

| Step | What it adds | Depends on |
|---|---|---|
| ❌ Border & box styling — finish | per-side `BorderStyle`, true `Rounded` corners, `background_color` fill, padding fidelity. (Uniform border only, today.) | render engine, `Pillow` |
| ❌ Overflow & long-word handling | actually honor `Clip`/`NoClip`/`Wrap` + `DrawOver`/`ThrowException`/`Hyphenation` (`pyphen`). Enums parse today but behavior is always NoClip/DrawOver. | render engine, border styling |
| 🚫 `SaveAsInteractivePdf` — **removed** from the FOSS surface (fillable/interactive PDF is out of the raster scope) | — | — |
| ❌ Block content capture (`block.is_clipped`) | crop a block's ROI from the registered scan for external OCR. (Parsed/stored; not cropped at recognition.) | ref-point detection, `block` |
| ❌ Write-in image capture (`write_in`, `RecognitionResult.Images`) | draw the write-in box; crop its region to a bitmap (no ICR). | render engine, registration |
| ❌ `vertical_choicebox` + `answer` | vertically stacked answers (bubble left/right), each optionally holding a write-in. | fill-ratio sampling, `write_in` |
| ❌ `table` family (`table`/`table_header`/`question`/`answer_value`/`table_title`) | grid of questions sharing one answer set (normal/striped/equalCells). | border styling, fill-ratio sampling |
| ❌ Score / grading model (`score_group`/`score_question`/`score_header`/`score_answer` + `ScoreDisplay`) | weighted multi-criterion scoring tables summed per question/group. | table rendering, fill-ratio sampling |
| ❌ `custom_answer_sheet` / `custom_row` / `bubble_array` | layout-controlled numbered-row sheets (open-ended exams). | `%index%` templating, border styling |
| ❌ Barcode / QR **generation** | encode a value as ~67 symbologies. | render engine; `treepoem`/`qrcode`/`python-barcode` |
| ❌ Presets — bubble sheet + survey (`Presets.CreateBubbleSheet`/`RecognizeBubbleSheet`/`CreateSurvey`/`RecognizeSurvey`) | counts-driven generate + recognize to CSV with identical geometry both sides. | render engine, `answer_sheet`/`choicebox`, recognize |
| ❌ Personalized batch pipeline (`BatchOmrEngine` + `.domr`) | mail-merge many forms from a `DataSet`; batch-recognize. | Generate dispatch, recognize, dataset input, `.domr` |

## `XL` — Hard

| Step | What it adds | Depends on |
|---|---|---|
| ❌ Robust auto-calibration (`-100` path) | replace the gap-detection heuristic with a robust calibrator under real scan noise. | fill-ratio sampling |
| ❌ Barcode / QR **decode** | locate + decode each `barcode` element (and batch-id barcode) under scan noise. | input decode, registration; `pyzbar`/`zxing-cpp` |
| ❌ Batch barcode routing (`GlobalPageSettings.BatchBarcode`) | mandatory per-form identifier barcode, decoded to route scans. | barcode gen + decode, registration |
| ❌ Multi-page `page` + robust merge (QR page-id) | stamp a QR page-id per page; order + merge scans into one logical form. | `PageConfig`, barcode (QR), registration |
| ❌ Handwriting ICR (`text_input` / `free_text_input`) | OCR of boxed/free handwriting (expose write-in crops + BYO OCR). | write-in crop |
| ⚠️ Registration hardening | 0/90/180/270° orientation, skew/perspective de-warp, 3-of-4 fiducial reconstruction and scanner-line suppression are **done** for each degradation individually (`tests/test_distortion_recognition.py`). Remaining: extreme oblique perspective (keystone beyond a firm hand-held angle); very low DPI; and *stacked* degradations where a corner is missing AND the page is grossly misaligned — a **torn corner + significant skew/perspective**, or skew + heavy banding + a fiducial-covering smudge. The registration objective is a single rotation-marker ROI that a stray mark can satisfy while the page is misaligned, so these can be **silently misregistered**; the robust fix is a whole-page validator (e.g. re-detecting the fiducial squares in warped space, or correlating against a template reference) instead of the single marker ROI. | ref-point detection |

## `XXL` — Very hard

| Step | What it adds | Depends on |
|---|---|---|
| ❌ Writing system / directionality (RTL + native digits) | LTR/RTL + Western/Arabic/Bengali/Hebrew/Persian/Urdu digit sets and complex-script shaping. | render engine; `uharfbuzz`/`python-bidi` |
| 🚫 `GetCorrectionControl` (interactive correction GUI) — **removed** from the API (desktop GUI is out of a headless FOSS core). | — | — |

---

## Parity notes (track alongside the steps above)

- **`.omr` format shape.** Our descriptor (`Pages → Elements → ResultGrouping → Fields →
  Bubbles[Box]`) is internally consistent but differs from Aspose's per-bubble
  `Top/Left` shape. True drop-in interop with Aspose-generated `.omr` files would be a
  separate (`M`–`L`) compatibility layer — only needed if cross-tool file exchange
  becomes a goal.
- **`.domr`** (batch descriptor) is unbuilt; it arrives with the batch pipeline (`M`/`L`
  above).
- **Documented deviations that are intentional, not roadmap items:** pragmatic
  (non-pixel-faithful) rendering, default paper A4 vs Aspose Letter, `#` as comment. See
  [README.md](README.md) "Known limitations".
