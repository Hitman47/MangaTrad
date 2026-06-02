from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path

from cbz_manga_translator.core.cache import ProjectCache
from cbz_manga_translator.core.models import OcrBlock, PageRecord, ProjectData, SourceLang
from cbz_manga_translator.ocr.fallback_engine import OcrFallbackEngine
from cbz_manga_translator.ocr.incomplete import zone_issue_categories
from cbz_manga_translator.ocr.text_cleanup import normalize_ocr_text_for_translation
from cbz_manga_translator.review.model import block_source_text, resolve_image_path
from cbz_manga_translator.translate.argos import ArgosTranslator
from cbz_manga_translator.translate.english_dialogue_normalizer import EnglishDialogueNormalizer
from cbz_manga_translator.translate.quality import TranslationQualityChecker


@dataclass(slots=True)
class RefreshResult:
    output_path: Path
    refreshed_blocks: int
    ocr_fallback_blocks: int
    preserved_blocks: int
    warning_blocks: int


def default_refreshed_path(project_path: str | Path) -> Path:
    path = Path(project_path)
    if path.suffix.lower() == ".json":
        return path.with_name(f"{path.stem}.refreshed.json")
    return path.with_suffix(path.suffix + ".refreshed.json")


def _iter_refreshable_blocks(
    project: ProjectData,
    source_lang: SourceLang,
    *,
    include_review: bool = False,
) -> tuple[list[OcrBlock], int]:
    refreshable: list[OcrBlock] = []
    preserved = 0
    refreshable_statuses = {"unchecked", "review"} if include_review else {"unchecked"}
    for page in project.pages:
        for block in page.blocks:
            if block.source_lang != source_lang:
                preserved += 1
                continue
            if block.manual_status in refreshable_statuses:
                refreshable.append(block)
            else:
                preserved += 1
    return refreshable, preserved


def _refresh_blocks_with_rules(blocks: list[OcrBlock], source_lang: SourceLang, *, normalize_english: bool) -> None:
    if source_lang != "en":
        return
    for block in blocks:
        source = block.ocr_text.strip()
        if not source:
            continue
        prepared = EnglishDialogueNormalizer.prepare(
            normalize_ocr_text_for_translation(source),
            normalize_english=normalize_english,
        )
        block.ocr_corrected_text = prepared.corrected_text
        block.normalized_source_text = prepared.normalized_text
        if prepared.override_translation_fr:
            block.raw_translation_fr = prepared.override_translation_fr
            block.translation_fr = prepared.override_translation_fr


def _is_zone_fallback_candidate(block: OcrBlock) -> bool:
    notes = block.review_notes.strip().lower()
    if "[zone]" in notes or "[fusion]" in notes:
        return True
    if any(token in notes for token in ("zone", "bbox", "crop", "bulle", "fusion")):
        return True
    source = block_source_text(block)
    return any(category in {"zone_too_small", "split_bubble", "fused_bubble", "sfx_mixed"} for category in zone_issue_categories(source))


def _zone_fallback_priority(block: OcrBlock) -> int:
    source = block_source_text(block)
    warnings = " ".join(block.quality_warnings).lower()
    categories = set(zone_issue_categories(source))
    words = re.findall(r"[A-Za-z']+", source)
    priority = 0
    if block.confidence is not None and block.confidence < 0.65:
        priority += 5
    if not (block.translation_fr or block.raw_translation_fr).strip():
        priority += 4
    if categories & {"split_bubble", "fused_bubble", "sfx_mixed"}:
        priority += 4
    if categories & {"zone_too_small"}:
        priority += 3
    if "bord du crop" in warnings or "bbox probablement trop petite" in warnings:
        priority += 3
    if "cesure" in warnings or re.search(r"\b[A-Za-z]{2,}-\s+[A-Za-z]{2,}\b", source):
        priority += 3
    if len(words) >= 4:
        priority += 2
    elif len(words) <= 1:
        priority -= 4
    return priority


def _refresh_zone_ocr_alternatives(
    project_path: Path,
    project: ProjectData,
    source_lang: SourceLang,
    *,
    use_gpu: bool,
    include_optional_ocr: bool,
    apply_best: bool,
    max_blocks: int | None,
    fallback_engine: OcrFallbackEngine,
) -> int:
    updated = 0
    candidates_by_page: list[tuple[int, int, PageRecord, OcrBlock]] = []
    for page in project.pages:
        zone_blocks = [
            block for block in page.blocks
            if block.source_lang == source_lang and block.manual_status == "review" and _is_zone_fallback_candidate(block)
        ]
        candidates_by_page.extend(
            (_zone_fallback_priority(block), page.page_index, page, block)
            for block in zone_blocks
        )

    candidates_by_page.sort(key=lambda item: (-item[0], item[1], item[3].reading_order))
    selected = candidates_by_page if max_blocks is None else candidates_by_page[:max_blocks]
    for _priority, _page_index, page, block in selected:
        image_path = resolve_image_path(project_path, project, page)
        if apply_best:
            before = block.ocr_text
            fallback_engine.improve_blocks(
                image_path,
                [block],
                source_lang,
                use_gpu=use_gpu,
                only_suspect=False,
                include_optional_engines=include_optional_ocr,
            )
            if block.ocr_text != before or block.ocr_alternatives:
                updated += 1
            continue
        candidates = fallback_engine.collect_candidates(
            image_path,
            block,
            source_lang,
            use_gpu=use_gpu,
            min_confidence=0.20,
            include_optional_engines=include_optional_ocr,
        )
        block.ocr_alternatives = [candidate.to_dict() for candidate in candidates[:8]]
        warning = "OCR zone fallback: alternatives crop elargi disponibles"
        if warning not in block.quality_warnings:
            block.quality_warnings.append(warning)
        updated += 1
    return updated


