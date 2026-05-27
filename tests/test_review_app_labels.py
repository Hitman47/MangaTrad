from cbz_manga_translator.review.model import ReviewItem
from cbz_manga_translator.review_app import (
    CORRECTION_MODE_HELP,
    DECISION_HELP_TEXT,
    FILTER_OPTIONS,
    REVIEW_FIELD_LABELS,
    REVIEW_WORKBENCH_HELP,
    item_matches_filter,
)


def test_review_app_labels_are_explicit_and_pairable():
    assert "OCR brut" in REVIEW_FIELD_LABELS["ocr_raw"]
    assert "OCR corrig" in REVIEW_FIELD_LABELS["ocr_corrected"]
    assert "Source actuelle" in REVIEW_FIELD_LABELS["source_current"]
    assert "Source corrig" in REVIEW_FIELD_LABELS["source_corrected"]
    assert "Traduction actuelle" in REVIEW_FIELD_LABELS["translation_current"]
    assert "Traduction FR corrig" in REVIEW_FIELD_LABELS["translation_corrected"]
    assert "QC" in REVIEW_FIELD_LABELS["warnings"]
    assert "Notes" in REVIEW_FIELD_LABELS["notes"]


def test_review_app_decision_help_mentions_all_decisions():
    for decision in ["validate", "correct", "review", "fused", "zone", "ignore", "sfx"]:
        assert decision in DECISION_HELP_TEXT


def test_correction_button_behavior_is_documented():
    assert "ne sauvegarde jamais" in CORRECTION_MODE_HELP or "sans sauvegarde" in CORRECTION_MODE_HELP
    assert "Sauvegarder seulement" in CORRECTION_MODE_HELP


def test_review_workbench_help_mentions_safe_workflow():
    assert "champs modifiables" in REVIEW_WORKBENCH_HELP
    assert "non sauvegard" in REVIEW_WORKBENCH_HELP


def test_review_filters_cover_done_todo_and_sfx_states():
    for label in ["À traiter", "Corrections faites", "À revoir", "Fusion", "Zones", "Alternatives OCR", "Validés", "Ignorés", "SFX"]:
        assert label in FILTER_OPTIONS


def _item(decision: str, diagnostics: str = "") -> ReviewItem:
    return ReviewItem(
        page_index=0,
        block_id="b",
        display="",
        risk_score=0,
        risk_band="OK",
        manual_status="review",
        review_decision=decision,
        source_preview="",
        translation_preview="",
        diagnostic_preview=diagnostics,
        notes_preview="",
    )


def test_todo_filter_includes_zone_and_fusion_blocks():
    assert item_matches_filter(_item("zone"), "À traiter")
    assert item_matches_filter(_item("fused"), "À traiter")
    assert item_matches_filter(_item("review"), "À traiter")
    assert not item_matches_filter(_item("sfx"), "À traiter")


def test_alternatives_filter_finds_ocr_alternative_blocks():
    assert item_matches_filter(_item("zone", "OCR zone fallback: alternatives crop elargi disponibles"), "Alternatives OCR")
    assert not item_matches_filter(_item("zone", "zone sans candidate"), "Alternatives OCR")
