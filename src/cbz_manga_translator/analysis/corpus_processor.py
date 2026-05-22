from __future__ import annotations

import csv
import json
import random
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from cbz_manga_translator.analysis.export_review import export_review_dataset
from cbz_manga_translator.core.cache import ProjectCache
from cbz_manga_translator.core.models import OcrBlock, PageRecord, ProjectData, SourceLang
from cbz_manga_translator.ocr.easyocr_engine import EasyOcrEngine
from cbz_manga_translator.ocr.fallback_engine import OcrFallbackEngine
from cbz_manga_translator.translate.argos import ArgosTranslator
from cbz_manga_translator.translate.quality import TranslationQualityChecker


IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}



def _count_images_under(path: Path, *, max_count: int | None = None) -> int:
    if not path.exists():
        return 0
    count = 0
    for child in path.rglob("*"):
        if child.is_file() and child.suffix.lower() in IMAGE_SUFFIXES:
            count += 1
            if max_count is not None and count >= max_count:
                return count
    return count


def _has_manifest(path: Path) -> bool:
    return (path / "manifest.jsonl").exists() or (path / "manifest.csv").exists()


def _looks_like_run_output(path: Path) -> bool:
    lowered = path.name.lower()
    return (
        "run" in lowered
        or lowered.endswith("analysis")
        or (path / "mangatrad_corpus_project.json").exists()
        or (path / "analysis").exists()
    )


def find_corpus_candidates(root: Path, *, max_depth: int = 3) -> list[Path]:
    """Find likely corpus input folders near *root*.

    The function is intentionally conservative: it ignores run/output folders and
    only returns directories that either contain a manifest or have page images
    below them. It is used for diagnostics, not for silently guessing in normal
    processing.
    """
    base = root if root.exists() and root.is_dir() else root.parent
    search_roots: list[Path] = []
    if base.exists():
        search_roots.append(base)
    if base.parent.exists() and base.parent != base:
        search_roots.append(base.parent)

    candidates: dict[str, Path] = {}
    for search_root in search_roots:
        try:
            iterator = search_root.rglob("*")
        except OSError:
            continue
        for path in iterator:
            if not path.is_dir():
                continue
            try:
                rel_depth = len(path.relative_to(search_root).parts)
            except ValueError:
                rel_depth = 999
            if rel_depth > max_depth:
                continue
            if _looks_like_run_output(path):
                continue
            if _has_manifest(path) or _count_images_under(path / "pages", max_count=1) > 0:
                candidates[str(path.resolve())] = path
    return sorted(candidates.values(), key=lambda item: str(item).lower())


def describe_corpus_path(corpus_dir: str | Path) -> str:
    """Return a human-readable diagnostic for a corpus path."""
    root = Path(corpus_dir)
    lines = [f"Chemin demandé : {root}"]
    lines.append(f"Existe         : {'oui' if root.exists() else 'non'}")
    lines.append(f"Est dossier    : {'oui' if root.exists() and root.is_dir() else 'non'}")
    if root.exists() and root.is_dir():
        children = sorted(root.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        lines.append(f"Entrées directes: {len(children)}")
        for child in children[:20]:
            kind = "dir " if child.is_dir() else "file"
            lines.append(f"  - [{kind}] {child.name}")
        if len(children) > 20:
            lines.append(f"  ... {len(children) - 20} entrée(s) masquée(s)")
        for candidate in (root, root / "pages"):
            lines.append(f"Images sous {candidate}: {_count_images_under(candidate)}")
        manifest_path = _find_manifest_file(root)
        lines.append(f"Manifest trouvé: {manifest_path if manifest_path else 'non'}")
    candidates = [path for path in find_corpus_candidates(root) if path != root]
    if candidates:
        lines.append("Candidats corpus proches:")
        for candidate in candidates[:20]:
            marker = "manifest" if _has_manifest(candidate) else "pages"
            count = _count_images_under(candidate / "pages") or _count_images_under(candidate, max_count=1000000)
            lines.append(f"  - {candidate} ({marker}, images={count})")
        if len(candidates) > 20:
            lines.append(f"  ... {len(candidates) - 20} candidat(s) masqué(s)")
    else:
        lines.append("Candidats corpus proches: aucun")
    return "\n".join(lines)


class Recognizer(Protocol):
    def recognize(
        self,
        image_path: str | Path,
        source_lang: SourceLang,
        page_index: int,
        *,
        use_gpu: bool = False,
        min_confidence: float = 0.20,
        merge_lines: bool = True,
        filter_noise: bool = True,
        refine_crops: bool = True,
    ) -> list[OcrBlock]: ...


class Translator(Protocol):
    def translate_blocks(
        self,
        blocks: list[OcrBlock],
        source_lang: SourceLang,
        *,
        use_gpu: bool = False,
        raw_terms: str | None = None,
        normalize_english: bool = True,
        use_builtin_glossary: bool = True,
        force: bool = False,
    ) -> list[OcrBlock]: ...


@dataclass(slots=True)
class CorpusManifestEntry:
    page_id: str
    page_number: int
    image_path: Path
    volume_path: str = ""
    series_label: str = ""
    series_path: str = ""
    source_page_index: int | None = None


@dataclass(slots=True)
class CorpusProcessResult:
    pages_total: int
    pages_processed: int
    pages_skipped: int
    blocks_total: int
    warnings_total: int
    cache_path: Path
    analysis_dir: Path
    review_csv: Path
    review_jsonl: Path
    quality_report: Path
    elapsed_seconds: float


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"JSONL invalide ligne {line_number} dans {path}: {exc}") from exc
    return rows


