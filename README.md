# omr-python-for-foss

A **FOSS Python OMR (Optical Mark Recognition) library** whose public API is a
**name-preserving port** of [Aspose.OMR for .NET](https://docs.aspose.com/omr/net/)
v26.1.0. You author a bubble-sheet form (in code or in the text-markup DSL), generate
a printable PNG plus a machine-readable `.omr` descriptor, print/scan/fill it, and
recognize the marks back into answers — all through the exact Aspose class, method,
property and enum names.

It is built only on **`numpy` + `opencv-python` + `Pillow`** (no Windows/.NET
dependency). The computer-vision recognition math is modeled on the FOSS
[OMRChecker](https://github.com/Udayraj123/OMRChecker) project; **no API shape** is
borrowed from OMRChecker — the surface is purely the Aspose port.

```python
from omr.api import OmrEngine, FormValidationLogic

engine = OmrEngine()
gen = engine.Generate("final-exam.txt")          # or a code-first TemplateConfig
gen.Save("out", "final-exam")                    # -> out/final-exam.png + out/final-exam.omr

processor = engine.GetTemplateProcessor("out/final-exam.omr", FormValidationLogic.Ignore)
result = processor.Recognize("scan.png")         # -100 = auto-calibrated threshold
print(result.GetCsv())                           # also GetJson() / GetXml()
```

## Scope

This build implements **Layers 0-2** of the
feature plan, focused on the **core bubble-sheet slice**:

| Layer | What | Status |
|---|---|---|
| **0 — Foundation** | Package layout, all enums + 140-name color set, exception hierarchy, `FormValidationLogic`, `.omr` serializer, code-first config tree, `GlobalPageSettings`, `OmrEngine` | ✅ complete |
| **1 — Generation** | Render/layout engine, text-markup parser, `Generate` dispatch, `GenerationResult.Save` (PNG + `.omr`), reference-point drawing, bubble geometry | ✅ core element set |
| **2 — Recognition** | `.omr` loader, image decode, rotation/perspective/damage-robust reference-point registration (0/90/180/270° + skew + torn-corner reconstruction), scanner-line suppression, fill-ratio sampling, threshold + auto-calibration, `Recalculate`, light-shade processing, multiselect validation, CSV/JSON/XML export | ✅ complete |

**Supported elements (generation + recognition):**

- **Layout:** `page`, `container` (columns), `block` (borders/padding), `positioned_block`, `text`, `content` (incl. `content_type=cells`), `empty_line`, `image`
- **Bubble:** `answer_sheet`, `choicebox` + `option`, `checkbox`, `grid`, `composite_grid`

**Out of scope for this build** (per the chosen "core bubble-sheet slice"): tables &
score groups, `vertical_choicebox`/`answer`, `write_in`/ICR, `custom_answer_sheet`,
barcode/QR generation & decode, RTL/complex-script writing systems, PDF export
(`SaveAsPdf`), and all of **Layer 3** (batch processing, presets). The enums for every feature are still present and
correct (e.g. the full 67-member `BarcodeType`); only the heavier element rendering
and the deferred surfaces are omitted. Stubs raise `NotImplementedError` where a
method exists but is intentionally unimplemented.

## Install

```bash
pip install -r requirements.txt     # numpy, opencv-python, Pillow
# or, as a package:
pip install -e .
```

Requires Python 3.10+.

## Developing in VS Code

**This folder is the project root** and ships a ready-to-use VS Code setup in
[`.vscode/`](https://github.com/omr-python-for-foss/omr-python-for-foss/tree/main/.vscode). Open **this folder** directly in VS Code (File ▸ Open
Folder…). Every path in the config is `${workspaceFolder}`-relative, so you can
copy this project anywhere (e.g. to your Desktop) and it launches without editing a
single path.

1. **Create the environment** — run the task **`env: create (.venv + install all)`**
   (Terminal ▸ Run Task…). It creates `./.venv`, installs
   [`requirements-dev.txt`](https://github.com/omr-python-for-foss/omr-python-for-foss/blob/main/requirements-dev.txt) (runtime deps **+ pytest**) and does
   `pip install -e .`. Then choose that interpreter via **Python: Select Interpreter**
   (it is already the configured default).
2. **Run the library via client code** — press **F5** on any script that imports `omr`
   (e.g. [`examples/quickstart_codefirst.py`](https://github.com/omr-python-for-foss/omr-python-for-foss/blob/main/examples/quickstart_codefirst.py)), or use
   the **"Example: …"** / **"Python: Current file"** launch configs, or the **`run: …`**
   tasks.
3. **Run the tests** — use the Test Explorer (flask icon), the **`test: pytest …`**
   tasks, or the **"Debug tests: …"** launch configs. A green run is
   `436 passed, 264 skipped, 0 failed`.

## Two ways to author a form

**1. Text markup (the DSL).** Pass a `.txt` file, a `list[str]` of lines, or a binary
stream to `Generate`. Markup tokens are byte-identical to Aspose's. See
[`examples/final-exam.txt`](https://github.com/omr-python-for-foss/omr-python-for-foss/blob/main/examples/final-exam.txt). Attribute lines must begin with
a real **TAB**. (Note: `#` begins a **comment** line, matching the reference sample;
author choiceboxes with `?choicebox=` + `?option=` or inline `(char) Answer` lines.)

**2. Code-first `TemplateConfig`.** Build the `*Config` tree in code and pass it to
`Generate`. See [`examples/quickstart_codefirst.py`](https://github.com/omr-python-for-foss/omr-python-for-foss/blob/main/examples/quickstart_codefirst.py).

Both feed the same render engine and produce the same `.omr`.

## API fidelity

Class / method / property / enum-type / enum-member names are copied
**character-for-character** from Aspose.OMR for .NET (this intentionally overrides
PEP 8 — methods and properties stay PascalCase, e.g. `GetCsv`, `RecognizeFolder`,
`ErrorCode`). Source quirks are preserved deliberately, including:

- `BubbleSize.Extrasmall` / `Extralarge` (not `ExtraSmall` / `ExtraLarge`)
- `FontStyle.Strikeout`, and the `undefined = 0` sentinels
- `BorderType["None"]` / `TableType["None"]` (the reserved Python keyword `None` is
  kept as the exact member name via the enum functional API)
- the misspelled `recogintion_values` markup attribute (on the out-of-scope
  `bubble_array`)

Enum **integer values** are verbatim from the .NET source and are what the `.omr`
descriptor serializes. The module tree mirrors the `Aspose.OMR.*` namespaces under a
lowercased `omr` root (e.g. `Aspose.OMR.Api` → `omr.api`,
`Aspose.OMR.Generation.Config.Enums` → `omr.generation.config.enums`).

No licensing or metering: a FOSS build has nothing to gate, so Aspose's `License` /
`Metered` classes are **not** ported. Also removed as inapplicable to a headless FOSS
library: the correction UI (`GetCorrectionControl`, `CorrectionControl`), the buffer
pool (`PoolFactory`; `OmrEngine()` is parameterless), the plugin hooks (`AddPlugin` /
`IPlugin`), the legacy aliases (`GenerateTemplate`, `GenerateJSONTemplate`,
`RecognizeImage`), `SaveAsInteractivePdf`, the `ConfigType.Column`/`Header` aliases and
the obsolete `ContainerConfig.ColumnsCount`.

## How recognition works

1. **Decode** the scan (JPG/PNG/TIFF/BMP/GIF, path/stream/`ndarray`/`PIL.Image`) to
   grayscale.
2. **Register** the scan into template pixel space. The four solid corner fiducials are
   detected rotation-invariantly (minAreaRect + a 4-vertex/circularity test tells a
   square fiducial from a round mark or a hollow box), and a perspective transform
   (`cv2.getPerspectiveTransform` + `warpPerspective`) de-skews them onto the template
   corners. Orientation (0/90/180/270°) is resolved by trying each and keeping the one
   that restores the asymmetric rotation marker to its template spot; a torn/occluded
   corner (only 3 fiducials) is reconstructed by parallelogram completion; and when the
   scan is already aligned (a flatbed scan or digital fill) a plain resize is used
   directly. Long thin dark runs (scanner banding, roller streaks) are suppressed before
   sampling so they cannot inflate a bubble's fill. See
   [`tests/test_distortion_recognition.py`](https://github.com/omr-python-for-foss/omr-python-for-foss/blob/main/tests/test_distortion_recognition.py) and
   [`examples/advanced_demo.py`](https://github.com/omr-python-for-foss/omr-python-for-foss/blob/main/examples/advanced_demo.py).
3. **Sample fill ratios** — for every bubble, measure the percentage of *ink* pixels
   (below a fixed cutoff) in its inset ROI on a min-max-normalized page, as a 0-100
   fill value. The cutoff is chosen so the light in-bubble guide glyph is never
   counted, so an unmarked bubble reads ~0%.
4. **Classify** filled vs blank. With a fixed `recognitionThreshold` (0-100) a bubble
   is marked when `fill >= threshold`. With the default `-100` (auto), the cut is
   found per question by sorting the field's fills and taking the midpoint of the
   first convincing gap (2-wide window), falling back to a page-global threshold — the
   OMRChecker gap-detection approach, with its constants rescaled to 0-100.
5. **Assemble** a `RecognitionResult`; per-bubble fills are cached so
   `TemplateProcessor.Recalculate(result, newThreshold)` re-scores without re-reading
   pixels.

The generation **drawer** and the recognition **sampler** share one geometry module
(`omr/_internal/geometry.py`), so a drawn bubble box and its sampled ROI are the same
rectangle by construction. The `.omr` JSON is the frozen contract between the two
pipelines.

## The `.omr` descriptor

JSON with, per page, the pixel size, the reference-mark centroids, and every
recognizable element reduced to a uniform shape: a list of **fields** (sampling
units), each with ordered **bubbles** carrying a returned value and an `[x, y, w, h]`
box. Two grouping modes drive result assembly: `"Field"` (each field → one recognized
element, e.g. one per `answer_sheet` line) and `"Element"` (fields' marked values
concatenated into one element, e.g. the `grid` digit string).

## Known limitations / deviations

- **Registration** is robust to the degradations a real scan or phone photo introduces,
  each handled individually: any cardinal rotation (0/90/180/270°), skew and perspective,
  scanner banding, ink smudges/scribbles, and a torn corner on an otherwise upright scan
  (an aligned same-size scan recovers directly, so the missing corner is irrelevant; the
  3-fiducial reconstruction additionally helps a torn corner under mild skew). It assumes
  the four corner marks are visible at a reasonable resolution (the Aspose design
  assumption is ≥300 DPI). **Known limits** (the registration objective is a single
  rotation-marker ROI, which the following defeat): extreme oblique perspective (keystone
  beyond a firm hand-held angle); and a **torn corner *combined* with significant
  skew/perspective** or the worst-case stacking of skew + heavy banding + a fiducial-
  covering smudge — in those a stray mark can satisfy the marker check and the scan may be
  **silently misregistered**. See the envelope note in
  [`tests/test_distortion_recognition.py`](https://github.com/omr-python-for-foss/omr-python-for-foss/blob/main/tests/test_distortion_recognition.py).
- **`#` in markup is a comment**, not the choicebox shorthand — the reference DSL
  documents both and the provided sample uses `#` for comments, so the sample wins.
- **Grid orientation** follows the .NET spec: `horizontal` (default) = each digit is a
  *column* of bubbles; `vertical` = each digit is a *row*.
- A few attributes are accepted for API fidelity but **not rendered** in the core slice:
  `choicebox.display_number` (questions carry their own number in the text),
  `option.row_index` (options auto-wrap), and `block.background_color` (border only).
- Rendering is pragmatic (fixed spacing, LTR), not the pixel-faithful Aspose
  typesetter; complex tables, hyphenation and RTL are out of scope.
- `SaveAsPdf` / `GetPDF` raise `NotImplementedError` (deferred output formats).

## Project layout

```
omr/
  __init__.py                 __version__ (no License/Metered in a FOSS build)
  api/                        OmrEngine, TemplateProcessor, ImageCollection, FormValidationLogic
  model/                      RecognitionResult, IOmrElement
  generation/                 enums, GlobalPageSettings, GenerationResult, offsets, ...
    config/                   BaseConfig, ParentConfig, TemplateConfig, BorderStyle
      enums/                  all config enums (ConfigType, BarcodeType, QRVersion, ...)
      elements/              leaf element configs (+ parents/ for container elements)
    overflowactions/          OverflowAction, Clip, NoClip, Wrap
    writingsystems/           WritingSystem, Western, Arabic, ...
  recognition/enums/          FormValidationLogic (canonical)
  exceptions/                 OMRException hierarchy
  _internal/                  render engine, recognizer, .omr format, markup parser,
                              geometry, fonts, color table (NOT part of the public API)
examples/                     quickstart scripts + final-exam.txt
tests/                        pytest suite (enums, generation, markup, round trip)
```

## Testing

```bash
python -m pytest -q
```

The suite covers enum name/value fidelity, generation + `.omr` structure, the
text-markup parser, and the full **generate → fill bubbles → recognize → verify**
round trip (including a skew/perspective registration path, `Recalculate`, multiselect
validation, and CSV/JSON/XML export).

## License

MIT.
