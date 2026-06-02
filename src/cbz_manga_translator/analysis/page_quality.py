from __future__ import annotations

import re

from cbz_manga_translator.core.models import OcrBlock, PageRecord, SourceLang

PAGE_DENSE_WARNING = "page QC: page dense/instable, verifier les zones avant traduction"
PAGE_CONTEXT_WARNING = "contexte: phrase probablement coupee entre bulles voisines"

_ZONE_WARNING_RE = re.compile(
    r"(zone|bulle|fusion|crop|bbox|sfx|preflight|incomplete|separee|trop petite)",
    flags=re.IGNORECASE,
)
_INCOMPLETE_EDGE_RE = re.compile(r"(^\s*\.\.\.|[A-Za-z0-9\"')\]]$|[:,]\s*$)")


def _is_actionable(block: OcrBlock) -> bool:
    return block.manual_status not in {"validated", "ignored"}


def _append_warning(block: OcrBlock, warning: str) -> bool:
    if warning in block.quality_warnings:
        return False
    block.quality_warnings.append(warning)
    if block.manual_status == "unchecked":
        block.manual_status = "review"
        if not block.review_notes.strip():
            block.review_notes = "[page-qc] verifier la zone/contexte avant validation"
    return True


def _block_text(block: OcrBlock) -> str:
    return " ".join((block.normalized_source_text or block.ocr_corrected_text or block.ocr_text).split())


def _has_zone_warning(block: OcrBlock) -> bool:
    return any(_ZONE_WARNING_RE.search(warning) for warning in block.quality_warnings)


def _needs_context(text: str) -> bool:
    if not text:
        return False
    if text.startswith("...") or text.endswith("...") or re.search(r"-\s*$", text):
        return True
    words = re.findall(r"[A-Za-z']+", text)
    return len(words) >= 3 and bool(_INCOMPLETE_EDGE_RE.search(text)) and not re.search(r"[.!?][\"')\]]?$", text)


def apply_page_quality_warnings(page: PageRecord, source_lang: SourceLang) -> int:
    """Add page-level diagnostics after block OCR/translation QC.

    This deliberately does not try to auto-split boxes. It escalates pages whose
    block warnings indicate unstable detection, then marks neighbouring partial
    phrases so review focuses on the page layout instead of isolated text.
    """
    if source_lang != "en":
        return 0

    blocks = [block for block in page.blocks if _is_actionable(block)]
    if not blocks:
        return 0

    changed = 0
    total = len(blocks)
    warning_count = sum(1 for block in blocks if block.quality_warnings)
    zone_count = sum(1 for block in blocks if _has_zone_warning(block))
    empty_translation_count = sum(1 for block in blocks if not (block.translation_fr or block.raw_translation_fr).strip())

    dense_zone_page = zone_count >= 3 or (total >= 6 and zone_count / total >= 0.35)
    unstable_page = total >= 6 and warning_count / total >= 0.55
    missing_translation_page = total >= 4 and empty_translation_count / total >= 0.40

    if dense_zone_page or unstable_page or missing_translation_page:
        for block in blocks:
            if _has_zone_warning(block) or missing_translation_page or not block.translation_fr.strip():
                changed += int(_append_warning(block, PAGE_DENSE_WARNING))

    ordered = sorted(blocks, key=lambda block: block.reading_order)
    texts = [_block_text(block) for block in ordered]
    for index, block in enumerate(ordered):
        text = texts[index]
        if not _needs_context(text):
            continue
        neighbour_texts = []
        if index > 0:
            neighbour_texts.append(texts[index - 1])
        if index + 1 < len(texts):
            neighbour_texts.append(texts[index + 1])
        if any(_needs_context(neighbour) or neighbour.startswith("...") for neighbour in neighbour_texts):
            changed += int(_append_warning(block, PAGE_CONTEXT_WARNING))

    return changed
