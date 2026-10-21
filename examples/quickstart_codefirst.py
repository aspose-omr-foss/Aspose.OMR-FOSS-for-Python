"""Quickstart: build a form in code, generate it, then recognize a filled copy.

Run from the repo root:

    python examples/quickstart_codefirst.py

Outputs quiz.png + quiz.omr (and a simulated filled scan) into ./out, and prints the
recognized answers. Uses the EXACT Aspose-style API names throughout.
"""
import json
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from omr.api import OmrEngine, FormValidationLogic
from omr.generation import GlobalPageSettings, PaperSize, Orientation, BubbleSize, Color
from omr.generation.config import TemplateConfig
from omr.generation.config.elements import (
    TextConfig, AnswerSheetConfig, ChoiceBoxConfig, ChoiceBoxAnswerConfig,
    GridConfig, ContentConfig,
)
from omr.generation.config.elements.parents import PageConfig, CheckBoxConfig
from omr.generation.config.enums import BubbleType

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
os.makedirs(OUT, exist_ok=True)


def build_template() -> TemplateConfig:
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

    question = ChoiceBoxConfig()
    question.Name = "capital"
    question.QuestionText = "Capital of France?"
    for name, value in [("Paris", "A"), ("Berlin", "B"), ("Rome", "C")]:
        opt = ChoiceBoxAnswerConfig()
        opt.Name = name
        opt.BubbleValue = value
        question.Children.append(opt)

    student_id = GridConfig()
    student_id.Name = "StudentID"
    student_id.SectionsCount = 4
    student_id.OptionsCount = 10
    student_id.GridOrientation = Orientation.Vertical
    student_id.BubbleSize = BubbleSize.Small

    consent = CheckBoxConfig()
    consent.Name = "I confirm:"
    for label in ["answers are my own", "rules were read"]:
        c = ContentConfig()
        c.Name = label
        consent.Children.append(c)

    page.Children = [title, answers, question, student_id, consent]
    template.Children = [page]
    return template


def simulate_fill(png_path: str, descriptor: dict, targets) -> str:
    img = Image.open(png_path).convert("RGB")
    draw = ImageDraw.Draw(img)
    for elem, field, value in targets:
        box = None
        for page in descriptor["Pages"]:
            for e in page["Elements"]:
                if e["Name"] != elem:
                    continue
                for f in e["Fields"]:
                    if field is not None and f["Name"] != field:
                        continue
                    for b in f["Bubbles"]:
                        if b["Value"] == value:
                            box = b["Box"]
        x, y, w, h = box
        r = w * 0.40
        cx, cy = x + w / 2, y + h / 2
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(10, 10, 10))
    out = os.path.join(OUT, "quiz_filled.png")
    img.save(out)
    return out


def main() -> None:
    engine = OmrEngine()

    settings = GlobalPageSettings()
    settings.PaperSize = PaperSize.A4
    settings.Orientation = Orientation.Vertical
    settings.BubbleColor = Color.Black

    result = engine.Generate(build_template(), settings)
    if result.ErrorCode != 0:
        raise SystemExit(f"Generation failed: {result.ErrorMessage}")
    result.Save(OUT, "quiz")
    print(f"Generated: {os.path.join(OUT, 'quiz.png')} + quiz.omr")

    descriptor = json.loads(result.Template)
    filled = simulate_fill(os.path.join(OUT, "quiz.png"), descriptor, [
        ("MainQuestions", "MainQuestions1", "B"),
        ("MainQuestions", "MainQuestions2", "D"),
        ("MainQuestions", "MainQuestions5", "A"),
        ("capital", "capital", "Paris"),
        ("StudentID", "StudentID_1", "2"),
        ("StudentID", "StudentID_2", "0"),
        ("StudentID", "StudentID_3", "2"),
        ("StudentID", "StudentID_4", "6"),
        ("I confirm:", "I confirm:", "answers are my own"),
    ])
    print(f"Simulated filled scan: {filled}")

    processor = engine.GetTemplateProcessor(os.path.join(OUT, "quiz.omr"),
                                            FormValidationLogic.Ignore)
    recognized = processor.Recognize(filled)  # -100 = auto-calibrated threshold

    print("\nRecognized answers:")
    for element in sorted(recognized.OmrElements, key=lambda e: e.SortWeight):
        print(f"  {element.QuestionName:18} = {element.GetAnswer()!r}")

    print("\nCSV:\n" + recognized.GetCsv())


if __name__ == "__main__":
    main()
