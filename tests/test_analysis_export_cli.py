from __future__ import annotations

from pathlib import Path

from cbz_manga_translator.analysis_export import main
from cbz_manga_translator.core.cache import ProjectCache
from cbz_manga_translator.core.models import OcrBlock, PageRecord, ProjectData


def test_analysis_export_cli(tmp_path: Path, capsys) -> None:
    project = ProjectData(
        cbz_path="sample.cbz",
        pages=[PageRecord(page_index=0, image_name="001.jpg", blocks=[
            OcrBlock(id="b1", bbox=[0, 0, 1, 1], source_lang="en", ocr_text="hello", translation_fr="bonjour")
        ])],
    )
    cache = tmp_path / "sample.cbz.manga_translate_project.json"
    out = tmp_path / "out"
    ProjectCache.save(cache, project)
    assert main(["--project", str(cache), "--out", str(out)]) == 0
    printed = capsys.readouterr().out
    assert "csv:" in printed
    assert (out / "mangatrad_review_blocks.csv").exists()
