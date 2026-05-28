from __future__ import annotations

from cbz_manga_translator.core.models import OcrBlock, ProjectData
from cbz_manga_translator.translate.quality import TranslationQualityChecker


def test_quality_checker_flags_gramma_mistranslation() -> None:
    block = OcrBlock(
        id="p0000_b0000",
        bbox=[1, 2, 3, 4],
        source_lang="en",
        ocr_text="GRAMMA, LOOKY THAT.",
        translation_fr="gamma; cela;",
        confidence=0.51,
    )

    warnings = TranslationQualityChecker().check_block(block)

    assert any("gramma" in warning.lower() for warning in warnings)
    assert any("confiance" in warning.lower() for warning in warnings)


def test_quality_checker_apply_persists_warnings() -> None:
    project = ProjectData.from_images("book.cbz", ["001.jpg"])
    project.pages[0].blocks.append(
        OcrBlock(
            id="p0000_b0000",
            bbox=[1, 2, 3, 4],
            source_lang="en",
            ocr_text="AIN'T AH TOID YA, NO CLIMBIN' NOWHERE DANGEROUS?",
            translation_fr="N'est-ce pas I TOLD YA Pas de DANGEROUS ?",
            confidence=0.52,
        )
    )

    count = TranslationQualityChecker().apply(project.pages[0].blocks)

    assert count == 1
    assert project.pages[0].blocks[0].quality_warnings


def test_quality_checker_marks_severe_translation_failures_for_review() -> None:
    block = OcrBlock(
        id="p0000_b0001",
        bbox=[1, 2, 3, 4],
        source_lang="en",
        ocr_text="I know I have to steal",
        translation_fr="I know I have to steal",
        confidence=0.91,
    )

    count = TranslationQualityChecker().apply([block], source_lang="en")

    assert count == 1
    assert block.manual_status == "review"
    assert block.review_notes.startswith("[postflight]")


def test_quality_checker_does_not_flag_good_high_confidence_slang_translation() -> None:
    block = OcrBlock(
        id="p0000_b0001",
        bbox=[1, 2, 3, 4],
        source_lang="en",
        ocr_text="WHAT YA DOIN' UP THERE?",
        translation_fr="Qu'est-ce que tu fais là-haut ?",
        confidence=0.82,
    )

    warnings = TranslationQualityChecker().check_block(block)

    assert warnings == []


def test_quality_checker_does_not_reflag_validated_blocks() -> None:
    block = OcrBlock(
        id="p0000_b0002",
        bbox=[1, 2, 3, 4],
        source_lang="en",
        ocr_text="GRAMMA, LOOKY THAT.",
        translation_fr="gamma; cela;",
        confidence=0.2,
        manual_status="validated",
        quality_warnings=["previous"],
    )

    count = TranslationQualityChecker().apply([block])

    assert count == 0
    assert block.quality_warnings == []


def test_quality_check_flags_isolated_ocr_fragments() -> None:
    from cbz_manga_translator.core.models import OcrBlock
    from cbz_manga_translator.translate.quality import TranslationQualityChecker

    block = OcrBlock(
        id="b",
        bbox=[0, 0, 10, 10],
        source_lang="en",
        ocr_text="Did:",
        translation_fr="A fait :",
        confidence=0.83,
    )
    warnings = TranslationQualityChecker().check_block(block)
    assert any("fragment OCR" in warning for warning in warnings)


def test_quality_check_flags_known_ocr_typos_and_translation_residue() -> None:
    block = OcrBlock(
        id="b",
        bbox=[0, 0, 10, 10],
        source_lang="en",
        ocr_text="The Tiger TCO WAS sighted FOLR DAYS Ago.",
        translation_fr="Le Tigre TCO a été vu FOLR DAYS Ago.",
        confidence=0.72,
    )

    warnings = TranslationQualityChecker().check_block(block)

    assert any("FOLR" in warning or "OCR probable" in warning for warning in warnings)
    assert any("anglais" in warning.lower() or "résidu" in warning.lower() for warning in warnings)


