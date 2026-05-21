from __future__ import annotations

import json
from pathlib import Path

from cbz_manga_translator.core.models import ProjectData


class ProjectCache:
    @staticmethod
    def default_path(cbz_path: str | Path) -> Path:
        path = Path(cbz_path)
        return path.with_suffix(path.suffix + ".manga_translate_project.json")

    @staticmethod
    def load(path: str | Path) -> ProjectData:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return ProjectData.from_dict(data)

    @staticmethod
    def save(path: str | Path, project: ProjectData) -> None:
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(project.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @staticmethod
    def load_or_create(cbz_path: str | Path, image_names: list[str]) -> ProjectData:
        cache_path = ProjectCache.default_path(cbz_path)
        if cache_path.exists():
            project = ProjectCache.load(cache_path)
            cached_names = [page.image_name for page in project.pages]
            if cached_names == image_names:
                project.cbz_path = str(cbz_path)
                return project
        return ProjectData.from_images(cbz_path, image_names)
