# Changelog

All notable changes to **omr-python-for-foss** are documented here. The format
is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this
project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-10-14

Initial public release: a FOSS Python OMR (Optical Mark Recognition) library
whose public API is a name-preserving port of the Aspose.OMR for .NET surface
(Layers 0-2: foundation, generation, recognition), built only on `numpy`,
`opencv-python`, and `Pillow`.

### Added
- **Layer 0 — Foundation:** full enum set + 140-name color table, exception
  hierarchy, `FormValidationLogic`, the `.omr` descriptor serializer, the
  code-first `TemplateConfig` tree, `GlobalPageSettings`, and `OmrEngine`.
- **Layer 1 — Generation:** render/layout engine, text-markup DSL parser,
  `Generate` dispatch, `GenerationResult.Save` (PNG + `.omr`), and the core
  element set (`page`, `container`, `block`, `positioned_block`, `text`,
  `content`, `empty_line`, `image`, `answer_sheet`, `choicebox`, `checkbox`,
  `grid`, `composite_grid`).
- **Layer 2 — Recognition:** `.omr` loader, rotation/perspective/damage-robust
  reference-point registration (0/90/180/270°, skew + perspective de-warp,
  3-of-4 fiducial reconstruction, scanner-line suppression), fill-ratio
  sampling, fixed-threshold and auto-calibrated classification, `Recalculate`,
  light-shade processing, multiselect validation, `RecognizeFolder` batch, and
  CSV/JSON/XML export.

See [ROADMAP.md](https://github.com/omr-python-for-foss/omr-python-for-foss/blob/main/ROADMAP.md)
for the deferred feature surface.

[Unreleased]: https://github.com/omr-python-for-foss/omr-python-for-foss/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/omr-python-for-foss/omr-python-for-foss/releases/tag/v0.1.0
