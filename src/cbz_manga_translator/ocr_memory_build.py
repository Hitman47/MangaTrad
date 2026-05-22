from __future__ import annotations

import argparse
from pathlib import Path

from cbz_manga_translator.ocr.memory import build_ocr_memory, write_ocr_memory


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Construit une memoire OCR depuis des projets MangaTrad reviewed.")
    parser.add_argument("projects", nargs="+", type=Path, help="Fichiers .reviewed.json a apprendre.")
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("C:/temp/mangatrad_ocr_memory.json"),
        help="Chemin JSON de la memoire OCR. Defaut: C:/temp/mangatrad_ocr_memory.json",
    )
    parser.add_argument("--statuses", default="edited,validated", help="Statuts a apprendre, separes par virgule.")
    args = parser.parse_args(argv)

    statuses = {item.strip() for item in args.statuses.split(",") if item.strip()}
    memory, metadata = build_ocr_memory(args.projects, statuses=statuses)
    output = write_ocr_memory(memory, metadata, args.out)
    print(f"Projets       : {len(args.projects)}")
    print(f"Blocs scannes : {metadata['scanned_blocks']}")
    print(f"Blocs appris  : {metadata['eligible_blocks']}")
    print(f"Entrees       : {metadata['entries']}")
    print(f"Conflits      : {len(metadata['conflicts'])}")
    print(f"Memoire OCR   : {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