def refresh_review_project(
    project_path: str | Path,
    output_path: str | Path | None = None,
    *,
    source_lang: SourceLang = "en",
    use_gpu: bool = False,
    normalize_english: bool = True,
    use_builtin_glossary: bool = True,
    translate_argos: bool = False,
    include_review: bool = False,
    ocr_fallback_zones: bool = False,
    apply_ocr_fallback: bool = False,
    include_optional_ocr: bool = False,
    max_ocr_fallback_zones: int | None = 1,
    translator: ArgosTranslator | None = None,
    quality_checker: TranslationQualityChecker | None = None,
    fallback_engine: OcrFallbackEngine | None = None,
) -> RefreshResult:
    path = Path(project_path)
    out = Path(output_path) if output_path else default_refreshed_path(path)
    project = ProjectCache.load(path)
    blocks, preserved = _iter_refreshable_blocks(project, source_lang, include_review=include_review)
    quality_checker = quality_checker or TranslationQualityChecker()

    if blocks:
        _refresh_blocks_with_rules(blocks, source_lang, normalize_english=normalize_english)
        if translate_argos:
            translator = translator or ArgosTranslator()
            translator.translate_blocks(
                blocks,
                source_lang,
                use_gpu=use_gpu,
                raw_terms=project.glossary_terms,
                normalize_english=normalize_english,
                use_builtin_glossary=use_builtin_glossary,
                force=True,
            )
        quality_checker.apply(blocks, source_lang=source_lang)

    ocr_fallback_blocks = 0
    if ocr_fallback_zones:
        ocr_fallback_blocks = _refresh_zone_ocr_alternatives(
            path,
            project,
            source_lang,
            use_gpu=use_gpu,
            include_optional_ocr=include_optional_ocr,
            apply_best=apply_ocr_fallback,
            max_blocks=max_ocr_fallback_zones,
            fallback_engine=fallback_engine or OcrFallbackEngine(),
        )

    warning_blocks = sum(1 for page in project.pages for block in page.blocks if block.quality_warnings)
    ProjectCache.save(out, project)
    return RefreshResult(
        output_path=out,
        refreshed_blocks=len(blocks),
        ocr_fallback_blocks=ocr_fallback_blocks,
        preserved_blocks=preserved,
        warning_blocks=warning_blocks,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Rafraîchir un projet reviewed sans écraser les corrections humaines."
    )
    parser.add_argument("project", type=Path, help="Projet JSON ou reviewed.json à rafraîchir")
    parser.add_argument("--out-project", type=Path, help="Sortie JSON. Défaut: <project>.refreshed.json")
    parser.add_argument("--source-lang", choices=["en", "ja"], default="en")
    parser.add_argument("--include-review", action="store_true", help="Rafraîchir aussi les blocs marqués review/à revoir")
    parser.add_argument("--gpu", action="store_true", help="Autoriser Argos/CTranslate2 GPU si disponible")
    parser.add_argument("--ocr-fallback-zones", action="store_true", help="Relire seulement les blocs zone/fusion avec crops OCR elargis.")
    parser.add_argument("--max-ocr-fallback-zones", type=int, default=1, help="Nombre maximum de blocs zone relus par OCR fallback. Défaut: 1.")
    parser.add_argument("--apply-ocr-fallback", action="store_true", help="Appliquer la meilleure alternative OCR zone. Par defaut, conserve le texte et stocke les alternatives.")
    parser.add_argument("--include-optional-ocr", action="store_true", help="Autoriser Tesseract/PaddleOCR si installes pour les zones.")
    parser.add_argument(
        "--translate-argos",
        action="store_true",
        help="Retraduire aussi avec Argos. Par défaut, reste offline-safe: règles déterministes + QC seulement.",
    )
    parser.add_argument("--no-normalize-en", action="store_true", help="Désactiver la normalisation anglaise")
    parser.add_argument("--no-builtin-glossary", action="store_true", help="Désactiver le glossaire intégré")
    args = parser.parse_args(argv)

    result = refresh_review_project(
        args.project,
        args.out_project,
        source_lang=args.source_lang,
        use_gpu=args.gpu,
        normalize_english=not args.no_normalize_en,
        use_builtin_glossary=not args.no_builtin_glossary,
        translate_argos=args.translate_argos,
        include_review=args.include_review,
        ocr_fallback_zones=args.ocr_fallback_zones,
        apply_ocr_fallback=args.apply_ocr_fallback,
        include_optional_ocr=args.include_optional_ocr,
        max_ocr_fallback_zones=args.max_ocr_fallback_zones,
    )
    print(f"Projet source       : {args.project}")
    print(f"Projet rafraîchi    : {result.output_path}")
    print(f"Blocs rafraîchis    : {result.refreshed_blocks}")
    print(f"Blocs OCR zone      : {result.ocr_fallback_blocks}")
    print(f"Blocs préservés     : {result.preserved_blocks}")
    print(f"Blocs avec warnings : {result.warning_blocks}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
