from __future__ import annotations

from pathlib import Path

from cbz_manga_translator.core.cache import ProjectCache
from cbz_manga_translator.core.models import OcrBlock, PageRecord, ProjectData
from cbz_manga_translator.translate.argos import ArgosTranslator
from cbz_manga_translator.translate.english_dialogue_normalizer import EnglishDialogueNormalizer
from cbz_manga_translator.translate.memory import (
    TranslationMemory,
    build_translation_memory,
    canonical_memory_key,
    clear_translation_memory_cache,
    memory_source_aliases,
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


def test_build_translation_memory_learns_raw_corrected_and_normalized_aliases(tmp_path: Path) -> None:
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
                            ocr_text="MAGIC? i From A TAMER? I",
                            ocr_corrected_text="magic?! from a tamer?!",
                            normalized_source_text="magic?! from a tamer?!",
                            translation_fr="De la magie ?! De la part d'un dompteur ?!",
                            manual_status="edited",
                        )
                    ],
                )
            ],
        ),
    )

    memory, metadata = build_translation_memory([project_path])

    assert metadata["eligible_blocks"] == 1
    assert memory.lookup("MAGIC? i From A TAMER? I") == "De la magie ?! De la part d'un dompteur ?!"
    assert memory.lookup("magic?! from a tamer?!") == "De la magie ?! De la part d'un dompteur ?!"


def test_build_translation_memory_skips_french_source_aliases(tmp_path: Path) -> None:
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
                            normalized_source_text="Je voulais quitter cette vie.",
                            translation_fr="Je voulais quitter cette vie.",
                            manual_status="edited",
                        )
                    ],
                )
            ],
        ),
    )

    memory, metadata = build_translation_memory([project_path])

    assert metadata["eligible_blocks"] == 1
    assert memory.lookup("I was leaving this mortal coil.") == "Je voulais quitter cette vie."
    assert memory.lookup("Je voulais quitter cette vie.") == ""


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


def test_memory_fuzzy_lookup_tolerates_small_ocr_noise() -> None:
    memory = TranslationMemory(
        {
            "just who do you think i am? i am sonic sodom, y'know!": "Mais pour qui me prends-tu ?",
        }
    )

    assert memory.lookup("Jst who DO You Think I AM? I am Sonic Sodom, Yknow!") == "Mais pour qui me prends-tu ?"


def test_memory_lookup_uses_current_ocr_aliases_before_fuzzy_match() -> None:
    memory = TranslationMemory(
        {
            "who gives a damn about having a perfectly accurate setup!?": "Qui se soucie d'avoir une configuration parfaite ?",
        }
    )

    assert (
        memory.lookup("Who 6ives A RARN About HAVING A Perfectly Accurte Setupi?")
        == "Qui se soucie d'avoir une configuration parfaite ?"
    )


def test_memory_fuzzy_lookup_rejects_ambiguous_near_tie() -> None:
    memory = TranslationMemory(
        {
            "i will protect the saint as the earth knight": "Je protegerai la sainte comme chevalier de la terre.",
            "i will protect the king as the earth knight": "Je protegerai le roi comme chevalier de la terre.",
        }
    )

    assert memory.lookup("I will protect the thing as the earth knight") == ""


def test_memory_source_aliases_follow_current_ocr_repairs() -> None:
    aliases = {canonical_memory_key(alias) for alias in memory_source_aliases("THINK About I, AN UNAPMED GIRL, IN A PLACE Like This. a.")}

    assert "think about it. an unarmed girl, in a place like this. a" in aliases


def test_argos_uses_memory_for_pre_normalized_blocks(tmp_path: Path, monkeypatch) -> None:
    memory_path = tmp_path / "memory.json"
    memory = TranslationMemory({"local residents are advised": "Les residents locaux sont conseilles."})
    write_translation_memory(memory, {}, memory_path)
    monkeypatch.setenv("MANGATRAD_TRANSLATION_MEMORY", str(memory_path))
    clear_translation_memory_cache()
    block = OcrBlock(
        id="b1",
        bbox=[0, 0, 1, 1],
        source_lang="en",
        ocr_text="LOCAL Residents ARE Advised",
        normalized_source_text="LOCAL Residents ARE Advised",
    )

    try:
        prepared = ArgosTranslator._prepare_block_text(block, "en")
    finally:
        clear_translation_memory_cache()

    assert prepared.override_translation_fr == "Les residents locaux sont conseilles."
