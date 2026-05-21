from cbz_manga_translator.review_app import (
    CORRECTION_MODE_HELP,
    DECISION_HELP_TEXT,
    FILTER_OPTIONS,
    REVIEW_FIELD_LABELS,
    REVIEW_WORKBENCH_HELP,
)


def test_review_app_labels_are_explicit_and_pairable():
    assert "OCR brut" in REVIEW_FIELD_LABELS["ocr_raw"]
    assert "OCR corrigé" in REVIEW_FIELD_LABELS["ocr_corrected"]
    assert "Source actuelle" in REVIEW_FIELD_LABELS["source_current"]
    assert "Source corrigée" in REVIEW_FIELD_LABELS["source_corrected"]
    assert "Traduction actuelle" in REVIEW_FIELD_LABELS["translation_current"]
    assert "Traduction FR corrigée" in REVIEW_FIELD_LABELS["translation_corrected"]
    assert "QC" in REVIEW_FIELD_LABELS["warnings"]
    assert "Notes" in REVIEW_FIELD_LABELS["notes"]


def test_review_app_decision_help_mentions_all_decisions():
    for decision in ["validate", "correct", "review", "ignore", "sfx"]:
        assert decision in DECISION_HELP_TEXT


def test_correction_button_behavior_is_documented():
    assert "ne sauvegarde jamais" in CORRECTION_MODE_HELP or "sans sauvegarde" in CORRECTION_MODE_HELP
    assert "Ctrl+Entrée" in CORRECTION_MODE_HELP


def test_review_workbench_help_mentions_safe_workflow():
    assert "champs modifiables" in REVIEW_WORKBENCH_HELP
    assert "non sauvegardés" in REVIEW_WORKBENCH_HELP


def test_review_filters_cover_done_todo_and_sfx_states():
    for label in ["À traiter", "Corrections faites", "À revoir", "Validés", "Ignorés", "SFX"]:
        assert label in FILTER_OPTIONS
