from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from difflib import SequenceMatcher
from pathlib import Path

from cbz_manga_translator.analysis.review_filter import non_reviewable_reason
from cbz_manga_translator.core.cache import ProjectCache
from cbz_manga_translator.core.models import OcrBlock
from cbz_manga_translator.ocr.incomplete import zone_issue_categories


@dataclass(slots=True)
class DiagnosticItem:
    category: str
    page_index: int
    block_id: str
    status: str
    ocr_text: str
    ocr_corrected_text: str
    normalized_source_text: str
    raw_translation_fr: str
    translation_fr: str
    review_notes: str
    reason: str


@dataclass(slots=True)
class DiagnosticReport:
    project_path: str
    total_blocks: int
    changed_blocks: int
    status_counts: dict[str, int]
    category_counts: dict[str, int]
    scores: dict[str, float]
    items: list[DiagnosticItem]


def _compact(text: str) -> str:
    return " ".join(str(text or "").strip().lower().split())


def _letters_digits(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(text).lower())


def _punctuation(text: str) -> str:
    return re.sub(r"[a-z0-9\s]+", "", str(text).lower())


def _similarity(left: str, right: str) -> float:
    compact_left = _compact(left)
    compact_right = _compact(right)
    if not compact_left and not compact_right:
        return 1.0
    return SequenceMatcher(None, compact_left, compact_right).ratio()


def _human_source(block: OcrBlock) -> str:
    return (block.normalized_source_text or block.ocr_corrected_text or block.ocr_text).strip()


def _is_changed(block: OcrBlock) -> bool:
    raw = block.ocr_text.strip()
    corrected = block.ocr_corrected_text.strip()
    normalized = block.normalized_source_text.strip()
    raw_translation = block.raw_translation_fr.strip()
    translation = block.translation_fr.strip()
    return (
        block.manual_status in {"edited", "review", "ignored"}
        or bool(block.review_notes.strip())
        or bool(corrected and _compact(corrected) != _compact(raw))
        or bool(normalized and _compact(normalized) != _compact(corrected or raw))
        or bool(raw_translation and translation and _compact(raw_translation) != _compact(translation))
    )


def _make_item(block: OcrBlock, page_index: int, category: str, reason: str) -> DiagnosticItem:
    return DiagnosticItem(
        category=category,
        page_index=page_index,
        block_id=block.id,
        status=block.manual_status,
        ocr_text=block.ocr_text,
        ocr_corrected_text=block.ocr_corrected_text,
        normalized_source_text=block.normalized_source_text,
        raw_translation_fr=block.raw_translation_fr,
        translation_fr=block.translation_fr,
        review_notes=block.review_notes,
        reason=reason,
    )


def _zone_categories_from_notes(notes: str) -> list[str]:
    compact = notes.lower()
    categories: list[str] = []
    if any(token in compact for token in ("sfx", "onomato", "onomatop", "sonore")) and any(token in compact for token in ("fusion", "melange", "mélange")):
        categories.append("sfx_mixed")
    if any(token in compact for token in ("fusion", "fusionne", "fusionné", "fusionnes", "fusionnés", "merged")):
        categories.append("fused_bubble")
    if any(token in compact for token in ("split", "separe", "sépar", "2 zones", "deux zones", "plusieurs zones")):
        categories.append("split_bubble")
    if any(token in compact for token in ("trop petit", "petite", "crop", "coupe", "coupé", "manque", "pas lu", "oubli")):
        categories.append("zone_too_small")
    if "[zone]" in compact and not categories:
        categories.append("zone_too_small")
    return categories


def _zone_categories_from_quality_warnings(warnings: list[str]) -> list[str]:
    compact = " ".join(warnings).lower()
    categories: list[str] = []
    if any(token in compact for token in ("sfx probablement melange", "sfx probablement m", "sfx melange")):
        categories.append("sfx_mixed")
    if any(token in compact for token in ("fusion probable", "plusieurs bulles", "meme bbox", "même bbox")):
        categories.append("fused_bubble")
    if any(token in compact for token in ("bulle probablement separee", "bulle probablement s", "split_bubble")):
        categories.append("split_bubble")
    if any(token in compact for token in ("zone trop petite", "bord du crop", "bbox probablement trop petite", "texte touche le bord")):
        categories.append("zone_too_small")
    return categories


