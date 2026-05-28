from pathlib import Path

from cbz_manga_translator.core.cache import ProjectCache
from cbz_manga_translator.core.models import OcrBlock, PageRecord, ProjectData
from cbz_manga_translator.ocr.candidates import OcrCandidate
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


class DummyZoneFallback:
    def collect_candidates(self, image_path, block, source_lang, **kwargs):  # type: ignore[no-untyped-def]
        return [
            OcrCandidate("easyocr-crop", "isn't that what a man's romance is about!!!", 0.91, 12.0, "wide crop"),
            OcrCandidate("current", block.ocr_text, block.confidence, 3.0, "current"),
        ]


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
                    OcrBlock(
                        id="review",
                        bbox=[0, 0, 1, 1],
                        source_lang="en",
                        ocr_text="Needs another look",
                        translation_fr="À revoir",
                        manual_status="review",
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
    assert result.preserved_blocks == 3
    assert blocks["todo"].translation_fr == "trad auto"
    assert blocks["todo"].manual_status == "unchecked"
    assert blocks["done"].translation_fr == "Salut."
    assert blocks["sfx"].review_notes == "[sfx]"
    assert blocks["review"].translation_fr == "À revoir"


def test_refresh_review_project_can_include_review_blocks(tmp_path: Path) -> None:
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
                            id="review",
                            bbox=[0, 0, 1, 1],
                            source_lang="en",
                            ocr_text="BMUSTHVB GALLENL ASLEEP inifront Computers",
                            translation_fr="bad",
                            manual_status="review",
                        )
                    ],
                )
            ],
        ),
    )
    out = tmp_path / "out.json"

    result = refresh_review_project(project_path, out, include_review=True, quality_checker=DummyQualityChecker())  # type: ignore[arg-type]

    block = ProjectCache.load(out).pages[0].blocks[0]
    assert result.refreshed_blocks == 1
    assert block.normalized_source_text == "I must've fallen asleep in front of my computer."
    assert block.translation_fr == "J'ai dû m'endormir devant mon ordinateur."
    assert block.manual_status == "review"


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


def test_refresh_review_project_recomputes_stale_english_diagnostics_from_raw_ocr(tmp_path: Path) -> None:
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
                            ocr_text="For stronger oppon- ents",
                            ocr_corrected_text="For stronger opponents",
                            normalized_source_text="For stronger opponents",
                        )
                    ],
                )
            ],
        ),
    )
    out = tmp_path / "out.json"

    refresh_review_project(project_path, out, quality_checker=DummyQualityChecker())  # type: ignore[arg-type]

    block = ProjectCache.load(out).pages[0].blocks[0]
    assert block.ocr_corrected_text == "For stronger opponents..."
    assert block.normalized_source_text == "For stronger opponents..."


def test_refresh_review_project_uses_shared_ocr_cleanup(tmp_path: Path) -> None:
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
                            ocr_text="The Tiger TCO WAS sighted FOLR DAYS Ago.",
                        )
                    ],
                )
            ],
        ),
    )
    out = tmp_path / "out.json"

    refresh_review_project(project_path, out, quality_checker=DummyQualityChecker())  # type: ignore[arg-type]

    block = ProjectCache.load(out).pages[0].blocks[0]
    assert block.normalized_source_text == "The Tiger TCO was sighted four days ago."


def test_refresh_review_project_collects_zone_ocr_alternatives_without_replacing(tmp_path: Path) -> None:
    image = tmp_path / "page.jpg"
    image.write_bytes(b"fake image path is enough for dummy fallback")
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
                            id="zone",
                            bbox=[0, 0, 100, 40],
                            source_lang="en",
                            ocr_text="ISN'T THAT WHAT A MAN'S POMANCE IS",
                            review_notes="[zone]",
                            manual_status="review",
                        )
                    ],
                )
            ],
        ),
    )
    out = tmp_path / "out.json"

    result = refresh_review_project(
        project_path,
        out,
        ocr_fallback_zones=True,
        fallback_engine=DummyZoneFallback(),  # type: ignore[arg-type]
    )

    block = ProjectCache.load(out).pages[0].blocks[0]
    assert result.ocr_fallback_blocks == 1
    assert block.ocr_text == "ISN'T THAT WHAT A MAN'S POMANCE IS"
    assert block.ocr_alternatives[0]["text"] == "isn't that what a man's romance is about!!!"
    assert any("OCR zone fallback" in warning for warning in block.quality_warnings)
