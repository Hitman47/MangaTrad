from __future__ import annotations

import csv
from pathlib import Path

from cbz_manga_translator.analysis.export_review import export_review_dataset
from cbz_manga_translator.analysis.review_workflow import create_review_pack, apply_review_pack
from cbz_manga_translator.core.cache import ProjectCache
from cbz_manga_translator.core.models import OcrBlock, PageRecord, ProjectData


def _project() -> ProjectData:
    return ProjectData(
        cbz_path="corpus",
        pages=[
            PageRecord(
                page_index=0,
                image_name="pages/SeriesA/Vol1/p001.jpg",
                blocks=[
                    OcrBlock(
                        id="a1",
                        bbox=[0, 0, 10, 10],
                        source_lang="en",
                        ocr_text="Iwas hungry",
                        translation_fr="Iwas faim",
                        confidence=0.5,
                        reading_order=0,
                    )
                ],
            ),
            PageRecord(
                page_index=1,
                image_name="pages/SeriesB/Vol1/p002.jpg",
                blocks=[
                    OcrBlock(
                        id="b1",
                        bbox=[0, 0, 10, 10],
                        source_lang="en",
                        ocr_text="Hello",
                        translation_fr="Bonjour.",
                        confidence=0.9,
                        reading_order=0,
                    )
                ],
            ),
        ],
    )


def test_create_review_pack_balanced(tmp_path: Path) -> None:
    project = _project()
    analysis = tmp_path / "analysis"
    export_review_dataset(project, analysis)
    result = create_review_pack(analysis, tmp_path / "review", max_blocks=10, include_ok=True)
    assert result.review_path.exists()
    assert result.review_path.suffix == ".tsv"
    rows = list(csv.DictReader(result.review_path.open("r", encoding="utf-8-sig"), delimiter="\t"))
    assert rows
    assert "review_decision" in rows[0]
    assert "corrected_fr" in rows[0]
    assert result.series_count == 2


def test_apply_review_pack_updates_project(tmp_path: Path) -> None:
    project = _project()
    project_path = tmp_path / "project.json"
    ProjectCache.save(project_path, project)
    review_csv = tmp_path / "review.csv"
    with review_csv.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["review_decision", "corrected_ocr", "corrected_source", "corrected_fr", "page_index", "block_id"],
        )
        writer.writeheader()
        writer.writerow({
            "review_decision": "correct",
            "corrected_ocr": "I was hungry",
            "corrected_source": "I was hungry",
            "corrected_fr": "J'avais faim.",
            "page_index": "0",
            "block_id": "a1",
        })
        writer.writerow({
            "review_decision": "sfx",
            "corrected_ocr": "",
            "corrected_source": "",
            "corrected_fr": "",
            "page_index": "1",
            "block_id": "b1",
        })
    out_project = tmp_path / "reviewed.json"
    result = apply_review_pack(project_path, review_csv, output_project_path=out_project)
    assert result.changed_blocks == 2
    reviewed = ProjectCache.load(out_project)
    first = reviewed.pages[0].blocks[0]
    second = reviewed.pages[1].blocks[0]
    assert first.ocr_corrected_text == "I was hungry"
    assert first.translation_fr == "J'avais faim."
    assert first.manual_status == "edited"
    assert second.manual_status == "ignored"


def test_apply_review_pack_preserves_fused_decision(tmp_path: Path) -> None:
    project = _project()
    project_path = tmp_path / "project.json"
    ProjectCache.save(project_path, project)
    review_csv = tmp_path / "review.csv"
    with review_csv.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["review_decision", "review_notes", "page_index", "block_id"],
        )
        writer.writeheader()
        writer.writerow({
            "review_decision": "fused",
            "review_notes": "bulle + SFX",
            "page_index": "0",
            "block_id": "a1",
        })

    out_project = tmp_path / "reviewed.json"
    result = apply_review_pack(project_path, review_csv, output_project_path=out_project)

    assert result.review_blocks == 1
    block = ProjectCache.load(out_project).pages[0].blocks[0]
    assert block.manual_status == "review"
    assert block.review_notes.startswith("[fusion]")


def test_apply_review_pack_reads_tsv_with_commas(tmp_path: Path) -> None:
    project = _project()
    project_path = tmp_path / "project.json"
    ProjectCache.save(project_path, project)
    review_tsv = tmp_path / "review.tsv"
    with review_tsv.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            delimiter="\t",
            quoting=csv.QUOTE_ALL,
            fieldnames=[
                "review_decision",
                "corrected_ocr",
                "corrected_source",
                "corrected_fr",
                "review_notes",
                "page_index",
                "block_id",
                "series_label",
            ],
        )
        writer.writeheader()
        writer.writerow({
            "review_decision": "correct",
            "corrected_ocr": "Hello, boss",
            "corrected_source": "Hello, boss",
            "corrected_fr": "Bonjour, chef.",
            "review_notes": "Titre, série avec virgule",
            "page_index": "0",
            "block_id": "a1",
            "series_label": "Series, With, Commas",
        })
    out_project = tmp_path / "reviewed_tsv.json"
    result = apply_review_pack(project_path, review_tsv, output_project_path=out_project)
    assert result.changed_blocks == 1
    reviewed = ProjectCache.load(out_project)
    block = reviewed.pages[0].blocks[0]
    assert block.ocr_corrected_text == "Hello, boss"
    assert block.translation_fr == "Bonjour, chef."
