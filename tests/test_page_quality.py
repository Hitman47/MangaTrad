from __future__ import annotations

from cbz_manga_translator.analysis.page_quality import PAGE_CONTEXT_WARNING, PAGE_DENSE_WARNING, apply_page_quality_warnings
from cbz_manga_translator.core.models import OcrBlock, PageRecord


def _block(index: int, *, warning: str = "", text: str = "I WANT A FULL REPORT BY TOMORROW.") -> OcrBlock:
    return OcrBlock(
        id=f"b{index}",
        bbox=[0, 0, 10, 10],
        source_lang="en",
        ocr_text=text,
        translation_fr="Je veux un rapport complet demain.",
        confidence=0.9,
        reading_order=index,
        quality_warnings=[warning] if warning else [],
    )


def test_page_quality_escalates_dense_zone_pages() -> None:
    page = PageRecord(
        page_index=0,
        image_name="page.jpg",
        blocks=[
            _block(0, warning="zone trop petite probable: crop a verifier"),
            _block(1, warning="fusion probable: deux bulles"),
            _block(2, warning="OCR zone visuelle: texte touche le bord du crop"),
            _block(3),
        ],
    )

    changed = apply_page_quality_warnings(page, "en")

    assert changed == 3
    assert sum(1 for block in page.blocks if PAGE_DENSE_WARNING in block.quality_warnings) == 3
    assert all(block.manual_status == "review" for block in page.blocks[:3])


def test_page_quality_marks_neighbouring_incomplete_context() -> None:
    page = PageRecord(
        page_index=0,
        image_name="page.jpg",
        blocks=[
            _block(0, text="then there are easier tar-"),
            _block(1, text="...gets."),
        ],
    )

    changed = apply_page_quality_warnings(page, "en")

    assert changed == 2
    assert all(PAGE_CONTEXT_WARNING in block.quality_warnings for block in page.blocks)
