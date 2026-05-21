from __future__ import annotations

import argparse
from pathlib import Path

from cbz_manga_translator.analysis.corpus_processor import process_corpus


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Batch OCR + local translation on a sampled MangaTrad corpus, then export review CSV/JSONL reports. "
            "This is the step to run after corpus_sample."
        )
    )
    parser.add_argument("--corpus", required=True, type=Path, help="Corpus folder created by corpus_sample.")
    parser.add_argument("--out", required=True, type=Path, help="Output folder for cache and analysis exports.")
    parser.add_argument("--source-lang", choices=["en", "ja"], default="en", help="Source language for OCR/translation.")
    parser.add_argument("--limit", type=int, default=None, help="Process only N pages for a quick test.")
    parser.add_argument("--start", type=int, default=0, help="Start from this corpus manifest index.")
    parser.add_argument(
        "--limit-mode",
        choices=["stratified", "random", "first"],
        default="stratified",
        help="How --limit selects pages. stratified spreads pages across series; first preserves manifest order.",
    )
    parser.add_argument("--seed", type=int, default=47, help="Seed used by --limit-mode random and for reproducible selection metadata.")
    parser.add_argument("--cpu", action="store_true", help="Force CPU instead of CUDA.")
    parser.add_argument("--min-confidence", type=float, default=0.20, help="OCR filtering confidence threshold.")
    parser.add_argument("--no-merge-lines", action="store_true", help="Disable OCR line grouping.")
    parser.add_argument("--no-filter-noise", action="store_true", help="Keep OCR fragments/noise.")
    parser.add_argument(
        "--refine-crops",
        action="store_true",
        help="Enable expensive EasyOCR crop refinement during primary OCR. Slower but sometimes better.",
    )
    parser.add_argument(
        "--fallback",
        choices=["off", "suspects", "all"],
        default="off",
        help="Run OCR fallback after primary OCR. 'all' is slow; start with 'suspects'.",
    )
    parser.add_argument(
        "--include-optional-ocr",
        action="store_true",
        help="Allow fallback to call Tesseract/PaddleOCR if installed. Slow and experimental.",
    )
    parser.add_argument("--ocr-only", action="store_true", help="Run OCR and QC, but skip translation.")
    parser.add_argument("--no-normalize-en", action="store_true", help="Disable English dialogue normalization.")
    parser.add_argument("--no-builtin-glossary", action="store_true", help="Disable built-in manga glossary.")
    parser.add_argument("--glossary", type=Path, default=None, help="Optional text file with project glossary rules.")
    parser.add_argument("--force", action="store_true", help="Reprocess pages even if cached blocks already exist.")
    parser.add_argument("--checkpoint-every", type=int, default=10, help="Save cache/progress every N processed pages.")
    args = parser.parse_args()

    glossary_terms = args.glossary.read_text(encoding="utf-8") if args.glossary else None
    result = process_corpus(
        args.corpus,
        args.out,
        source_lang=args.source_lang,  # type: ignore[arg-type]
        limit=args.limit,
        start=args.start,
        limit_mode=args.limit_mode,
        seed=args.seed,
        use_gpu=not args.cpu,
        min_confidence=args.min_confidence,
        merge_lines=not args.no_merge_lines,
        filter_noise=not args.no_filter_noise,
        refine_crops=args.refine_crops,
        fallback=args.fallback,
        include_optional_ocr=args.include_optional_ocr,
        translate=not args.ocr_only,
        normalize_english=not args.no_normalize_en,
        use_builtin_glossary=not args.no_builtin_glossary,
        force=args.force,
        checkpoint_every=args.checkpoint_every,
        raw_terms=glossary_terms,
    )

    print(f"Pages corpus      : {result.pages_total}")
    print(f"Pages traitées    : {result.pages_processed}")
    print(f"Pages ignorées    : {result.pages_skipped}")
    print(f"Blocs             : {result.blocks_total}")
    print(f"Blocs QC          : {result.warnings_total}")
    print(f"Durée             : {result.elapsed_seconds:.1f}s")
    print(f"Cache projet      : {result.cache_path}")
    print(f"Analyse           : {result.analysis_dir}")
    print(f"CSV review        : {result.review_csv}")
    print(f"JSONL review      : {result.review_jsonl}")
    print(f"Rapport qualité   : {result.quality_report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
