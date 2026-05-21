from __future__ import annotations

import csv
import hashlib
import json
import random
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Literal

from cbz_manga_translator.core.cbz_reader import CbzReader

SamplingMode = Literal["stratified", "random", "mixed"]
SeriesSamplingMode = Literal["mixed", "first", "last", "random"]
SUPPORTED_VOLUME_EXTENSIONS = (".cbz", ".zip")


@dataclass(frozen=True)
class VolumeSource:
    index: int
    path: Path
    parent: Path
    label: str
    series_index: int
    series_path: Path
    series_label: str
    series_volume_number: int
    series_volume_count: int


@dataclass(frozen=True)
class SeriesGroup:
    index: int
    path: Path
    label: str
    volumes: tuple[Path, ...]


@dataclass(frozen=True)
class SampledPage:
    volume_index: int
    volume_label: str
    source_path: Path
    source_parent: Path
    source_page_index: int
    source_page_number: int
    source_image_name: str
    page_count: int
    output_path: Path
    output_relpath: str
    output_sha256: str
    sampling_mode: str
    seed: int
    series_index: int
    series_label: str
    series_path: Path
    series_volume_number: int
    series_volume_count: int


@dataclass(frozen=True)
class CorpusSamplingResult:
    output_dir: Path
    pages_dir: Path
    manifest_csv: Path
    manifest_jsonl: Path
    report_md: Path
    volumes_total: int
    volumes_processed: int
    pages_total: int
    warnings: tuple[str, ...]
    series_total: int = 0


def read_volume_list(list_path: str | Path) -> list[Path]:
    """Read one archive or folder path per line. Empty lines and # comments are ignored."""
    source = Path(list_path)
    base_dir = source.parent
    paths: list[Path] = []
    for raw_line in source.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith('"') and line.endswith('"') and len(line) >= 2:
            line = line[1:-1]
        if line.startswith("'") and line.endswith("'") and len(line) >= 2:
            line = line[1:-1]
        path = Path(line)
        if not path.is_absolute():
            path = base_dir / path
        paths.append(path)
    return paths


def safe_slug(value: str, max_length: int = 80) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip())
    cleaned = re.sub(r"_+", "_", cleaned).strip("._-")
    if not cleaned:
        cleaned = "volume"
    return cleaned[:max_length].rstrip("._-") or "volume"


def short_path_hash(path: Path, length: int = 10) -> str:
    normalized = str(path).replace("\\", "/").lower().encode("utf-8", errors="replace")
    return hashlib.sha1(normalized).hexdigest()[:length]


def _is_supported_volume(path: Path, extensions: Iterable[str] = SUPPORTED_VOLUME_EXTENSIONS) -> bool:
    return path.is_file() and path.suffix.lower() in {ext.lower() for ext in extensions}


def _natural_key(path: Path) -> list[object]:
    parts = re.split(r"(\d+)", path.name.lower())
    return [int(part) if part.isdigit() else part for part in parts]


def _find_archives_in_directory(
    directory: Path,
    *,
    recursive: bool,
    extensions: Iterable[str] = SUPPORTED_VOLUME_EXTENSIONS,
) -> list[Path]:
    patterns = [f"*{ext}" for ext in extensions]
    found: list[Path] = []
    for pattern in patterns:
        iterator = directory.rglob(pattern) if recursive else directory.glob(pattern)
        found.extend(path for path in iterator if path.is_file())
    return sorted(set(found), key=_natural_key)