def test_quality_flags_source_residue_copied_to_translation() -> None:
    checker = TranslationQualityChecker()
    block = OcrBlock(
        id="b",
        bbox=[0, 0, 1, 1],
        source_lang="en",
        ocr_text="I know I have to steal",
        translation_fr="Je dois steal",
        confidence=0.9,
    )
    warnings = checker.check_block(block)
    assert any("source recopi" in warning or "anglais" in warning for warning in warnings)


def test_quality_allows_preserved_proper_nouns() -> None:
    block = OcrBlock(
        id="b",
        bbox=[0, 0, 1, 1],
        source_lang="en",
        ocr_text="He Took AME-NO- Gozen FROM Me!",
        ocr_corrected_text="He Took Ame-no-Gozen FROM Me!",
        normalized_source_text="He Took Ame-no-Gozen FROM Me!",
        translation_fr="Il m'a pris Ame-no-Gozen !",
        confidence=0.86,
    )

    warnings = TranslationQualityChecker().check_block(block)

    assert not any("source recopi" in warning for warning in warnings)


def test_quality_allows_recent_busy_batch_proper_names() -> None:
    block = OcrBlock(
        id="b",
        bbox=[0, 0, 1, 1],
        source_lang="en",
        ocr_text="KARIU YOUR FACE Is SCARY",
        ocr_corrected_text="kariu your face is scary",
        normalized_source_text="kariu your face is scary",
        translation_fr="Kariu, ton visage fait peur.",
        confidence=0.86,
    )

    warnings = TranslationQualityChecker().check_block(block)

    assert not any("source recopi" in warning for warning in warnings)


def test_quality_allows_preserved_transit_and_french_caps() -> None:
    transit = OcrBlock(
        id="transit",
        bbox=[0, 0, 1, 1],
        source_lang="en",
        ocr_text='MEANS I\'m Like YOUR "public TRANSIT" For the DAY.',
        translation_fr='En gros, je suis ton "transport public" pour la journee.',
        confidence=0.86,
    )
    no = OcrBlock(
        id="no",
        bbox=[0, 0, 1, 1],
        source_lang="en",
        ocr_text="NO",
        translation_fr="NON",
        confidence=0.86,
    )

    checker = TranslationQualityChecker()
    assert not any("source recopi" in warning for warning in checker.check_block(transit))
    assert not any("MAJUSCULES" in warning for warning in checker.check_block(no))


def test_quality_allows_music_genre_terms() -> None:
    block = OcrBlock(
        id="music",
        bbox=[0, 0, 1, 1],
        source_lang="en",
        ocr_text="I Guess They're a Melodic HARDCORE OR MAYBE Loud ROCK BAND, huh?",
        translation_fr="Je dirais que c'est du hardcore melodique, ou peut-etre un groupe de rock bruyant, hein ?",
        confidence=0.9,
    )

    warnings = TranslationQualityChecker().check_block(block)

    assert not any("source recopi" in warning for warning in warnings)


def test_quality_allows_preserved_elizabeth_name() -> None:
    block = OcrBlock(
        id="name",
        bbox=[0, 0, 1, 1],
        source_lang="en",
        ocr_text="It's trying To eliminate Elizabeth.",
        translation_fr="Il essaie d'eliminer Elizabeth.",
        confidence=0.9,
    )

    warnings = TranslationQualityChecker().check_block(block)

    assert not any("source recopi" in warning for warning in warnings)


def test_quality_allows_french_service_word() -> None:
    block = OcrBlock(
        id="service",
        bbox=[0, 0, 1, 1],
        source_lang="en",
        ocr_text="The funeral service!!",
        translation_fr="Le service funebre !",
        confidence=0.9,
    )

    warnings = TranslationQualityChecker().check_block(block)

    assert not any("source recopi" in warning for warning in warnings)


def test_quality_allows_french_game_boss_word() -> None:
    block = OcrBlock(
        id="boss",
        bbox=[0, 0, 1, 1],
        source_lang="en",
        ocr_text="The strongest boss in the game...",
        translation_fr="le boss le plus fort du jeu...",
        confidence=0.9,
    )

    warnings = TranslationQualityChecker().check_block(block)

    assert not any("anglais restants" in warning for warning in warnings)
    assert not any("source recopi" in warning for warning in warnings)


