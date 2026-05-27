from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw

from cbz_manga_translator.analysis.corpus_processor import process_corpus, read_corpus_manifest
from cbz_manga_translator.core.models import OcrBlock


class FakeRecognizer:
    def recognize(self, image_path, source_lang, page_index, **kwargs):
        return [
            OcrBlock(
                id=f"p{page_index:04d}_b0000",
                bbox=[1, 2, 30, 40],
                source_lang=source_lang,
                ocr_text="hello",
                confidence=0.91,
                reading_order=0,
            )
        ]


class FakeTranslator:
    def translate_blocks(self, blocks, source_lang, **kwargs):
        for block in blocks:
            block.ocr_corrected_text = block.ocr_text
            block.normalized_source_text = block.ocr_text
            block.raw_translation_fr = "bonjour"
            block.translation_fr = "bonjour"
        return blocks


class RecordingRecognizer(FakeRecognizer):
    def __init__(self) -> None:
        self.use_gpu_values: list[bool] = []

    def recognize(self, image_path, source_lang, page_index, **kwargs):
        self.use_gpu_values.append(kwargs["use_gpu"])
        return super().recognize(image_path, source_lang, page_index, **kwargs)


class RecordingTranslator(FakeTranslator):
    def __init__(self) -> None:
        self.use_gpu_values: list[bool] = []

    def translate_blocks(self, blocks, source_lang, **kwargs):
        self.use_gpu_values.append(kwargs["use_gpu"])
        return super().translate_blocks(blocks, source_lang, **kwargs)


class FailingRecognizer(FakeRecognizer):
    def recognize(self, image_path, source_lang, page_index, **kwargs):
        raise AssertionError("recognizer should not run for skipped non-dialogue pages")


