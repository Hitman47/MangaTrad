from pathlib import Path

from cbz_manga_translator.core.cache import ProjectCache
from cbz_manga_translator.core.models import OcrBlock, PageRecord, ProjectData
from cbz_manga_translator.review_refresh import default_refreshed_path, refresh_review_project


class DummyTranslator:
    def translate_blocks(self, blocks, source_lang, **kwargs):  # type: ignore[no-untyped-def]
        for block in blocks:
            block.ocr_corrected_text = f"fixed {block.ocr_text}"
            block.normalized_source_text = f"fixed {block.ocr_text}"
            block.raw_translation_fr = "trad auto"
            block.translation_fr = "trad auto"
        return blocks


class DummyQualityChecker:
    def apply(self, blocks, source_lang=None):  # type: ignore[no-untyped-def]
        for block in blocks:
            block.quality_warnings = ["checked"]
        return len(blocks)


def test_default_refreshed_path() -> None:
    assert default_refreshed_path("project.reviewed.json").name == "project.reviewed.refreshed.json"


def test_refresh_review_project_preserves_human_reviewed_blocks(tmp_path: Path) -> None:
    project_path = tmp_path / "project.reviewed.json"
    project = ProjectData(
        cbz_path="corpus",
        pages=[
            PageRecord(
                page_index=0,
                image_name="page.jpg",
                blocks=[
                    OcrBlock(id="todo", bbox=[0, 0, 1, 1], source_lang="en", ocr_text="Hello"),
                    OcrBlock(
                        id="done",
                        bbox=[0, 0, 1, 1],
                        source_lang="en",
                        ocr_text="Hi",
                        translation_fr="Salut.",
                        manual_status="edited",
                    ),
                    OcrBlock(
                        id="sfx",
                        bbox=[0, 0, 1, 1],
                        source_lang="en",
                        ocr_text="BOOM",
                        review_notes="[sfx]",
                        manual_status="ignored",
                    ),
                ],
            )
        ],
    )
    ProjectCache.save(project_path, project)
    out = tmp_path / "out.json"

    result = refresh_review_project(
        project_path,
        out,
        translate_argos=True,
        translator=DummyTranslator(),  # type: ignore[arg-type]
        quality_checker=DummyQualityChecker(),  # type: ignore[arg-type]
    )

    refreshed = ProjectCache.load(out)
    blocks = {block.id: block for block in refreshed.pages[0].blocks}
    assert result.refreshed_blocks == 1
    assert result.preserved_blocks == 2
    assert blocks["todo"].translation_fr == "trad auto"
    assert blocks["todo"].manual_status == "unchecked"
    assert blocks["done"].translation_fr == "Salut."
    assert blocks["sfx"].review_notes == "[sfx]"


def test_refresh_review_project_rules_only_is_default(tmp_path: Path) -> None:
    project_path = tmp_path / "project.reviewed.json"
    ProjectCache.save(
        project_path,
        ProjectData(
            cbz_path="corpus",
            pages=[
                PageRecord(
                    page_index=0,
                    image_name="page.jpg",
                    blocks=[
                        OcrBlock(
                            id="todo",
                            bbox=[0, 0, 1, 1],
                            source_lang="en",
                            ocr_text="Hi-yaaa-!",
                            raw_translation_fr="Bonjour!",
                        )
                    ],
                )
            ],
        ),
    )
    out = tmp_path / "out.json"

    result = refresh_review_project(project_path, out, quality_checker=DummyQualityChecker())  # type: ignore[arg-type]

    refreshed = ProjectCache.load(out)
    block = refreshed.pages[0].blocks[0]
    assert result.refreshed_blocks == 1
    assert block.translation_fr == "Hi-yaaa-!"
    assert block.manual_status == "unchecked"
