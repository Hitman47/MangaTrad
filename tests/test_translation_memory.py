from __future__ import annotations

from pathlib import Path

from cbz_manga_translator.core.cache import ProjectCache
from cbz_manga_translator.core.models import OcrBlock, PageRecord, ProjectData
from cbz_manga_translator.translate.english_dialogue_normalizer import EnglishDialogueNormalizer
from cbz_manga_translator.translate.memory import (
    build_translation_memory,
    canonical_memory_key,
    clear_translation_memory_cache,
    write_translation_memory,
)


def test_canonical_memory_key_matches_dialogue_key_shape() -> None:
    assert canonical_memory_key(" Hello  ... ") == "hello"
    assert canonical_memory_key("Right??") == "right?"


def test_build_translation_memory_uses_human_corrected_blocks(tmp_path: Path) -> None:
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
                            ocr_text="Just LEAVE It Be",
                            normalized_source_text="Just LEAVE It Be",
                            translation_fr="Laisse tomber",
                            manual_status="edited",
                        ),
                        OcrBlock(
                            id="b2",
                            bbox=[0, 0, 1, 1],
                            source_lang="en",
                            ocr_text="Ignored",
                            normalized_source_text="Ignored",
                            translation_fr="Ignore",
                            manual_status="unchecked",
                        ),
                    ],
                )
            ],
        ),
    )

    memory, metadata = build_translation_memory([project_path])

    assert metadata["eligible_blocks"] == 1
    assert memory.lookup("just leave it be") == "Laisse tomber"
    assert memory.lookup("ignored") == ""


def test_english_normalizer_uses_external_translation_memory(tmp_path: Path, monkeypatch) -> None:
    memory_path = tmp_path / "memory.json"
    memory, metadata = build_translation_memory([])
    memory.entries["custom sentence"] = "Phrase apprise."
    write_translation_memory(memory, metadata, memory_path)
    monkeypatch.setenv("MANGATRAD_TRANSLATION_MEMORY", str(memory_path))
    clear_translation_memory_cache()

    try:
        prepared = EnglishDialogueNormalizer.prepare("Custom sentence.")
    finally:
        clear_translation_memory_cache()

    assert prepared.override_translation_fr == "Phrase apprise."
