from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

ManualStatus = Literal["unchecked", "edited", "validated", "review", "ignored"]
SourceLang = Literal["en", "ja"]


@dataclass(slots=True)
class OcrBlock:
    """A localized OCR block kept compatible with future bubble replacement."""

    id: str
    bbox: list[int]  # [x1, y1, x2, y2] in original page pixels
    source_lang: SourceLang
    ocr_text: str
    ocr_corrected_text: str = ""
    normalized_source_text: str = ""
    raw_translation_fr: str = ""
    translation_fr: str = ""
    confidence: float | None = None
    reading_order: int = 0
    manual_status: ManualStatus = "unchecked"
    quality_warnings: list[str] = field(default_factory=list)
    ocr_alternatives: list[dict[str, Any]] = field(default_factory=list)
    review_notes: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "OcrBlock":
        return cls(
            id=str(data["id"]),
            bbox=[int(v) for v in data.get("bbox", [0, 0, 0, 0])],
            source_lang=data.get("source_lang", "en"),
            ocr_text=str(data.get("ocr_text", "")),
            ocr_corrected_text=str(data.get("ocr_corrected_text", "")),
            normalized_source_text=str(data.get("normalized_source_text", "")),
            raw_translation_fr=str(data.get("raw_translation_fr", "")),
            translation_fr=str(data.get("translation_fr", "")),
            confidence=(None if data.get("confidence") is None else float(data["confidence"])),
            reading_order=int(data.get("reading_order", 0)),
            manual_status=data.get("manual_status", "unchecked"),
            quality_warnings=[str(item) for item in data.get("quality_warnings", [])],
            ocr_alternatives=[dict(item) for item in data.get("ocr_alternatives", []) if isinstance(item, dict)],
            review_notes=str(data.get("review_notes", "")),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class PageRecord:
    page_index: int
    image_name: str
    blocks: list[OcrBlock] = field(default_factory=list)
    status: str = "new"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PageRecord":
        return cls(
            page_index=int(data["page_index"]),
            image_name=str(data["image_name"]),
            blocks=[OcrBlock.from_dict(item) for item in data.get("blocks", [])],
            status=str(data.get("status", "new")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "page_index": self.page_index,
            "image_name": self.image_name,
            "status": self.status,
            "blocks": [block.to_dict() for block in self.blocks],
        }


@dataclass(slots=True)
class ProjectData:
    cbz_path: str
    pages: list[PageRecord]
    version: int = 1
    glossary_terms: str = ""

    @classmethod
    def from_images(cls, cbz_path: str | Path, image_names: list[str]) -> "ProjectData":
        return cls(
            cbz_path=str(cbz_path),
            pages=[PageRecord(page_index=i, image_name=name) for i, name in enumerate(image_names)],
            glossary_terms="",
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProjectData":
        return cls(
            cbz_path=str(data.get("cbz_path", "")),
            version=int(data.get("version", 1)),
            glossary_terms=str(data.get("glossary_terms", "")),
            pages=[PageRecord.from_dict(item) for item in data.get("pages", [])],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "cbz_path": self.cbz_path,
            "glossary_terms": self.glossary_terms,
            "pages": [page.to_dict() for page in self.pages],
        }

    def page_by_index(self, index: int) -> PageRecord:
        return self.pages[index]
