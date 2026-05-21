from __future__ import annotations

from cbz_manga_translator.translate.argos import ArgosTranslator


def test_prepare_source_text_normalizes_colloquial_english() -> None:
    prepared = ArgosTranslator._prepare_source_text(
        "WHAT YA DOIN' UP THERE?",
        "en",
        raw_terms=None,
        normalize_english=True,
        use_builtin_glossary=False,
    )

    assert prepared.text == "what are you doing up there?"


def test_prepare_source_text_normalizes_ain_t_toid_and_dropped_g() -> None:
    prepared = ArgosTranslator._prepare_source_text(
        "AIN'T AH TOID YA, NO CLIMBIN' NOWHERE DANGEROUS?",
        "en",
        raw_terms=None,
        normalize_english=True,
        use_builtin_glossary=False,
    )

    assert prepared.text == "haven't I told you not to climb anywhere dangerous?"


def test_prepare_source_text_normalizes_gramma_looky_that() -> None:
    prepared = ArgosTranslator._prepare_source_text(
        "GRAMMA, LOOKY THAT.",
        "en",
        raw_terms=None,
        normalize_english=True,
        use_builtin_glossary=False,
    )

    assert prepared.text == "grandma, look at that."


def test_prepare_source_text_protects_names_and_glossary_terms() -> None:
    prepared = ArgosTranslator._prepare_source_text(
        "HERE NOW! NARU! WHAT? THE CONTRAIL?",
        "en",
        raw_terms="Naru, contrail=traînée de condensation",
        normalize_english=True,
        use_builtin_glossary=False,
    )

    assert "NARU" not in prepared.text.upper()
    assert "CONTRAIL" not in prepared.text.upper()
    restored = prepared.restore("C'est ici, maintenant ! MKTERM000TOKEN ! Quoi ? Le MKTERM001TOKEN ?")
    assert restored == "C'est ici, maintenant! Naru! Quoi? Le traînée de condensation?"


def test_builtin_glossary_protects_common_manga_terms() -> None:
    prepared = ArgosTranslator._prepare_source_text(
        "Naru eats ramen in Tokyo.",
        "en",
        raw_terms=None,
        normalize_english=True,
        use_builtin_glossary=True,
    )

    assert "NARU" not in prepared.text.upper()
    assert "RAMEN" not in prepared.text.upper()
    assert "TOKYO" not in prepared.text.upper()
    restored = prepared.restore(prepared.text)
    assert "Naru" in restored
    assert "ramen" in restored
    assert "Tokyo" in restored


def test_translate_blocks_bypasses_argos_package_for_local_overrides(monkeypatch) -> None:
    from cbz_manga_translator.core.models import OcrBlock

    translator = ArgosTranslator()

    def fail_chain(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("Argos package should not be loaded for deterministic local overrides")

    monkeypatch.setattr(translator, "_translation_chain", fail_chain)
    blocks = [
        OcrBlock(id="b1", bbox=[0, 0, 10, 10], source_lang="en", ocr_text="Aww:"),
        OcrBlock(id="b2", bbox=[0, 0, 10, 10], source_lang="en", ocr_text="please Inhook this"),
    ]

    translator.translate_blocks(blocks, "en")

    assert blocks[0].translation_fr == "Aww..."
    assert blocks[1].ocr_corrected_text == "please unhook this"
    assert blocks[1].translation_fr == "Décroche ça, s’il te plaît."
