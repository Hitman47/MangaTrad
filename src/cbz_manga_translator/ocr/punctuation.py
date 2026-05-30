from __future__ import annotations

import re
from collections import deque
from dataclasses import dataclass
from pathlib import Path

from cbz_manga_translator.core.models import OcrBlock

_TERMINAL_RE = re.compile(r"[.!?][\"')\]]?$")
_QUESTION_START_RE = re.compile(
    r"^\s*(?:what|why|how|where|when|who|is|are|do|did|does|can|could|would|should|will)\b",
    flags=re.IGNORECASE,
)
_EDGE_WARNING = "OCR zone visuelle: texte touche le bord du crop, bbox probablement trop petite"


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


def _dark_components_from_crop(crop: object) -> list[_Component]:
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


def _crop_grayscale(image: object, bbox: list[int]) -> object:
    from PIL import ImageOps

    x1, y1, x2, y2 = [int(value) for value in bbox]
    crop = image.crop((max(0, x1), max(0, y1), max(x1 + 1, x2), max(y1 + 1, y2)))
    return ImageOps.autocontrast(crop)


def _dark_components(image_path: str | Path, bbox: list[int]) -> list[_Component]:
    try:
        from PIL import Image
    except Exception:
        return []
    try:
        image = Image.open(image_path).convert("L")
        crop = _crop_grayscale(image, bbox)
    except Exception:
        return []
    return _dark_components_from_crop(crop)


def _detect_hints_from_components(components: list[_Component], width: int, height: int) -> list[PunctuationHint]:
    if not components:
        return []
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

    for dot in dot_components:
        hooks = [
            comp for comp in components
            if comp.cy < dot.cy
            and comp.area > dot.area * 2.2
            and comp.width >= max(5, dot.width * 1.5)
            and comp.height >= max(6, dot.height * 1.6)
            and abs(comp.cx - dot.cx) <= max(12, comp.width * 0.9)
            and not (comp.height >= max(8, comp.width * 2.8) and comp.width <= max(5, dot.width * 1.5))
        ]
        if hooks:
            hints.append(PunctuationHint("?", 0.68, "courbe et point detectes dans le crop"))
            break

    deduped: dict[str, PunctuationHint] = {}
    for hint in hints:
        current = deduped.get(hint.mark)
        if current is None or hint.confidence > current.confidence:
            deduped[hint.mark] = hint
    return sorted(deduped.values(), key=lambda item: item.confidence, reverse=True)


def infer_textual_punctuation_hints(text: str) -> list[PunctuationHint]:
    value = " ".join(str(text).strip().split())
    if not value:
        return []
    if _QUESTION_START_RE.search(value) and "?" not in value and not _TERMINAL_RE.search(value):
        return [PunctuationHint("?", 0.61, "forme interrogative anglaise sans ponctuation")]
    return []


def _zone_warnings_from_components(components: list[_Component], width: int, height: int) -> list[str]:
    if not components:
        return []
    edge = max(2, int(min(width, height) * 0.05))
    for comp in components:
        if comp.area < 3:
            continue
        if comp.x1 <= edge or comp.y1 <= edge or comp.x2 >= width - 1 - edge or comp.y2 >= height - 1 - edge:
            return [_EDGE_WARNING]
    return []


def detect_visual_punctuation_hints(image_path: str | Path, block: OcrBlock) -> list[PunctuationHint]:
    components = _dark_components(image_path, block.bbox)
    x1, y1, x2, y2 = block.bbox
    width = max(1, int(x2) - int(x1))
    height = max(1, int(y2) - int(y1))
    return _detect_hints_from_components(components, width, height)


def apply_punctuation_hints(text: str, hints: list[PunctuationHint]) -> str:
    value = " ".join(str(text).strip().split())
    if not value:
        return value
    marks = {hint.mark for hint in hints if hint.confidence >= 0.60}
    if "?" in marks and "?" not in value and "!" not in value:
        if value.endswith("..."):
            value = f"{value}?"
        elif value.endswith((".", ":", ",")):
            value = value.rstrip(".:,") + "?"
        elif not _TERMINAL_RE.search(value):
            value = f"{value}?"
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


def visual_zone_warnings_for_block(image_path: str | Path, block: OcrBlock) -> list[str]:
    try:
        from PIL import Image
    except Exception:
        return []
    try:
        image = Image.open(image_path).convert("L")
        crop = _crop_grayscale(image, block.bbox)
    except Exception:
        return []
    components = _dark_components_from_crop(crop)
    width, height = crop.size
    return _zone_warnings_from_components(components, width, height)


def apply_visual_punctuation_to_blocks(image_path: str | Path, blocks: list[OcrBlock]) -> int:
    try:
        from PIL import Image
    except Exception:
        return 0
    try:
        image = Image.open(image_path).convert("L")
    except Exception:
        return 0

    changed = 0
    for block in blocks:
        try:
            crop = _crop_grayscale(image, block.bbox)
        except Exception:
            continue
        components = _dark_components_from_crop(crop)
        width, height = crop.size
        hints = _detect_hints_from_components(components, width, height)
        hints.extend(infer_textual_punctuation_hints(block.ocr_text))
        updated = apply_punctuation_hints(block.ocr_text, hints)
        if updated and updated != block.ocr_text:
            block.ocr_text = updated
            note = "OCR ponctuation visuelle ajoutee: " + ", ".join(hint.mark for hint in hints)
            if note not in block.quality_warnings:
                block.quality_warnings.append(note)
            changed += 1
        for warning in _zone_warnings_from_components(components, width, height):
            if warning not in block.quality_warnings:
                block.quality_warnings.append(warning)
    return changed
