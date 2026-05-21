from __future__ import annotations

from collections.abc import Iterable
from copy import deepcopy
from typing import Literal

from cbz_manga_translator.core.models import ManualStatus, OcrBlock

EditableField = Literal["ocr_text", "ocr_corrected_text", "normalized_source_text", "translation_fr"]

STATUS_LABELS: dict[ManualStatus, str] = {
    "unchecked": "brut",
    "edited": "corrigé",
    "validated": "validé",
    "review": "à revoir",
    "ignored": "ignoré",
}


def status_label(status: ManualStatus) -> str:
    return STATUS_LABELS.get(status, str(status))


def _invalidate_generated_fields(block: OcrBlock) -> None:
    block.ocr_corrected_text = ""
    block.normalized_source_text = ""
    block.raw_translation_fr = ""
    block.translation_fr = ""
    block.quality_warnings = []
    block.ocr_alternatives = []


def set_block_field(block: OcrBlock, field: EditableField, value: str) -> None:
    """Apply a manual edit and invalidate downstream generated fields when needed.

    The GUI uses this helper so table edits behave consistently and are testable
    without Qt. Edits are intentionally conservative: changing a source field
    clears generated fields that depend on it, while editing the final French text
    only changes the final text.
    """
    clean_value = value.strip()
    if field == "ocr_text":
        block.ocr_text = clean_value
        block.ocr_corrected_text = ""
        block.normalized_source_text = ""
        block.raw_translation_fr = ""
        block.translation_fr = ""
        block.quality_warnings = []
        block.ocr_alternatives = []
    elif field == "ocr_corrected_text":
        block.ocr_corrected_text = clean_value
        block.normalized_source_text = ""
        block.raw_translation_fr = ""
        block.translation_fr = ""
        block.quality_warnings = []
    elif field == "normalized_source_text":
        block.normalized_source_text = clean_value
        block.raw_translation_fr = ""
        block.translation_fr = ""
        block.quality_warnings = []
    elif field == "translation_fr":
        block.translation_fr = clean_value
        block.quality_warnings = []
    else:  # pragma: no cover - defensive future-proofing
        raise ValueError(f"Unsupported editable field: {field}")
    if block.manual_status != "ignored":
        block.manual_status = "edited"


def set_manual_status(blocks: Iterable[OcrBlock], status: ManualStatus) -> int:
    """Set a workflow status on blocks and return the number of updated blocks."""
    count = 0
    for block in blocks:
        block.manual_status = status
        if status in {"validated", "ignored"}:
            block.quality_warnings = []
        elif status == "review":
            warning = "marqué à revoir manuellement"
            if warning not in block.quality_warnings:
                block.quality_warnings.append(warning)
        count += 1
    return count


def is_translation_protected(block: OcrBlock) -> bool:
    """Return True when automatic page translation should not overwrite a block."""
    return block.manual_status in {"validated", "ignored"}


def renumber_reading_order(blocks: list[OcrBlock]) -> None:
    """Normalize reading_order so it is contiguous and deterministic."""
    for order, block in enumerate(sorted(blocks, key=lambda item: (item.reading_order, item.bbox[1], item.bbox[0], item.id))):
        block.reading_order = order


def apply_ocr_alternative(block: OcrBlock, alternative_index: int) -> str:
    """Use one stored OCR alternative as the canonical OCR text.

    Returns the selected text so the GUI can display a precise status message.
    Raises ValueError for invalid indices or empty alternatives.
    """
    if alternative_index < 0 or alternative_index >= len(block.ocr_alternatives):
        raise ValueError("Alternative OCR invalide")
    item = block.ocr_alternatives[alternative_index]
    text = str(item.get("text", "")).strip()
    if not text:
        raise ValueError("Alternative OCR vide")
    confidence = item.get("confidence")
    block.ocr_text = text
    block.confidence = None if confidence is None else float(confidence)
    block.ocr_corrected_text = ""
    block.normalized_source_text = ""
    block.raw_translation_fr = ""
    block.translation_fr = ""
    block.quality_warnings = [f"alternative OCR utilisée: {item.get('engine', 'unknown')}"]
    block.manual_status = "edited" if block.manual_status != "ignored" else block.manual_status
    return text


