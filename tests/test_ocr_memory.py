from __future__ import annotations

from pathlib import Path

from cbz_manga_translator.core.cache import ProjectCache
from cbz_manga_translator.core.models import OcrBlock, PageRecord, ProjectData
from cbz_manga_translator.ocr.memory import build_ocr_memory, clear_ocr_memory_cache, write_ocr_memory
from cbz_manga_translator.ocr.text_cleanup import normalize_ocr_text_for_translation
from cbz_manga_translator.translate.english_dialogue_normalizer import EnglishDialogueNormalizer


def test_build_ocr_memory_uses_human_source_corrections(tmp_path: Path) -> None:
    project_path = tmp_path / "project.reviewed.json"
    ProjectCache.save(
        project_path,
        ProjectData(
            cbz_path="corpus",
            pages=[
                PageRecord(
                    page_index=0,
                    image_name="page.jpg",
                    blocks=[
                        OcrBlock(
                            id="b1",
                            bbox=[0, 0, 1, 1],
                            source_lang="en",
                            ocr_text="BLOPR ME N0W",
                            ocr_corrected_text="help me now!",
                            manual_status="edited",
                        ),
                        OcrBlock(
                            id="b2",
                            bbox=[0, 0, 1, 1],
                            source_lang="en",
                            ocr_text="unchecked noise",
                            ocr_corrected_text="do not learn this",
                            manual_status="unchecked",
                        ),
                    ],
                )
            ],
        ),
    )

    memory, metadata = build_ocr_memory([project_path])

    assert metadata["eligible_blocks"] == 1
    assert memory.lookup("BLOPR ME N0W") == "help me now!"
    assert memory.lookup("unchecked noise") == ""


def test_build_ocr_memory_does_not_learn_french_translation_as_source(tmp_path: Path) -> None:
    project_path = tmp_path / "project.reviewed.json"
    ProjectCache.save(
        project_path,
        ProjectData(
            cbz_path="corpus",
            pages=[
                PageRecord(
                    page_index=0,
                    image_name="page.jpg",
                    blocks=[
                        OcrBlock(
                            id="b1",
                            bbox=[0, 0, 1, 1],
                            source_lang="en",
                            ocr_text="I was leaving this mortal coil.",
                            ocr_corrected_text="Je voulais quitter cette vie.",
                            translation_fr="Je voulais quitter cette vie.",
                            manual_status="edited",
                        )
                    ],
                )
            ],
        ),
    )

    memory, metadata = build_ocr_memory([project_path])

    assert metadata["eligible_blocks"] == 0
    assert memory.lookup("I was leaving this mortal coil.") == ""


def test_build_ocr_memory_does_not_learn_corrections_that_drop_strong_punctuation(tmp_path: Path) -> None:
    project_path = tmp_path / "project.reviewed.json"
    ProjectCache.save(
        project_path,
        ProjectData(
            cbz_path="corpus",
            pages=[
                PageRecord(
                    page_index=0,
                    image_name="page.jpg",
                    blocks=[
                        OcrBlock(
                            id="b1",
                            bbox=[0, 0, 1, 1],
                            source_lang="en",
                            ocr_text="then? THERE ARE EASIER TAR- GETS.",
                            ocr_corrected_text="then there are easier targets.",
                            manual_status="edited",
                        )
                    ],
                )
            ],
        ),
    )

    memory, metadata = build_ocr_memory([project_path])

    assert metadata["eligible_blocks"] == 0
    assert memory.lookup("then? THERE ARE EASIER TAR- GETS.") == ""


def test_ocr_cleanup_uses_external_ocr_memory(tmp_path: Path, monkeypatch) -> None:
    memory_path = tmp_path / "ocr_memory.json"
    memory, metadata = build_ocr_memory([])
    memory.entries["blopr me n0w"] = "help me now!"
    write_ocr_memory(memory, metadata, memory_path)
    monkeypatch.setenv("MANGATRAD_OCR_MEMORY", str(memory_path))
    clear_ocr_memory_cache()

    try:
        assert normalize_ocr_text_for_translation("BLOPR ME N0W") == "help me now!"
        assert EnglishDialogueNormalizer.prepare("BLOPR ME N0W").corrected_text == "help me now!"
    finally:
        clear_ocr_memory_cache()
