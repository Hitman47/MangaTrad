from __future__ import annotations

from cbz_manga_translator.ocr.candidates import candidate_quality
from cbz_manga_translator.ocr.fallback_engine import OcrFallbackEngine
from cbz_manga_translator.ocr.text_cleanup import (
    has_random_ocr_casing,
    normalize_ocr_text_for_translation,
)


def test_normalize_random_easyocr_casing() -> None:
    assert has_random_ocr_casing("I NeVeR Expected I'D HAVE:")
    assert normalize_ocr_text_for_translation("I NeVeR Expected I'D HAVE:") == "I never expected I'd have:"


def test_normalize_short_semicolon_dialogue() -> None:
    assert normalize_ocr_text_for_translation("Director; With All Due ReSpect. .") == "Director, with all due respect."


def test_common_ocr_corrections_run_after_cleanup() -> None:
    assert OcrFallbackEngine.apply_common_ocr_corrections("Director; With All Due ReSpect. .") == "Director, with all due respect."
    assert OcrFallbackEngine.apply_common_ocr_corrections("I'Il just ignore him") == "I'll just ignore him"


def test_candidate_quality_penalizes_random_case_noise() -> None:
    noisy = candidate_quality("I NeVeR Expected I'D HAVE:", 0.72)
    clean = candidate_quality("I never expected I'd have:", 0.72)
    assert clean > noisy


def test_normalize_linebreak_hyphen_and_common_ocr_typos() -> None:
    assert normalize_ocr_text_for_translation("CERTAIN CIRCUM- STANCES") == "CERTAIN CIRCUMSTANCES"
    assert normalize_ocr_text_for_translation("YeS. He TRANS- FORMED INTO ANIMAL Fopm") == "Yes. he transformed into animal form"
    assert normalize_ocr_text_for_translation("The Tiger TCO WAS sighted FOLR DAYS Ago.") == "The Tiger TCO was sighted four days ago."
