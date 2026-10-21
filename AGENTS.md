# AGENTS.md — omr-python-for-foss

Guidance for AI coding agents (and humans) working in this repository. Read this
before changing code. It encodes the non-obvious rules that keep the two pipelines
(generation ↔ recognition) in sync and the public surface faithful to Aspose.

## 1. What this project is

`omr-python-for-foss` is a **FOSS Python OMR (Optical Mark Recognition) library**
whose public API is a **name-preserving port of [Aspose.OMR for .NET] v26.1.0**. You
author a bubble-sheet form (code-first or in the text-markup DSL), generate a printable
PNG + a machine-readable `.omr` descriptor, print/scan/fill it, then recognize the marks
back into answers — through the exact Aspose class / method / property / enum names.

It is built **only** on `numpy` + `opencv-python` + `Pillow` (no .NET, no Windows
dependency). The recognition CV math is **modeled on** the FOSS [OMRChecker] project; **no
API shape** is borrowed from OMRChecker — the public surface is purely the Aspose port.

[Aspose.OMR for .NET]: https://docs.aspose.com/omr/net/
[OMRChecker]: https://github.com/Udayraj123/OMRChecker

## 2. Repository layout (two nested folders — know which one you are in)

```
Z:\IoT\omr-python-for-foss\           <- git repo root (branch: master; PRs -> main)
├─ aspose-omr-for-.net-API.md          Aspose .NET API dump — SOURCE OF TRUTH (265 KB)
├─ python_api.md                       intended Python port surface (verbatim names)
├─ features_list.md                    full feature inventory + difficulty + roadmap
├─ OMRChecker/                         READ-ONLY reference CV project (never edit)
└─ omr-python-for-foss/                <- THE TARGET PROJECT (edit here)
   ├─ AGENTS.md  ROADMAP.md  TODO.md    (this file + planning docs live here)
   ├─ omr/                             the library package
   ├─ tests/                           pytest suite + ported Aspose corpus
   ├─ examples/                        quickstart scripts + final-exam.txt
   ├─ pyproject.toml  requirements.txt  README.md
```

- **Edit only inside `omr-python-for-foss/omr-python-for-foss/`** (the inner target
  project). The `*.md` spec files and `OMRChecker/` sit one level up and are inputs.
- **`OMRChecker/` is strictly read-only** — a reference for recognition algorithms only.
  Do not import it, copy its API, or modify it.
- Spec files are referenced from the project with `../` relative paths (e.g.
  `../features_list.md`), matching the README.

## 3. The golden rule: identifier fidelity (overrides PEP 8)

Class / method / property / enum-type / enum-member names are copied
**character-for-character** from Aspose.OMR for .NET. **This intentionally violates
PEP 8 and must not be "fixed".**

- Methods/properties stay **PascalCase**: `GetCsv`, `RecognizeFolder`, `ErrorCode`,
  `ApplyLightShadeProcessing`, `GetTemplateProcessor`.
- Enum **integer values** are verbatim from the .NET source — they are what the `.omr`
  descriptor serializes, so changing one silently breaks the format contract.
- **Preserve source quirks deliberately.** Do not correct any of these:
  - `BubbleSize.Extrasmall` / `Extralarge` (not `ExtraSmall` / `ExtraLarge`)
  - `FontStyle.Strikeout`; the `undefined = 0` sentinels
  - `BorderType["None"]` / `TableType["None"]` — `None` is a reserved Python keyword, so
    these two enums are built with the functional API to keep the exact member name.
  - `ConfigType` values are non-contiguous (0–24, then 200–210). The .NET alias
    members `Column`=177 / `Header`=199 are intentionally **not** ported (FOSS removal).
  - the misspelled markup attribute `recogintion_values` (on the out-of-scope
    `bubble_array`).
- When adding an identifier, **verify its exact spelling/casing/value against
  `../python_api.md` and `../aspose-omr-for-.net-API.md` first.** Those two files are the
  authority; if they disagree, the `aspose-omr-for-.net-API.md` dump wins.
- snake_case is used **only** for internal (`_internal/*`, leading-underscore) helpers
  and for the markup DSL attribute keys (which are themselves Aspose tokens, e.g.
  `elements_count`, `bubble_size`).

## 4. Scope: the "Layer 0-2 core bubble-sheet slice"

