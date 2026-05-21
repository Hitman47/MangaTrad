from __future__ import annotations

import csv
import json
from pathlib import Path

from cbz_manga_translator.analysis.corpus_rules import build_learned_profile, read_review_rows, write_learned_profile


def test_build_learned_profile_detects_residue_and_ocr_tokens() -> None:
    rows = [
        {
            "series_label": "SeriesA",
            "page_number": "1",
            "block_id": "b1",
            "risk_score": "80",
            "suggested_action": "review_high",
            "source_for_review": "I know 1 have TO ROB OR STEAL",
            "translation_fr": "Je sais que je dois steal",
            "risk_reasons": "",
            "quality_warnings": "",
        },
        {
            "series_label": "SeriesB",
            "page_number": "2",
            "block_id": "b2",
            "risk_score": "0",
            "suggested_action": "probably_ok",
            "source_for_review": "Kanade is here",
            "translation_fr": "Kanade est ici",
            "risk_reasons": "",
            "quality_warnings": "",
        },
    ]
    profile = build_learned_profile(rows)
    residue_tokens = {row["token"] for row in profile.source_residue_tokens}
    assert "steal" in residue_tokens
    names = {row["term"] for row in profile.probable_name_candidates}
    assert "Kanade" in names
    assert profile.summary["rows"] == 2
    assert profile.summary["high_risk_rows"] == 1


def test_write_learned_profile_outputs_files(tmp_path: Path) -> None:
    profile = build_learned_profile([
        {
            "series_label": "SeriesA",
            "page_number": "1",
            "block_id": "b1",
            "risk_score": "80",
            "suggested_action": "review_high",
            "source_for_review": "thess60 billiondoubve dollarman",
            "translation_fr": "thess60 milliardsdoubve dollarman",
            "risk_reasons": "",
            "quality_warnings": "",
        }
    ])
    paths = write_learned_profile(profile, tmp_path)
    assert paths["profile"].exists()
    assert paths["report"].exists()
    data = json.loads(paths["profile"].read_text(encoding="utf-8"))
    assert data["summary"]["rows"] == 1


def test_read_review_rows_from_analysis_dir(tmp_path: Path) -> None:
    csv_path = tmp_path / "mangatrad_review_blocks.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["source_for_review", "translation_fr", "risk_score"])
        writer.writeheader()
        writer.writerow({"source_for_review": "Hello", "translation_fr": "Bonjour", "risk_score": "0"})
    rows = read_review_rows(tmp_path)
    assert rows[0]["source_for_review"] == "Hello"
