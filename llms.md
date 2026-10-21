# omr-python-for-foss — LLM Context

omr-python-for-foss is a pure-Python OMR (Optical Mark Recognition) library for authoring
bubble-sheet forms, generating a printable PNG plus a machine-readable `.omr` descriptor,
and recognizing the filled marks back into answers. The current package version is `0.1.0`.
Its public API is a **name-preserving port of Aspose.OMR for .NET v26.1.0**: the top-level
import package is `omr`, and the working types live in `omr.api`, `omr.generation`,
`omr.model`, and `omr.exceptions`.

This document is a high-confidence usage guide, not an exhaustive API reference. When it
conflicts with the repository, use the following sources in order:

1. `omr/` for behavior
2. each subpackage's `__init__.py::__all__` for supported imports (e.g.
   `omr/api/__init__.py`, `omr/generation/__init__.py`, `omr/model/__init__.py`)
3. `examples/` for executable public workflows
4. `README.md` for installation and scope, and `AGENTS.md` for conventions

## Installation

```bash
pip install -r requirements.txt     # numpy, opencv-python, Pillow
# or, as a package:
pip install -e .
```

Python 3.10 or later is required. The runtime dependencies are `numpy>=1.23`,
`opencv-python>=4.6`, and `Pillow>=9.2`. There is no .NET or Windows dependency.

## Rules for Generated Code

- Public identifiers are **PascalCase and copied character-for-character from Aspose.OMR for
  .NET**. Methods and properties stay PascalCase: `Generate`, `GetTemplateProcessor`,
  `Recognize`, `RecognizeFolder`, `Recalculate`, `GetCsv`, `ErrorCode`,
  `ApplyLightShadeProcessing`. This intentionally overrides PEP 8; never "fix" a public name
  to snake_case.
- Do not invent names. Use only identifiers exported from each subpackage's `__all__`.
  Anything under `omr._internal/` or any leading-underscore name is private and must not be
  imported.
- Enum **integer values** are verbatim from the .NET source and are serialized into the
  `.omr` descriptor; never change them. Member **names** are verbatim too, including the
  deliberate quirks below.
- Preserve source quirks exactly: `BubbleSize.Extrasmall` / `BubbleSize.Extralarge` (not
  `ExtraSmall` / `ExtraLarge`), `FontStyle.Strikeout`, the `undefined = 0` sentinels on
  most enums, and `BorderType["None"]` / `TableType["None"]` — the member is named `None`,
  a reserved Python keyword, so it is reached with bracket access, not attribute access.
- Generation **reports** problems; it does not raise for unsupported markup or elements.
  Always check `result.ErrorCode == 0` before using a `GenerationResult`; read
  `result.ErrorMessage` otherwise. The only generation exceptions are a missing markup file
  (`FileNotFoundError`) and a `None` source (`TypeError`).
- Recognition threshold is an `int` in `0-100`, or `-100` (the default) for a per-question
  auto-calibrated cut. Do not pass a `0.0-1.0` float.
- Obtain a `TemplateProcessor` only from `OmrEngine.GetTemplateProcessor(...)`. Do not
  construct `TemplateProcessor`, `RecognitionResult`, or `GenerationResult` directly; they
  come from the engine.
- This is a FOSS build with features intentionally removed. Do not generate calls to
  Aspose's `License` / `Metered`, the correction UI (`GetCorrectionControl`,
  `CorrectionControl`), the buffer pool (`PoolFactory`; `OmrEngine()` is parameterless), the
  plugin hooks (`AddPlugin` / `IPlugin`), the legacy aliases (`GenerateTemplate`,
  `GenerateJSONTemplate`, `RecognizeImage`), or `SaveAsInteractivePdf`.
- Methods that exist but are deferred (`GenerationResult.SaveAsPdf`,
  `MemoryGenerationResult.GetPDF`) raise `NotImplementedError`. Do not present them as
  working.

## Core Generation Usage

Build a form in code with the `*Config` tree and pass it to `OmrEngine.Generate`:

