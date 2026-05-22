from __future__ import annotations

import json
import re
import time
from dataclasses import asdict, dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Protocol

from cbz_manga_translator.core.cache import ProjectCache
from cbz_manga_translator.core.models import OcrBlock, PageRecord, ProjectData, SourceLang
from cbz_manga_translator.ocr.easyocr_engine import EasyOcrEngine
from cbz_manga_translator.review.model import block_source_text, resolve_image_path
from cbz_manga_translator.translate.argos import ArgosTranslator
from cbz_manga_translator.translate.quality import TranslationQualityChecker


class Recognizer(Protocol):
    def recognize(
        self,
        image_path: str | Path,
        source_lang: SourceLang,
        page_index: int,
        **kwargs: object,
    ) -> list[OcrBlock]: ...


class Translator(Protocol):
    def translate_blocks(
        self,
        blocks: list[OcrBlock],
        source_lang: SourceLang,
        **kwargs: object,
    ) -> list[OcrBlock]: ...


@dataclass(slots=True)
class ReplayBlockResult:
    page_index: int
    target_block_id: str
    matched_block_id: str
    status: str
    bbox_iou: float
    source_similarity: float
    translation_similarity: float
    expected_source: str
    actual_source: str
    expected_translation: str
    actual_translation: str


@dataclass(slots=True)
class ReplayReport:
    project_path: str
    pages_replayed: int
    target_blocks: int
    matched_blocks: int
    source_matches: int
    translation_matches: int
    full_matches: int
    elapsed_seconds: float
    results: list[ReplayBlockResult]


def canonical_text(value: str) -> str:
    compact = " ".join(str(value).replace("’", "'").strip().lower().split())
    compact = re.sub(r"\s+([,.;:!?])", r"\1", compact)
    compact = re.sub(r"[“”\"`´]", "", compact)
    compact = re.sub(r"\.{2,}", "...", compact)
    return compact


def text_similarity(left: str, right: str) -> float:
    left_key = canonical_text(left)
    right_key = canonical_text(right)
    if not left_key and not right_key:
        return 1.0
    if not left_key or not right_key:
        return 0.0
    return SequenceMatcher(None, left_key, right_key).ratio()


def bbox_iou(left: list[int], right: list[int]) -> float:
    lx1, ly1, lx2, ly2 = left
    rx1, ry1, rx2, ry2 = right
    ix1 = max(lx1, rx1)
    iy1 = max(ly1, ry1)
    ix2 = min(lx2, rx2)
    iy2 = min(ly2, ry2)
    intersection = max(0, ix2 - ix1) * max(0, iy2 - iy1)
    if intersection <= 0:
        return 0.0
    left_area = max(0, lx2 - lx1) * max(0, ly2 - ly1)
    right_area = max(0, rx2 - rx1) * max(0, ry2 - ry1)
    union = left_area + right_area - intersection
    return 0.0 if union <= 0 else intersection / union


def _target_blocks(page: PageRecord, statuses: set[str]) -> list[OcrBlock]:
    return [block for block in page.blocks if block.manual_status in statuses]


def _best_match(target: OcrBlock, candidates: list[OcrBlock]) -> tuple[OcrBlock | None, float]:
    best: OcrBlock | None = None
    best_iou = 0.0
    for candidate in candidates:
        score = bbox_iou(target.bbox, candidate.bbox)
        if score > best_iou:
            best = candidate
            best_iou = score
    return best, best_iou


