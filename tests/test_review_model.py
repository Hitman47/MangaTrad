from pathlib import Path

from cbz_manga_translator.core.cache import ProjectCache
from cbz_manga_translator.core.models import OcrBlock, PageRecord, ProjectData
from cbz_manga_translator.review.model import (
    apply_review_to_block,
    default_reviewed_path,
    iter_review_items,
    is_fused_block,
    is_sfx_block,
    load_review_project,
    review_decision_for_block,
    resolve_image_path,
)


def test_default_reviewed_path():
    assert default_reviewed_path("project.json").name == "project.reviewed.json"
    assert default_reviewed_path("project.reviewed.json").name == "project.reviewed.json"


def test_apply_review_to_block_sets_fields_and_status():
    block = OcrBlock(id="b1", bbox=[1, 2, 3, 4], source_lang="en", ocr_text="bad")
    apply_review_to_block(
        block,
        decision="correct",
        corrected_ocr="good source",
        corrected_source="good normalized",
        corrected_fr="bonne traduction",
        notes="cas utile",
    )
    assert block.manual_status == "edited"
    assert block.ocr_corrected_text == "good source"
    assert block.normalized_source_text == "good normalized"
    assert block.translation_fr == "bonne traduction"
    assert block.review_notes == "cas utile"


def test_review_items_and_image_resolution(tmp_path: Path):
    image = tmp_path / "page.jpg"
    image.write_bytes(b"fake")
    project = ProjectData(
        cbz_path=str(tmp_path),
        pages=[
            PageRecord(
                page_index=0,
                image_name="page.jpg",
                blocks=[
                    OcrBlock(
                        id="b1",
                        bbox=[1, 2, 3, 4],
                        source_lang="en",
                        ocr_text="Hello",
                        translation_fr="Hello",
                        quality_warnings=["identique"],
                    )
                ],
            )
        ],
    )
    project_path = tmp_path / "project.json"
    ProjectCache.save(project_path, project)
    loaded = load_review_project(project_path)
    items = list(iter_review_items(loaded.project))
    assert len(items) == 1
    assert items[0].risk_band == "HIGH"
    assert resolve_image_path(project_path, loaded.project, loaded.project.pages[0]) == image


def test_sfx_decision_is_preserved_in_notes():
    block = OcrBlock(id="b1", bbox=[1, 2, 3, 4], source_lang="en", ocr_text="THWAM")
    apply_review_to_block(block, decision="sfx", notes="onomatopée")
    assert block.manual_status == "ignored"
    assert "[sfx]" in block.review_notes
    assert "onomatopée" in block.review_notes
    assert is_sfx_block(block)
    assert review_decision_for_block(block) == "sfx"


def test_fused_decision_marks_review_with_searchable_note():
    block = OcrBlock(id="b1", bbox=[1, 2, 3, 4], source_lang="en", ocr_text="dialogue SFX dialogue")

    apply_review_to_block(block, decision="fused", notes="bulle + bruit melanges")

    assert block.manual_status == "review"
    assert "[fusion]" in block.review_notes
    assert "bulle + bruit melanges" in block.review_notes
    assert is_fused_block(block)
    assert review_decision_for_block(block) == "fused"


def test_apply_review_to_block_does_not_store_unchanged_mirror_fields():
    block = OcrBlock(
        id="b1",
        bbox=[1, 2, 3, 4],
        source_lang="en",
        ocr_text="Hello",
        raw_translation_fr="Bonjour.",
    )
    apply_review_to_block(
        block,
        decision="validate",
        corrected_ocr="Hello",
        corrected_source="Hello",
        corrected_fr="Bonjour.",
    )

    assert block.manual_status == "validated"
    assert block.ocr_corrected_text == ""
    assert block.normalized_source_text == ""
    assert block.translation_fr == ""


def test_iter_review_items_exposes_sfx_and_searchable_diagnostics():
    project = ProjectData(
        cbz_path="corpus",
        pages=[
            PageRecord(
                page_index=0,
                image_name="page.jpg",
                blocks=[
                    OcrBlock(
                        id="b1",
                        bbox=[1, 2, 3, 4],
                        source_lang="en",
                        ocr_text="BOOM",
                        manual_status="ignored",
                        quality_warnings=["sound effect"],
                        review_notes="[sfx] explosion",
                    )
                ],
            )
        ],
    )

    item = next(iter(iter_review_items(project)))

    assert item.review_decision == "sfx"
    assert "SFX" in item.display
    assert "sound effect" in item.diagnostic_preview
    assert "explosion" in item.notes_preview


def test_iter_review_items_exposes_fused_decision():
    project = ProjectData(
        cbz_path="corpus",
        pages=[
            PageRecord(
                page_index=0,
                image_name="page.jpg",
                blocks=[
                    OcrBlock(
                        id="b1",
                        bbox=[1, 2, 3, 4],
                        source_lang="en",
                        ocr_text="dialogue SFX dialogue",
                        manual_status="review",
                        review_notes="[fusion] bulles melangees",
                    )
                ],
            )
        ],
    )

    item = next(iter(iter_review_items(project)))

    assert item.review_decision == "fused"
    assert "fusion" in item.display
    assert "bulles melangees" in item.notes_preview
