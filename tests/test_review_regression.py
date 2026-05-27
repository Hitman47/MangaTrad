from pathlib import Path

from cbz_manga_translator.analysis.review_regression import (
    discover_review_projects,
    run_review_regression,
    write_regression_report,
)
from cbz_manga_translator.core.cache import ProjectCache
from cbz_manga_translator.core.models import OcrBlock, PageRecord, ProjectData
from cbz_manga_translator.review_regression import main


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
                            id="source",
                            bbox=[0, 0, 10, 10],
                            source_lang="en",
                            ocr_text="BMUSTHVB GALLENL ASLEEP inifront Computers",
                            normalized_source_text="i must've fallen asleep in front of my computer.",
                            raw_translation_fr="",
                            translation_fr="J'ai dû m'endormir devant mon ordinateur.",
                            manual_status="edited",
                        ),
                        OcrBlock(
                            id="translation",
                            bbox=[0, 0, 10, 10],
                            source_lang="en",
                            ocr_text="THIS IS.",
                            normalized_source_text="this is...",
                            raw_translation_fr="Ceci est.",
                            translation_fr="C'est...",
                            manual_status="edited",
                        ),
                        OcrBlock(
                            id="sfx",
                            bbox=[0, 0, 10, 10],
                            source_lang="en",
                            ocr_text="CLACK",
                            review_notes="[sfx]",
                            manual_status="ignored",
                        ),
                        OcrBlock(
                            id="zone",
                            bbox=[0, 0, 10, 10],
                            source_lang="en",
                            ocr_text="BAD CROP",
                            review_notes="[zone] trop petit",
                            manual_status="review",
                        ),
                    ],
                )
            ],
        ),
    )
    return path


def test_review_regression_scores_history(tmp_path: Path) -> None:
    project = _project(tmp_path / "project.reviewed.json")

    report = run_review_regression([project])

    assert report.project_count == 1
    assert report.block_count == 4
    assert report.source_match_count == report.evaluated_source_count
    assert report.translation_match_count == report.evaluated_translation_count
    assert report.ignored_auto_covered_count == report.ignored_count
    assert report.status_counts["zone_excluded"] == 1


def test_review_regression_uses_page_context_for_ignored_blocks(tmp_path: Path) -> None:
    project = tmp_path / "dense.reviewed.json"
    ProjectCache.save(
        project,
        ProjectData(
            cbz_path="corpus",
            pages=[
                PageRecord(
                    page_index=0,
                    image_name="page.jpg",
                    blocks=[
                        OcrBlock(
                            id=f"b{i}",
                            bbox=[0, 0, 10, 10],
                            source_lang="en",
                            ocr_text=text,
                            manual_status="ignored",
                        )
                        for i, text in enumerate(
                            [
                                "CHARACTERS Currently holds the majority within the West Oasis government",
                                "West Oasis Government Mitsuru Master and pupil",
                                "Kosuna Koizumi Taiko",
                                "Aspiring beauty Kanto",
                                "In control of the opposing faction",
                                "The Vixen of the Desert defects to the Majority Faction",
                            ]
                        )
                    ],
                )
            ],
        ),
    )

    report = run_review_regression([project])

    assert report.ignored_auto_covered_count == report.ignored_count


def test_review_regression_treats_contraction_expansion_as_source_match(tmp_path: Path) -> None:
    project = tmp_path / "contraction.reviewed.json"
    ProjectCache.save(
        project,
        ProjectData(
            cbz_path="corpus",
            pages=[
                PageRecord(
                    page_index=0,
                    image_name="page.jpg",
                    blocks=[
                        OcrBlock(
                            id="b",
                            bbox=[0, 0, 10, 10],
                            source_lang="en",
                            ocr_text="ILL Help RIGHT NOW:",
                            ocr_corrected_text="I'll help right now!",
                            translation_fr="Je vais aider tout de suite !",
                            manual_status="edited",
                        )
                    ],
                )
            ],
        ),
    )

    report = run_review_regression([project])

    assert report.source_match_count == report.evaluated_source_count


def test_discover_review_projects_from_directory(tmp_path: Path) -> None:
    project = _project(tmp_path / "project.reviewed.json")
    (tmp_path / "note.txt").write_text("ignore", encoding="utf-8")

    assert discover_review_projects([tmp_path]) == [project]


def test_write_regression_report(tmp_path: Path) -> None:
    report = run_review_regression([_project(tmp_path / "project.reviewed.json")])
    json_path, md_path = write_regression_report(report, tmp_path / "out")

    assert json_path.exists()
    assert "MangaTrad Review Regression" in md_path.read_text(encoding="utf-8")


def test_review_regression_cli(tmp_path: Path, capsys) -> None:
    project = _project(tmp_path / "project.reviewed.json")
    out = tmp_path / "out"

    assert main([str(project), "--out", str(out)]) == 0

    printed = capsys.readouterr().out
    assert "Blocs historiques" in printed
    assert (out / "mangatrad_review_regression_report.json").exists()
