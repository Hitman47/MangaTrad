from __future__ import annotations

import re
from collections import deque
from dataclasses import dataclass
from pathlib import Path

from cbz_manga_translator.core.models import OcrBlock

_TERMINAL_RE = re.compile(r"[.!?][\"')\]]?$")


@dataclass(slots=True)
class PunctuationHint:
    mark: str
    confidence: float
    reason: str


@dataclass(slots=True)
class _Component:
    x1: int
    y1: int
    x2: int
    y2: int
    area: int

    @property
    def width(self) -> int:
        return self.x2 - self.x1 + 1

    @property
    def height(self) -> int:
        return self.y2 - self.y1 + 1

    @property
    def cx(self) -> float:
        return (self.x1 + self.x2) / 2

    @property
    def cy(self) -> float:
        return (self.y1 + self.y2) / 2


def _dark_components(image_path: str | Path, bbox: list[int]) -> list[_Component]:
    try:
        from PIL import Image, ImageOps
    except Exception:
        return []
    try:
        image = Image.open(image_path).convert("L")
        x1, y1, x2, y2 = [int(value) for value in bbox]
        crop = image.crop((max(0, x1), max(0, y1), max(x1 + 1, x2), max(y1 + 1, y2)))
        crop = ImageOps.autocontrast(crop)
    except Exception:
        return []

    width, height = crop.size
    if width < 8 or height < 8:
        return []
    pixels = crop.load()
    dark = {
        (x, y)
        for y in range(height)
        for x in range(width)
        if int(pixels[x, y]) < 95
    }
    components: list[_Component] = []
    while dark:
        start = dark.pop()
        queue: deque[tuple[int, int]] = deque([start])
        xs = [start[0]]
        ys = [start[1]]
        area = 1
        while queue:
            x, y = queue.popleft()
            for nx in (x - 1, x, x + 1):
                for ny in (y - 1, y, y + 1):
                    if (nx, ny) not in dark:
                        continue
                    dark.remove((nx, ny))
                    queue.append((nx, ny))
                    xs.append(nx)
                    ys.append(ny)
                    area += 1
        components.append(_Component(min(xs), min(ys), max(xs), max(ys), area))
    return components


def detect_visual_punctuation_hints(image_path: str | Path, block: OcrBlock) -> list[PunctuationHint]:
    components = _dark_components(image_path, block.bbox)
    if not components:
        return []

    x1, y1, x2, y2 = block.bbox
    width = max(1, int(x2) - int(x1))
    height = max(1, int(y2) - int(y1))
    dot_max = max(5, int(min(width, height) * 0.12))
    dot_components = [
        comp for comp in components
        if 2 <= comp.area <= dot_max * dot_max
        and comp.width <= dot_max
        and comp.height <= dot_max
        and comp.y1 >= height * 0.35
    ]
    hints: list[PunctuationHint] = []

    for y_band in dot_components:
        aligned = [
            comp for comp in dot_components
            if abs(comp.cy - y_band.cy) <= max(3, dot_max * 0.65)
        ]
        aligned = sorted(aligned, key=lambda comp: comp.cx)
        if len(aligned) >= 3:
            span = aligned[-1].cx - aligned[0].cx
            if span >= dot_max * 1.8:
                hints.append(PunctuationHint("...", 0.72, "trois petits points detectes dans le crop"))
                break

    verticals = [
        comp for comp in components
        if comp.height >= max(8, comp.width * 2.8)
        and comp.area <= max(30, width * height * 0.08)
    ]
    for vertical in verticals:
        below = [
            dot for dot in dot_components
            if dot.cy > vertical.y2 and abs(dot.cx - vertical.cx) <= max(4, vertical.width * 1.5)
        ]
        if below:
            hints.append(PunctuationHint("!", 0.70, "trait vertical et point detectes dans le crop"))
            break

    deduped: dict[str, PunctuationHint] = {}
    for hint in hints:
        current = deduped.get(hint.mark)
        if current is None or hint.confidence > current.confidence:
            deduped[hint.mark] = hint
    return sorted(deduped.values(), key=lambda item: item.confidence, reverse=True)


def apply_punctuation_hints(text: str, hints: list[PunctuationHint]) -> str:
    value = " ".join(str(text).strip().split())
    if not value:
        return value
    marks = {hint.mark for hint in hints if hint.confidence >= 0.60}
    if "..." in marks and "..." not in value:
        if value.endswith((".", ":", ",")):
            value = value.rstrip(".:,") + "..."
        elif not _TERMINAL_RE.search(value):
            value = f"{value}..."
    if "!" in marks and "!" not in value and "?" not in value:
        if value.endswith("..."):
            value = f"{value}!"
        elif value.endswith((".", ":", ",")):
            value = value.rstrip(".:,") + "!"
        elif not _TERMINAL_RE.search(value):
            value = f"{value}!"
    return value
