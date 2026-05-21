from __future__ import annotations

import argparse
from pathlib import Path

from cbz_manga_translator.analysis.corpus_rules import build_learned_profile, read_review_rows, write_learned_profile


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Learn lightweight QC/glossary hints from MangaTrad analysis exports.")
    parser.add_argument("--analysis", required=True, help="Analysis directory containing mangatrad_review_blocks.csv")
    parser.add_argument("--out", required=True, help="Output directory for learned profile/report files")
    parser.add_argument("--max-items", type=int, default=120, help="Maximum rows per learned section")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    rows = read_review_rows(args.analysis)
    profile = build_learned_profile(rows, max_items=args.max_items)
    paths = write_learned_profile(profile, args.out)
    print(f"Blocs analysés      : {profile.summary['rows']}")
    print(f"High risk          : {profile.summary['high_risk_rows']}")
    print(f"Medium risk        : {profile.summary['medium_risk_rows']}")
    print(f"Séries             : {profile.summary['series_count']}")
    print(f"Profil JSON        : {paths['profile']}")
    print(f"Rapport            : {paths['report']}")
    print(f"Glossaire candidat : {paths['glossary']}")
    print(f"Résidus QC         : {paths['residue_words']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
