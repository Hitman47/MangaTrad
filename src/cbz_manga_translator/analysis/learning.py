from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
from typing import Any

from cbz_manga_translator.core.models import ProjectData, OcrBlock
from cbz_manga_translator.analysis.light_quality import compute_quality_features

_LEARNABLE_STATUSES = {"edited", "validated"}
_WORD_RE = re.compile(r"\b[A-Z][A-Za-zÀ-ÖØ-öø-ÿ'\-]{2,}\b")


@dataclass(slots=True)
class LearningReport:
    exact_translation_memory: list[dict[str, Any]]
    ocr_correction_memory: list[dict[str, Any]]
    glossary_candidates: list[dict[str, Any]]
    high_risk_examples: list[dict[str, Any]]
    summary: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _source_for_memory(block: OcrBlock) -> str:
    return (block.normalized_source_text or block.ocr_corrected_text or block.ocr_text or "").strip()


def _is_learnable(block: OcrBlock) -> bool:
    return block.manual_status in _LEARNABLE_STATUSES and bool(block.translation_fr.strip())


def build_learning_report(project: ProjectData, *, max_examples: int = 100) -> LearningReport:
    translation_counts: dict[tuple[str, str, str], int] = defaultdict(int)
    correction_counts: dict[tuple[str, str], int] = defaultdict(int)
    glossary_counter: Counter[str] = Counter()
    high_risk: list[dict[str, Any]] = []
    total_blocks = 0
    learnable_blocks = 0
    validated_blocks = 0

    for page in project.pages:
        for block in page.blocks:
            total_blocks += 1
            if block.manual_status == "validated":
                validated_blocks += 1
            source = _source_for_memory(block)
            if _is_learnable(block) and source:
                learnable_blocks += 1
                translation_counts[(block.source_lang, source, block.translation_fr.strip())] += 1
                raw = (block.ocr_text or "").strip()
                corrected = (block.ocr_corrected_text or "").strip()
                if raw and corrected and raw != corrected:
                    correction_counts[(raw, corrected)] += 1
                for candidate in _WORD_RE.findall(source):
                    if len(candidate) >= 3 and candidate.upper() != candidate:
                        glossary_counter[candidate] += 1
            features = compute_quality_features(block)
            if features.risk_score >= 55:
                high_risk.append({
                    "page_index": page.page_index,
                    "image_name": page.image_name,
                    "block_id": block.id,
                    "risk_score": features.risk_score,
                    "action": features.action,
                    "reasons": features.reasons,
                    "source": source,
                    "translation_fr": block.translation_fr,
                    "status": block.manual_status,
                })

    exact_memory = [
        {"source_lang": lang, "source": source, "translation_fr": translation, "count": count}
        for (lang, source, translation), count in sorted(
            translation_counts.items(), key=lambda item: (-item[1], item[0][1].lower())
        )
    ][:max_examples]
    ocr_memory = [
        {"ocr_raw": raw, "ocr_corrected": corrected, "count": count}
        for (raw, corrected), count in sorted(correction_counts.items(), key=lambda item: (-item[1], item[0][0].lower()))
    ][:max_examples]
    glossary = [
        {"term": term, "count": count}
        for term, count in glossary_counter.most_common(max_examples)
    ]
    high_risk_sorted = sorted(high_risk, key=lambda row: -int(row["risk_score"]))[:max_examples]
    summary = {
        "pages": len(project.pages),
        "blocks": total_blocks,
        "learnable_blocks": learnable_blocks,
        "validated_blocks": validated_blocks,
        "high_risk_blocks": len(high_risk),
    }
    return LearningReport(exact_memory, ocr_memory, glossary, high_risk_sorted, summary)