def merge_blocks(blocks: list[OcrBlock], block_ids: Iterable[str]) -> OcrBlock:
    """Merge selected blocks into the earliest block and remove the others.

    Text is joined in reading order. The bbox becomes the union of selected bboxes.
    This is intentionally conservative: generated translation fields are cleared.
    """
    ids = {str(item) for item in block_ids}
    selected = sorted([block for block in blocks if block.id in ids], key=lambda item: item.reading_order)
    if len(selected) < 2:
        raise ValueError("Sélectionne au moins deux blocs à fusionner")

    primary = selected[0]
    x1 = min(block.bbox[0] for block in selected)
    y1 = min(block.bbox[1] for block in selected)
    x2 = max(block.bbox[2] for block in selected)
    y2 = max(block.bbox[3] for block in selected)
    texts = [
        (block.ocr_corrected_text or block.ocr_text).strip()
        for block in selected
        if (block.ocr_corrected_text or block.ocr_text).strip()
    ]
    primary.bbox = [x1, y1, x2, y2]
    primary.ocr_text = "\n".join(texts)
    primary.confidence = _average_confidence(selected)
    primary.manual_status = "edited"
    primary.quality_warnings = ["blocs OCR fusionnés manuellement"]
    primary.ocr_alternatives = _merged_alternatives(selected)
    primary.ocr_corrected_text = ""
    primary.normalized_source_text = ""
    primary.raw_translation_fr = ""
    primary.translation_fr = ""

    selected_ids = {block.id for block in selected[1:]}
    blocks[:] = [block for block in blocks if block.id not in selected_ids]
    renumber_reading_order(blocks)
    return primary


def split_block_by_lines(blocks: list[OcrBlock], block_id: str, raw_lines: str | None = None) -> list[OcrBlock]:
    """Split one block into line-based blocks.

    The GUI passes manual lines when the user edits OCR corrected text before
    splitting. Bboxes are split vertically as an approximation; the user can still
    correct text/order before future bubble replacement.
    """
    index = next((i for i, block in enumerate(blocks) if block.id == block_id), -1)
    if index < 0:
        raise ValueError("Bloc introuvable")
    source = blocks[index]
    text = raw_lines if raw_lines is not None else (source.ocr_corrected_text or source.ocr_text)
    lines = [line.strip() for line in str(text).replace("\r\n", "\n").split("\n") if line.strip()]
    if len(lines) < 2:
        raise ValueError("Le bloc doit contenir au moins deux lignes non vides")

    x1, y1, x2, y2 = source.bbox
    height = max(1, y2 - y1)
    split_blocks: list[OcrBlock] = []
    for offset, line in enumerate(lines):
        y_start = y1 + int(height * offset / len(lines))
        y_end = y1 + int(height * (offset + 1) / len(lines))
        new_block = deepcopy(source)
        new_block.id = f"{source.id}_s{offset + 1}"
        new_block.bbox = [x1, y_start, x2, max(y_start + 1, y_end)]
        new_block.ocr_text = line
        new_block.ocr_corrected_text = ""
        new_block.normalized_source_text = ""
        new_block.raw_translation_fr = ""
        new_block.translation_fr = ""
        new_block.quality_warnings = ["bloc OCR séparé manuellement"]
        new_block.ocr_alternatives = []
        new_block.manual_status = "edited"
        split_blocks.append(new_block)

    blocks[index : index + 1] = split_blocks
    renumber_reading_order(blocks)
    return split_blocks


def move_block_order(blocks: list[OcrBlock], block_id: str, direction: int) -> OcrBlock:
    """Move one block up/down in reading order and renumber the page."""
    ordered = sorted(blocks, key=lambda item: item.reading_order)
    position = next((i for i, block in enumerate(ordered) if block.id == block_id), -1)
    if position < 0:
        raise ValueError("Bloc introuvable")
    new_position = position + (-1 if direction < 0 else 1)
    if new_position < 0 or new_position >= len(ordered):
        return ordered[position]
    ordered[position], ordered[new_position] = ordered[new_position], ordered[position]
    for order, block in enumerate(ordered):
        block.reading_order = order
    return ordered[new_position]


def _average_confidence(blocks: list[OcrBlock]) -> float | None:
    values = [block.confidence for block in blocks if block.confidence is not None]
    if not values:
        return None
    return sum(values) / len(values)


def _merged_alternatives(blocks: list[OcrBlock]) -> list[dict[str, object]]:
    alternatives: list[dict[str, object]] = []
    for block in blocks:
        alternatives.extend(block.ocr_alternatives[:3])
    return alternatives[:10]
