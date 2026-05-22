from __future__ import annotations

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


def test_candidate_quality_prefers_more_complete_dialogue() -> None:
    assert EasyOcrEngine._candidate_quality("GRAMMA LOOKY THAT", 0.51) > EasyOcrEngine._candidate_quality("GRAMMA; THAT;", 0.51)


def test_cuda_out_of_memory_detection() -> None:
    assert EasyOcrEngine._is_cuda_out_of_memory(RuntimeError("CUDA error: out of memory"))
    assert EasyOcrEngine._is_cuda_out_of_memory(RuntimeError("cudaErrorMemoryAllocation"))
    assert not EasyOcrEngine._is_cuda_out_of_memory(RuntimeError("file not found"))
