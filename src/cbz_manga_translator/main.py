from __future__ import annotations

import argparse
from pathlib import Path

from cbz_manga_translator import __version__
from cbz_manga_translator.core.cache import ProjectCache
from cbz_manga_translator.core.cbz_reader import CbzReader
from cbz_manga_translator.export.html_export import export_html_project


def main() -> int:
    parser = argparse.ArgumentParser(description="CBZ manga OCR + Argos translation prototype")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--inspect", type=Path, help="Inspect a CBZ and list detected image pages")
    parser.add_argument("--export-html", type=Path, help="Export an already-saved project cache to HTML for this CBZ")
    parser.add_argument("--project", type=Path, help="Project JSON cache path. Defaults to <cbz>.manga_translate_project.json")
    parser.add_argument("--output", type=Path, help="HTML output folder")
    args = parser.parse_args()

    if args.inspect:
        reader = CbzReader(args.inspect)
        images = reader.image_names()
        print(f"CBZ: {reader.path}")
        print(f"Images: {len(images)}")
        for index, image in enumerate(images[:20], start=1):
            print(f"{index:03d}: {image}")
        if len(images) > 20:
            print(f"... {len(images) - 20} more")
        return 0

    if args.export_html:
        if args.output is None:
            parser.error("--output is required with --export-html")
        reader = CbzReader(args.export_html)
        project_path = args.project or ProjectCache.default_path(args.export_html)
        project = ProjectCache.load(project_path)
        index = export_html_project(reader, project, args.output)
        print(index)
        return 0

    from cbz_manga_translator.app import run_gui

    return run_gui()


if __name__ == "__main__":
    raise SystemExit(main())
