from __future__ import annotations

import argparse
from pathlib import Path

from cbz_manga_translator.review.replay import replay_review_project, write_replay_report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Rejoue OCR + traduction sur les pages déjà corrigées et compare aux corrections humaines."
    )
    parser.add_argument("project", type=Path, help="Projet .reviewed.json à rejouer.")
    parser.add_argument("--out", type=Path, default=None, help="Dossier de rapport. Défaut: <projet>/replay_review.")
    parser.add_argument("--source-lang", choices=["en", "ja"], default="en")
    parser.add_argument("--max-pages", type=int, default=3, help="Nombre max de pages corrigées à rejouer.")
    parser.add_argument("--statuses", default="edited,validated", help="Statuts humains ciblés, séparés par virgule.")
    parser.add_argument("--cpu", action="store_true", help="Force OCR et traduction CPU.")
    parser.add_argument("--ocr-cpu", action="store_true", help="Force seulement l'OCR CPU.")
    parser.add_argument("--refine-crops", action="store_true", help="OCR crop refinement, plus lent.")
    parser.add_argument("--rescue-small-text", action="store_true", help="Second passage OCR lent pour petits textes/interjections.")
    parser.add_argument("--min-iou", type=float, default=0.35, help="Recouvrement bbox minimum pour matcher un bloc.")
    parser.add_argument("--source-threshold", type=float, default=0.92)
    parser.add_argument("--translation-threshold", type=float, default=0.85)
    args = parser.parse_args(argv)

    statuses = {item.strip() for item in args.statuses.split(",") if item.strip()}
    output_dir = args.out or args.project.with_suffix("").with_name(f"{args.project.stem}.replay")
    report = replay_review_project(
        args.project,
        source_lang=args.source_lang,  # type: ignore[arg-type]
        max_pages=args.max_pages,
        statuses=statuses,
        min_iou=args.min_iou,
        source_threshold=args.source_threshold,
        translation_threshold=args.translation_threshold,
        use_gpu=not args.cpu,
        ocr_use_gpu=False if args.ocr_cpu else None,
        refine_crops=args.refine_crops,
        rescue_small_text=args.rescue_small_text,
    )
    json_path, md_path = write_replay_report(report, output_dir)
    print(f"Pages rejouées       : {report.pages_replayed}")
    print(f"Blocs ciblés         : {report.target_blocks}")
    print(f"Blocs retrouvés      : {report.matched_blocks}")
    print(f"Sources OK           : {report.source_matches}")
    print(f"Traductions OK       : {report.translation_matches}")
    print(f"Match complet        : {report.full_matches}")
    print(f"Durée                : {report.elapsed_seconds:.1f}s")
    print(f"Rapport JSON         : {json_path}")
    print(f"Rapport Markdown     : {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
