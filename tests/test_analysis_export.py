from __future__ import annotations

import json
from pathlib import Path

from cbz_manga_translator.analysis.export_review import export_review_dataset, iter_review_rows
from cbz_manga_translator.analysis.learning import build_learning_report
from cbz_manga_translator.analysis.light_quality import compute_quality_features
from cbz_manga_translator.core.models import OcrBlock, PageRecord, ProjectData


def sample_project() -> ProjectData:
    return ProjectData(
        cbz_path="sample.cbz",
        pages=[
            PageRecord(
                page_index=0,
                image_name="001.jpg",
                blocks=[
                    OcrBlock(
                        id="b1",
                        bbox=[1, 2, 3, 4],
                        source_lang="en",
                        ocr_text="Inhook this",
                        ocr_corrected_text="Unhook this",
                        normalized_source_text="unhook this",
                        raw_translation_fr="",
                        translation_fr="Décroche ça.",
                        confidence=0.55,
                        reading_order=0,
                        manual_status="validated",
                    ),
                    OcrBlock(
                        id="b2",
                        bbox=[5, 6, 7, 8],
                        source_lang="en",
                        ocr_text="the on plane",
                        translation_fr="sur le plan",
                        confidence=0.45,
                        reading_order=1,
                        quality_warnings=["fragment suspect"],
                    ),
                ],
            )
        ],
    )


def test_quality_features_flags_suspicious_block() -> None:
    block = sample_project().pages[0].blocks[1]
    features = compute_quality_features(block)
    assert features.risk_score >= 25
    assert features.action in {"review_medium", "review_high"}
    assert features.reasons


def test_quality_features_allow_preserved_proper_nouns() -> None:
    block = OcrBlock(
        id="proper",
        bbox=[1, 2, 3, 4],
        source_lang="en",
        ocr_text="He Took AME-NO- Gozen FROM Me!",
        ocr_corrected_text="He Took Ame-no-Gozen FROM Me!",
        normalized_source_text="He Took Ame-no-Gozen FROM Me!",
        translation_fr="Il m'a pris Ame-no-Gozen !",
        confidence=0.86,
    )

    features = compute_quality_features(block)

    assert "source residue copied into translation" not in features.reasons


def test_quality_features_allow_recent_busy_batch_proper_names() -> None:
    block = OcrBlock(
        id="proper2",
        bbox=[1, 2, 3, 4],
        source_lang="en",
        ocr_text="KARIU YOUR FACE Is SCARY",
        ocr_corrected_text="kariu your face is scary",
        normalized_source_text="kariu your face is scary",
        translation_fr="Kariu, ton visage fait peur.",
        confidence=0.86,
    )

    features = compute_quality_features(block)

    assert "source residue copied into translation" not in features.reasons


def test_quality_features_allow_manga_tilde_punctuation() -> None:
    block = OcrBlock(
        id="tilde",
        bbox=[1, 2, 3, 4],
        source_lang="en",
        ocr_text="ALRIGHT Get CLOSER To EACH Other~",
        translation_fr="Allez, rapprochez-vous l'un de l'autre.",
        confidence=0.86,
    )

    features = compute_quality_features(block)

    assert "suspicious symbols" not in features.reasons


def test_quality_features_allow_known_preserved_terms_and_french_caps() -> None:
    transit = OcrBlock(
        id="transit",
        bbox=[1, 2, 3, 4],
        source_lang="en",
        ocr_text='MEANS I\'m Like YOUR "public TRANSIT" For the DAY.',
        translation_fr='En gros, je suis ton "transport public" pour la journee.',
        confidence=0.86,
    )
    no = OcrBlock(
        id="no",
        bbox=[1, 2, 3, 4],
        source_lang="en",
        ocr_text="NO",
        translation_fr="NON",
        confidence=0.86,
    )

    assert "source residue copied into translation" not in compute_quality_features(transit).reasons
    assert "uppercase residue in translation" not in compute_quality_features(no).reasons

    cool = OcrBlock(
        id="cool",
        bbox=[1, 2, 3, 4],
        source_lang="en",
        ocr_text="SO COOL!",
        translation_fr="Trop cool !",
        confidence=0.86,
    )
    assert "source residue copied into translation" not in compute_quality_features(cool).reasons


def test_learning_report_extracts_memory() -> None:
    report = build_learning_report(sample_project())
    assert report.summary["learnable_blocks"] == 1
    assert report.exact_translation_memory[0]["source"] == "unhook this"
    assert report.ocr_correction_memory[0]["ocr_raw"] == "Inhook this"


def test_export_review_dataset_writes_files(tmp_path: Path) -> None:
    outputs = export_review_dataset(sample_project(), tmp_path)
    assert outputs["csv"].exists()
    assert outputs["jsonl"].exists()
    assert outputs["learning_report"].exists()
    assert outputs["quality_report"].exists()
    csv_text = outputs["csv"].read_text(encoding="utf-8-sig")
    assert "risk_score" in csv_text
    assert "Unhook this" in csv_text
    lines = outputs["jsonl"].read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    payload = json.loads(lines[0])
    assert payload["page_number"] == 1


def test_iter_review_rows_contains_expected_columns() -> None:
    rows = list(iter_review_rows(sample_project()))
    assert rows[0]["source_for_review"] == "unhook this"
    assert rows[0]["ocr_alternatives_count"] == 0
