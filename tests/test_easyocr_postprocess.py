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


def test_candidate_quality_prefers_more_complete_dialogue() -> None:
    assert EasyOcrEngine._candidate_quality("GRAMMA LOOKY THAT", 0.51) > EasyOcrEngine._candidate_quality("GRAMMA; THAT;", 0.51)
