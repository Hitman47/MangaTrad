from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Literal

from cbz_manga_translator.core.cache import ProjectCache
from cbz_manga_translator.core.models import OcrBlock, PageRecord, ProjectData

ReviewDecision = Literal["validate", "correct", "review", "ignore", "sfx"]
DECISIONS: tuple[str, ...] = ("validate", "correct", "review", "ignore", "sfx")


@dataclass(slots=True)
class ReviewItem:
    page_index: int
    block_id: str
    display: str
    risk_score: int
    risk_band: str
    manual_status: str
    source_preview: str
    translation_preview: str


@dataclass(slots=True)
class ReviewProject:
    project_path: Path
    output_path: Path
    project: ProjectData


def default_reviewed_path(project_path: str | Path) -> Path:
    path = Path(project_path)
    if path.name.endswith(".reviewed.json"):
        return path
    if path.suffix.lower() == ".json":
        return path.with_name(f"{path.stem}.reviewed.json")
    return path.with_suffix(path.suffix + ".reviewed.json")


def load_review_project(project_path: str | Path, output_path: str | Path | None = None) -> ReviewProject:
    path = Path(project_path)
    project = ProjectCache.load(path)
    return ReviewProject(
        project_path=path,
        output_path=Path(output_path) if output_path else default_reviewed_path(path),
        project=project,
    )


def save_review_project(review_project: ReviewProject) -> None:
    ProjectCache.save(review_project.output_path, review_project.project)


def block_source_text(block: OcrBlock) -> str:
    return block.normalized_source_text or block.ocr_corrected_text or block.ocr_text


def risk_score(block: OcrBlock) -> int:
    score = 0
    if block.quality_warnings:
        score += min(70, 15 * len(block.quality_warnings))
    if block.confidence is not None and block.confidence < 0.35:
        score += 25
    source = block_source_text(block)
    translation = block.translation_fr or block.raw_translation_fr
    if not translation.strip():
        score += 35
    if source.strip() and translation.strip() and source.strip().lower() == translation.strip().lower():
        score += 35
    if block.manual_status in {"review", "unchecked"}:
        score += 5
    if block.manual_status in {"validated", "ignored"}:
        score -= 20
    return max(0, min(100, score))


def risk_band(score: int) -> str:
    if score >= 55:
        return "HIGH"
    if score >= 25:
        return "MED"
    return "OK"


def iter_review_items(project: ProjectData) -> Iterable[ReviewItem]:
    for page in project.pages:
        for block in sorted(page.blocks, key=lambda item: item.reading_order):
            score = risk_score(block)
            source = block_source_text(block).replace("\n", " ").strip()
            translation = (block.translation_fr or block.raw_translation_fr).replace("\n", " ").strip()
            display = f"[{risk_band(score)}] p{page.page_index + 1:03d} · {block.manual_status} · {source[:70]}"
            yield ReviewItem(
                page_index=page.page_index,
                block_id=block.id,
                display=display,
                risk_score=score,
                risk_band=risk_band(score),
                manual_status=block.manual_status,
                source_preview=source,
                translation_preview=translation,
            )


def find_page(project: ProjectData, page_index: int) -> PageRecord:
    for page in project.pages:
        if page.page_index == page_index:
            return page
    raise KeyError(f"Page introuvable: {page_index}")


def find_block(project: ProjectData, page_index: int, block_id: str) -> OcrBlock:
    page = find_page(project, page_index)
    for block in page.blocks:
        if block.id == block_id:
            return block
    raise KeyError(f"Bloc introuvable: page={page_index} block={block_id}")


def resolve_image_path(project_path: str | Path, project: ProjectData, page: PageRecord) -> Path:
    image = Path(page.image_name)
    candidates = []
    if image.is_absolute():
        candidates.append(image)
    root = Path(project_path).parent
    candidates.append(root / image)
    if project.cbz_path:
        cbz_root = Path(project.cbz_path)
        candidates.append(cbz_root / image)
        candidates.append(cbz_root.parent / image)
    candidates.append(image)
    for candidate in candidates:
        try:
            if candidate.exists():
                return candidate
        except OSError:
            continue
    # Return the most informative path even if it does not exist.
    return candidates[0] if candidates else image


def apply_review_to_block(
    block: OcrBlock,
    *,
    decision: str,
    corrected_ocr: str = "",
    corrected_source: str = "",
    corrected_fr: str = "",
    notes: str = "",
) -> None:
    normalized_decision = decision.strip().lower().replace("à", "a")
    if corrected_ocr.strip():
        block.ocr_corrected_text = corrected_ocr.strip()
    if corrected_source.strip():
        block.normalized_source_text = corrected_source.strip()
    if corrected_fr.strip():
        block.translation_fr = corrected_fr.strip()
        block.raw_translation_fr = block.raw_translation_fr or corrected_fr.strip()
    note_value = notes.strip()
    if normalized_decision in {"sfx", "noise"}:
        note_value = f"[sfx] {note_value}".strip()
    if note_value:
        block.review_notes = note_value

    if normalized_decision in {"validate", "valid", "validated", "ok"}:
        block.manual_status = "validated"
    elif normalized_decision in {"ignore", "ignored", "sfx", "noise"}:
        block.manual_status = "ignored"
    elif normalized_decision in {"review", "revoir", "a revoir", "todo"}:
        block.manual_status = "review"
    elif normalized_decision in {"correct", "corrected", "edit", "edited"} or corrected_ocr or corrected_source or corrected_fr:
        block.manual_status = "edited"
    else:
        block.manual_status = "review"
