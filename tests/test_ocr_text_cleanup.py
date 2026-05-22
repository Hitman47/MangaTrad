from __future__ import annotations

from cbz_manga_translator.ocr.candidates import candidate_quality
from cbz_manga_translator.ocr.fallback_engine import OcrFallbackEngine
from cbz_manga_translator.ocr.text_cleanup import (
    has_random_ocr_casing,
    normalize_ocr_text_for_translation,
)


def test_normalize_random_easyocr_casing() -> None:
    assert has_random_ocr_casing("I NeVeR Expected I'D HAVE:")
    assert normalize_ocr_text_for_translation("I NeVeR Expected I'D HAVE:") == "I never expected I'd have."


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


def test_review_learned_ocr_cleanup_examples() -> None:
    assert normalize_ocr_text_for_translation("WHAATI? PEALLYI?") == "what? really?"
    assert normalize_ocr_text_for_translation("The KAWAZL Family") == "The KAWAZU Family"
    assert normalize_ocr_text_for_translation("Sepiously Dont do Something LNNECES- SARY") == "seriously don't do Something unnecessary"
    assert normalize_ocr_text_for_translation("BMUSTHVB GALLENL ASLEEP inifront Computers") == "I must've fallen asleep in front of my computer."


def test_second_review_batch_ocr_cleanup_examples() -> None:
    assert normalize_ocr_text_for_translation("NO WAYI") == "no way!"
    assert normalize_ocr_text_for_translation("Victopy is Minel!") == "Victory is Mine!"
    assert normalize_ocr_text_for_translation("arb What saying? You") == "What are you saying?"
    assert normalize_ocr_text_for_translation("YOU'LL UNDER- STAND ONCE YOU DO!") == "YOU'LL UNDERSTAND ONCE YOU DO!"


def test_third_review_batch_sfx_edges_and_ocr_cleanup_examples() -> None:
    assert normalize_ocr_text_for_translation("WHISPER WE ALWAYS TAKE YOU OUT ON OUR QUESTS, RIGHT? WHISPER") == "WE ALWAYS TAKE YOU OUT ON OUR QUESTS, RIGHT?"
    assert normalize_ocr_text_for_translation("Fop Singing") == "For Singing"
    assert normalize_ocr_text_for_translation("Fljimura-kln") == "Fujimura-kun"
    assert normalize_ocr_text_for_translation("WHAAAI?") == "WHAAAT?"
    assert normalize_ocr_text_for_translation("BREASTSI!") == "breasts!!"


def test_fourth_review_batch_punctuation_numbers_and_hyphenation_examples() -> None:
    assert normalize_ocr_text_for_translation("The Drugs ARE Still IN YOUR System:") == "The Drugs ARE Still IN YOUR System."
    assert normalize_ocr_text_for_translation("Don't do Anything Sudden:") == "Don't do Anything Sudden."
    assert normalize_ocr_text_for_translation("LISTEN, Yuki:") == "LISTEN, Yuki..."
    assert normalize_ocr_text_for_translation("SO Why,") == "SO Why..."
    assert normalize_ocr_text_for_translation("IF ONE ENER IS About one HLNDRED YEN:, .") == "IF ONE ENER IS About one hundred YEN..."
    assert normalize_ocr_text_for_translation("AND I50, 000 FOR THE INTEL ON THEIR BASE:") == "AND 150,000 FOR THE INTEL ON THEIR BASE."
    assert normalize_ocr_text_for_translation("MAYBE SOME UN- CONTROLLED MONSTERS") == "MAYBE SOME UNCONTROLLED MONSTERS"
    assert normalize_ocr_text_for_translation("In PAR- Ticu- LAR:") == "In particular."
    assert normalize_ocr_text_for_translation("qualification t0 be here, our Iives") == "qualification to be here, our lives"
    assert normalize_ocr_text_for_translation("Feels Like The Kind OF Thing 4 High SCHOOL BOY would") == "Feels Like The Kind OF Thing a High SCHOOL BOY would"


