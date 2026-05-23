from __future__ import annotations

from pathlib import Path

from cbz_manga_translator.analysis.ignore_memory import build_ignore_memory, clear_ignore_memory_cache, write_ignore_memory
from cbz_manga_translator.analysis.review_filter import apply_review_filters, non_reviewable_reason
from cbz_manga_translator.core.cache import ProjectCache
from cbz_manga_translator.core.models import OcrBlock, PageRecord, ProjectData


def _block(text: str, status: str = "unchecked", note: str = "") -> OcrBlock:
    return OcrBlock(
        id=text.lower().replace(" ", "_"),
        bbox=[0, 0, 10, 10],
        source_lang="en",
        ocr_text=text,
        manual_status=status,  # type: ignore[arg-type]
        review_notes=note,
    )


def test_build_ignore_memory_learns_human_ignored_blocks(tmp_path: Path) -> None:
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
                        _block("SAAAAA (fwsssh)", "ignored", "[sfx]"),
                        _block("What are you doing?", "edited"),
                    ],
                )
            ],
        ),
    )

    memory, metadata = build_ignore_memory([project_path])

    assert metadata["eligible_blocks"] == 1
    assert memory.lookup("SAAAAA (fwsssh)") == "ignore appris: sfx/bruit"
    assert memory.lookup("What are you doing?") == ""


def test_review_filter_uses_external_ignore_memory(tmp_path: Path, monkeypatch) -> None:
    memory_path = tmp_path / "ignore_memory.json"
    memory, metadata = build_ignore_memory([])
    memory.entries["manual sign"] = "ignore appris"
    write_ignore_memory(memory, metadata, memory_path)
    monkeypatch.setenv("MANGATRAD_IGNORE_MEMORY", str(memory_path))
    clear_ignore_memory_cache()

    try:
        block = _block("Manual sign")
        assert non_reviewable_reason(block) == "ignore appris"
        assert apply_review_filters([block]) == 1
        assert block.manual_status == "ignored"
    finally:
        clear_ignore_memory_cache()


def test_review_filter_does_not_apply_learned_ignore_to_dialogue_like_text(tmp_path: Path, monkeypatch) -> None:
    memory_path = tmp_path / "ignore_memory.json"
    memory, metadata = build_ignore_memory([])
    memory.entries["on your mark, take aim at the 100 meter target! selector on full, fire in short bursts!"] = "ignore appris"
    write_ignore_memory(memory, metadata, memory_path)
    monkeypatch.setenv("MANGATRAD_IGNORE_MEMORY", str(memory_path))
    clear_ignore_memory_cache()

    try:
        block = _block("ON YOUR MARK, TAKE AIM At THE 100 meter TARGET! SELECTOR ON Full, FIRE IN SHORT BURSTS!")
        assert non_reviewable_reason(block) == ""
        assert apply_review_filters([block]) == 0
        assert block.manual_status == "unchecked"
    finally:
        clear_ignore_memory_cache()


def test_signage_and_standalone_sfx_are_auto_ignored() -> None:
    assert non_reviewable_reason(_block("Convenience store ATM")) == "signalétique/interface"
    assert non_reviewable_reason(_block("Fee Phone Card Fee Transfer")) == "signalétique/interface"
    assert non_reviewable_reason(_block("CREAK")) == "sfx/bruit"
    assert non_reviewable_reason(_block("LUNGE")) == "sfx/bruit"
