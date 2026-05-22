from __future__ import annotations

import argparse
from pathlib import Path

from cbz_manga_translator.analysis.review_diagnose import diagnose_review_project, write_diagnostic_report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Diagnostique les corrections humaines d'un projet MangaTrad reviewed.")
    parser.add_argument("project", type=Path, help="Projet .reviewed.json à diagnostiquer.")
    parser.add_argument("--out", type=Path, default=None, help="Dossier de rapport. Défaut: <projet>.diagnostic")
    args = parser.parse_args(argv)

    output_dir = args.out or args.project.with_suffix("").with_name(f"{args.project.stem}.diagnostic")
    report = diagnose_review_project(args.project)
    json_path, md_path = write_diagnostic_report(report, output_dir)
    print(f"Blocs total      : {report.total_blocks}")
    print(f"Blocs modifiés   : {report.changed_blocks}")
    for category, count in sorted(report.category_counts.items(), key=lambda item: (-item[1], item[0])):
        print(f"{category:22}: {count}")
    for key, value in sorted(report.scores.items()):
        print(f"{key:22}: {value:.2%}")
    print(f"Rapport JSON     : {json_path}")
    print(f"Rapport Markdown : {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
