from __future__ import annotations

from cbz_manga_translator.ocr.text_cleanup import normalize_ocr_text_for_translation
from cbz_manga_translator.translate.english_dialogue_normalizer import EnglishDialogueNormalizer


def test_reviewed_dialogue_ellipsis_repairs_are_conservative() -> None:
    assert normalize_ocr_text_for_translation("Oh NO, NOT At ALL.") == "Oh NO, NOT At ALL..."
    assert normalize_ocr_text_for_translation("So THAT Big-time job You Guys Were talking About.") == "So THAT Big-time job You Guys Were talking About..."
    assert normalize_ocr_text_for_translation("If They're Family.") == "If They're Family..."
    assert normalize_ocr_text_for_translation("I just Thought You were A BANDIT.") == "I just Thought You were A BANDIT..."
    assert normalize_ocr_text_for_translation("And if | could save a citizen of Dalmasca at the same time") == "And if I could save a citizen of Dalmasca at the same time..."


def test_incomplete_tail_gets_ellipsis_without_touching_complete_sentence() -> None:
    assert normalize_ocr_text_for_translation("We should talk about") == "We should talk about..."
    assert normalize_ocr_text_for_translation("We should talk about it.") == "We should talk about it."


def test_dialogue_normalizer_uses_ellipsis_repairs() -> None:
    assert EnglishDialogueNormalizer.prepare("have Left Me At DEATH'S DOOR").corrected_text == "...have Left Me At DEATH'S DOOR"
