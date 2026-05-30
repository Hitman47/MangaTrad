from __future__ import annotations

from PIL import Image

from cbz_manga_translator.ocr.easyocr_engine import EasyOcrEngine


def poly(x1: int, y1: int, x2: int, y2: int) -> list[list[int]]:
    return [[x1, y1], [x2, y1], [x2, y2], [x1, y2]]


def test_postprocess_filters_noise_and_merges_dialogue_lines() -> None:
    engine = EasyOcrEngine()
    raw_results = [
        (poly(100, 100, 240, 125), "WHY AM I", 0.88),
        (poly(102, 132, 235, 158), "THE ONLY", 0.86),
        (poly(105, 165, 250, 190), "ONE WHO", 0.83),
        (poly(106, 198, 225, 222), "GETS IN", 0.82),
        (poly(104, 230, 245, 255), "TROUBLE?", 0.81),
        (poly(600, 100, 615, 116), "8", 0.99),
        (poly(620, 100, 640, 116), "<", 0.90),
        (poly(300, 300, 420, 350), "RUSTLE", 0.20),
    ]

    blocks = engine._postprocess_results(
        raw_results,
        source_lang="en",
        page_index=0,
        min_confidence=0.35,
        merge_lines=True,
        filter_noise=True,
    )

    assert len(blocks) == 1
    assert blocks[0].ocr_text == "WHY AM I THE ONLY ONE WHO GETS IN TROUBLE?"
    assert blocks[0].bbox == [100, 100, 250, 255]
    assert blocks[0].reading_order == 0


def test_postprocess_can_keep_unmerged_blocks_when_requested() -> None:
    engine = EasyOcrEngine()
    raw_results = [
        (poly(100, 100, 200, 125), "HELLO", 0.9),
        (poly(100, 132, 200, 158), "THERE", 0.9),
    ]

    blocks = engine._postprocess_results(
        raw_results,
        source_lang="en",
        page_index=3,
        min_confidence=0.35,
        merge_lines=False,
        filter_noise=True,
    )

    assert [block.ocr_text for block in blocks] == ["HELLO", "THERE"]
    assert [block.reading_order for block in blocks] == [0, 1]
    assert blocks[0].id == "p0003_b0000"


def test_postprocess_keeps_sfx_labels_out_of_dialogue_merge() -> None:
    engine = EasyOcrEngine()
    raw_results = [
        (poly(100, 100, 230, 125), "WE ALWAYS", 0.88),
        (poly(102, 132, 250, 158), "TAKE YOU", 0.86),
        (poly(104, 165, 245, 190), "OUT ON OUR", 0.84),
        (poly(106, 198, 240, 222), "QUESTS,", 0.83),
        (poly(108, 230, 245, 255), "RIGHT?", 0.82),
        (poly(112, 65, 170, 85), "WHISPER", 0.91),
        (poly(255, 265, 315, 286), "WHISPER", 0.91),
    ]

    blocks = engine._postprocess_results(
        raw_results,
        source_lang="en",
        page_index=0,
        min_confidence=0.35,
        merge_lines=True,
        filter_noise=True,
    )

    assert "WE ALWAYS TAKE YOU OUT ON OUR QUESTS, RIGHT?" in [block.ocr_text for block in blocks]
    assert all("WHISPER" not in block.ocr_text for block in blocks if "WE ALWAYS" in block.ocr_text)


def test_postprocess_keeps_reviewed_sfx_labels_out_of_dialogue_merge() -> None:
    engine = EasyOcrEngine()
    raw_results = [
        (poly(100, 100, 230, 125), "ARE YOU MIS-", 0.88),
        (poly(102, 132, 250, 158), "UNDERSTANDING", 0.86),
        (poly(104, 165, 245, 190), "SOMETHING YOU", 0.84),
        (poly(106, 198, 240, 222), "IDIOT?!", 0.83),
        (poly(112, 65, 170, 85), "SLAP", 0.91),
        (poly(255, 265, 315, 286), "TREMBLE", 0.91),
    ]

    blocks = engine._postprocess_results(
        raw_results,
        source_lang="en",
        page_index=0,
        min_confidence=0.35,
        merge_lines=True,
        filter_noise=True,
    )

    dialogue = [block.ocr_text for block in blocks if "IDIOT" in block.ocr_text]
    assert dialogue == ["ARE YOU MIS- UNDERSTANDING SOMETHING YOU IDIOT?!"]
    assert all("SLAP" not in text and "TREMBLE" not in text for text in dialogue)


