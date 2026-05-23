from __future__ import annotations

import argparse
from pathlib import Path

from cbz_manga_translator.analysis.ignore_memory import build_ignore_memory, write_ignore_memory


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Construit une mémoire d'ignorés/SFX depuis des projets MangaTrad reviewed.")
    parser.add_argument("projects", nargs="+", type=Path, help="Fichiers .reviewed.json à apprendre.")
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("C:/temp/mangatrad_ignore_memory.json"),
        help="Chemin JSON de la mémoire d'ignorés. Défaut: C:/temp/mangatrad_ignore_memory.json",
    )
    args = parser.parse_args(argv)

    memory, metadata = build_ignore_memory(args.projects)
    output = write_ignore_memory(memory, metadata, args.out)
    print(f"Projets       : {len(args.projects)}")
    print(f"Blocs scannés : {metadata['scanned_blocks']}")
    print(f"Blocs appris  : {metadata['eligible_blocks']}")
    print(f"Entrées       : {metadata['entries']}")
    print(f"Conflits      : {len(metadata['conflicts'])}")
    print(f"Mémoire ignore: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
