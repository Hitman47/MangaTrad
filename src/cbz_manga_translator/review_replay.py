from __future__ import annotations

import argparse
import json
from pathlib import Path

from cbz_manga_translator.review.replay import replay_review_project, write_replay_report


def _parse_index_list(value: str) -> set[int]:
    indices: set[int] = set()
    for chunk in value.split(","):
        item = chunk.strip().lower().removeprefix("p")
        if not item:
            continue
        if "-" in item:
            left, right = item.split("-", 1)
            start = int(left)
            end = int(right)
            if end < start:
                start, end = end, start
            indices.update(range(start, end + 1))
        else:
            indices.add(int(item))
    return indices


def _failure_page_indices(report_path: Path, statuses: set[str]) -> set[int]:
    data = json.loads(report_path.read_text(encoding="utf-8"))
    results = data.get("results", [])
    indices: set[int] = set()
    for item in results:
        if isinstance(item, dict) and str(item.get("status", "")) in statuses:
            indices.add(int(item.get("page_index", -1)))
    return {index for index in indices if index >= 0}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Rejoue OCR + traduction sur les pages déjà corrigées et compare aux corrections humaines."
    )
    parser.add_argument("project", type=Path, help="Projet .reviewed.json à rejouer.")
    parser.add_argument("--out", type=Path, default=None, help="Dossier de rapport. Défaut: <projet>/replay_review.")
    parser.add_argument("--source-lang", choices=["en", "ja"], default="en")
    parser.add_argument("--page-indices", default="", help="Pages projet zero-based a rejouer, ex: 506,447 ou 120-123.")
    parser.add_argument("--page-numbers", default="", help="Pages humaines one-based a rejouer, ex: 507,448 ou 121-124.")
    parser.add_argument("--failures-from", type=Path, default=None, help="Rapport replay JSON precedent: rejoue seulement les pages en echec.")
    parser.add_argument("--failure-statuses", default="missing,mismatch,source_mismatch,translation_mismatch")
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
    selected_indices: set[int] = set()
    if args.page_indices:
        selected_indices.update(_parse_index_list(args.page_indices))
    if args.page_numbers:
        selected_indices.update(index - 1 for index in _parse_index_list(args.page_numbers) if index > 0)
    if args.failures_from:
        failure_statuses = {item.strip() for item in args.failure_statuses.split(",") if item.strip()}
        selected_indices.update(_failure_page_indices(args.failures_from, failure_statuses))
    page_indices = selected_indices or None
    max_pages = None if args.max_pages <= 0 else args.max_pages
    output_dir = args.out or args.project.with_suffix("").with_name(f"{args.project.stem}.replay")
    report = replay_review_project(
        args.project,
        source_lang=args.source_lang,  # type: ignore[arg-type]
        max_pages=max_pages,
        page_indices=page_indices,
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
