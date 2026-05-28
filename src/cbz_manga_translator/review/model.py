from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Literal

from cbz_manga_translator.core.cache import ProjectCache
from cbz_manga_translator.core.models import OcrBlock, PageRecord, ProjectData

ReviewDecision = Literal["validate", "correct", "review", "fused", "zone", "ignore", "sfx"]
DECISIONS: tuple[str, ...] = ("validate", "correct", "review", "fused", "zone", "ignore", "sfx")


@dataclass(slots=True)
class ReviewItem:
    page_index: int
    block_id: str
    display: str
    risk_score: int
    risk_band: str
    manual_status: str
    review_decision: str
    source_preview: str
    translation_preview: str
    diagnostic_preview: str
    notes_preview: str


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


def resolve_review_project_input(input_path: str | Path) -> Path:
    """Resolve a GUI review input from a project JSON, CBZ, or series folder."""
    path = Path(input_path)
    if path.is_file() and path.suffix.lower() == ".json":
        return path
    if path.is_file() and path.suffix.lower() in {".cbz", ".zip"}:
        project_path = ProjectCache.default_path(path)
        if project_path.exists():
            return project_path
        raise FileNotFoundError(
            f"Projet OCR introuvable pour {path}. Lance d'abord OCR + traduction dans le GUI principal, "
            f"ou cree {project_path}."
        )
    if path.is_dir():
        json_candidates = [
            *sorted(path.glob("*.reviewed.json")),
            *sorted(path.glob("*.manga_translate_project.json")),
            *sorted(path.glob("mangatrad_corpus_project*.json")),
        ]
        json_candidates = [candidate for candidate in json_candidates if candidate.is_file()]
        if json_candidates:
            return json_candidates[0]
        cbz_candidates = sorted([candidate for candidate in path.glob("*.cbz") if candidate.is_file()])
        for cbz_path in cbz_candidates:
            project_path = ProjectCache.default_path(cbz_path)
            if project_path.exists():
                return project_path
        raise FileNotFoundError(
            f"Aucun projet MangaTrad trouve dans {path}. Le dossier contient peut-etre des CBZ, "
            "mais aucun .manga_translate_project.json n'existe encore."
        )
    return path


def load_review_project(project_path: str | Path, output_path: str | Path | None = None) -> ReviewProject:
    path = resolve_review_project_input(project_path)
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


def is_sfx_block(block: OcrBlock) -> bool:
    return block.manual_status == "ignored" and block.review_notes.strip().lower().startswith("[sfx]")


def is_fused_block(block: OcrBlock) -> bool:
    return block.manual_status == "review" and block.review_notes.strip().lower().startswith("[fusion]")


def is_bad_zone_block(block: OcrBlock) -> bool:
    return block.manual_status == "review" and block.review_notes.strip().lower().startswith("[zone]")


def review_decision_for_block(block: OcrBlock) -> str:
    if is_sfx_block(block):
        return "sfx"
    if is_fused_block(block):
        return "fused"
    if is_bad_zone_block(block):
        return "zone"
    if block.manual_status == "validated":
        return "validate"
    if block.manual_status == "ignored":
        return "ignore"
    if block.manual_status == "review":
        return "review"
    if block.manual_status == "edited":
        return "correct"
    return "unchecked"


def review_status_label(block: OcrBlock) -> str:
    labels = {
        "validate": "validé",
        "correct": "corrigé",
        "review": "à revoir",
        "fused": "fusion",
        "zone": "zone",
        "ignore": "ignoré",
        "sfx": "SFX",
        "unchecked": "brut",
    }
    return labels.get(review_decision_for_block(block), block.manual_status)


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
            diagnostics = " ".join(block.quality_warnings).replace("\n", " ").strip()
            notes = block.review_notes.replace("\n", " ").strip()
            display = f"[{risk_band(score)}] p{page.page_index + 1:03d} · {review_status_label(block)} · {source[:70]}"
            yield ReviewItem(
                page_index=page.page_index,
                block_id=block.id,
                display=display,
                risk_score=score,
                risk_band=risk_band(score),
                manual_status=block.manual_status,
                review_decision=review_decision_for_block(block),
                source_preview=source,
                translation_preview=translation,
                diagnostic_preview=diagnostics,
                notes_preview=notes,
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


def _clean_sfx_prefix(text: str) -> str:
    value = text.strip()
    if value.lower().startswith("[sfx]"):
        return value[5:].strip()
    return value


def _clean_fusion_prefix(text: str) -> str:
    value = text.strip()
    if value.lower().startswith("[fusion]"):
        return value[8:].strip()
    return value


def _clean_zone_prefix(text: str) -> str:
    value = text.strip()
    if value.lower().startswith("[zone]"):
        return value[6:].strip()
    return value


def apply_review_to_block(
    block: OcrBlock,
    *,
    decision: str,
    corrected_ocr: str = "",
    corrected_source: str = "",
    corrected_fr: str = "",
    notes: str = "",
) -> None:
    normalized_decision = decision.strip().lower().replace("à", "a").replace("Ã ", "a")

    ocr_value = corrected_ocr.strip()
    source_value = corrected_source.strip()
    fr_value = corrected_fr.strip()
    current_source = block_source_text(block).strip()
    current_translation = (block.translation_fr or block.raw_translation_fr).strip()
    if ocr_value and ocr_value != block.ocr_text.strip():
        block.ocr_corrected_text = ocr_value
    if source_value and source_value != current_source:
        block.normalized_source_text = source_value
    if fr_value and fr_value != current_translation:
        block.translation_fr = fr_value
        block.raw_translation_fr = block.raw_translation_fr or fr_value

    note_value = notes.strip()
    if normalized_decision in {"sfx", "noise"}:
        note_value = note_value if note_value.lower().startswith("[sfx]") else f"[sfx] {note_value}".strip()
    elif normalized_decision in {"fused", "fusion", "merged", "merge", "bulle fusionnee", "bulles fusionnees"}:
        note_value = note_value if note_value.lower().startswith("[fusion]") else f"[fusion] {note_value}".strip()
    elif normalized_decision in {"zone", "bad_zone", "crop", "bbox", "segmentation", "zone incorrecte"}:
        note_value = note_value if note_value.lower().startswith("[zone]") else f"[zone] {note_value}".strip()
    elif note_value.lower().startswith("[sfx]"):
        note_value = _clean_sfx_prefix(note_value)
    elif note_value.lower().startswith("[fusion]"):
        note_value = _clean_fusion_prefix(note_value)
    elif note_value.lower().startswith("[zone]"):
        note_value = _clean_zone_prefix(note_value)
    if note_value:
        block.review_notes = note_value

    has_text_change = (
        bool(ocr_value and ocr_value != block.ocr_text.strip())
        or bool(source_value and source_value != current_source)
        or bool(fr_value and fr_value != current_translation)
    )
    if normalized_decision in {"validate", "valid", "validated", "ok"}:
        block.manual_status = "validated"
    elif normalized_decision in {"ignore", "ignored", "sfx", "noise"}:
        block.manual_status = "ignored"
    elif normalized_decision in {
        "review", "revoir", "a revoir", "todo",
        "fused", "fusion", "merged", "merge", "bulle fusionnee", "bulles fusionnees",
        "zone", "bad_zone", "crop", "bbox", "segmentation", "zone incorrecte",
    }:
        block.manual_status = "review"
    elif normalized_decision in {"correct", "corrected", "edit", "edited"} or has_text_change:
        block.manual_status = "edited"
    else:
        block.manual_status = "review"