def test_quality_flags_missing_prefix_and_missing_terminal_punctuation() -> None:
    block = OcrBlock(
        id="b",
        bbox=[0, 0, 1, 1],
        source_lang="en",
        ocr_text="have Left Me At DEATH'S DOOR",
        translation_fr="Me laisser à la porte de la mort",
        confidence=0.9,
    )

    warnings = TranslationQualityChecker().check_block(block)

    assert any("début de phrase" in warning for warning in warnings)
    assert any("ponctuation finale" in warning for warning in warnings)


def test_quality_flags_intentional_cutoff_to_preserve() -> None:
    block = OcrBlock(
        id="b",
        bbox=[0, 0, 1, 1],
        source_lang="en",
        ocr_text="ASPHYXI- WHAT?",
        translation_fr="Asphyx... quoi?",
        confidence=0.9,
    )

    warnings = TranslationQualityChecker().check_block(block)

    assert any("volontairement coupé" in warning for warning in warnings)


def test_quality_flags_obvious_reviewed_ocr_confusion() -> None:
    block = OcrBlock(
        id="b",
        bbox=[0, 0, 1, 1],
        source_lang="en",
        ocr_text="BMUSTHVB GALLENL ASLEEP inifront Computers",
        translation_fr="BMUSTHVB GALLENL ASLEP inifront Computers",
        confidence=0.62,
    )

    warnings = TranslationQualityChecker().check_block(block)

    assert any("I must've fallen asleep" in warning for warning in warnings)


def test_quality_flags_possible_fused_bubbles_from_review_notes() -> None:
    block = OcrBlock(
        id="b",
        bbox=[0, 0, 1, 1],
        source_lang="en",
        ocr_text="They say you should live life counting the good things instead of the bad, don't they!? Like manga or songs.",
        translation_fr="Ils disent que vous devriez vivre la vie. Comme manga ou chansons.",
        confidence=0.9,
    )

    warnings = TranslationQualityChecker().check_block(block)

    assert any("deux bulles" in warning or "fusion" in warning for warning in warnings)


def test_quality_flags_incomplete_manga_fragments_and_ambiguous_expressions() -> None:
    checker = TranslationQualityChecker()
    fragment = OcrBlock(
        id="b",
        bbox=[0, 0, 1, 1],
        source_lang="en",
        ocr_text="DO something! I'm Counting ON",
        normalized_source_text="do something! I am counting on",
        translation_fr="Fais quelque chose je compte sur",
        confidence=0.9,
    )
    warnings = checker.check_block(fragment)
    assert any("fin de bulle" in warning for warning in warnings)

    ellipsis = OcrBlock(
        id="b2",
        bbox=[0, 0, 1, 1],
        source_lang="en",
        ocr_text=". AFTER",
        normalized_source_text="...after me?!",
        translation_fr="...Après moi ?!",
        confidence=0.9,
    )
    warnings = checker.check_block(ellipsis)
    assert any("ellipse" in warning for warning in warnings)

    right = OcrBlock(
        id="b3",
        bbox=[0, 0, 1, 1],
        source_lang="en",
        ocr_text="Right",
        normalized_source_text="Right?",
        translation_fr="N'est-ce pas ?",
        confidence=0.9,
    )
    warnings = checker.check_block(right)
    assert any("ambiguïté" in warning for warning in warnings)


