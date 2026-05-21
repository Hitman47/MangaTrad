from __future__ import annotations

import argparse
from pathlib import Path

from cbz_manga_translator.analysis.export_review import export_review_dataset
from cbz_manga_translator.core.cache import ProjectCache


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Export MangaTrad OCR/translation review dataset.")
    parser.add_argument("--project", required=True, help="Path to .manga_translate_project.json")
    parser.add_argument("--out", required=True, help="Output directory for CSV/JSONL/reports")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    project_path = Path(args.project)
    if not project_path.exists():
        raise SystemExit(f"Project cache not found: {project_path}")
    project = ProjectCache.load(project_path)
    outputs = export_review_dataset(project, args.out)
    for label, path in outputs.items():
        print(f"{label}: {path}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
