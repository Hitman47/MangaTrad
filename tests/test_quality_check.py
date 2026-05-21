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
