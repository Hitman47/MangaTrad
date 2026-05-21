from __future__ import annotations

import csv
import zipfile
from pathlib import Path

import pytest

from cbz_manga_translator.analysis.corpus_sampler import (
    choose_page_indices,
    discover_series_groups,
    read_volume_list,
    sample_corpus,
    select_volumes_from_series,
)


def _make_fake_cbz(path: Path, count: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as archive:
        for index in range(1, count + 1):
            archive.writestr(f"page_{index:03d}.jpg", f"fake image {index}".encode())


def test_choose_page_indices_is_deterministic_and_skips_edges() -> None:
    first = choose_page_indices(100, 10, seed=47, volume_index=1, mode="mixed", skip_first=2, skip_last=1)
    second = choose_page_indices(100, 10, seed=47, volume_index=1, mode="mixed", skip_first=2, skip_last=1)
    assert first == second
    assert len(first) == 10
    assert min(first) >= 2
    assert max(first) <= 98


def test_read_volume_list_supports_comments_and_relative_paths(tmp_path: Path) -> None:
    list_path = tmp_path / "volumes.txt"
    list_path.write_text("# comment\nA.cbz\n\n'B.cbz'\n", encoding="utf-8")
    paths = read_volume_list(list_path)
    assert paths == [tmp_path / "A.cbz", tmp_path / "B.cbz"]


def test_discover_series_groups_accepts_series_directories(tmp_path: Path) -> None:
    serie_a = tmp_path / "Serie A"
    serie_b = tmp_path / "Serie B"
    _make_fake_cbz(serie_a / "Tome 01.cbz", 10)
    _make_fake_cbz(serie_a / "Tome 02.cbz", 10)
    _make_fake_cbz(serie_b / "Tome 01.cbz", 10)

    groups, warnings = discover_series_groups([serie_a, serie_b])

    assert warnings == ()
    assert len(groups) == 2
    assert [len(group.volumes) for group in groups] == [2, 1]


def test_discover_series_groups_recursive_child_series(tmp_path: Path) -> None:
    root = tmp_path / "root"
    _make_fake_cbz(root / "A" / "Tome 01.cbz", 10)
    _make_fake_cbz(root / "B" / "Tome 01.cbz", 10)

    groups, warnings = discover_series_groups([root], recursive=True)

    assert warnings == ()
    assert len(groups) == 2
    assert {group.path.name for group in groups} == {"A", "B"}


def test_select_volumes_from_series_limits_each_series(tmp_path: Path) -> None:
    serie = tmp_path / "Serie"
    for index in range(1, 5):
        _make_fake_cbz(serie / f"Tome {index:02d}.cbz", 10)
    groups, _warnings = discover_series_groups([serie])

    sources = select_volumes_from_series(groups, volumes_per_series=2, seed=47, mode="mixed")

    assert len(sources) == 2
    assert all(source.series_volume_count == 2 for source in sources)
    assert all(source.series_path == serie.resolve() for source in sources)


def test_sample_corpus_writes_pages_and_manifests_from_series_folders(tmp_path: Path) -> None:
    serie_a = tmp_path / "A"
    serie_b = tmp_path / "B"
    _make_fake_cbz(serie_a / "vol1.cbz", 12)
    _make_fake_cbz(serie_a / "vol2.cbz", 12)
    _make_fake_cbz(serie_b / "vol1.cbz", 12)
    _make_fake_cbz(serie_b / "vol2.cbz", 12)

    result = sample_corpus(
        [serie_a, serie_b],
        tmp_path / "corpus",
        pages_per_volume=5,
        volumes_per_series=2,
        seed=47,
        mode="stratified",
    )

    assert result.series_total == 2
    assert result.volumes_processed == 4
    assert result.pages_total == 20
    assert result.manifest_csv.exists()
    assert result.manifest_jsonl.exists()
    assert result.report_md.exists()
    extracted = list(result.pages_dir.rglob("*.jpg"))
    assert len(extracted) == 20

    with result.manifest_csv.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 20
    assert "series_label" in rows[0]
    assert {row["series_volume_count"] for row in rows} == {"2"}


def test_sample_corpus_can_reject_duplicate_parent_in_legacy_strict_mode(tmp_path: Path) -> None:
    same = tmp_path / "same"
    _make_fake_cbz(same / "vol1.cbz", 5)
    _make_fake_cbz(same / "vol2.cbz", 5)

    with pytest.raises(ValueError, match="plusieurs tomes par série"):
        sample_corpus(
            [same],
            tmp_path / "corpus",
            volumes_per_series=2,
            require_distinct_parent=True,
        )