def test_fifth_review_batch_punctuation_digits_and_hyphenation_examples() -> None:
    assert normalize_ocr_text_for_translation("HE'S A Big-time Ceo_") == "HE'S A Big-time CEO"
    assert normalize_ocr_text_for_translation("A MEAL without MEAT ISN'T DINNERI") == "A MEAL without MEAT ISN'T DINNER!"
    assert normalize_ocr_text_for_translation("AND:. =") == "AND..."
    assert normalize_ocr_text_for_translation("~But I Agree With The Other PARTS.") == "...But I Agree With The Other PARTS."
    assert normalize_ocr_text_for_translation("I MUST SHOW MS: ELIZABETH, MS: KAREN, AND MS: UNDINE.") == "I MUST SHOW MS. ELIZABETH, MS. KAREN, AND MS. UNDINE."
    assert normalize_ocr_text_for_translation("WE'LL ACCEPT THIS QUEST,, ,") == "WE'LL ACCEPT THIS QUEST..."
    assert normalize_ocr_text_for_translation("The RECEPTION ANDPOID At Mei's MANU- FACTURER TOLD ME") == "The RECEPTION android At Mei's MANUFACTURER TOLD ME"
    assert normalize_ocr_text_for_translation("WHAT Ape yo4 TALKING Abolt? THIS IS No TIME To Be ACTING STUBBORNI") == "WHAT Are you TALKING About? THIS IS No TIME To Be ACTING STUBBORN!"


def test_sixth_review_batch_incomplete_bubbles_questions_and_contractions() -> None:
    assert normalize_ocr_text_for_translation("DO NOT YOURSELF") == "do not torture yourself"
    assert normalize_ocr_text_for_translation("DO Some- thing! I'm Counting ON") == "DO something! I'm Counting ON you...!!"
    assert normalize_ocr_text_for_translation("WHAT GOING") == "what are you going to do?!"
    assert normalize_ocr_text_for_translation("Could accomp any you?") == "Could I accompany you?"
    assert normalize_ocr_text_for_translation("there'@ NO WAY Theo COULD Ve pulled It OFF!") == "there's no way theo could've pulled it off!"
    assert normalize_ocr_text_for_translation("CAN I BOPROW THAT Volume AGAIN?") == "CAN I borrow THAT Volume AGAIN?"
    assert normalize_ocr_text_for_translation("WHAT The,") == "what the...?!"
    assert normalize_ocr_text_for_translation("4NDER- STOOD.") == "Understood."


def test_seventh_review_batch_ellipsis_and_zone_examples() -> None:
    assert normalize_ocr_text_for_translation(": why isn't Sigma-kun Waking Up.") == "...why isn't Sigma-kun waking up...?"
    assert normalize_ocr_text_for_translation("He's COMING. ISN'T He,.") == "he's coming... isn't he...?"
    assert normalize_ocr_text_for_translation("Hi everyone We're going To Be working Together now, OKAY-?") == "Hi everyone. We're going to be working together now, okay?"
    assert normalize_ocr_text_for_translation("SORRY I'm LATE-") == "sorry I'm late..."
    assert normalize_ocr_text_for_translation("WAIT A SEC, You guys") == "WAIT A SEC, You guys know..."
    assert normalize_ocr_text_for_translation("So THAT Big-twme job You Guys Were talking About.") == "So THAT Big-time job You Guys Were talking About..."
    assert normalize_ocr_text_for_translation("LNDER- STAND Why knives CHOSE This PLACE.") == "I UNDERSTAND Why Knives CHOSE This PLACE..."
    assert normalize_ocr_text_for_translation("Only found Five.") == "...but they only found five."
    assert normalize_ocr_text_for_translation("SHOLLD WE WITHORAW For Now?") == "should WE withdraw For Now?"