This build deliberately implements a slice (see [ROADMAP.md](ROADMAP.md) for the full
map). Know the boundary before you file a "bug" or add a feature.

**Implemented (changes here are real features/bugfixes):**
- Layer 0 foundation: full enum set + 140-name color table, exceptions,
  `FormValidationLogic`, `.omr` serializer, code-first config tree, `GlobalPageSettings`,
  `OmrEngine`.
- Layer 1 generation: render engine, markup parser, `Generate` dispatch,
  `GenerationResult.Save` (PNG + `.omr`), `MemoryGenerationResult` (images/omr),
  reference-point drawing, bubble geometry. Elements: `page`, `container`, `block`,
  `positioned_block`, `text`, `content` (+ `content_type=cells`), `empty_line`, `image`,
  `answer_sheet`, `choicebox`+`option`, `checkbox`, `grid`, `composite_grid`.
- Layer 2 recognition: `.omr` loader, image decode, rotation/perspective/damage-robust
  reference-point registration (0/90/180/270° orientation via the rotation marker, skew +
  perspective de-warp, 3-of-4 fiducial reconstruction, scanner-line suppression),
  fill-ratio sampling, threshold + auto-calibration, `Recalculate`, light-shade,
  multiselect validation, folder batch (`RecognizeFolder`), CSV/JSON/XML export. The
  robustness is pinned by `tests/test_distortion_recognition.py` (generate → ink → degrade
  → recognize → assert exact recovery), which handles each degradation **individually**.
  Registration still trusts a single rotation-marker ROI, so *stacked* worst cases — a
  torn corner combined with significant skew/perspective, or extreme oblique perspective —
  are documented limits (ROADMAP.md "Registration hardening"), not supported; don't claim
  them as covered.

**Intentionally deferred — NOT bugs (these belong in ROADMAP, never TODO):**
tables & score groups, `vertical_choicebox`/`answer`, `write_in`/ICR,
`custom_answer_sheet`/`custom_row`, barcode/QR generation & decode, batch barcode,
RTL/complex-script writing systems, PDF export (`SaveAsPdf`/`GetPDF`), personalized
batch pipeline, presets, and JSON markup. The **enums for every deferred feature are still present and
correct** (e.g. the 67-member `BarcodeType`); only the heavy rendering/decoding is
omitted. Methods that exist but are intentionally unimplemented raise
`NotImplementedError` with a message naming the scope boundary. Markup/elements outside
the slice are **reported** via `GenerationResult.ErrorCode != 0` with the message
`"... not supported by the Layer 0-2 core build"` — generation never throws for them.

**Intentionally REMOVED — not part of the FOSS surface (do not re-add):** Aspose's
licensing/metering classes (`License`, `Metered`); the desktop correction UI
(`OmrEngine.GetCorrectionControl`, `CorrectionUI`/`CorrectionControl`); the .NET
buffer-pool plumbing (`Aspose.OMR.Buffers`/`PoolFactory` and the `OmrEngine(PoolFactory)`
parameter — the ctor is now parameterless); the plugin extension point (`AddPlugin`,
`IPlugin`, `omr.api.plugins`); the legacy aliases (`GenerateTemplate`,
`GenerateJSONTemplate`, `RecognizeImage`); `GenerationResult.SaveAsInteractivePdf`; and
the `ConfigType.Column`/`Header` alias members plus the obsolete
`ContainerConfig.ColumnsCount` (the non-obsolete `ColumnsCount` on `answer_sheet` /
`composite_grid` stays). None of these have meaning in a headless FOSS build.

## 5. Build, run, test

Requires **Python 3.10+**. Current dev env: Python 3.12, numpy 2.5, opencv 5.0, Pillow 12.

```bash
pip install -r requirements.txt        # numpy, opencv-python, Pillow
pip install -e .                        # optional: install as a package
python -m pytest -q                     # full suite (~50s): expect "4xx passed, 2xx skipped"
python -m pytest tests/test_roundtrip.py -q   # a single file
python -m pytest -q -k recognition      # by keyword
```

- The suite's **skips are expected** — they are the out-of-scope corpus fixtures (see
  §4 and §7). A green run is `N passed, M skipped, 0 failed`. **Zero failures is the bar.**
- `tests/conftest.py` puts the repo on `sys.path`, so pytest works from the project root.
- Run tests from the inner project directory
  (`Z:\IoT\omr-python-for-foss\omr-python-for-foss`).

