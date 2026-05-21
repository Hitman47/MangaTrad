from __future__ import annotations

import re
import zipfile
from pathlib import Path

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".tif", ".tiff"}


def natural_sort_key(value: str) -> list[object]:
    """Sort filenames in human page order: 2.jpg before 10.jpg."""
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", value)]


class CbzReader:
    def __init__(self, cbz_path: str | Path) -> None:
        self.path = Path(cbz_path)
        if not self.path.exists():
            raise FileNotFoundError(f"CBZ not found: {self.path}")
        if not zipfile.is_zipfile(self.path):
            raise ValueError(f"File is not a valid CBZ/ZIP archive: {self.path}")
        self._image_names: list[str] | None = None

    def image_names(self) -> list[str]:
        if self._image_names is None:
            with zipfile.ZipFile(self.path) as archive:
                names = [
                    info.filename
                    for info in archive.infolist()
                    if not info.is_dir() and Path(info.filename).suffix.lower() in IMAGE_EXTENSIONS
                ]
            self._image_names = sorted(names, key=natural_sort_key)
        return list(self._image_names)

    def read_image_bytes(self, image_name: str) -> bytes:
        with zipfile.ZipFile(self.path) as archive:
            return archive.read(image_name)

    def extract_image(self, image_name: str, output_path: str | Path) -> Path:
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(self.read_image_bytes(image_name))
        return output