def test_read_corpus_manifest_resolves_output_relpath(tmp_path: Path) -> None:
    pages_dir = tmp_path / "pages" / "Series" / "Vol01"
    pages_dir.mkdir(parents=True)
    image = pages_dir / "sample_001__page_0003.jpg"
    Image.new("RGB", (20, 20), "white").save(image)
    (tmp_path / "manifest.jsonl").write_text(
        json.dumps(
            {
                "series_label": "Series",
                "source_path": "vol.cbz",
                "source_page_number": 3,
                "source_page_index": 2,
                "output_relpath": "pages/Series/Vol01/sample_001__page_0003.jpg",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    entries = read_corpus_manifest(tmp_path)

    assert len(entries) == 1
    assert entries[0].image_path == image
    assert entries[0].series_label == "Series"
    assert entries[0].source_page_index == 2


def test_process_corpus_exports_review_files(tmp_path: Path) -> None:
    corpus = tmp_path / "corpus"
    pages_dir = corpus / "pages" / "Series" / "Vol01"
    pages_dir.mkdir(parents=True)
    image = pages_dir / "sample_001__page_0003.jpg"
    Image.new("RGB", (20, 20), "white").save(image)
    (corpus / "manifest.jsonl").write_text(
        json.dumps({"output_relpath": "pages/Series/Vol01/sample_001__page_0003.jpg"}) + "\n",
        encoding="utf-8",
    )
    out = tmp_path / "run"

    result = process_corpus(
        corpus,
        out,
        source_lang="en",
        limit=1,
        use_gpu=False,
        recognizer=FakeRecognizer(),
        translator=FakeTranslator(),
    )

    assert result.pages_processed == 1
    assert result.blocks_total == 1
    assert result.cache_path.exists()
    assert result.review_csv.exists()
    assert result.review_jsonl.exists()
    assert result.quality_report.exists()
    assert "bonjour" in result.review_csv.read_text(encoding="utf-8-sig")


def test_process_corpus_skips_cached_pages_without_force(tmp_path: Path) -> None:
    corpus = tmp_path / "corpus"
    pages_dir = corpus / "pages"
    pages_dir.mkdir(parents=True)
    image = pages_dir / "sample.jpg"
    Image.new("RGB", (20, 20), "white").save(image)
    (corpus / "manifest.jsonl").write_text(json.dumps({"output_relpath": "pages/sample.jpg"}) + "\n", encoding="utf-8")
    out = tmp_path / "run"

    first = process_corpus(corpus, out, source_lang="en", limit=1, recognizer=FakeRecognizer(), translator=FakeTranslator())
    second = process_corpus(corpus, out, source_lang="en", limit=1, recognizer=FakeRecognizer(), translator=FakeTranslator())

    assert first.pages_processed == 1
    assert second.pages_processed == 0
    assert second.pages_skipped == 1


def test_process_corpus_can_split_ocr_and_translation_gpu_policy(tmp_path: Path) -> None:
    corpus = tmp_path / "corpus"
    pages_dir = corpus / "pages"
    pages_dir.mkdir(parents=True)
    image = pages_dir / "sample.jpg"
    Image.new("RGB", (20, 20), "white").save(image)
    (corpus / "manifest.jsonl").write_text(json.dumps({"output_relpath": "pages/sample.jpg"}) + "\n", encoding="utf-8")
    recognizer = RecordingRecognizer()
    translator = RecordingTranslator()

    process_corpus(
        corpus,
        tmp_path / "run",
        source_lang="en",
        limit=1,
        use_gpu=True,
        ocr_use_gpu=False,
        translation_use_gpu=True,
        recognizer=recognizer,
        translator=translator,
    )

    assert recognizer.use_gpu_values == [False]
    assert translator.use_gpu_values == [True]


def test_limit_mode_stratified_spreads_pages_across_series(tmp_path: Path) -> None:
    corpus = tmp_path / "corpus"
    lines = []
    for series in ("SeriesA", "SeriesB", "SeriesC"):
        for index in range(3):
            image = corpus / "pages" / series / "Vol01" / f"sample_{index}.jpg"
            image.parent.mkdir(parents=True, exist_ok=True)
            Image.new("RGB", (20, 20), "white").save(image)
            lines.append(json.dumps({"series_label": series, "output_relpath": str(image.relative_to(corpus)).replace("\\\\", "/")}))
    (corpus / "manifest.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    out = tmp_path / "run"

    result = process_corpus(
        corpus,
        out,
        source_lang="en",
        limit=3,
        limit_mode="stratified",
        recognizer=FakeRecognizer(),
        translator=FakeTranslator(),
    )

    assert result.pages_processed == 3
    exported = result.review_csv.read_text(encoding="utf-8-sig")
    assert "SeriesA" in exported
    assert "SeriesB" in exported
    assert "SeriesC" in exported


def test_read_corpus_manifest_rebuilds_from_pages_without_manifest(tmp_path: Path) -> None:
    corpus = tmp_path / "corpus"
    image = corpus / "pages" / "SeriesA" / "Vol02" / "sample_001__page_0007.jpg"
    image.parent.mkdir(parents=True)
    Image.new("RGB", (20, 20), "white").save(image)

    entries = read_corpus_manifest(corpus)

    assert len(entries) == 1
    assert entries[0].image_path == image
    assert entries[0].series_label == "SeriesA"
    assert entries[0].volume_path == "Vol02"
    assert entries[0].source_page_index == 6


def test_process_corpus_accepts_pages_only_corpus(tmp_path: Path) -> None:
    corpus = tmp_path / "corpus"
    image = corpus / "pages" / "SeriesA" / "Vol01" / "sample_001__page_0001.jpg"
    image.parent.mkdir(parents=True)
    Image.new("RGB", (20, 20), "white").save(image)
    out = tmp_path / "run"

    result = process_corpus(
        corpus,
        out,
        source_lang="en",
        limit=1,
        use_gpu=False,
        recognizer=FakeRecognizer(),
        translator=FakeTranslator(),
    )

    assert result.pages_processed == 1
    assert result.review_csv.exists()
    assert "SeriesA" in result.review_csv.read_text(encoding="utf-8-sig")


def test_process_corpus_skips_color_heavy_info_pages_before_ocr(tmp_path: Path) -> None:
    corpus = tmp_path / "corpus"
    pages_dir = corpus / "pages" / "SeriesA" / "Vol01"
    pages_dir.mkdir(parents=True)
    image = pages_dir / "sample_001__page_0209.png"
    page = Image.new("RGB", (900, 1300), "white")
    draw = ImageDraw.Draw(page)
    for x0, y0, x1, y1, color in (
        (120, 120, 780, 360, (0, 170, 220)),
        (120, 430, 780, 720, (40, 40, 40)),
        (120, 780, 780, 1180, (20, 120, 210)),
    ):
        draw.rectangle((x0, y0, x1, y1), fill=color)
    page.save(image)
    (corpus / "manifest.jsonl").write_text(
        json.dumps({"series_label": "SeriesA", "output_relpath": str(image.relative_to(corpus)).replace("\\", "/")}) + "\n",
        encoding="utf-8",
    )

    result = process_corpus(
        corpus,
        tmp_path / "run",
        source_lang="en",
        limit=1,
        recognizer=FailingRecognizer(),
        translator=FakeTranslator(),
    )

    assert result.pages_processed == 0
    assert result.pages_skipped == 1
    project = json.loads(result.cache_path.read_text(encoding="utf-8"))
    assert project["pages"][0]["status"] == "ignored"


def test_process_corpus_skips_oversized_pages_for_fast_validation(tmp_path: Path) -> None:
    corpus = tmp_path / "corpus"
    pages_dir = corpus / "pages" / "SeriesA" / "Vol01"
    pages_dir.mkdir(parents=True)
    image = pages_dir / "sample_001__page_0209.png"
    Image.new("RGB", (1200, 1200), "white").save(image)
    (corpus / "manifest.jsonl").write_text(
        json.dumps({"series_label": "SeriesA", "output_relpath": str(image.relative_to(corpus)).replace("\\", "/")}) + "\n",
        encoding="utf-8",
    )

    result = process_corpus(
        corpus,
        tmp_path / "run",
        source_lang="en",
        limit=1,
        recognizer=FailingRecognizer(),
        translator=FakeTranslator(),
        max_image_megapixels=1.0,
    )

    assert result.pages_processed == 0
    assert result.pages_skipped == 1
    assert "1.44 MP > 1.00 MP" in (tmp_path / "run" / "mangatrad_corpus_progress.json").read_text(encoding="utf-8")
    project = json.loads(result.cache_path.read_text(encoding="utf-8"))
    assert project["pages"][0]["status"] == "ignored"


def test_read_corpus_manifest_accepts_manifest_file_path(tmp_path: Path) -> None:
    corpus = tmp_path / "corpus"
    image = corpus / "pages" / "SeriesA" / "Vol01" / "sample_001__page_0001.jpg"
    image.parent.mkdir(parents=True)
    Image.new("RGB", (20, 20), "white").save(image)
    manifest = corpus / "manifest.jsonl"
    manifest.write_text(json.dumps({"output_relpath": "pages/SeriesA/Vol01/sample_001__page_0001.jpg"}) + "\n", encoding="utf-8")

    entries = read_corpus_manifest(manifest)

    assert len(entries) == 1
    assert entries[0].image_path == image


def test_read_corpus_manifest_error_contains_diagnostics(tmp_path: Path) -> None:
    corpus = tmp_path / "empty_corpus"
    corpus.mkdir()

    try:
        read_corpus_manifest(corpus)
    except FileNotFoundError as exc:
        message = str(exc)
    else:  # pragma: no cover - defensive
        raise AssertionError("Expected FileNotFoundError")

    assert "Chemin demandé" in message
    assert "Entrées directes" in message
    assert "Candidats corpus proches" in message
