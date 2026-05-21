from __future__ import annotations

from cbz_manga_translator.core.models import OcrBlock
from cbz_manga_translator.server import TranslationRequestError, translate_blocks_request


class FakeTranslator:
    def translate_blocks(self, blocks, source_lang, **kwargs):  # type: ignore[no-untyped-def]
        for block in blocks:
            block.translation_fr = f"FR:{block.ocr_text}"
            block.raw_translation_fr = block.translation_fr
        return blocks


def test_translate_blocks_request_serializes_blocks() -> None:
    block = OcrBlock(
        id="p000_b000",
        bbox=[1, 2, 3, 4],
        source_lang="en",
        ocr_text="hello",
        reading_order=0,
    )

    response = translate_blocks_request(
        FakeTranslator(),  # type: ignore[arg-type]
        {"source_lang": "en", "blocks": [block.to_dict()], "force": True},
    )

    assert response["backend"] == "argos"
    assert response["blocks"][0]["translation_fr"] == "FR:hello"


def test_translate_blocks_request_rejects_unknown_language() -> None:
    try:
        translate_blocks_request(FakeTranslator(), {"source_lang": "de", "blocks": []})  # type: ignore[arg-type]
    except TranslationRequestError as exc:
        assert "source_lang" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("TranslationRequestError expected")
