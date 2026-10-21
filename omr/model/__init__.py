"""Recognition results & export.

Port of ``Aspose.OMR.Model``: ``RecognitionResult`` (the container returned by every
``Recognize*`` call) and ``IOmrElement`` (one recognized question). Method/property
names/casing are copied verbatim from the .NET source (intentionally non-PEP8).
Instances are produced by ``omr.api.TemplateProcessor``; do not construct directly.
"""
from __future__ import annotations

import csv
import io
import json
import typing
import xml.etree.ElementTree as ET

__all__ = ["RecognitionResult", "IOmrElement"]


@typing.runtime_checkable
class IOmrElement(typing.Protocol):
    """The interface for the OMR elements (one recognized question/element)."""

    QuestionName: str
    SortWeight: int

    def GetAnswer(self) -> str:
        """Forms a string with the recognition result for this element."""
        ...

    def GetCsv(self) -> str:
        """Forms this element's answers as a comma-separated-values fragment."""
        ...


class _OmrElement:
    """Concrete ``IOmrElement`` implementation (not part of the public surface)."""

    def __init__(self, question_name: str, sort_weight: int, answer: str) -> None:
        self.QuestionName: str = question_name
        self.SortWeight: int = sort_weight
        self._answer: str = answer

    def GetAnswer(self) -> str:
        return self._answer

    def GetCsv(self) -> str:
        buf = io.StringIO()
        writer = csv.writer(buf, lineterminator="")
        writer.writerow([self.QuestionName, self._answer])
        return buf.getvalue()

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<OmrElement {self.QuestionName!r}={self._answer!r}>"


class RecognitionResult:
    """The result of image recognition. Contains all OMR elements with detailed
    recognition information and methods for results export."""

    def __init__(self) -> None:
        self.ImagePath: str = ""
        self.Images: list[typing.Any] = []
        self.OmrElements: list[IOmrElement] = []
        self.PageName: str = ""
        self.TemplateName: str = ""
        # Private caches used by TemplateProcessor.Recalculate (fill ratios per
        # bubble + the validation logic), so re-scoring needs no pixels.
        self._fill_cache: list[dict] = []
        self._validation = None

    # ── internal helpers ──

    def _sorted_elements(self) -> list[IOmrElement]:
        return sorted(self.OmrElements, key=lambda e: e.SortWeight)

    # ── CSV ──

    def GetCsv(self, encoding: str | None = None):
        buf = io.StringIO()
        writer = csv.writer(buf, lineterminator="\n")
        writer.writerow(["Question", "Answer"])
        for el in self._sorted_elements():
            writer.writerow([el.QuestionName, el.GetAnswer()])
        text = buf.getvalue()
        if encoding is None:
            return text
        return text.encode(encoding)

    def GetCsvAsStream(self, encoding: str = "utf-8") -> io.BytesIO:
        stream = io.BytesIO(self.GetCsv(encoding or "utf-8"))
        stream.seek(0)
        return stream

    # ── JSON ──

    def _json_obj(self) -> dict:
        return {
            "TemplateName": self.TemplateName,
            "PageName": self.PageName,
            "ImagePath": self.ImagePath,
            "Elements": [
                {"QuestionName": el.QuestionName, "Answer": el.GetAnswer()}
                for el in self._sorted_elements()
            ],
        }

    def GetJson(self, encoding: str | None = None):
        text = json.dumps(self._json_obj(), indent=2, ensure_ascii=False)
        if encoding is None:
            return text
        return text.encode(encoding)

    def GetJsonAsStream(self, encoding: str = "utf-8") -> io.BytesIO:
        stream = io.BytesIO(self.GetJson(encoding or "utf-8"))
        stream.seek(0)
        return stream

    # ── XML ──

    def _xml_string(self) -> str:
        root = ET.Element("RecognitionResult")
        root.set("TemplateName", self.TemplateName)
        root.set("PageName", self.PageName)
        root.set("ImagePath", self.ImagePath)
        for el in self._sorted_elements():
            node = ET.SubElement(root, "Element")
            node.set("QuestionName", el.QuestionName)
            node.set("Answer", el.GetAnswer())
        return ET.tostring(root, encoding="unicode")

    def GetXml(self, encoding: str | None = None):
        text = self._xml_string()
        if encoding is None:
            return text
        return text.encode(encoding)

    def GetXmlAsStream(self, encoding: str = "utf-8") -> io.BytesIO:
        stream = io.BytesIO(self.GetXml(encoding or "utf-8"))
        stream.seek(0)
        return stream
