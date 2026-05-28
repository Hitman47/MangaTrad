from __future__ import annotations

from cbz_manga_translator.core.editing import is_translation_protected, set_block_field, set_manual_status, status_label
from cbz_manga_translator.core.models import OcrBlock
from cbz_manga_translator.translate.argos import ArgosTranslator


def make_block() -> OcrBlock:
    return OcrBlock(
        id="p0000_b0000",
        bbox=[1, 2, 3, 4],
        source_lang="en",
        ocr_text="GRAMMA; THAT;",
        normalized_source_text="grandma; that;",
        raw_translation_fr="grand-mère; cela;",
        translation_fr="grand-mère; cela;",
        quality_warnings=["bad"],
    )


def test_set_block_field_invalidates_downstream_generated_fields() -> None:
    block = make_block()

    set_block_field(block, "ocr_corrected_text", "GRAMMA, LOOKY THAT.")

    assert block.ocr_corrected_text == "GRAMMA, LOOKY THAT."
    assert block.normalized_source_text == ""
    assert block.raw_translation_fr == ""
    assert block.translation_fr == ""
    assert block.quality_warnings == []
    assert block.manual_status == "edited"


def test_set_manual_status_validates_and_clears_warnings() -> None:
    block = make_block()

    count = set_manual_status([block], "validated")

    assert count == 1
    assert block.manual_status == "validated"
    assert block.quality_warnings == []
    assert status_label(block.manual_status) == "validé"
    assert is_translation_protected(block)


def test_set_manual_status_review_keeps_visible_warning() -> None:
    block = make_block()

    set_manual_status([block], "review")

    assert block.manual_status == "review"
    assert any("revoir" in warning for warning in block.quality_warnings)
    assert not is_translation_protected(block)


def test_translator_uses_manual_corrected_text_before_raw_ocr() -> None:
    block = make_block()
    block.ocr_corrected_text = "GRAMMA, LOOKY THAT."
    block.normalized_source_text = ""

    prepared = ArgosTranslator._prepare_block_text(
        block,
        "en",
        raw_terms=None,
        normalize_english=True,
        use_builtin_glossary=False,
    )

    assert prepared.corrected_text == "grandma, looky that."
    assert prepared.normalized_source_text == "grandma, look at that."
    assert prepared.override_translation_fr == "Grand-mère, regarde ça !"


def test_translator_respects_manual_normalized_text() -> None:
    block = make_block()
    block.ocr_corrected_text = "A rough OCR line"
    block.normalized_source_text = "grandma, look at that."
    block.manual_status = "edited"

    prepared = ArgosTranslator._prepare_block_text(
        block,
        "en",
        raw_terms=None,
        normalize_english=True,
        use_builtin_glossary=False,
    )

    assert prepared.text == "grandma, look at that."
    assert prepared.corrected_text == "A rough OCR line"
    assert prepared.normalized_source_text == "grandma, look at that."


def test_translator_recomputes_stale_generated_source_for_unchecked_blocks() -> None:
    block = make_block()
    block.ocr_text = "WAIT? THERE' $ SOME KIND OF FRUITY SMELL!"
    block.ocr_corrected_text = "wait? there' $ some kind of fruity smell!"
    block.normalized_source_text = "wait? there' $ some kind of fruity smell!"
    block.manual_status = "unchecked"

    prepared = ArgosTranslator._prepare_block_text(
        block,
        "en",
        raw_terms=None,
        normalize_english=True,
        use_builtin_glossary=False,
    )

    assert prepared.normalized_source_text == "wait! there is some kind of fruity smell...!"
    assert prepared.override_translation_fr == "Attendez ! Il y a une odeur fruitee... !"


def test_translator_preserves_human_edited_normalized_text() -> None:
    block = make_block()
    block.ocr_text = "WAIT? THERE' $ SOME KIND OF FRUITY SMELL!"
    block.ocr_corrected_text = "human OCR"
    block.normalized_source_text = "human normalized source"
    block.manual_status = "edited"

    prepared = ArgosTranslator._prepare_block_text(
        block,
        "en",
        raw_terms=None,
        normalize_english=True,
        use_builtin_glossary=False,
    )

    assert prepared.corrected_text == "human OCR"
    assert prepared.normalized_source_text == "human normalized source"


def test_apply_ocr_alternative_invalidates_generated_fields() -> None:
    from cbz_manga_translator.core.editing import apply_ocr_alternative

    block = make_block()
    block.ocr_alternatives = [
        {"engine": "paddleocr", "text": "please unhook this", "confidence": 0.91, "score": 9.2, "note": "fallback"}
    ]

    selected = apply_ocr_alternative(block, 0)

    assert selected == "please unhook this"
    assert block.ocr_text == "please unhook this"
    assert block.confidence == 0.91
    assert block.normalized_source_text == ""
    assert block.translation_fr == ""
    assert block.manual_status == "edited"
    assert any("alternative OCR" in warning for warning in block.quality_warnings)


def test_merge_blocks_joins_text_and_unions_bbox() -> None:
    from cbz_manga_translator.core.editing import merge_blocks

    first = OcrBlock(id="b1", bbox=[10, 10, 30, 20], source_lang="en", ocr_text="please", reading_order=0, confidence=0.8)
    second = OcrBlock(id="b2", bbox=[28, 18, 60, 40], source_lang="en", ocr_text="unhook this", reading_order=1, confidence=0.6)
    third = OcrBlock(id="b3", bbox=[70, 50, 90, 80], source_lang="en", ocr_text="later", reading_order=2)
    blocks = [first, second, third]

    merged = merge_blocks(blocks, ["b1", "b2"])

    assert merged.id == "b1"
    assert merged.bbox == [10, 10, 60, 40]
    assert merged.ocr_text == "please\nunhook this"
    assert merged.translation_fr == ""
    assert [block.id for block in blocks] == ["b1", "b3"]
    assert [block.reading_order for block in blocks] == [0, 1]


def test_split_block_by_lines_creates_separate_blocks() -> None:
    from cbz_manga_translator.core.editing import split_block_by_lines

    source = OcrBlock(id="b1", bbox=[10, 10, 30, 50], source_lang="en", ocr_text="one\ntwo", reading_order=0)
    other = OcrBlock(id="b2", bbox=[50, 10, 70, 30], source_lang="en", ocr_text="other", reading_order=1)
    blocks = [source, other]

    created = split_block_by_lines(blocks, "b1", "one\ntwo")

    assert [block.ocr_text for block in created] == ["one", "two"]
    assert [block.id for block in blocks] == ["b1_s1", "b1_s2", "b2"]
    assert created[0].bbox == [10, 10, 30, 30]
    assert created[1].bbox == [10, 30, 30, 50]
    assert [block.reading_order for block in blocks] == [0, 1, 2]


def test_move_block_order_swaps_reading_order() -> None:
    from cbz_manga_translator.core.editing import move_block_order

    blocks = [
        OcrBlock(id="b1", bbox=[0, 0, 1, 1], source_lang="en", ocr_text="first", reading_order=0),
        OcrBlock(id="b2", bbox=[0, 0, 1, 1], source_lang="en", ocr_text="second", reading_order=1),
    ]

    moved = move_block_order(blocks, "b2", -1)

    assert moved.id == "b2"
    assert {block.id: block.reading_order for block in blocks} == {"b1": 1, "b2": 0}
