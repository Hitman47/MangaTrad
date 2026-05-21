from __future__ import annotations

from cbz_manga_translator.core.models import OcrBlock
from cbz_manga_translator.translate.local_server_client import LocalTranslationServerClient


def test_local_server_url_is_normalized() -> None:
    assert LocalTranslationServerClient("127.0.0.1:8765/").base_url == "http://127.0.0.1:8765"
    assert LocalTranslationServerClient("").base_url == "http://127.0.0.1:8765"


def test_copy_blocks_in_place_keeps_original_objects() -> None:
    original = OcrBlock(
        id="p000_b000",
        bbox=[0, 0, 10, 10],
        source_lang="en",
        ocr_text="hello",
        reading_order=0,
    )
    updated = OcrBlock(
        id="p000_b000",
        bbox=[0, 0, 10, 10],
        source_lang="en",
        ocr_text="hello",
        translation_fr="bonjour",
        reading_order=0,
        manual_status="edited",
    )

    LocalTranslationServerClient._copy_blocks_in_place([original], [updated])

    assert original.translation_fr == "bonjour"
    assert original.manual_status == "edited"
