from __future__ import annotations

import pytest

from cbz_manga_translator.core.models import OcrBlock
from cbz_manga_translator.translate.argos import ArgosTranslator
from cbz_manga_translator.translate.memory import clear_translation_memory_cache
from cbz_manga_translator.translate.quality import TranslationQualityChecker
from cbz_manga_translator.translate.source_quality_gate import SourceQualityGate


@pytest.fixture(autouse=True)
def disable_external_translation_memory(monkeypatch):
    monkeypatch.setenv("MANGATRAD_DISABLE_TRANSLATION_MEMORY", "1")
    clear_translation_memory_cache()
    yield
    clear_translation_memory_cache()


@pytest.mark.parametrize(
    ("raw", "expected_source"),
    [
        ("WAIT? THERE' $ SOME KIND OF FRUITY SMELL!", "wait! there is some kind of fruity smell...!"),
        ("LADY Eliza- Beth,. .?", "Lady Elizabeth...?"),
        ("there'@ NO WAY Theo COULD Ve pulled It OFF!", "there is no way theo could have pulled it off!"),
        ("Nopel Bi6 Nopel", "Nope! Big Nope!"),
        ("WHO 6IVES A RAMN ABOUT THOSE SMALL DETAILS", "who gives a damn about those small details"),
        ("BMUSTHVB GALLENL ASLEEP inifront Computers", "I must've fallen asleep in front of my computer."),
    ],
)
def test_hard_ocr_source_regression_set(raw: str, expected_source: str) -> None:
    prepared = ArgosTranslator._prepare_source_text(
        raw,
        "en",
        raw_terms=None,
        normalize_english=True,
        use_builtin_glossary=False,
    )

    assert prepared.normalized_source_text == expected_source


@pytest.mark.parametrize(
    "raw",
    [
        "because of all the",
        "ISN'T THAT WHAT A MAN'S ROMANCE IS",
        "Krehble 4h, Seriously? You MEAN THAT? Krembue",
    ],
)
def test_hard_regression_set_blocks_or_flags_bad_sources_before_translation(raw: str) -> None:
    block = OcrBlock(id="b", bbox=[0, 0, 1, 1], source_lang="en", ocr_text=raw)
    prepared = ArgosTranslator._prepare_block_text(
        block,
        "en",
        raw_terms=None,
        normalize_english=True,
        use_builtin_glossary=False,
    )

    gate = SourceQualityGate().evaluate(
        block,
        "en",
        raw_source_text=raw,
        normalized_source_text=prepared.normalized_source_text,
    )

    assert gate.warnings
    assert gate.should_translate is False


def test_hard_regression_set_postflight_marks_copied_translation_for_review() -> None:
    block = OcrBlock(
        id="b",
        bbox=[0, 0, 1, 1],
        source_lang="en",
        ocr_text="The Tiger TCO was sighted four days ago.",
        normalized_source_text="The Tiger TCO was sighted four days ago.",
        translation_fr="The Tiger TCO was sighted four days ago.",
        confidence=0.92,
    )

    TranslationQualityChecker().apply([block], source_lang="en")

    assert block.manual_status == "review"
    assert any("traduction identique" in warning for warning in block.quality_warnings)