def _resolve_image_path(raw: dict[str, Any], corpus_root: Path) -> Path:
    candidates = [
        raw.get("sample_path"),
        raw.get("extracted_path"),
        raw.get("output_path"),
        raw.get("image_path"),
        raw.get("sample_file"),
        raw.get("relative_path"),
        raw.get("output_relpath"),
    ]
    for candidate in candidates:
        if not candidate:
            continue
        path = Path(str(candidate))
        if path.is_absolute():
            if path.exists():
                return path
        else:
            for base in (corpus_root, corpus_root / "pages"):
                resolved = base / path
                if resolved.exists():
                    return resolved
    # Fallback for older manifests: try every string-like value ending as an image path.
    for value in raw.values():
        if not isinstance(value, str):
            continue
        if Path(value).suffix.lower() not in IMAGE_SUFFIXES:
            continue
        path = Path(value)
        if path.is_absolute() and path.exists():
            return path
        resolved = corpus_root / path
        if resolved.exists():
            return resolved
    raise ValueError(f"Impossible de trouver l'image extraite dans l'entrée manifest: {raw}")


def _entry_from_manifest_row(raw: dict[str, Any], corpus_root: Path, index: int) -> CorpusManifestEntry:
    image_path = _resolve_image_path(raw, corpus_root)
    page_number = int(raw.get("sample_index") or raw.get("page_number") or raw.get("source_page_number") or index + 1)
    page_id = str(raw.get("sample_id") or raw.get("page_id") or f"corpus_page_{index:05d}")
    source_page_index = raw.get("source_page_index")
    if source_page_index is not None:
        try:
            source_page_index = int(source_page_index)
        except Exception:
            source_page_index = None
    return CorpusManifestEntry(
        page_id=page_id,
        page_number=page_number,
        image_path=image_path,
        volume_path=str(raw.get("volume_path") or raw.get("source_volume") or raw.get("source_cbz") or ""),
        series_label=str(raw.get("series_label") or raw.get("series") or ""),
        series_path=str(raw.get("series_path") or ""),
        source_page_index=source_page_index,
    )