## 6. Architecture & where things live

```
omr/
  __init__.py                 __version__ (FOSS build: no License/Metered)
  api/__init__.py             OmrEngine, TemplateProcessor, ImageCollection, FormValidationLogic
  model/__init__.py           RecognitionResult, IOmrElement (+ CSV/JSON/XML export)
  generation/__init__.py      PaperSize/Orientation/BubbleSize/FontStyle/Color/RotationPointPosition,
                              GlobalPageSettings, ReferencePointsSettings, offsets,
                              GenerationResult, MemoryGenerationResult
                              (assembled from private _enums / _settings / _results submodules)
    config/__init__.py        BaseConfig, ParentConfig, TemplateConfig, BorderStyle
      enums/__init__.py       all config enums (ConfigType, BarcodeType, QRVersion, ...)
      elements/__init__.py    leaf configs (text/content/image/answer_sheet/choicebox/grid/...)
        parents/__init__.py   container configs (page/container/block/positioned_block/checkbox)
    overflowactions/__init__  OverflowAction, Clip, NoClip, Wrap (classes, NOT an enum)
    writingsystems/__init__   WritingSystem, Western, Arabic, ... (core treats all as LTR Western)
  recognition/enums/__init__  FormValidationLogic (canonical home; re-exported from omr.api)
  exceptions/__init__.py      OMRException hierarchy
  _internal/                  NOT public API:
    markup_parser/            text DSL -> TemplateConfig tree (package: values
                              string->value coercions, elements factory, attributes
                              per-element-type appliers, parser line loop; entry parse_markup)
    renderer/                 TemplateConfig tree -> page raster + .omr descriptor
                              (package: constants, context, support, text, bubbles,
                              layout, questions, reference_marks, engine [HANDLERS +
                              render loop]; entry render)
    recognizer/               scan image + .omr -> RecognitionResult (package: constants,
                              image_io, fiducials, quad, registration, line_suppression,
                              sampling, classification, engine; entries recognize,
                              build_elements_from_cache)
    omr_format.py             the .omr JSON descriptor builders/parser (the contract)
    geometry.py               SHARED pixel conventions (see §8)
    colors.py                 Color name->value order + name->RGB table
    fonts.py                  (family,size,style) -> PIL font, with graceful fallback
```

**Data flow:**
- Generation: `OmrEngine.Generate(source, settings, ...)` → (markup_parser *or* a passed
  `TemplateConfig`) → `renderer.render()` → `(list[PIL.Image], descriptor dict)` →
  `GenerationResult` (`.Template` = `omr_format.to_json(descriptor)`).
- Recognition: `OmrEngine.GetTemplateProcessor(.omr)` → `omr_format.parse()` →
  `TemplateProcessor.Recognize(scan)` → `recognizer.recognize()` → `RecognitionResult`.

**Public vs internal:** everything under `omr/_internal/` and any leading-underscore
name is private. Never widen the public surface except to add a genuine Aspose
identifier. Keep CV/rendering imports lazy where they already are (so `import omr.api`
stays cheap and generation needs no OpenCV).

## 7. The `.omr` contract and the two testing invariants

### The `.omr` descriptor (`_internal/omr_format.py`) is the frozen contract
JSON of: per page → pixel `Width`/`Height`, `ReferenceCenters` (4 corner centroids),
`RotationMarker` box, and `Elements`. Every recognizable element collapses to a uniform
shape — a list of **fields** (sampling units), each an ordered list of **bubbles**
(`Value` + `[x, y, w, h]` `Box`) — plus a `ResultGrouping`:
- `"Field"` → each field becomes one recognized element (`answer_sheet` line, `choicebox`,
  `checkbox`).
- `"Element"` → all fields' marked values are concatenated into one element (`grid` /
  `composite_grid` digit strings).

The recognizer samples/classifies **without knowing element types** — so new bubble
elements just emit this shape. **Do not change the descriptor schema without updating
both the renderer (writer) and recognizer (reader) together.**