def discover_series_groups(
    input_paths: Iterable[str | Path],
    *,
    recursive: bool = False,
    extensions: Iterable[str] = SUPPORTED_VOLUME_EXTENSIONS,
) -> tuple[list[SeriesGroup], tuple[str, ...]]:
    """Expand mixed file/folder inputs into series groups.

    A listed archive belongs to the series represented by its parent folder.
    A listed folder is treated as one series if it directly contains archives.
    With recursive=True, if a listed folder does not directly contain archives, each child folder containing archives
    becomes its own series.
    """
    warnings: list[str] = []
    grouped: dict[str, tuple[Path, list[Path]]] = {}

    def add_series(series_path: Path, volumes: Iterable[Path]) -> None:
        resolved_series = series_path.expanduser().resolve()
        resolved_volumes = sorted({volume.expanduser().resolve() for volume in volumes}, key=_natural_key)
        if not resolved_volumes:
            return
        key = str(resolved_series).lower()
        if key not in grouped:
            grouped[key] = (resolved_series, [])
        grouped[key][1].extend(resolved_volumes)

    for raw_path in input_paths:
        path = Path(raw_path).expanduser().resolve()
        if path.is_file():
            if _is_supported_volume(path, extensions):
                add_series(path.parent, [path])
            else:
                warnings.append(f"Fichier ignoré, extension non supportée: {path}")
            continue

        if path.is_dir():
            direct_archives = _find_archives_in_directory(path, recursive=False, extensions=extensions)
            if direct_archives:
                add_series(path, direct_archives)
                continue

            if recursive:
                recursive_archives = _find_archives_in_directory(path, recursive=True, extensions=extensions)
                if not recursive_archives:
                    warnings.append(f"Dossier sans CBZ/ZIP, ignoré: {path}")
                    continue
                by_parent: dict[Path, list[Path]] = {}
                for archive in recursive_archives:
                    by_parent.setdefault(archive.parent, []).append(archive)
                for parent, volumes in sorted(by_parent.items(), key=lambda item: str(item[0]).lower()):
                    add_series(parent, volumes)
                continue

            warnings.append(f"Dossier sans CBZ/ZIP direct, ignoré: {path} | ajoute --recursive si les tomes sont dans des sous-dossiers")
            continue

        warnings.append(f"Chemin introuvable, ignoré: {path}")

    series_groups: list[SeriesGroup] = []
    for index, (_key, (series_path, volumes)) in enumerate(
        sorted(grouped.items(), key=lambda item: str(item[1][0]).lower()),
        start=1,
    ):
        unique_volumes = tuple(sorted(set(volumes), key=_natural_key))
        label = f"{index:03d}_{safe_slug(series_path.name)}_{short_path_hash(series_path)}"
        series_groups.append(SeriesGroup(index=index, path=series_path, label=label, volumes=unique_volumes))
    return series_groups, tuple(warnings)


def select_volumes_from_series(
    groups: Iterable[SeriesGroup],
    *,
    volumes_per_series: int = 2,
    seed: int = 47,
    mode: SeriesSamplingMode = "mixed",
) -> list[VolumeSource]:
    if volumes_per_series <= 0:
        return []
    sources: list[VolumeSource] = []
    global_index = 1
    for group in groups:
        volumes = list(group.volumes)
        selected = _choose_volumes(volumes, volumes_per_series, seed=seed, series_index=group.index, mode=mode)
        for series_volume_number, volume in enumerate(selected, start=1):
            label = f"{global_index:003d}_{safe_slug(group.path.name)}_{safe_slug(volume.stem)}_{short_path_hash(volume)}"
            sources.append(
                VolumeSource(
                    index=global_index,
                    path=volume,
                    parent=volume.parent,
                    label=label,
                    series_index=group.index,
                    series_path=group.path,
                    series_label=group.label,
                    series_volume_number=series_volume_number,
                    series_volume_count=len(selected),
                )
            )
            global_index += 1
    return sources


def _choose_volumes(
    volumes: list[Path],
    count: int,
    *,
    seed: int,
    series_index: int,
    mode: SeriesSamplingMode,
) -> list[Path]:
    volumes = sorted(volumes, key=_natural_key)
    if count >= len(volumes):
        return volumes
    rng = random.Random(f"volumes:{seed}:{series_index}:{len(volumes)}:{count}:{mode}")
    if mode == "first":
        return volumes[:count]
    if mode == "last":
        return volumes[-count:]
    if mode == "random":
        return sorted(rng.sample(volumes, count), key=_natural_key)
    if mode == "mixed":
        if count == 1:
            return [volumes[rng.randrange(len(volumes))]]
        selected = {volumes[0], volumes[-1]}
        remaining = [volume for volume in volumes if volume not in selected]
        needed = count - len(selected)
        if needed > 0:
            selected.update(rng.sample(remaining, min(needed, len(remaining))))
        return sorted(selected, key=_natural_key)[:count]
    raise ValueError(f"Unsupported series sampling mode: {mode}")


