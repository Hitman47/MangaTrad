from __future__ import annotations

import csv
from pathlib import Path

from cbz_manga_translator.corpus_learn import main


def test_corpus_learn_cli(tmp_path: Path) -> None:
    analysis = tmp_path / "analysis"
    analysis.mkdir()
    csv_path = analysis / "mangatrad_review_blocks.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["series_label", "source_for_review", "translation_fr", "risk_score", "suggested_action"])
        writer.writeheader()
        writer.writerow({
            "series_label": "S",
            "source_for_review": "FOLR DAYS Ago",
            "translation_fr": "FOLR DAYS Ago",
            "risk_score": "90",
            "suggested_action": "review_high",
        })
    out = tmp_path / "learned"
    assert main(["--analysis", str(analysis), "--out", str(out)]) == 0
    assert (out / "mangatrad_learned_profile.json").exists()