def replay_review_project(
    project_path: str | Path,
    *,
    source_lang: SourceLang = "en",
    max_pages: int | None = None,
    statuses: set[str] | None = None,
    min_iou: float = 0.35,
    source_threshold: float = 0.92,
    translation_threshold: float = 0.85,
    use_gpu: bool = True,
    ocr_use_gpu: bool | None = None,
    refine_crops: bool = False,
    fallback: str = "off",
    recognizer: Recognizer | None = None,
    translator: Translator | None = None,
    quality_checker: TranslationQualityChecker | None = None,
) -> ReplayReport:
    started = time.monotonic()
    path = Path(project_path)
    project = ProjectCache.load(path)
    target_statuses = statuses or {"edited", "validated"}
    recognizer = recognizer or EasyOcrEngine()
    translator = translator or ArgosTranslator()
    quality_checker = quality_checker or TranslationQualityChecker()
    active_ocr_gpu = use_gpu if ocr_use_gpu is None else ocr_use_gpu

    pages = [page for page in project.pages if _target_blocks(page, target_statuses)]
    if max_pages is not None:
        pages = pages[:max_pages]

    results: list[ReplayBlockResult] = []
    for page in pages:
        image_path = resolve_image_path(path, project, page)
        replayed = recognizer.recognize(
            image_path,
            source_lang,
            page.page_index,
            use_gpu=active_ocr_gpu,
            min_confidence=0.20,
            merge_lines=True,
            filter_noise=True,
            refine_crops=refine_crops,
        )
        if fallback != "off":
            # Keep this command deliberately simple and reproducible for replay tests.
            quality_checker.apply(replayed, source_lang=source_lang)
        replayed = translator.translate_blocks(
            replayed,
            source_lang,
            use_gpu=use_gpu,
            raw_terms=project.glossary_terms,
            normalize_english=True,
            use_builtin_glossary=True,
            force=True,
        )
        quality_checker.apply(replayed, source_lang=source_lang)
        for target in _target_blocks(page, target_statuses):
            candidate, overlap = _best_match(target, replayed)
            expected_source = block_source_text(target)
            expected_translation = target.translation_fr or target.raw_translation_fr
            if candidate is None or overlap < min_iou:
                results.append(
                    ReplayBlockResult(
                        page_index=page.page_index,
                        target_block_id=target.id,
                        matched_block_id="",
                        status="missing",
                        bbox_iou=overlap,
                        source_similarity=0.0,
                        translation_similarity=0.0,
                        expected_source=expected_source,
                        actual_source="",
                        expected_translation=expected_translation,
                        actual_translation="",
                    )
                )
                continue
            actual_source = block_source_text(candidate)
            actual_translation = candidate.translation_fr or candidate.raw_translation_fr
            source_score = text_similarity(expected_source, actual_source)
            translation_score = text_similarity(expected_translation, actual_translation)
            source_ok = source_score >= source_threshold
            translation_ok = translation_score >= translation_threshold
            if source_ok and translation_ok:
                status = "match"
            elif source_ok:
                status = "translation_mismatch"
            elif translation_ok:
                status = "source_mismatch"
            else:
                status = "mismatch"
            results.append(
                ReplayBlockResult(
                    page_index=page.page_index,
                    target_block_id=target.id,
                    matched_block_id=candidate.id,
                    status=status,
                    bbox_iou=overlap,
                    source_similarity=source_score,
                    translation_similarity=translation_score,
                    expected_source=expected_source,
                    actual_source=actual_source,
                    expected_translation=expected_translation,
                    actual_translation=actual_translation,
                )
            )

    return ReplayReport(
        project_path=str(path),
        pages_replayed=len(pages),
        target_blocks=len(results),
        matched_blocks=sum(1 for item in results if item.status != "missing"),
        source_matches=sum(1 for item in results if item.source_similarity >= source_threshold),
        translation_matches=sum(1 for item in results if item.translation_similarity >= translation_threshold),
        full_matches=sum(1 for item in results if item.status == "match"),
        elapsed_seconds=round(time.monotonic() - started, 3),
        results=results,
    )


def write_replay_report(report: ReplayReport, output_dir: str | Path) -> tuple[Path, Path]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    json_path = out / "mangatrad_review_replay_report.json"
    md_path = out / "mangatrad_review_replay_report.md"
    json_path.write_text(
        json.dumps(asdict(report), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    lines = [
        "# MangaTrad Review Replay",
        "",
        f"- Projet: `{report.project_path}`",
        f"- Pages rejouées: {report.pages_replayed}",
        f"- Blocs corrigés ciblés: {report.target_blocks}",
        f"- Blocs retrouvés par bbox: {report.matched_blocks}",
        f"- Source OK: {report.source_matches}",
        f"- Traduction OK: {report.translation_matches}",
        f"- Match complet: {report.full_matches}",
        f"- Durée: {report.elapsed_seconds:.1f}s",
        "",
        "## Écarts",
        "",
    ]
    failures = [item for item in report.results if item.status != "match"]
    if not failures:
        lines.append("Aucun écart sur les blocs ciblés.")
    for item in failures:
        lines.extend(
            [
                f"### p{item.page_index + 1} · {item.target_block_id} · {item.status}",
                "",
                f"- Match bbox: {item.bbox_iou:.2f}",
                f"- Similarité source: {item.source_similarity:.2f}",
                f"- Similarité traduction: {item.translation_similarity:.2f}",
                f"- Source attendue: `{item.expected_source}`",
                f"- Source rejouée: `{item.actual_source}`",
                f"- Traduction attendue: `{item.expected_translation}`",
                f"- Traduction rejouée: `{item.actual_translation}`",
                "",
            ]
        )
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return json_path, md_path