### Testing strategy (ported Aspose corpus under `tests/testdata/api/`)
The corpus is the Aspose.OMR for .NET test suite ported wholesale (~1864 files):
`<name>.txt` markup + `<name>_SAMPLE.csv` answer key / `.omr` / `.png` scan. Read
`tests/_testdata.py`'s module docstring before touching these tests. Four non-obvious
rules (learned the hard way — don't regress them):

1. **Recognition is a self-consistent ROUND TRIP, not scan-recognition.** This build is
   not pixel-faithful and defaults to A4 (Aspose uses Letter), so Aspose's `_SAMPLE.png`
   scans do not line up with a regenerated template. Tests instead: generate our own
   sheet → mark bubbles (driven by the CSV answer key where it maps cleanly, else
   synthesized) → recognize our own image → assert exact recovery.
2. **The corpus splits ~114 in-scope / ~123 out-of-scope.** Out-of-scope markup must be
   *reported* (`ErrorCode != 0`, message names the boundary), never raised.
3. **Element/question names are NOT unique** (e.g. `GridOrientation.txt` has two grids
   named `ID2`; the CSV has one row per occurrence). Compare **by name multiset** and
   consume CSV rows **occurrence-aware**. Keying by name (last-wins dict) silently drops a
   real answer key and hides regressions — do not do it.
4. **Execution-floor tests pin coverage** (`test_*_execution_floor`, `test_scope_split_is_stable`,
   in-scope ≥110, out-of-scope ≥115, round-trip ≥37, pure-csv ≥5). They exist so that a
   regression turning in-scope fixtures into skips *fails the build* instead of staying
   green. If you legitimately change the scope split, update the floors deliberately and
   explain why in the commit.

The in-bubble guide glyph is drawn light gray (`_GLYPH_GRAY = 210`) on purpose so the
recognizer's ink test (`fill < FILL_DARK_CUTOFF ≈ 175`) never counts it — an unmarked
bubble reads ~0%. If you change glyph lightness, the sampling cutoff, or the inset ratio,
re-verify `test_review_fixes.py::test_empty_glyph_bubbles_read_near_zero`.

## 8. `_internal/geometry.py` is the single source of truth

The generation **drawer** and the recognition **sampler** share this module so a drawn
bubble box and its sampled ROI stay aligned **by construction** (the sampled ROI is the inset of that box). Paper pixel
dims (@300 DPI), bubble diameters, reference-mark placement, and the `SAMPLE_INSET_RATIO`
all live here. **A mismatch here silently breaks recognition.** Never hard-code a pixel
dimension in `renderer.py` or `recognizer.py` that belongs in `geometry.py`; add it to
`geometry.py` and import it from both sides.

## 9. How to add an element or feature

1. Confirm the exact Aspose names/values in `../python_api.md` /
   `../aspose-omr-for-.net-API.md`.
2. Add the `*Config` class (correct `ConfigType`, verbatim property names) in
   `generation/config/elements/` (leaf) or `.../parents/` (container).
3. Teach the markup parser (`_internal/markup_parser/`): add the element to the factory
   in `elements.py` and a branch to the matching `_apply_*` applier in `attributes.py`
   (attribute keys verbatim).
4. Add a renderer handler in the `_internal/renderer/` package (bubble elements live in
   `questions.py`), register it in `HANDLERS` in `engine.py`, and emit the uniform `.omr`
   field/bubble shape via `omr_format.new_element/new_field/new_bubble`.
   Use `geometry.py` for every pixel dimension.
5. If recognizable, no recognizer change is usually needed (it is element-type-agnostic);
   pick the right `ResultGrouping`.
6. Add tests: a code-first generation test, a markup test, and a round-trip recovery test.
   If this moves the scope split, update the execution floors in
   `test_testdata_generation.py` / `test_testdata_recognition.py`.
7. Update `README.md` scope table and [ROADMAP.md](ROADMAP.md).

## 10. Conventions & etiquette

- Match the surrounding style: module docstrings explain the "why", `# backed by:`
  comments name the FOSS lib. Keep that density.
- Generation **reports** problems (`ErrorCode`/`ErrorMessage`), it does not throw — except
  genuine I/O errors like a missing markup file (`FileNotFoundError`) and a `None` source
  (`TypeError`). Preserve this contract.
- Prefer small, verifiable changes; run the full suite before declaring done, and report
  failures honestly with the output.
- Git: current branch is `master`, PRs target `main`. Branch before committing; only
  commit/push when asked. End commit messages with the required
  `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>` line.
- Record durable, non-obvious project facts in agent memory rather than re-deriving them.
