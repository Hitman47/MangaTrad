from __future__ import annotations

from pathlib import Path

from PIL import Image

from cbz_manga_translator.core.cache import ProjectCache
from cbz_manga_translator.core.models import OcrBlock, PageRecord, ProjectData
from cbz_manga_translator.review.replay import (
    ReplayBlockResult,
    ReplayReport,
    bbox_iou,
    replay_review_project,
    text_similarity,
    write_replay_report,
)


class FakeRecognizer:
    def recognize(self, image_path, source_lang, page_index, **kwargs):  # type: ignore[no-untyped-def]
        return [
            OcrBlock(
                id="new",
                bbox=[10, 10, 60, 40],
                source_lang=source_lang,
                ocr_text="SHE'S G0T An IDIOT Like that FOR AM OLD MAN.",
                confidence=0.8,
            )
        ]


class FakeTranslator:
    def translate_blocks(self, blocks, source_lang, **kwargs):  # type: ignore[no-untyped-def]
        for block in blocks:
            block.ocr_corrected_text = "she's got an idiot like that for an old man."
            block.normalized_source_text = "she has got an idiot like that for an old man."
            block.translation_fr = "Elle a un idiot comme ça pour père."
            block.raw_translation_fr = block.translation_fr
        return blocks


def test_text_similarity_normalizes_case_and_spacing() -> None:
    assert text_similarity("Hello  !", "hello!") == 1.0


def test_bbox_iou() -> None:
    assert bbox_iou([0, 0, 10, 10], [5, 5, 15, 15]) == 25 / 175


def test_replay_review_project_compares_reprocessed_page_to_human_review(tmp_path: Path) -> None:
    image = tmp_path / "page.jpg"
    Image.new("RGB", (80, 80), "white").save(image)
    project_path = tmp_path / "project.reviewed.json"
    ProjectCache.save(
        project_path,
        ProjectData(
            cbz_path=str(tmp_path),
            pages=[
                PageRecord(
                    page_index=0,
                    image_name=str(image),
                    blocks=[
                        OcrBlock(
                            id="human",
                            bbox=[10, 10, 60, 40],
                            source_lang="en",
                            ocr_text="SHE'S G0T An IDIOT Like that FOR AM OLD MAN.",
                            normalized_source_text="she has got an idiot like that for an old man.",
                            translation_fr="Elle a un idiot comme ça pour père.",
                            manual_status="edited",
                        )
                    ],
                )
            ],
        ),
    )

    report = replay_review_project(
        project_path,
        max_pages=1,
        use_gpu=False,
        recognizer=FakeRecognizer(),
        translator=FakeTranslator(),
    )

    assert report.pages_replayed == 1
    assert report.target_blocks == 1
    assert report.full_matches == 1
    assert report.results[0].status == "match"


def test_replay_review_project_skips_source_when_old_review_stored_translation(tmp_path: Path) -> None:
    class FakeStoredTranslationTranslator:
        def translate_blocks(self, blocks, source_lang, **kwargs):  # type: ignore[no-untyped-def]
            for block in blocks:
                block.normalized_source_text = "she has got an idiot like that for an old man."
                block.translation_fr = "Je veux aller la bas."
                block.raw_translation_fr = block.translation_fr
            return blocks

    image = tmp_path / "page.jpg"
    Image.new("RGB", (80, 80), "white").save(image)
    project_path = tmp_path / "project.reviewed.json"
    ProjectCache.save(
        project_path,
        ProjectData(
            cbz_path=str(tmp_path),
            pages=[
                PageRecord(
                    page_index=0,
                    image_name=str(image),
                    blocks=[
                        OcrBlock(
                            id="human",
                            bbox=[10, 10, 60, 40],
                            source_lang="en",
                            ocr_text="Je veux aller la bas.",
                            normalized_source_text="Je veux aller la bas.",
                            translation_fr="Je veux aller la bas.",
                            manual_status="edited",
                        )
                    ],
                )
            ],
        ),
    )

    report = replay_review_project(
        project_path,
        max_pages=1,
        use_gpu=False,
        recognizer=FakeRecognizer(),
        translator=FakeStoredTranslationTranslator(),
    )

    assert report.source_matches == 1
    assert report.full_matches == 1
    assert report.results[0].status == "match"
    assert report.results[0].source_evaluation == "skipped_translation_in_source"


def test_write_replay_report(tmp_path: Path) -> None:
    report = ReplayReport(
        project_path="project.reviewed.json",
        pages_replayed=1,
        target_blocks=1,
        matched_blocks=1,
        source_matches=0,
        translation_matches=0,
        full_matches=0,
        elapsed_seconds=0.1,
        results=[
            ReplayBlockResult(
                page_index=0,
                target_block_id="b1",
                matched_block_id="b2",
                status="mismatch",
                bbox_iou=0.5,
                source_similarity=0.2,
                translation_similarity=0.3,
                expected_source="expected",
                actual_source="actual",
                expected_translation="attendu",
                actual_translation="actuel",
            )
        ],
    )

    json_path, md_path = write_replay_report(report, tmp_path)

    assert json_path.exists()
    assert md_path.exists()
    assert "mismatch" in md_path.read_text(encoding="utf-8")
