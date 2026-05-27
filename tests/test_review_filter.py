from __future__ import annotations

from cbz_manga_translator.analysis.review_filter import apply_review_filters, page_non_reviewable_reason
from cbz_manga_translator.core.models import OcrBlock


def _block(text: str, order: int = 0) -> OcrBlock:
    return OcrBlock(
        id=f"b{order}",
        bbox=[0, 0, 10, 10],
        source_lang="en",
        ocr_text=text,
        reading_order=order,
    )


def test_scanlation_credit_blocks_are_auto_ignored() -> None:
    blocks = [
        _block("This image is hosted at mangafox com", 1),
        _block("we take no credit for creation editing or translation", 2),
        _block("imangareadernet", 4),
        _block("What are you doing here?", 3),
    ]

    changed = apply_review_filters(blocks)

    assert changed == 3
    assert blocks[0].manual_status == "ignored"
    assert blocks[1].manual_status == "ignored"
    assert blocks[2].manual_status == "ignored"
    assert blocks[3].manual_status == "unchecked"
    assert blocks[0].review_notes.startswith("[auto-ignore]")


def test_sfx_caption_blocks_are_auto_ignored() -> None:
    blocks = [
        _block("Sfx: kasha", 1),
        _block("EXHALING THE SMOKE Sfx: f4", 2),
        _block("LIGHTING up", 4),
        _block("What on earth is this person?", 3),
    ]

    changed = apply_review_filters(blocks)

    assert changed == 3
    assert blocks[0].manual_status == "ignored"
    assert blocks[1].manual_status == "ignored"
    assert blocks[2].manual_status == "ignored"
    assert blocks[3].manual_status == "unchecked"


def test_infographic_page_is_marked_non_reviewable() -> None:
    blocks = [
        _block("Phase 4", 1),
        _block("300m", 2),
        _block("Monument Height", 3),
        _block("Stab Radius", 4),
        _block("Main Hall", 5),
        _block("Drift", 6),
        _block("Phase 5", 7),
        _block("10km", 8),
        _block("Maximum Depth", 9),
        _block("Notable Hives", 10),
        _block("Hall", 11),
        _block("600m", 12),
    ]

    assert page_non_reviewable_reason(blocks)
    assert apply_review_filters(blocks) == len(blocks)
    assert all(block.manual_status == "ignored" for block in blocks)


def test_extra_dense_character_profile_page_is_marked_non_reviewable() -> None:
    blocks = [
        _block("CHARACTERS Currently holds the majority within the West Oasis government and the opposing faction", 1),
        _block("West Oasis Government Mitsuru Master and pupil", 2),
        _block("Kosuna (Koizumi Taiko)", 3),
        _block("Aspiring", 4),
        _block("In control of", 5),
        _block("A group that proposes using remnant technology from the Dark Ages to aid the Opposing Faction", 6),
        _block("combat", 7),
        _block("The Vixen of the Desert defects to the Majority Faction", 8),
        _block("The Opposing Faction", 9),
    ]

    assert page_non_reviewable_reason(blocks) == "page non exploitable: fiche personnages/extra dense"
    assert apply_review_filters(blocks) == len(blocks)
    assert all(block.manual_status == "ignored" for block in blocks)


def test_dialogue_page_is_not_auto_ignored() -> None:
    blocks = [
        _block("What are you doing here?", 1),
        _block("I thought something was troubling you.", 2),
        _block("We always take you out on our quests, right?", 3),
    ]

    assert apply_review_filters(blocks) == 0
    assert all(block.manual_status == "unchecked" for block in blocks)


def test_short_dialogue_fragments_are_kept_for_review() -> None:
    blocks = [
        _block("IS THAT", 1),
        _block("YES.", 2),
        _block("AGAIN.", 3),
        _block("WAY. ~", 4),
        _block("NO", 5),
    ]

    assert apply_review_filters(blocks) == 0
    assert all(block.manual_status == "unchecked" for block in blocks)
