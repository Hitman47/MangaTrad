from __future__ import annotations

import argparse
from pathlib import Path

from cbz_manga_translator.analysis.corpus_processor import describe_corpus_path, read_corpus_manifest


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inspecte un dossier de corpus MangaTrad et explique pourquoi corpus_process peut ou non le lire."
    )
    parser.add_argument("path", type=Path, help="Dossier corpus à inspecter, par exemple C:\\temp\\mangatrad_corpus")
    parser.add_argument("--count", action="store_true", help="Tente aussi de lire le manifest et affiche le nombre de pages.")
    args = parser.parse_args()

    print(describe_corpus_path(args.path))
    if args.count:
        entries = read_corpus_manifest(args.path)
        print()
        print(f"Pages lisibles par corpus_process: {len(entries)}")
        if entries:
            print(f"Première image: {entries[0].image_path}")
            print(f"Première série: {entries[0].series_label or '(inconnue)'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
