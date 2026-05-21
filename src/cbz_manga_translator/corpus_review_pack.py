from __future__ import annotations

import argparse
from pathlib import Path

from cbz_manga_translator.analysis.review_workflow import create_review_pack


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Create a human-correction TSV pack from a MangaTrad analysis folder."
    )
    parser.add_argument("--analysis", required=True, type=Path, help="Folder containing mangatrad_review_blocks.csv")
    parser.add_argument("--out", required=True, type=Path, help="Output folder for the human review pack")
    parser.add_argument("--max-blocks", type=int, default=200, help="Maximum number of blocks to include")
    parser.add_argument("--include-ok", action="store_true", help="Also include low-risk/probably OK blocks")
    parser.add_argument("--only-high", action="store_true", help="Include high-risk blocks only")
    parser.add_argument("--not-balanced", action="store_true", help="Do not balance selected blocks across series")
    args = parser.parse_args(argv)
    result = create_review_pack(
        args.analysis,
        args.out,
        max_blocks=args.max_blocks,
        include_high=True,
        include_medium=not args.only_high,
        include_ok=args.include_ok,
        balanced=not args.not_balanced,
    )
    print(f"Blocs source      : {result.total_rows}")
    print(f"Blocs à corriger  : {result.selected_rows}")
    print(f"Séries couvertes  : {result.series_count}")
    print(f"TSV correction    : {result.review_path}")
    print(f"JSONL correction  : {result.jsonl_path}")
    print(f"Guide             : {result.guide_path}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