def classify_block(block: OcrBlock, page_index: int) -> list[DiagnosticItem]:
    items: list[DiagnosticItem] = []
    raw = block.ocr_text.strip()
    corrected = block.ocr_corrected_text.strip()
    normalized = block.normalized_source_text.strip()
    raw_translation = block.raw_translation_fr.strip()
    translation = block.translation_fr.strip()
    notes = block.review_notes.strip().lower()

    if block.manual_status == "ignored":
        auto_reason = non_reviewable_reason(block)
        reason = auto_reason or "ignore humain non couvert automatiquement"
        items.append(_make_item(block, page_index, "sfx_or_non_dialogue", reason))

    note_categories = _zone_categories_from_notes(notes)
    for category in note_categories:
        items.append(_make_item(block, page_index, category, "note humaine zone/bbox"))

    warning_categories = [
        category
        for category in _zone_categories_from_quality_warnings(block.quality_warnings)
        if category not in note_categories
    ]
    for category in warning_categories:
        items.append(_make_item(block, page_index, category, "warning qualite zone/bbox"))

    structure_source = normalized or corrected or raw
    for category in zone_issue_categories(structure_source):
        if category not in note_categories and category not in warning_categories:
            items.append(_make_item(block, page_index, category, "heuristique texte/zone"))

    if corrected and _compact(corrected) != _compact(raw):
        letter_score = SequenceMatcher(None, _letters_digits(raw), _letters_digits(corrected)).ratio()
        if letter_score >= 0.90 and _punctuation(raw) != _punctuation(corrected):
            items.append(_make_item(block, page_index, "punctuation", f"texte proche, ponctuation différente ({letter_score:.2f})"))
        elif letter_score < 0.90:
            items.append(_make_item(block, page_index, "ocr_text", f"texte OCR corrigé ({letter_score:.2f})"))
        else:
            items.append(_make_item(block, page_index, "casing_or_spacing", "casse/espacement corrigé"))

    if normalized and _compact(normalized) != _compact(corrected or raw):
        items.append(_make_item(block, page_index, "source_normalization", "source reformulée avant traduction"))

    if raw_translation and translation and _compact(raw_translation) != _compact(translation):
        score = _similarity(raw_translation, translation)
        items.append(_make_item(block, page_index, "translation", f"traduction corrigée ({score:.2f})"))

    if not items and _is_changed(block):
        items.append(_make_item(block, page_index, "other", "modification non classée"))
    return items


def diagnose_review_project(project_path: str | Path) -> DiagnosticReport:
    project = ProjectCache.load(project_path)
    status_counts: Counter[str] = Counter()
    category_counts: Counter[str] = Counter()
    items: list[DiagnosticItem] = []
    total_blocks = 0
    changed_blocks = 0
    score_buckets: dict[str, list[float]] = defaultdict(list)

    for page in project.pages:
        for block in page.blocks:
            total_blocks += 1
            status_counts[block.manual_status] += 1
            if _is_changed(block):
                changed_blocks += 1
            block_items = classify_block(block, page.page_index)
            for item in block_items:
                items.append(item)
                category_counts[item.category] += 1

            expected_source = _human_source(block)
            if block.ocr_text.strip() and expected_source and block.manual_status in {"edited", "validated", "review"}:
                score_buckets["source_similarity"].append(_similarity(expected_source, block.ocr_text))
            if block.raw_translation_fr.strip() and block.translation_fr.strip():
                score_buckets["translation_similarity"].append(_similarity(block.raw_translation_fr, block.translation_fr))
            if block.manual_status == "ignored":
                score_buckets["ignored_auto_covered"].append(1.0 if non_reviewable_reason(block) else 0.0)

    scores = {
        key: round(sum(values) / len(values), 4)
        for key, values in score_buckets.items()
        if values
    }
    return DiagnosticReport(
        project_path=str(project_path),
        total_blocks=total_blocks,
        changed_blocks=changed_blocks,
        status_counts=dict(sorted(status_counts.items())),
        category_counts=dict(sorted(category_counts.items())),
        scores=scores,
        items=items,
    )


def write_diagnostic_report(report: DiagnosticReport, output_dir: str | Path) -> tuple[Path, Path]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    json_path = out / "mangatrad_review_diagnostic.json"
    md_path = out / "mangatrad_review_diagnostic.md"
    json_path.write_text(json.dumps(asdict(report), ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Diagnostic review MangaTrad",
        "",
        f"- Projet: `{report.project_path}`",
        f"- Blocs total: {report.total_blocks}",
        f"- Blocs modifiés: {report.changed_blocks}",
        "",
        "## Statuts",
        "",
    ]
    for status, count in report.status_counts.items():
        lines.append(f"- {status}: {count}")
    lines.extend(["", "## Catégories", ""])
    for category, count in sorted(report.category_counts.items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"- {category}: {count}")
    lines.extend(["", "## Scores", ""])
    for key, value in sorted(report.scores.items()):
        lines.append(f"- {key}: {value:.2%}")
    lines.extend(["", "## Exemples prioritaires", ""])
    for category, _count in sorted(report.category_counts.items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"### {category}")
        for item in [candidate for candidate in report.items if candidate.category == category][:8]:
            lines.append(f"- Page {item.page_index + 1} / {item.block_id} / {item.status}: {item.reason}")
            if item.review_notes:
                lines.append(f"  - Note: {item.review_notes}")
            lines.append(f"  - OCR: `{item.ocr_text}`")
            if item.ocr_corrected_text:
                lines.append(f"  - OCR corrigé: `{item.ocr_corrected_text}`")
            if item.normalized_source_text:
                lines.append(f"  - Source: `{item.normalized_source_text}`")
            if item.raw_translation_fr or item.translation_fr:
                lines.append(f"  - Trad: `{item.raw_translation_fr}` -> `{item.translation_fr}`")
        lines.append("")
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return json_path, md_path