def _read_manifest_file(manifest_path: Path, corpus_root: Path) -> list[CorpusManifestEntry]:
    if manifest_path.suffix.lower() == ".jsonl":
        rows = _read_jsonl(manifest_path)
    elif manifest_path.suffix.lower() == ".csv":
        with manifest_path.open("r", encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
    else:  # pragma: no cover - internal guard
        raise ValueError(f"Format de manifest non supporté: {manifest_path}")
    return [_entry_from_manifest_row(row, corpus_root, index) for index, row in enumerate(rows)]


def _find_manifest_file(root: Path) -> Path | None:
    for name in ("manifest.jsonl", "manifest.csv"):
        candidate = root / name
        if candidate.exists():
            return candidate

    nested = sorted(
        path
        for pattern in ("manifest.jsonl", "manifest.csv")
        for path in root.rglob(pattern)
        if "analysis" not in path.parts and "mangatrad_corpus_run" not in path.parts
    )
    if len(nested) == 1:
        return nested[0]
    if len(nested) > 1:
        names = "; ".join(str(path) for path in nested[:10])
        raise FileNotFoundError(
            f"Plusieurs manifests trouvés sous {root}. Donne le dossier exact du corpus ou précise un corpus propre. Trouvés: {names}"
        )
    return None


def _infer_series_label_from_image(image_path: Path, pages_root: Path) -> str:
    try:
        rel = image_path.relative_to(pages_root)
    except ValueError:
        return image_path.parent.name
    if len(rel.parts) >= 3:
        return rel.parts[0]
    if len(rel.parts) >= 2:
        return image_path.parent.name
    return "filesystem_corpus"


def _infer_volume_label_from_image(image_path: Path, pages_root: Path) -> str:
    try:
        rel = image_path.relative_to(pages_root)
    except ValueError:
        return image_path.parent.name
    if len(rel.parts) >= 3:
        return rel.parts[1]
    return image_path.parent.name


def _build_manifest_from_pages(root: Path) -> list[CorpusManifestEntry]:
    """Recover a corpus when only extracted page images are present.

    This is intentionally a fallback. The real manifest generated by corpus_sample
    keeps source CBZ/page metadata, but users can move or copy only pages/. In
    that situation corpus_process should still work instead of failing after a
    long setup step.
    """
    pages_root = root / "pages" if (root / "pages").exists() else root
    images = sorted(path for path in pages_root.rglob("*") if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES)
    if not images:
        raise FileNotFoundError(
            f"Manifest introuvable dans {root}, et aucune image exploitable trouvée sous {pages_root}.\n"
            "Attendu: manifest.jsonl, manifest.csv, ou un dossier pages/ contenant des images.\n\n"
            + describe_corpus_path(root)
        )

    entries: list[CorpusManifestEntry] = []
    for index, image_path in enumerate(images):
        series_label = _infer_series_label_from_image(image_path, pages_root)
        volume_label = _infer_volume_label_from_image(image_path, pages_root)
        source_page_index = None
        # sample_001__page_0003.jpg -> 2, useful for debugging/reporting only.
        stem = image_path.stem.lower()
        marker = "__page_"
        if marker in stem:
            try:
                source_page_index = max(0, int(stem.rsplit(marker, 1)[1]) - 1)
            except ValueError:
                source_page_index = None
        entries.append(
            CorpusManifestEntry(
                page_id=f"filesystem_page_{index:05d}",
                page_number=index + 1,
                image_path=image_path,
                volume_path=volume_label,
                series_label=series_label,
                series_path=str((pages_root / series_label) if series_label else pages_root),
                source_page_index=source_page_index,
            )
        )
    return entries


def read_corpus_manifest(corpus_dir: str | Path) -> list[CorpusManifestEntry]:
    root = Path(corpus_dir)
    if root.is_file() and root.name in {"manifest.jsonl", "manifest.csv"}:
        return _read_manifest_file(root, root.parent)
    manifest_path = _find_manifest_file(root)
    if manifest_path is not None:
        manifest_root = manifest_path.parent
        return _read_manifest_file(manifest_path, manifest_root)

    return _build_manifest_from_pages(root)


def _load_or_create_project(cache_path: Path, entries: list[CorpusManifestEntry]) -> ProjectData:
    if cache_path.exists():
        return ProjectCache.load(cache_path)
    pages = [
        PageRecord(page_index=index, image_name=str(entry.image_path), blocks=[], status="new")
        for index, entry in enumerate(entries)
    ]
    return ProjectData(cbz_path=str(cache_path.parent), pages=pages, version=1, glossary_terms="")


def _write_progress(progress_path: Path, payload: dict[str, Any]) -> None:
    progress_path.parent.mkdir(parents=True, exist_ok=True)
    progress_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")



def _entry_group_key(entry: CorpusManifestEntry) -> str:
    """Return a stable group key used for stratified corpus limits.

    corpus_sample stores sampled pages as pages/<series>/<volume>/<image>. When
    metadata is present, series_label/series_path are preferred; otherwise the
    extracted image path still gives us a reasonable series bucket.
    """
    if entry.series_label:
        return entry.series_label
    if entry.series_path:
        return entry.series_path
    parts = entry.image_path.parts
    if "pages" in parts:
        index = parts.index("pages")
        if len(parts) > index + 1:
            return parts[index + 1]
    if entry.volume_path:
        return str(Path(entry.volume_path).parent)
    return str(entry.image_path.parent)


def _select_manifest_entries(
    entries: list[CorpusManifestEntry],
    *,
    start: int = 0,
    limit: int | None = None,
    limit_mode: str = "stratified",
    seed: int = 47,
) -> list[tuple[int, CorpusManifestEntry]]:
    """Select corpus entries while preserving original manifest indices.

    The first V0.3.9 implementation sliced the manifest. With a sampled corpus,
    that meant `--limit 30` only processed the first series. Stratified selection
    is a better default for quality work: it spreads a small test run across
    series/volumes instead of overfitting the QC to one book.
    """
    if start < 0:
        raise ValueError("start doit être >= 0")
    mode = limit_mode.strip().lower()
    if mode not in {"first", "random", "stratified"}:
        raise ValueError("limit_mode doit valoir: first, random ou stratified")

    indexed = list(enumerate(entries))[start:]
    if limit is None:
        return indexed
    safe_limit = max(0, limit)
    if safe_limit >= len(indexed):
        return indexed
    if safe_limit == 0:
        return []

    if mode == "first":
        return indexed[:safe_limit]
    if mode == "random":
        rng = random.Random(seed)
        selected = rng.sample(indexed, safe_limit)
        return sorted(selected, key=lambda item: item[0])

    groups: dict[str, list[tuple[int, CorpusManifestEntry]]] = {}
    for item in indexed:
        groups.setdefault(_entry_group_key(item[1]), []).append(item)
    ordered_group_keys = sorted(groups, key=lambda key: groups[key][0][0])
    selected: list[tuple[int, CorpusManifestEntry]] = []
    cursor = 0
    while len(selected) < safe_limit and ordered_group_keys:
        progressed = False
        for key in list(ordered_group_keys):
            bucket = groups[key]
            if cursor < len(bucket):
                selected.append(bucket[cursor])
                progressed = True
                if len(selected) >= safe_limit:
                    break
        if not progressed:
            break
        cursor += 1
    return sorted(selected, key=lambda item: item[0])

def process_corpus(
    corpus_dir: str | Path,
    output_dir: str | Path,
    *,
    source_lang: SourceLang = "en",
    limit: int | None = None,
    start: int = 0,
    limit_mode: str = "stratified",
    seed: int = 47,
    use_gpu: bool = True,
    min_confidence: float = 0.20,
    merge_lines: bool = True,
    filter_noise: bool = True,
    refine_crops: bool = False,
    fallback: str = "off",
    include_optional_ocr: bool = False,
    translate: bool = True,
    normalize_english: bool = True,
    use_builtin_glossary: bool = True,
    ocr_use_gpu: bool | None = None,
    translation_use_gpu: bool | None = None,
    force: bool = False,
    checkpoint_every: int = 10,
    raw_terms: str | None = None,
    recognizer: Recognizer | None = None,
    translator: Translator | None = None,
    quality_checker: TranslationQualityChecker | None = None,
) -> CorpusProcessResult:
    """Batch OCR/translate a sampled corpus and export review datasets.

    Defaults are intentionally conservative: crop refinement and optional OCR backends
    are disabled to avoid the multi-minute-per-page behaviour seen in manual tests.
    """
    started = time.monotonic()
    corpus_root = Path(corpus_dir)
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    analysis_dir = output_root / "analysis"
    analysis_dir.mkdir(parents=True, exist_ok=True)
    cache_path = output_root / "mangatrad_corpus_project.json"
    progress_path = output_root / "mangatrad_corpus_progress.json"

    entries = read_corpus_manifest(corpus_root)
    selected_entries = _select_manifest_entries(entries, start=start, limit=limit, limit_mode=limit_mode, seed=seed)

    project = _load_or_create_project(cache_path, entries)
    if len(project.pages) != len(entries):
        # Safer to rebuild when the manifest changed rather than corrupt alignment.
        project = _load_or_create_project(Path("__nonexistent__"), entries)

    recognizer = recognizer or EasyOcrEngine()
    translator = translator or ArgosTranslator()
    quality_checker = quality_checker or TranslationQualityChecker()
    fallback_engine = OcrFallbackEngine(recognizer if isinstance(recognizer, EasyOcrEngine) else None)

    fallback_mode = fallback.strip().lower()
    if fallback_mode not in {"off", "suspects", "all"}:
        raise ValueError("fallback doit valoir: off, suspects ou all")
    active_ocr_gpu = use_gpu if ocr_use_gpu is None else ocr_use_gpu
    active_translation_gpu = use_gpu if translation_use_gpu is None else translation_use_gpu

    pages_processed = 0
    pages_skipped = 0
    blocks_total = 0
    warnings_total = 0

    for local_index, entry in selected_entries:
        page = project.pages[local_index]
        page.image_name = str(entry.image_path)
        if page.blocks and not force:
            pages_skipped += 1
            blocks_total += len(page.blocks)
            warnings_total += sum(1 for block in page.blocks if block.quality_warnings)
            continue

        blocks = recognizer.recognize(
            entry.image_path,
            source_lang,
            local_index,
            use_gpu=active_ocr_gpu,
            min_confidence=min_confidence,
            merge_lines=merge_lines,
            filter_noise=filter_noise,
            refine_crops=refine_crops,
        )

        if fallback_mode != "off" and blocks:
            # First pass QC gives fallback something meaningful to target.
            quality_checker.apply(blocks, source_lang=source_lang)
            only_suspect = fallback_mode == "suspects"
            blocks, _ = fallback_engine.improve_blocks(
                entry.image_path,
                blocks,
                source_lang,
                use_gpu=active_ocr_gpu,
                min_confidence=min_confidence,
                only_suspect=only_suspect,
                include_optional_engines=include_optional_ocr,
            )

        if translate and blocks:
            blocks = translator.translate_blocks(
                blocks,
                source_lang,
                use_gpu=active_translation_gpu,
                raw_terms=raw_terms or project.glossary_terms,
                normalize_english=normalize_english,
                use_builtin_glossary=use_builtin_glossary,
                force=True,
            )

        quality_checker.apply(blocks, source_lang=source_lang)
        page.blocks = blocks
        page.status = "translated" if translate else "ocr_done"
        pages_processed += 1
        blocks_total += len(blocks)
        warnings_total += sum(1 for block in blocks if block.quality_warnings)

        if checkpoint_every > 0 and pages_processed % checkpoint_every == 0:
            ProjectCache.save(cache_path, project)
            _write_progress(
                progress_path,
                {
                    "pages_total": len(entries),
                    "pages_processed": pages_processed,
                    "pages_skipped": pages_skipped,
                    "last_page_index": local_index,
                    "last_image_path": str(entry.image_path),
                    "elapsed_seconds": round(time.monotonic() - started, 3),
                },
            )

    ProjectCache.save(cache_path, project)
    exported = export_review_dataset(project, analysis_dir)
    elapsed = time.monotonic() - started
    _write_progress(
        progress_path,
        {
            "pages_total": len(entries),
            "pages_processed": pages_processed,
            "pages_skipped": pages_skipped,
            "blocks_total": blocks_total,
            "warnings_total": warnings_total,
            "elapsed_seconds": round(elapsed, 3),
            "cache_path": str(cache_path),
            "analysis_dir": str(analysis_dir),
        },
    )

    return CorpusProcessResult(
        pages_total=len(entries),
        pages_processed=pages_processed,
        pages_skipped=pages_skipped,
        blocks_total=blocks_total,
        warnings_total=warnings_total,
        cache_path=cache_path,
        analysis_dir=analysis_dir,
        review_csv=exported["csv"],
        review_jsonl=exported["jsonl"],
        quality_report=exported["quality_report"],
        elapsed_seconds=elapsed,
    )
