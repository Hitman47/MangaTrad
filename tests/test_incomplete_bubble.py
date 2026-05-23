from __future__ import annotations

from cbz_manga_translator.ocr.incomplete import (
    FUSED_BUBBLE_WARNING,
    INCOMPLETE_BUBBLE_WARNING,
    is_probably_fused_source,
    is_probably_incomplete_source,
    zone_quality_warnings,
)


def test_detects_reviewed_incomplete_bubble_shapes() -> None:
    assert is_probably_incomplete_source("NOW I GOTTA Get Out Before Sensei CATCHES")
    assert is_probably_incomplete_source("But OUR SOLRCES SAY THAT")
    assert is_probably_incomplete_source("DO something! I'm Counting ON")


def test_does_not_flag_complete_common_dialogue() -> None:
    assert not is_probably_incomplete_source("WHAT YA DOIN' UP THERE?")
    assert not is_probably_incomplete_source("The Tiger I Just SLASHED was A Mirage!")


def test_detects_fused_sfx_or_multiple_bubbles() -> None:
    assert is_probably_fused_source("Krehble 4h, Seriously? You MEAN THAT? Krembue")
    assert is_probably_fused_source("They say you should live life counting the good things instead of the bad, don't they!? Like manga or songs.")


def test_zone_quality_warnings_are_stable() -> None:
    warnings = zone_quality_warnings("NOW I GOTTA Get Out Before Sensei CATCHES")
    assert INCOMPLETE_BUBBLE_WARNING in warnings
    assert FUSED_BUBBLE_WARNING not in warnings
