from __future__ import annotations

import zipfile
from pathlib import Path

from cbz_manga_translator.core.cbz_reader import CbzReader, natural_sort_key


def test_natural_sort_key_orders_pages() -> None:
    names = ["10.jpg", "2.jpg", "001.jpg", "page 3.png"]
    assert sorted(names, key=natural_sort_key) == ["001.jpg", "2.jpg", "10.jpg", "page 3.png"]


def test_cbz_reader_lists_supported_images(tmp_path: Path) -> None:
    cbz = tmp_path / "sample.cbz"
    with zipfile.ZipFile(cbz, "w") as archive:
        archive.writestr("10.jpg", b"x")
        archive.writestr("2.png", b"y")
        archive.writestr("notes.txt", b"ignore")
        archive.writestr("folder/1.webp", b"z")
    reader = CbzReader(cbz)
    assert reader.image_names() == ["2.png", "10.jpg", "folder/1.webp"]
    assert reader.read_image_bytes("2.png") == b"y"