def test_postprocess_prefers_best_aligned_group_when_bubbles_are_close() -> None:
    engine = EasyOcrEngine()
    raw_results = [
        (poly(696, 564, 744, 590), "WHO", 0.78),
        (poly(577, 593, 655, 633), "I've", 0.77),
        (poly(690, 590, 752, 618), "CARES", 0.99),
        (poly(690, 614, 752, 642), "ABOUT", 0.79),
        (poly(558, 630, 674, 670), "WAITED", 0.98),
        (poly(690, 640, 750, 666), "THOSE", 0.96),
        (poly(555, 671, 677, 713), "FOR TOO", 0.28),
        (poly(686, 666, 752, 690), "SMALL", 0.99),
        (poly(684, 690, 756, 716), "DETAILS", 0.99),
        (poly(565, 711, 667, 753), "LONG!!!", 0.63),
    ]

    blocks = engine._postprocess_results(
        raw_results,
        source_lang="en",
        page_index=6,
        min_confidence=0.20,
        merge_lines=True,
        filter_noise=True,
    )

    assert "I've WAITED FOR TOO LONG!!!" in [block.ocr_text for block in blocks]
    assert "WHO CARES ABOUT THOSE SMALL DETAILS" in [block.ocr_text for block in blocks]


def test_postprocess_keeps_scribble_and_nod_sfx_out_of_dialogue_merge() -> None:
    engine = EasyOcrEngine()
    raw_results = [
        (poly(100, 100, 230, 125), "THANKS.", 0.88),
        (poly(112, 65, 170, 85), "NOD", 0.91),
        (poly(255, 265, 345, 286), "scribble", 0.91),
    ]

    blocks = engine._postprocess_results(
        raw_results,
        source_lang="en",
        page_index=0,
        min_confidence=0.35,
        merge_lines=True,
        filter_noise=True,
    )

    assert "THANKS." in [block.ocr_text for block in blocks]
    assert all(block.ocr_text != "NOD THANKS. scribble" for block in blocks)


def test_candidate_quality_prefers_more_complete_dialogue() -> None:
    assert EasyOcrEngine._candidate_quality("GRAMMA LOOKY THAT", 0.51) > EasyOcrEngine._candidate_quality("GRAMMA; THAT;", 0.51)


def test_safe_crop_replacement_allows_suffix_completion_only() -> None:
    assert EasyOcrEngine._safe_crop_replacement(
        "ISN'T THAT WHAT A MAN'S ROMANCE IS",
        "ISN'T THAT WHAT A MAN'S ROMANCE IS ABOUT!!!",
    )
    assert not EasyOcrEngine._safe_crop_replacement(
        "I've WAITED",
        "Whi CAR! KVE ABO( WAITED Those SMALL Details",
    )
    assert not EasyOcrEngine._safe_crop_replacement(
        "WE ALWAYS TAKE YOU OUT ON OUR QUESTS, RIGHT?",
        "WHISPER WE ALWAYS TAKE YOU OUT ON OUR QUESTS, RIGHT? WHISPER",
    )


def test_append_supplemental_blocks_does_not_modify_existing_block() -> None:
    engine = EasyOcrEngine()
    blocks = engine._postprocess_results(
        [(poly(100, 100, 170, 130), "GET", 0.64)],
        source_lang="en",
        page_index=0,
        min_confidence=0.20,
        merge_lines=True,
        filter_noise=True,
    )

    rescued = engine._append_supplemental_blocks(
        blocks,
        [(poly(98, 98, 190, 132), "I GET IT!!", 0.72), (poly(20, 20, 55, 42), "NO!", 0.62)],
        source_lang="en",
        page_index=0,
        min_confidence=0.20,
        merge_lines=True,
        filter_noise=True,
    )

    assert [block.ocr_text for block in rescued] == ["NO!", "GET"]
    assert blocks[0].ocr_text == "GET"


def test_recognize_uses_supplemental_low_text_pass_for_english(tmp_path) -> None:
    class FakeReader:
        def __init__(self) -> None:
            self.calls = []

        def readtext(self, image_path, **kwargs):  # type: ignore[no-untyped-def]
            self.calls.append(kwargs)
            if "text_threshold" in kwargs:
                return [(poly(20, 20, 55, 42), "NO!", 0.62)]
            return []

    class TestEngine(EasyOcrEngine):
        def __init__(self, reader: FakeReader) -> None:
            super().__init__()
            self.reader = reader

        def _reader(self, source_lang, use_gpu):  # type: ignore[no-untyped-def]
            return self.reader

    image_path = tmp_path / "page.png"
    Image.new("RGB", (80, 80), "white").save(image_path)
    reader = FakeReader()
    engine = TestEngine(reader)

    blocks = engine.recognize(image_path, "en", 0, use_gpu=False, refine_crops=False, rescue_small_text=True)

    assert [block.ocr_text for block in blocks] == ["NO!"]
    assert any("text_threshold" in call for call in reader.calls)


def test_cuda_out_of_memory_detection() -> None:
    assert EasyOcrEngine._is_cuda_out_of_memory(RuntimeError("CUDA error: out of memory"))
    assert EasyOcrEngine._is_cuda_out_of_memory(RuntimeError("cudaErrorMemoryAllocation"))
    assert not EasyOcrEngine._is_cuda_out_of_memory(RuntimeError("file not found"))


def test_crop_variants_include_wide_zone_retries(tmp_path) -> None:
    image_path = tmp_path / "page.png"
    Image.new("RGB", (240, 240), "white").save(image_path)

    paths = EasyOcrEngine._crop_variants(image_path, [80, 80, 140, 130], tmp_path)
    names = [path.name for path in paths]

    assert any("wide32" in name for name in names)
    assert any("wide50" in name for name in names)
