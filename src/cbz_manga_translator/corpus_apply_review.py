from __future__ import annotations

import argparse
from pathlib import Path

from cbz_manga_translator.analysis.review_workflow import apply_review_pack


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Apply a corrected human review TSV/CSV to a MangaTrad project cache.")
    parser.add_argument("--project", required=True, type=Path, help="mangatrad_corpus_project.json or .manga_translate_project.json")
    parser.add_argument("--review", required=True, type=Path, help="Corrected mangatrad_human_review_pack.tsv, or legacy .csv")
    parser.add_argument("--out-project", type=Path, default=None, help="Optional output project path. Defaults to in-place.")
    args = parser.parse_args(argv)
    result = apply_review_pack(args.project, args.review, output_project_path=args.out_project)
    print(f"Projet écrit       : {result.output_project_path}")
    print(f"Blocs changés      : {result.changed_blocks}")
    print(f"Validés            : {result.validated_blocks}")
    print(f"Corrigés           : {result.corrected_blocks}")
    print(f"Ignorés/SFX        : {result.ignored_blocks}")
    print(f"À revoir           : {result.review_blocks}")
    print(f"Lignes ignorées    : {result.skipped_rows}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
