from __future__ import annotations

import argparse
from pathlib import Path

from cbz_manga_translator.analysis.review_regression import discover_review_projects
from cbz_manga_translator.translate.memory import build_translation_memory, write_translation_memory


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Construit une memoire de traduction depuis des projets MangaTrad reviewed.")
    parser.add_argument("projects", nargs="+", type=Path, help="Fichiers .reviewed.json a apprendre.")
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("C:/temp/mangatrad_translation_memory.json"),
        help="Chemin JSON de la memoire. Defaut: C:/temp/mangatrad_translation_memory.json",
    )
    parser.add_argument("--statuses", default="edited,validated,review", help="Statuts a apprendre, separes par virgule.")
    args = parser.parse_args(argv)

    statuses = {item.strip() for item in args.statuses.split(",") if item.strip()}
    projects = discover_review_projects(args.projects)
    memory, metadata = build_translation_memory(projects, statuses=statuses)
    output = write_translation_memory(memory, metadata, args.out)
    print(f"Projets       : {len(projects)}")
    print(f"Blocs scannes : {metadata['scanned_blocks']}")
    print(f"Blocs appris  : {metadata['eligible_blocks']}")
    print(f"Entrees       : {metadata['entries']}")
    print(f"Conflits      : {len(metadata['conflicts'])}")
    print(f"Memoire       : {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
