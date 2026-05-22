from __future__ import annotations

from pathlib import Path

from cbz_manga_translator.analysis.review_diagnose import diagnose_review_project, write_diagnostic_report
from cbz_manga_translator.core.cache import ProjectCache
from cbz_manga_translator.core.models import OcrBlock, PageRecord, ProjectData
from cbz_manga_translator.review_diagnose import main


def _project(path: Path) -> Path:
    ProjectCache.save(
        path,
        ProjectData(
            cbz_path="corpus",
            pages=[
                PageRecord(
                    page_index=0,
                    image_name="page.jpg",
                    blocks=[
                        OcrBlock(
                            id="punct",
                            bbox=[0, 0, 10, 10],
                            source_lang="en",
                            ocr_text="Light Snow",
                            ocr_corrected_text="Light Snow...!",
                            raw_translation_fr="Neige légère",
                            translation_fr="Neige légère...!",
                            manual_status="edited",
                        ),
                        OcrBlock(
                            id="fusion",
                            bbox=[0, 0, 10, 10],
                            source_lang="en",
                            ocr_text="BAD MERGE",
                            review_notes="[fusion]",
                            manual_status="review",
                        ),
                        OcrBlock(
                            id="sfx",
                            bbox=[0, 0, 10, 10],
                            source_lang="en",
                            ocr_text="CLACK",
                            review_notes="[sfx]",
                            manual_status="ignored",
                        ),
                    ],
                )
            ],
        ),
    )
    return path


def test_diagnose_review_project_classifies_common_failures(tmp_path: Path) -> None:
    report = diagnose_review_project(_project(tmp_path / "project.reviewed.json"))

    assert report.total_blocks == 3
    assert report.changed_blocks == 3
    assert report.category_counts["punctuation"] == 1
    assert report.category_counts["translation"] == 1
    assert report.category_counts["fusion_or_bad_zone"] == 1
    assert report.category_counts["sfx_or_non_dialogue"] == 1
    assert report.scores["ignored_auto_covered"] == 1.0


def test_write_diagnostic_report(tmp_path: Path) -> None:
    report = diagnose_review_project(_project(tmp_path / "project.reviewed.json"))
    json_path, md_path = write_diagnostic_report(report, tmp_path / "diagnostic")

    assert json_path.exists()
    text = md_path.read_text(encoding="utf-8")
    assert "Diagnostic review MangaTrad" in text
    assert "punctuation" in text


def test_review_diagnose_cli(tmp_path: Path, capsys) -> None:
    project_path = _project(tmp_path / "project.reviewed.json")
    out = tmp_path / "out"

    assert main([str(project_path), "--out", str(out)]) == 0

    printed = capsys.readouterr().out
    assert "Blocs total" in printed
    assert (out / "mangatrad_review_diagnostic.json").exists()