```python
from omr.api import OmrEngine
from omr.generation import GlobalPageSettings, PaperSize, Orientation, BubbleSize, Color
from omr.generation.config import TemplateConfig
from omr.generation.config.elements import AnswerSheetConfig, TextConfig
from omr.generation.config.elements.parents import PageConfig
from omr.generation.config.enums import BubbleType

template = TemplateConfig()
template.Name = "quiz"
page = PageConfig()

title = TextConfig()
title.Name = "Weekly Quiz"
title.FontSize = 28

answers = AnswerSheetConfig()
answers.Name = "MainQuestions"
answers.ElementsCount = 6
answers.AnswersCount = 4
answers.AnswersValues = ["A", "B", "C", "D"]
answers.ColumnsCount = 2
answers.StartId = 1
answers.BubbleType = BubbleType.Round
answers.BubbleSize = BubbleSize.Normal

page.Children = [title, answers]
template.Children = [page]

engine = OmrEngine()
settings = GlobalPageSettings()
settings.PaperSize = PaperSize.A4
settings.Orientation = Orientation.Vertical
settings.BubbleColor = Color.Black

result = engine.Generate(template, settings)
if result.ErrorCode != 0:
    raise SystemExit(result.ErrorMessage)
result.Save("out", "quiz")          # -> out/quiz.png + out/quiz.omr
```

Alternatively, author the form in the Aspose text-markup DSL and pass the source to the same
`Generate`. The source may be a markup file path (`str`), a `list[str]` of lines, or a
binary/text stream:

```python
from omr.api import OmrEngine
from omr.generation import GlobalPageSettings, PaperSize

engine = OmrEngine()
settings = GlobalPageSettings()
settings.PaperSize = PaperSize.Letter

result = engine.Generate("final-exam.txt", settings)
if result.ErrorCode != 0:
    raise SystemExit(result.ErrorMessage)
for warning in result.Warnings:
    print("WARNING:", warning)
result.Save("out", "final-exam")    # -> out/final-exam.png + out/final-exam.omr
```

`GenerationResult` carries `ErrorCode`, `ErrorMessage`, `Template` (the `.omr` JSON string),
`TemplateImage`, `MultipageTemplateImages`, and `Warnings`. `Save(folder, name)` writes the
PNG page(s) plus `<name>.omr`; `folder=""` means the current directory. For in-memory output
wrap it with `MemoryGenerationResult(result)` and call `GetImages()` / `GetOmr()`.

## Recognition Usage

Load the `.omr` template, recognize a scan, and export:

```python
from omr.api import OmrEngine, FormValidationLogic

engine = OmrEngine()
processor = engine.GetTemplateProcessor("out/quiz.omr", FormValidationLogic.Ignore)

result = processor.Recognize("scan.png")      # -100 = auto-calibrated threshold

for element in sorted(result.OmrElements, key=lambda e: e.SortWeight):
    print(element.QuestionName, "=", element.GetAnswer())

print(result.GetCsv())                         # also result.GetJson() / result.GetXml()
```

- `Recognize(source, recognitionThreshold=-100)` takes an image path, stream, `ndarray`, or
  `PIL.Image`. A `list` source is treated as one multi-page form and merged into a single
  result.
- `RecognizeFolder(folderPath, recognitionThreshold=-100)` recognizes every supported image
  (`.jpg/.jpeg/.png/.tif/.tiff/.bmp/.gif`) in a folder, each as an independent form, and
  returns a list of `RecognitionResult`.
- `Recalculate(result, recognitionThreshold)` re-scores an existing result in place at a new
  threshold using cached per-bubble fill ratios — no pixels are re-read.
- Set `processor.ApplyLightShadeProcessing = True` before `Recognize` to normalize faint
  pencil marks.
- `FormValidationLogic.Ignore` (the default) ignores validation violations;
  `FormValidationLogic.Exception` raises a `MultiselectException` when a single-select
  question has more than one mark.

`RecognitionResult` exposes `OmrElements` (each an `IOmrElement` with `QuestionName`,
`SortWeight`, `GetAnswer()`), plus `GetCsv()`, `GetJson()`, `GetXml()` and their
`*AsStream` variants. Passing an `encoding` to an exporter returns `bytes` instead of `str`.

## Public API Groups

Inspect each subpackage's `__init__.py` before asserting that a symbol is importable.

- **Engine and recognition** (`omr.api`): `OmrEngine`, `TemplateProcessor`,
  `ImageCollection`, `FormValidationLogic`.
- **Generation** (`omr.generation`): enums `PaperSize`, `Orientation`, `BubbleSize`,
  `FontStyle`, `Color`, `RotationPointPosition`, `LongWordHandling`; settings
  `GlobalPageSettings`, `ReferencePointsSettings`, `BaseOffset`, `PixelOffset`; results
  `GenerationResult`, `MemoryGenerationResult`; and `TemplateConfig` (re-exported).
