from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

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
