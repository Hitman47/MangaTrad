from cbz_manga_translator.core.block_view import (
    block_display_source,
    block_matches_search,
    page_block_stats,
    project_stats,
    visible_blocks,
)
from cbz_manga_translator.core.models import OcrBlock, PageRecord, ProjectData


def block(**overrides):
    data = {
        "id": "b1",
        "bbox": [0, 0, 10, 10],
        "source_lang": "en",
        "ocr_text": "RAW",
        "ocr_corrected_text": "",
        "normalized_source_text": "",
        "raw_translation_fr": "",
        "translation_fr": "",
        "reading_order": 0,
        "manual_status": "unchecked",
        "quality_warnings": [],
    }
    data.update(overrides)
    return OcrBlock(**data)


def test_block_display_source_prefers_normalized_then_corrected_then_raw():
    raw = block(ocr_text="raw")
    corrected = block(ocr_text="raw", ocr_corrected_text="corrected")
    normalized = block(ocr_text="raw", ocr_corrected_text="corrected", normalized_source_text="normalized")

    assert block_display_source(raw) == "raw"
    assert block_display_source(corrected) == "corrected"
    assert block_display_source(normalized) == "normalized"


def test_visible_blocks_filters_without_mutating_input_order():
    blocks = [
        block(id="ok", reading_order=2, translation_fr="trad", manual_status="validated"),
        block(id="warn", reading_order=0, quality_warnings=["bad ocr"]),
        block(id="empty", reading_order=1, translation_fr=""),
        block(id="ignored", reading_order=3, manual_status="ignored"),
    ]

    assert [item.id for item in visible_blocks(blocks, "all")] == ["warn", "empty", "ok", "ignored"]
    assert [item.id for item in visible_blocks(blocks, "warnings")] == ["warn"]
    assert [item.id for item in visible_blocks(blocks, "untranslated")] == ["warn", "empty"]
    assert [item.id for item in visible_blocks(blocks, "unvalidated")] == ["warn", "empty"]
    assert [item.id for item in visible_blocks(blocks, "validated")] == ["ok"]
    assert [item.id for item in visible_blocks(blocks, "ignored")] == ["ignored"]


def test_search_matches_ocr_translation_and_warnings():
    item = block(
        ocr_text="please unhook this",
        translation_fr="Décroche ça, s'il te plaît.",
        quality_warnings=["OCR suspect"],
    )

    assert block_matches_search(item, "unhook")
    assert block_matches_search(item, "décroche")
    assert block_matches_search(item, "ocr suspect")
    assert not block_matches_search(item, "ramen")


def test_page_and_project_stats():
    page = PageRecord(
        page_index=0,
        image_name="001.jpg",
        blocks=[
            block(id="validated", manual_status="validated", translation_fr="OK"),
            block(id="warning", quality_warnings=["à vérifier"]),
            block(id="review", manual_status="review"),
            block(id="ignored", manual_status="ignored"),
        ],
        status="translated",
    )
    stats = page_block_stats(page)
    assert stats.total == 4
    assert stats.active == 3
    assert stats.validated == 1
    assert stats.warnings == 1
    assert stats.review == 1
    assert stats.untranslated == 2
    assert stats.ignored == 1

    project = ProjectData(cbz_path="demo.cbz", pages=[page])
    project_summary = project_stats(project)
    assert project_summary.pages == 1
    assert project_summary.blocks == 4
    assert project_summary.validated_blocks == 1
    assert project_summary.warning_blocks == 1
    assert project_summary.review_blocks == 1
    assert project_summary.translated_pages == 0
    assert project_summary.validated_pages == 0