- **Code-first config tree** (`omr.generation.config` and its subpackages): `TemplateConfig`,
  `BaseConfig`, `ParentConfig`, `BorderStyle`; leaf elements (`omr.generation.config.elements`)
  `TextConfig`, `ContentConfig`, `EmptyLineConfig`, `ImageConfig`, `AnswerSheetConfig`,
  `ChoiceBoxConfig`, `ChoiceBoxAnswerConfig`, `GridConfig`, `CompositeGridConfig`; container
  elements (`omr.generation.config.elements.parents`) `PageConfig`, `BlockConfig`,
  `ContainerConfig`, `PositionedBlockConfig`, `CheckBoxConfig`.
- **Config enums** (`omr.generation.config.enums`): `ConfigType`, `BubbleType`,
  `BubblePositionType`, `ContentType`, `BorderType`, `TableType`, `AlignmentEnum`,
  `VerticalAlignment`, `Directionality`, `ContainerTypeEnum`, `ParagraphTypeEnum`,
  `GridHeaderTypeEnum`, `LongWordHandling`, `TriggerType`, `ScoreDisplay`, `ScoreGroupType`,
  `ScoreHeaderType`, `BarcodeType`, `QRVersion`.
- **Overflow and writing systems**: `omr.generation.overflowactions` (`OverflowAction`,
  `Clip`, `NoClip`, `Wrap`); `omr.generation.writingsystems` (`WritingSystem`, `Western`,
  `Arabic`, `Bengali`, `Hebrew`, `Persian`, `Urdu` — the core treats all as LTR Western).
- **Results** (`omr.model`): `RecognitionResult`, `IOmrElement`.
- **Exceptions** (`omr.exceptions`): `OMRException` (base), `RuntimeExceptionOMR`,
  `InvalidConfigurationException`, `ChildOverflowException`, `MultiselectException`.

The module tree mirrors the `Aspose.OMR.*` namespaces under a lowercased `omr` root (e.g.
`Aspose.OMR.Api` → `omr.api`, `Aspose.OMR.Generation.Config.Enums` →
`omr.generation.config.enums`).

## The `.omr` Descriptor

`GenerationResult.Template` is the `.omr` JSON contract between the two pipelines. Per page it
records the pixel `Width`/`Height`, the reference-mark centroids, the rotation-marker box, and
`Elements`. Every recognizable element reduces to a uniform shape: a list of **fields**
(sampling units), each an ordered list of **bubbles** (a returned `Value` plus an
`[x, y, w, h]` `Box`), plus a `ResultGrouping` of `"Field"` (each field becomes one recognized
element) or `"Element"` (the fields' marked values are concatenated, as for a `grid` digit
string). The recognizer samples and classifies without knowing element types.

## Scope and Limitations

- This build implements **Layers 0-2** (foundation, generation, recognition) of the feature
  plan, focused on the core bubble-sheet slice. Supported elements: `page`, `container`,
  `block`, `positioned_block`, `text`, `content`, `empty_line`, `image`, `answer_sheet`,
  `choicebox` + `option`, `checkbox`, `grid`, `composite_grid`.
- Out of scope for this build (reported via `ErrorCode`, not raised): tables and score
  groups, `vertical_choicebox` / `answer`, `write_in` / ICR, `custom_answer_sheet`, barcode
  and QR generation/decode, RTL / complex-script writing systems, PDF export (`SaveAsPdf`),
  and Layer 3 batch/preset processing. The enums for every deferred feature are still present
  and correct (e.g. the full `BarcodeType`); only the heavy rendering/decoding is omitted.
- Registration is robust to the degradations a real scan or phone photo introduces, each
  handled individually: any cardinal rotation (0/90/180/270°), skew, perspective, scanner
  banding, ink smudges, and a torn corner on an otherwise upright scan. Stacked worst cases
  (a torn corner combined with significant skew/perspective, or extreme oblique perspective)
  are documented limits, not supported.
- Rendering is pragmatic (fixed spacing, LTR), not the pixel-faithful Aspose typesetter.

## Development and Verification

```bash
python -m pytest -q
```

The suite covers enum name/value fidelity, generation and `.omr` structure, the text-markup
parser, and the full generate → fill bubbles → recognize → verify round trip. A green run is
`N passed, M skipped, 0 failed`; the skips are the out-of-scope corpus fixtures and are
expected. Run the examples directly, e.g. `python examples/quickstart_codefirst.py`.