def test_quality_prioritizes_ellipsis_zone_and_sfx_fusion_problems() -> None:
    checker = TranslationQualityChecker()

    short_zone = OcrBlock(
        id="short",
        bbox=[0, 0, 1, 1],
        source_lang="en",
        ocr_text="WAIT A SEC, You guys",
        normalized_source_text="wait a sec, you guys",
        translation_fr="Attendez un peu, vous les gars",
        confidence=0.9,
    )
    warnings = checker.check_block(short_zone)
    assert any("zone de texte" in warning for warning in warnings)
    assert any("crop" in warning and "fallback" in warning for warning in warnings)

    ellipsis = OcrBlock(
        id="ellipsis",
        bbox=[0, 0, 1, 1],
        source_lang="en",
        ocr_text="He's COMING. ISN'T He,.",
        normalized_source_text="he's coming... isn't he..",
        translation_fr="Il arrive...",
        confidence=0.9,
    )
    warnings = checker.check_block(ellipsis)
    assert any("points de suspension" in warning for warning in warnings)

    fused = OcrBlock(
        id="fused",
        bbox=[0, 0, 1, 1],
        source_lang="en",
        ocr_text="Krehble 4h, Seriously? You MEAN THAT? Krembue",
        translation_fr="Krehble tu veux dire ça Krembue",
        confidence=0.9,
    )
    warnings = checker.check_block(fused)
    assert any("SFX" in warning and "fusion" in warning for warning in warnings)
    assert any("fusion probable" in warning for warning in warnings)


def test_quality_flags_reviewed_incomplete_bubble_for_wide_crop() -> None:
    block = OcrBlock(
        id="incomplete",
        bbox=[0, 0, 1, 1],
        source_lang="en",
        ocr_text="NOW I GOTTA Get Out Before Sensei CATCHES",
        translation_fr="Maintenant je dois sortir avant que Sensei attrape",
        confidence=0.95,
    )

    warnings = TranslationQualityChecker().check_block(block)

    assert any("zone/bulle probablement incomplete" in warning for warning in warnings)


def test_quality_does_not_flag_complete_but_sentence_as_missing_prefix() -> None:
    block = OcrBlock(
        id="complete",
        bbox=[0, 0, 1, 1],
        source_lang="en",
        ocr_text="But it's FAR Too LATE FOR THAT!",
        normalized_source_text="But it is FAR Too LATE FOR THAT!",
        translation_fr="Mais c'est trop tard pour ça!",
        confidence=0.95,
    )

    warnings = TranslationQualityChecker().check_block(block)

    assert not any("phrase possiblement manquant" in warning for warning in warnings)


def test_quality_flags_manga_font_confusion_profile() -> None:
    checker = TranslationQualityChecker()
    block = OcrBlock(
        id="font",
        bbox=[0, 0, 10, 10],
        source_lang="en",
        ocr_text="ISN'T Lrabe COMING TODAY?",
        translation_fr="Urabe ne vient pas aujourd'hui ?",
        confidence=0.9,
    )

    warnings = checker.check_block(block)

    assert any("fonte manga" in warning for warning in warnings)


def test_quality_prioritizes_colon_and_missing_question_punctuation() -> None:
    checker = TranslationQualityChecker()
    colon = OcrBlock(
        id="colon",
        bbox=[0, 0, 1, 1],
        source_lang="en",
        ocr_text="OR MAYBE THE CREATIVE TEAM:",
        translation_fr="Ou peut-être l'équipe créative.",
        confidence=0.92,
    )
    question = OcrBlock(
        id="question",
        bbox=[0, 0, 1, 1],
        source_lang="en",
        ocr_text="What are you doing",
        translation_fr="Que fais-tu",
        confidence=0.92,
    )

    colon_warnings = checker.check_block(colon)
    question_warnings = checker.check_block(question)

    assert any("':' suspecte" in warning for warning in colon_warnings)
    assert any("interrogation" in warning for warning in question_warnings)


def test_quality_flags_non_japanese_source_when_running_ja_mode() -> None:
    block = OcrBlock(
        id="ja_mismatch",
        bbox=[0, 0, 1, 1],
        source_lang="ja",
        ocr_text="Et puis avec plus de 200 heures de vol.",
        translation_fr="",
        confidence=0.9,
    )

    warnings = TranslationQualityChecker().check_block(block)

    assert any("non japonaise" in warning for warning in warnings)
    assert any("fragment japonais" in warning for warning in warnings)
    assert any("traduction vide" in warning for warning in warnings)
