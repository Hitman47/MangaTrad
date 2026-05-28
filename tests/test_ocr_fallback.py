from __future__ import annotations

from cbz_manga_translator.core.models import OcrBlock
from cbz_manga_translator.ocr.candidates import OcrCandidate, candidate_quality
from cbz_manga_translator.ocr.fallback_engine import OcrFallbackEngine


def test_common_ocr_corrections_fix_unhook_and_toid() -> None:
    assert OcrFallbackEngine.apply_common_ocr_corrections("please Inhook this") == "please unhook this"
    assert OcrFallbackEngine.apply_common_ocr_corrections("AIN'T AH TOID YA") == "AIN'T AH told YA"


def test_candidate_quality_penalizes_known_bad_ocr_token() -> None:
    bad = candidate_quality("please Inhook this", 0.82)
    good = candidate_quality("please unhook this", 0.82)
    assert good > bad


def test_candidate_quality_prefers_complete_punctuated_bubble() -> None:
    incomplete = candidate_quality("ISN'T THAT WHAT A MAN'S ROMANCE IS", 0.92)
    complete = candidate_quality("ISN'T THAT WHAT A MAN'S ROMANCE IS ABOUT!!!", 0.86)

    assert complete > incomplete


def test_candidate_quality_penalizes_raw_digit_letter_confusions() -> None:
    bad = candidate_quality("Bi6 news!", 0.88)
    good = candidate_quality("Big news!", 0.88)

    assert good > bad


def test_block_serializes_ocr_alternatives() -> None:
    block = OcrBlock(
        id="p0001_b0002",
        bbox=[1, 2, 3, 4],
        source_lang="en",
        ocr_text="please Inhook this",
        ocr_alternatives=[OcrCandidate("ocr-corrections", "please unhook this", 0.8, 4.2, "test").to_dict()],
    )
    restored = OcrBlock.from_dict(block.to_dict())
    assert restored.ocr_alternatives[0]["engine"] == "ocr-corrections"
    assert restored.ocr_alternatives[0]["text"] == "please unhook this"


def test_improve_blocks_uses_local_correction_without_optional_backends(tmp_path) -> None:
    image_path = tmp_path / "page.png"
    image_path.write_bytes(b"not a real image, local correction path should still be enough")
    block = OcrBlock(
        id="p0000_b0000",
        bbox=[0, 0, 100, 50],
        source_lang="en",
        ocr_text="please Inhook this",
        confidence=0.80,
        quality_warnings=["test warning"],
    )

    class DummyEasyOcr:
        def _reader(self, source_lang: str, use_gpu: bool):  # pragma: no cover - should not be reached successfully
            raise RuntimeError("no EasyOCR in unit test")

        def _crop_variants(self, image_path, bbox, temp_dir):  # pragma: no cover
            raise RuntimeError("no crop in unit test")

    engine = OcrFallbackEngine(easyocr_engine=DummyEasyOcr())  # type: ignore[arg-type]
    blocks, changed = engine.improve_blocks(
        image_path,
        [block],
        "en",
        use_gpu=False,
        only_suspect=True,
        include_optional_engines=False,
    )
    assert changed == 1
    assert blocks[0].ocr_text == "please unhook this"
    assert blocks[0].ocr_alternatives


def test_fallback_treats_probably_incomplete_bubble_as_suspect() -> None:
    block = OcrBlock(
        id="p0000_b0001",
        bbox=[0, 0, 100, 50],
        source_lang="en",
        ocr_text="NOW I GOTTA Get Out Before Sensei CATCHES",
        confidence=0.95,
    )

    assert OcrFallbackEngine._is_suspect(block, 0.20)


def test_fallback_treats_auxiliary_end_without_punctuation_as_suspect() -> None:
    block = OcrBlock(
        id="p0000_b0001",
        bbox=[0, 0, 100, 50],
        source_lang="en",
        ocr_text="ISN'T THAT WHAT A MAN'S ROMANCE IS",
        confidence=0.95,
    )

    assert OcrFallbackEngine._is_suspect(block, 0.20)


def test_auto_replacement_allows_suffix_completion_but_rejects_inserted_noise() -> None:
    block = OcrBlock(
        id="zone",
        bbox=[0, 0, 100, 50],
        source_lang="en",
        ocr_text="ISN'T THAT WHAT A MAN'S ROMANCE IS",
        confidence=0.90,
    )
    good = OcrCandidate("easyocr-crop", "ISN'T THAT WHAT A MAN'S ROMANCE IS ABOUT!!!", 0.8, 11.5, "wide32")
    noisy = OcrCandidate("easyocr-crop", "P Ai THAT WHAT A MAN'S ROMANCE IS ABOUT!!! 4", 0.8, 13.0, "wide50")

    assert OcrFallbackEngine._is_auto_replacement_safe(block, good)
    assert not OcrFallbackEngine._is_auto_replacement_safe(block, noisy)


def test_fallback_rerank_demotes_overwide_zone_candidates() -> None:
    block = OcrBlock(
        id="zone",
        bbox=[0, 0, 100, 50],
        source_lang="en",
        ocr_text="I've WAITED",
        confidence=0.90,
    )
    candidates = [
        OcrCandidate("easyocr-crop", "Whi CAR! KVE ABO( WAITED Thos SMA For TOO DETA! nu^III", 0.8, 11.5, "wide50"),
        OcrCandidate("easyocr-crop", "I've WAITED SN For Too", 0.7, 6.3, "wide32"),
    ]

    ranked = OcrFallbackEngine._rerank_candidates_for_block(block, candidates)

    assert ranked[0].text == "I've WAITED SN For Too"
    assert "crop trop large" in ranked[-1].note


def test_collect_candidates_adds_visual_punctuation_candidate(tmp_path) -> None:
    from PIL import Image, ImageDraw

    image_path = tmp_path / "page.png"
    image = Image.new("L", (80, 40), "white")
    draw = ImageDraw.Draw(image)
    for x in (46, 54, 62):
        draw.ellipse((x, 28, x + 3, 31), fill="black")
    image.save(image_path)
    block = OcrBlock(
        id="p0000_b0001",
        bbox=[0, 0, 80, 40],
        source_lang="en",
        ocr_text="SO Why",
        confidence=0.90,
    )

    class DummyEasyOcr:
        def _reader(self, source_lang: str, use_gpu: bool):  # pragma: no cover - should not be reached successfully
            raise RuntimeError("no EasyOCR in unit test")

    engine = OcrFallbackEngine(easyocr_engine=DummyEasyOcr())  # type: ignore[arg-type]

    candidates = engine.collect_candidates(
        image_path,
        block,
        "en",
        use_gpu=False,
        min_confidence=0.20,
        include_optional_engines=False,
    )

    assert any(candidate.engine == "punctuation-detector" and candidate.text == "SO Why..." for candidate in candidates)