def build_volume_sources(paths: Iterable[str | Path]) -> list[VolumeSource]:
    groups, _warnings = discover_series_groups(paths, recursive=False)
    return select_volumes_from_series(groups, volumes_per_series=10_000)


def find_duplicate_parents(sources: Iterable[VolumeSource]) -> dict[str, list[Path]]:
    by_parent: dict[str, list[Path]] = {}
    for source in sources:
        key = str(source.parent).lower()
        by_parent.setdefault(key, []).append(source.path)
    return {parent: paths for parent, paths in by_parent.items() if len(paths) > 1}


def choose_page_indices(
    page_count: int,
    pages_per_volume: int,
    *,
    seed: int,
    volume_index: int,
    mode: SamplingMode = "mixed",
    skip_first: int = 2,
    skip_last: int = 1,
) -> list[int]:
    """Choose 0-based page indices.

    Defaults avoid covers/front matter and the last page, then sample across the whole book.
    """
    if page_count <= 0 or pages_per_volume <= 0:
        return []

    start = min(max(skip_first, 0), page_count)
    end_exclusive = max(start, page_count - max(skip_last, 0))
    candidates = list(range(start, end_exclusive)) or list(range(page_count))

    if pages_per_volume >= len(candidates):
        return candidates

    rng = random.Random(f"{seed}:{volume_index}:{page_count}:{pages_per_volume}:{mode}")

    if mode == "random":
        return sorted(rng.sample(candidates, pages_per_volume))

    if mode == "stratified":
        return _choose_stratified(candidates, pages_per_volume, rng)

    if mode == "mixed":
        # Mostly stratified, with a few random replacements to avoid always taking
        # the exact same page positions across similar volumes.
        stratified_count = max(1, round(pages_per_volume * 0.75))
        selected = set(_choose_stratified(candidates, stratified_count, rng))
        remaining = [idx for idx in candidates if idx not in selected]
        random_count = pages_per_volume - len(selected)
        if random_count > 0:
            selected.update(rng.sample(remaining, min(random_count, len(remaining))))
        while len(selected) < pages_per_volume:
            selected.add(rng.choice(candidates))
        return sorted(selected)[:pages_per_volume]

    raise ValueError(f"Unsupported sampling mode: {mode}")


def _choose_stratified(candidates: list[int], count: int, rng: random.Random) -> list[int]:
    if count >= len(candidates):
        return list(candidates)
    selected: list[int] = []
    total = len(candidates)
    for bucket in range(count):
        left = round(bucket * total / count)
        right = round((bucket + 1) * total / count)
        bucket_values = candidates[left:right] or [candidates[min(left, total - 1)]]
        mid = len(bucket_values) // 2
        # Small jitter inside the bucket keeps the corpus varied while staying balanced.
        jittered = min(max(mid + rng.choice([-1, 0, 1]), 0), len(bucket_values) - 1)
        selected.append(bucket_values[jittered])
    return sorted(set(selected))


