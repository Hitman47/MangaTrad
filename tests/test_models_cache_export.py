from __future__ import annotations

import zipfile
from pathlib import Path

from cbz_manga_translator.core.cache import ProjectCache
from cbz_manga_translator.core.cbz_reader import CbzReader
from cbz_manga_translator.core.models import OcrBlock, ProjectData
from cbz_manga_translator.export.html_export import export_html_project


def test_project_data_roundtrip(tmp_path: Path) -> None:
    project = ProjectData.from_images("book.cbz", ["001.jpg"])
    project.pages[0].blocks.append(
        OcrBlock(
            id="p0000_b0000",
            bbox=[1, 2, 3, 4],
            source_lang="en",
            ocr_text="Hello",
            ocr_corrected_text="Hello",
            normalized_source_text="Hello",
            raw_translation_fr="Salut",
            translation_fr="Bonjour",
            confidence=0.9,
            manual_status="review",
            quality_warnings=["test warning"],
        )
    )
    cache = tmp_path / "project.json"
    ProjectCache.save(cache, project)
    loaded = ProjectCache.load(cache)
    assert loaded.pages[0].blocks[0].translation_fr == "Bonjour"
    assert loaded.pages[0].blocks[0].bbox == [1, 2, 3, 4]
    assert loaded.pages[0].blocks[0].quality_warnings == ["test warning"]
    assert loaded.pages[0].blocks[0].ocr_corrected_text == "Hello"
    assert loaded.pages[0].blocks[0].normalized_source_text == "Hello"
    assert loaded.pages[0].blocks[0].raw_translation_fr == "Salut"
    assert loaded.pages[0].blocks[0].manual_status == "review"


def test_export_html_project(tmp_path: Path) -> None:
    cbz = tmp_path / "sample.cbz"
    with zipfile.ZipFile(cbz, "w") as archive:
        archive.writestr("001.jpg", b"fake-image-bytes")
    reader = CbzReader(cbz)
    project = ProjectData.from_images(cbz, reader.image_names())
    project.pages[0].blocks.append(
        OcrBlock(
            id="p0000_b0000",
            bbox=[10, 20, 30, 40],
            source_lang="en",
            ocr_text="Test",
            translation_fr="Essai",
            confidence=0.75,
        )
    )
    index = export_html_project(reader, project, tmp_path / "export")
    content = index.read_text(encoding="utf-8")
    assert "Essai" in content
    assert "bbox 10,20,30,40" in content
    assert (tmp_path / "export" / "images" / "001.jpg").exists()
