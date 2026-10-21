"""Quickstart: generate a form from the text-markup DSL file (examples/final-exam.txt).

Run from the repo root:

    python examples/quickstart_markup.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from omr.api import OmrEngine
from omr.generation import GlobalPageSettings, PaperSize, Orientation

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
os.makedirs(OUT, exist_ok=True)


def main() -> None:
    engine = OmrEngine()

    settings = GlobalPageSettings()
    settings.PaperSize = PaperSize.Letter
    settings.Orientation = Orientation.Vertical

    markup_path = os.path.join(HERE, "final-exam.txt")
    result = engine.Generate(markup_path, settings)
    if result.ErrorCode != 0:
        raise SystemExit(f"Generation failed: {result.ErrorMessage}")

    for warning in result.Warnings:
        print("WARNING:", warning)

    result.Save(OUT, "final-exam")
    print(f"Generated {os.path.join(OUT, 'final-exam.png')} + final-exam.omr")
    print("Open the PNG, fill some bubbles, scan it, then recognize with:")
    print("    processor = engine.GetTemplateProcessor('out/final-exam.omr')")
    print("    result = processor.Recognize('scan.png')")
    print("    print(result.GetCsv())")


if __name__ == "__main__":
    main()