def sample_corpus(
    volume_paths: Iterable[str | Path],
    output_dir: str | Path,
    *,
    pages_per_volume: int = 25,
    volumes_per_series: int = 2,
    seed: int = 47,
    mode: SamplingMode = "mixed",
    series_mode: SeriesSamplingMode = "mixed",
    skip_first: int = 2,
    skip_last: int = 1,
    recursive: bool = False,
    require_distinct_parent: bool = False,
    overwrite: bool = False,
) -> CorpusSamplingResult:
    output = Path(output_dir).resolve()
    pages_dir = output / "pages"
    manifest_csv = output / "manifest.csv"
    manifest_jsonl = output / "manifest.jsonl"
    report_md = output / "sample_report.md"

    if output.exists() and overwrite:
        shutil.rmtree(output)
    output.mkdir(parents=True, exist_ok=True)
    pages_dir.mkdir(parents=True, exist_ok=True)

    series_groups, discovery_warnings = discover_series_groups(volume_paths, recursive=recursive)
    sources = select_volumes_from_series(
        series_groups,
        volumes_per_series=volumes_per_series,
        seed=seed,
        mode=series_mode,
    )
    warnings: list[str] = list(discovery_warnings)

    duplicate_parents = find_duplicate_parents(sources)
    if duplicate_parents and require_distinct_parent:
        details = "; ".join(f"{parent}: {len(paths)} fichiers" for parent, paths in duplicate_parents.items())
        raise ValueError(
            "Plusieurs tomes sélectionnés proviennent du même dossier. "
            "C'est normal quand tu prends plusieurs tomes par série ; retire --require-distinct-parent "
            "ou mets --volumes-per-series 1. "
            f"Détails: {details}"
        )

    sampled_pages: list[SampledPage] = []
    processed = 0

    for source in sources:
        if not source.path.exists():
            warnings.append(f"Introuvable, ignoré: {source.path}")
            continue
        try:
            reader = CbzReader(source.path)
            image_names = reader.image_names()
        except Exception as exc:  # noqa: BLE001 - report bad archives without stopping the batch.
            warnings.append(f"Archive illisible, ignorée: {source.path} | {type(exc).__name__}: {exc}")
            continue

        processed += 1
        indices = choose_page_indices(
            len(image_names),
            pages_per_volume,
            seed=seed,
            volume_index=source.index,
            mode=mode,
            skip_first=skip_first,
            skip_last=skip_last,
        )
        volume_output_dir = pages_dir / source.series_label / source.label
        volume_output_dir.mkdir(parents=True, exist_ok=True)

        for sample_number, page_index in enumerate(indices, start=1):
            image_name = image_names[page_index]
            suffix = Path(image_name).suffix.lower() or ".img"
            output_name = f"sample_{sample_number:03d}__page_{page_index + 1:04d}{suffix}"
            output_path = volume_output_dir / output_name
            data = reader.read_image_bytes(image_name)
            output_path.write_bytes(data)
            sampled_pages.append(
                SampledPage(
                    volume_index=source.index,
                    volume_label=source.label,
                    source_path=source.path,
                    source_parent=source.parent,
                    source_page_index=page_index,
                    source_page_number=page_index + 1,
                    source_image_name=image_name,
                    page_count=len(image_names),
                    output_path=output_path,
                    output_relpath=output_path.relative_to(output).as_posix(),
                    output_sha256=hashlib.sha256(data).hexdigest(),
                    sampling_mode=mode,
                    seed=seed,
                    series_index=source.series_index,
                    series_label=source.series_label,
                    series_path=source.series_path,
                    series_volume_number=source.series_volume_number,
                    series_volume_count=source.series_volume_count,
                )
            )

    _write_manifest_csv(manifest_csv, sampled_pages)
    _write_manifest_jsonl(manifest_jsonl, sampled_pages)
    _write_report(
        report_md,
        series_groups=series_groups,
        sources=sources,
        sampled_pages=sampled_pages,
        warnings=warnings,
        pages_per_volume=pages_per_volume,
        volumes_per_series=volumes_per_series,
        seed=seed,
        mode=mode,
        series_mode=series_mode,
        skip_first=skip_first,
        skip_last=skip_last,
        recursive=recursive,
    )

    return CorpusSamplingResult(
        output_dir=output,
        pages_dir=pages_dir,
        manifest_csv=manifest_csv,
        manifest_jsonl=manifest_jsonl,
        report_md=report_md,
        volumes_total=len(sources),
        volumes_processed=processed,
        pages_total=len(sampled_pages),
        warnings=tuple(warnings),
        series_total=len(series_groups),
    )


