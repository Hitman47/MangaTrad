import argparse
from pathlib import Path

from cbz_manga_translator.analysis.review_regression import run_review_regression, write_regression_report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Scanne les projets .reviewed.json et vérifie les corrections humaines contre les règles actuelles."
    )
    parser.add_argument("paths", nargs="+", type=Path, help="Fichiers, dossiers ou glob patterns de projets reviewed.")
    parser.add_argument("--out", type=Path, default=Path("review_regression"), help="Dossier de rapport.")
    parser.add_argument("--source-threshold", type=float, default=0.92)
    parser.add_argument("--translation-threshold", type=float, default=0.85)
    args = parser.parse_args(argv)

    report = run_review_regression(
        args.paths,
        source_threshold=args.source_threshold,
        translation_threshold=args.translation_threshold,
    )
    json_path, md_path = write_regression_report(report, args.out)
    print(f"Projets analysés             : {report.project_count}")
    print(f"Blocs historiques évalués    : {report.block_count}")
    print(
        f"Source OK                    : {report.source_match_count}/{report.evaluated_source_count} "
        f"({report.scores['source_match_rate']:.2%})"
    )
    print(
        f"Traductions apprises OK      : {report.translation_match_count}/{report.evaluated_translation_count} "
        f"({report.scores['translation_rule_match_rate']:.2%})"
    )
    print(
        f"Ignorés auto-couverts        : {report.ignored_auto_covered_count}/{report.ignored_count} "
        f"({report.scores['ignored_auto_covered_rate']:.2%})"
    )
    print(f"Rapport JSON                 : {json_path}")
    print(f"Rapport Markdown             : {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
