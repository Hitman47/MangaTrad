from __future__ import annotations

import argparse
from pathlib import Path

from cbz_manga_translator.analysis.corpus_sampler import read_volume_list, sample_corpus


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Extract a representative local page corpus from a list of CBZ/ZIP volumes or series folders. "
            "Folder inputs are treated as series; a few volumes can be sampled from each series."
        )
    )
    parser.add_argument(
        "--input",
        required=True,
        type=Path,
        help="Text file containing one CBZ/ZIP path or one series folder path per line.",
    )
    parser.add_argument("--out", required=True, type=Path, help="Output corpus folder.")
    parser.add_argument("--pages-per-volume", type=int, default=25, help="Number of pages to extract per selected volume.")
    parser.add_argument(
        "--volumes-per-series",
        type=int,
        default=2,
        help="Number of CBZ/ZIP volumes to select from each detected series folder.",
    )
    parser.add_argument("--seed", type=int, default=47, help="Deterministic sampling seed.")
    parser.add_argument(
        "--mode",
        choices=["mixed", "stratified", "random", "busy"],
        default="mixed",
        help="Page sampling strategy. busy = visually dense challenge pages for harder OCR review.",
    )
    parser.add_argument(
        "--series-mode",
        choices=["mixed", "first", "last", "random"],
        default="mixed",
        help="Volume sampling strategy inside each series folder.",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="When an input folder has no direct CBZ/ZIP, scan child folders and treat each parent folder as a series.",
    )
    parser.add_argument("--skip-first", type=int, default=2, help="Ignore this many first pages by default.")
    parser.add_argument("--skip-last", type=int, default=1, help="Ignore this many last pages by default.")
    parser.add_argument(
        "--require-distinct-parent",
        action="store_true",
        help=(
            "Strict legacy check: fail if selected volumes share the same parent folder. "
            "Do not use this when sampling several volumes per series."
        ),
    )
    parser.add_argument("--overwrite", action="store_true", help="Delete the output folder before writing.")
    args = parser.parse_args()

    input_paths = read_volume_list(args.input)
    if not input_paths:
        parser.error("Input list is empty. Add one CBZ/ZIP path or one series folder path per line.")

    result = sample_corpus(
        input_paths,
        args.out,
        pages_per_volume=args.pages_per_volume,
        volumes_per_series=args.volumes_per_series,
        seed=args.seed,
        mode=args.mode,
        series_mode=args.series_mode,
        skip_first=args.skip_first,
        skip_last=args.skip_last,
        recursive=args.recursive,
        require_distinct_parent=args.require_distinct_parent,
        overwrite=args.overwrite,
    )

    print(f"Séries détectées   : {result.series_total}")
    print(f"Tomes sélectionnés : {result.volumes_total}")
    print(f"Tomes traités      : {result.volumes_processed}")
    print(f"Pages extraites    : {result.pages_total}")
    print(f"Images             : {result.pages_dir}")
    print(f"Manifest CSV       : {result.manifest_csv}")
    print(f"Manifest JSONL     : {result.manifest_jsonl}")
    print(f"Rapport            : {result.report_md}")
    if result.warnings:
        print("\nAvertissements:")
        for warning in result.warnings:
            print(f"- {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
