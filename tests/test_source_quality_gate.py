from __future__ import annotations

from cbz_manga_translator.core.models import OcrBlock
from cbz_manga_translator.translate.argos import ArgosTranslator
from cbz_manga_translator.translate.quality import TranslationQualityChecker
from cbz_manga_translator.translate.source_quality_gate import SourceQualityGate


def test_source_quality_gate_holds_probably_incomplete_unchecked_source() -> None:
    block = OcrBlock(id="b", bbox=[0, 0, 1, 1], source_lang="en", ocr_text="because of all the")

    result = SourceQualityGate().evaluate(
        block,
        "en",
        raw_source_text=block.ocr_text,
        normalized_source_text="because of all the",
    )

    assert result.should_translate is False
    assert "split_bubble" in result.categories
    assert any("traduction suspendue" in warning for warning in result.warnings)


def test_source_quality_gate_warns_without_holding_human_edited_source() -> None:
    block = OcrBlock(
        id="b",
        bbox=[0, 0, 1, 1],
        source_lang="en",
        ocr_text="have Left Me At DEATH'S DOOR",
        manual_status="edited",
    )

    result = SourceQualityGate().evaluate(
        block,
        "en",
        raw_source_text=block.ocr_text,
        normalized_source_text="have left me at death's door",
    )

    assert result.should_translate is True
    assert any("zone" in warning for warning in result.warnings)


def test_argos_preflight_gate_blocks_bad_source_before_model(monkeypatch) -> None:
    translator = ArgosTranslator()

    def fail_chain(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("Bad source must not be sent to Argos")

    monkeypatch.setattr(translator, "_translation_chain", fail_chain)
    block = OcrBlock(id="b", bbox=[0, 0, 1, 1], source_lang="en", ocr_text="because of all the")

    translator.translate_blocks([block], "en")

    assert block.translation_fr == ""
    assert block.manual_status == "review"
    assert block.review_notes.startswith("[preflight]")
    assert any("traduction suspendue" in warning for warning in block.quality_warnings)


def test_quality_checker_preserves_preflight_warnings() -> None:
    block = OcrBlock(
        id="b",
        bbox=[0, 0, 1, 1],
        source_lang="en",
        ocr_text="have Left Me At DEATH'S DOOR",
        translation_fr="",
        quality_warnings=["preflight: traduction suspendue, source anglaise trop incertaine"],
    )

    TranslationQualityChecker().apply([block], source_lang="en")

    assert any("preflight: traduction suspendue" in warning for warning in block.quality_warnings)
    assert any("traduction vide" in warning for warning in block.quality_warnings)