def _write_manifest_csv(path: Path, pages: list[SampledPage]) -> None:
    fields = [
        "series_index",
        "series_label",
        "series_path",
        "series_volume_number",
        "series_volume_count",
        "volume_index",
        "volume_label",
        "source_path",
        "source_parent",
        "page_count",
        "source_page_number",
        "source_page_index",
        "source_image_name",
        "output_relpath",
        "output_sha256",
        "sampling_mode",
        "seed",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for page in pages:
            writer.writerow(_page_to_dict(page))


def _write_manifest_jsonl(path: Path, pages: list[SampledPage]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for page in pages:
            handle.write(json.dumps(_page_to_dict(page), ensure_ascii=False) + "\n")


def _page_to_dict(page: SampledPage) -> dict[str, object]:
    return {
        "series_index": page.series_index,
        "series_label": page.series_label,
        "series_path": str(page.series_path),
        "series_volume_number": page.series_volume_number,
        "series_volume_count": page.series_volume_count,
        "volume_index": page.volume_index,
        "volume_label": page.volume_label,
        "source_path": str(page.source_path),
        "source_parent": str(page.source_parent),
        "page_count": page.page_count,
        "source_page_number": page.source_page_number,
        "source_page_index": page.source_page_index,
        "source_image_name": page.source_image_name,
        "output_relpath": page.output_relpath,
        "output_sha256": page.output_sha256,
        "sampling_mode": page.sampling_mode,
        "seed": page.seed,
    }


def _write_report(
    path: Path,
    *,
    series_groups: list[SeriesGroup],
    sources: list[VolumeSource],
    sampled_pages: list[SampledPage],
    warnings: list[str],
    pages_per_volume: int,
    volumes_per_series: int,
    seed: int,
    mode: str,
    series_mode: str,
    skip_first: int,
    skip_last: int,
    recursive: bool,
) -> None:
    lines = [
        "# Rapport d'échantillonnage MangaTrad",
        "",
        f"- Séries détectées : {len(series_groups)}",
        f"- Tomes sélectionnés : {len(sources)}",
        f"- Pages extraites : {len(sampled_pages)}",
        f"- Tomes demandés par série : {volumes_per_series}",
        f"- Pages demandées par tome : {pages_per_volume}",
        f"- Mode pages : `{mode}`",
        f"- Mode tomes/série : `{series_mode}`",
        f"- Seed : `{seed}`",
        f"- Recherche récursive dossiers : `{recursive}`",
        f"- Pages ignorées au début : {skip_first}",
        f"- Pages ignorées à la fin : {skip_last}",
        "",
    ]
    if warnings:
        lines.extend(["## Avertissements", ""])
        lines.extend(f"- {warning}" for warning in warnings)
        lines.append("")

    lines.extend(["## Séries et tomes", ""])
    pages_by_volume: dict[int, int] = {}
    for page in sampled_pages:
        pages_by_volume[page.volume_index] = pages_by_volume.get(page.volume_index, 0) + 1
    sources_by_series: dict[int, list[VolumeSource]] = {}
    for source in sources:
        sources_by_series.setdefault(source.series_index, []).append(source)
    for group in series_groups:
        selected = sources_by_series.get(group.index, [])
        lines.append(f"- `{group.label}` — {len(selected)}/{len(group.volumes)} tomes sélectionnés — `{group.path}`")
        for source in selected:
            lines.append(f"  - `{source.label}` — {pages_by_volume.get(source.index, 0)} pages — `{source.path}`")
    lines.append("")
    lines.extend([
        "## Fichiers générés",
        "",
        "- `pages/` : images extraites, regroupées par série puis par tome.",
        "- `manifest.csv` : manifeste exploitable dans Excel/LibreOffice/Pandas.",
        "- `manifest.jsonl` : manifeste ligne par ligne pour scripts d'analyse.",
        "- `sample_report.md` : ce rapport.",
        "",
        "## Utilisation conseillée",
        "",
        "1. Donne une liste de dossiers de séries ou de fichiers CBZ/ZIP.",
        "2. Sélectionne 1–3 tomes par série avec `--volumes-per-series`.",
        "3. Extrait 20–30 pages par tome avec `--pages-per-volume`.",
        "4. Utilise ensuite ce corpus pour tester OCR/traduction par lots.",
        "5. Exporte les résultats MangaTrad avec `Exporter analyse`.",
        "6. Construis les règles OCR, glossaire et quality check à partir des erreurs répétées.",
    ])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
