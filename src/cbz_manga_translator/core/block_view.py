from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from cbz_manga_translator.core.models import OcrBlock, PageRecord, ProjectData

BlockFilter = Literal["all", "warnings", "review", "untranslated", "unvalidated", "validated", "ignored"]


@dataclass(frozen=True, slots=True)
class BlockStats:
    total: int = 0
    active: int = 0
    warnings: int = 0
    review: int = 0
    untranslated: int = 0
    validated: int = 0
    ignored: int = 0

    def as_status_text(self) -> str:
        return (
            f"{self.active}/{self.total} actifs · "
            f"{self.validated} validés · "
            f"{self.warnings} QC · "
            f"{self.review} à revoir · "
            f"{self.untranslated} sans trad"
        )


@dataclass(frozen=True, slots=True)
class ProjectStats:
    pages: int = 0
    blocks: int = 0
    validated_blocks: int = 0
    warning_blocks: int = 0
    review_blocks: int = 0
    translated_pages: int = 0
    validated_pages: int = 0

    def as_status_text(self) -> str:
        return (
            f"{self.pages} pages · "
            f"{self.blocks} blocs · "
            f"{self.validated_blocks} blocs validés · "
            f"{self.warning_blocks} QC · "
            f"{self.review_blocks} à revoir · "
            f"{self.translated_pages} pages traduites · "
            f"{self.validated_pages} pages validées"
        )


def block_display_source(block: OcrBlock) -> str:
    return block.normalized_source_text or block.ocr_corrected_text or block.ocr_text


def block_matches_filter(block: OcrBlock, block_filter: BlockFilter) -> bool:
    if block_filter == "all":
        return True
    if block_filter == "warnings":
        return bool(block.quality_warnings)
    if block_filter == "review":
        return block.manual_status == "review"
    if block_filter == "untranslated":
        return block.manual_status != "ignored" and not block.translation_fr.strip()
    if block_filter == "unvalidated":
        return block.manual_status not in {"validated", "ignored"}
    if block_filter == "validated":
        return block.manual_status == "validated"
    if block_filter == "ignored":
        return block.manual_status == "ignored"
    return True


def block_matches_search(block: OcrBlock, query: str) -> bool:
    terms = [part.casefold() for part in query.split() if part.strip()]
    if not terms:
        return True
    haystack = "\n".join(
        [
            block.id,
            block.ocr_text,
            block.ocr_corrected_text,
            block.normalized_source_text,
            block.raw_translation_fr,
            block.translation_fr,
            "\n".join(block.quality_warnings),
        ]
    ).casefold()
    return all(term in haystack for term in terms)


def visible_blocks(blocks: list[OcrBlock], block_filter: BlockFilter = "all", query: str = "") -> list[OcrBlock]:
    return [
        block
        for block in sorted(blocks, key=lambda item: item.reading_order)
        if block_matches_filter(block, block_filter) and block_matches_search(block, query)
    ]


def page_block_stats(page: PageRecord) -> BlockStats:
    total = len(page.blocks)
    ignored = sum(1 for block in page.blocks if block.manual_status == "ignored")
    active_blocks = [block for block in page.blocks if block.manual_status != "ignored"]
    return BlockStats(
        total=total,
        active=len(active_blocks),
        warnings=sum(1 for block in page.blocks if block.quality_warnings),
        review=sum(1 for block in page.blocks if block.manual_status == "review"),
        untranslated=sum(1 for block in active_blocks if not block.translation_fr.strip()),
        validated=sum(1 for block in page.blocks if block.manual_status == "validated"),
        ignored=ignored,
    )


def project_stats(project: ProjectData) -> ProjectStats:
    pages = len(project.pages)
    blocks = sum(len(page.blocks) for page in project.pages)
    validated_blocks = 0
    warning_blocks = 0
    review_blocks = 0
    translated_pages = 0
    validated_pages = 0
    for page in project.pages:
        active = [block for block in page.blocks if block.manual_status != "ignored"]
        validated_blocks += sum(1 for block in page.blocks if block.manual_status == "validated")
        warning_blocks += sum(1 for block in page.blocks if block.quality_warnings)
        review_blocks += sum(1 for block in page.blocks if block.manual_status == "review")
        if active and all(block.translation_fr.strip() for block in active):
            translated_pages += 1
        if active and all(block.manual_status == "validated" for block in active):
            validated_pages += 1
    return ProjectStats(
        pages=pages,
        blocks=blocks,
        validated_blocks=validated_blocks,
        warning_blocks=warning_blocks,
        review_blocks=review_blocks,
        translated_pages=translated_pages,
        validated_pages=validated_pages,
    )
