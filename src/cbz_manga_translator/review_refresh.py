from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

from cbz_manga_translator.core.cache import ProjectCache
from cbz_manga_translator.core.models import OcrBlock, ProjectData, SourceLang
from cbz_manga_translator.translate.argos import ArgosTranslator
from cbz_manga_translator.translate.english_dialogue_normalizer import EnglishDialogueNormalizer
from cbz_manga_translator.translate.quality import TranslationQualityChecker


@dataclass(slots=True)
class RefreshResult:
    output_path: Path
    refreshed_blocks: int
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
        source = (block.normalized_source_text or block.ocr_corrected_text or block.ocr_text).strip()
        if not source:
            continue
        prepared = EnglishDialogueNormalizer.prepare(source, normalize_english=normalize_english)
        block.ocr_corrected_text = prepared.corrected_text
        block.normalized_source_text = prepared.normalized_text
        if prepared.override_translation_fr:
            block.raw_translation_fr = prepared.override_translation_fr
            block.translation_fr = prepared.override_translation_fr


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
    translator: ArgosTranslator | None = None,
    quality_checker: TranslationQualityChecker | None = None,
) -> RefreshResult:
    path = Path(project_path)
    out = Path(output_path) if output_path else default_refreshed_path(path)
    project = ProjectCache.load(path)
    blocks, preserved = _iter_refreshable_blocks(project, source_lang, include_review=include_review)
    quality_checker = quality_checker or TranslationQualityChecker()

    if blocks:
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
        else:
            _refresh_blocks_with_rules(blocks, source_lang, normalize_english=normalize_english)
        quality_checker.apply(blocks, source_lang=source_lang)

    warning_blocks = sum(1 for block in blocks if block.quality_warnings)
    ProjectCache.save(out, project)
    return RefreshResult(
        output_path=out,
        refreshed_blocks=len(blocks),
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
    )
    print(f"Projet source       : {args.project}")
    print(f"Projet rafraîchi    : {result.output_path}")
    print(f"Blocs rafraîchis    : {result.refreshed_blocks}")
    print(f"Blocs préservés     : {result.preserved_blocks}")
    print(f"Blocs avec warnings : {result.warning_blocks}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
