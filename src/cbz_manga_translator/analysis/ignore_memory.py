from __future__ import annotations

import json
import os
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Iterable

from cbz_manga_translator.core.cache import ProjectCache
from cbz_manga_translator.core.models import OcrBlock


def canonical_ignore_key(text: str) -> str:
    compact = " ".join(str(text).replace("\u2019", "'").strip().lower().split())
    compact = compact.strip("\"'`\u00b4\u2018\u2019\u201c\u201d ")
    compact = re.sub(r"\s+([,.;:!?])", r"\1", compact)
    compact = re.sub(r"\s+", " ", compact)
    return compact


@dataclass(slots=True)
class IgnoreMemory:
    entries: dict[str, str]

    def lookup(self, text: str) -> str:
        return self.entries.get(canonical_ignore_key(text), "")


def _default_memory_candidates() -> list[Path]:
    candidates: list[Path] = []
    env_path = os.environ.get("MANGATRAD_IGNORE_MEMORY", "").strip()
    if env_path:
        candidates.append(Path(env_path))
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return candidates
    candidates.append(Path.cwd() / "mangatrad_ignore_memory.json")
    candidates.append(Path("C:/temp/mangatrad_ignore_memory.json"))
    return candidates


@lru_cache(maxsize=8)
def load_ignore_memory(path: str) -> IgnoreMemory:
    memory_path = Path(path)
    if not memory_path.exists():
        return IgnoreMemory(entries={})
    data = json.loads(memory_path.read_text(encoding="utf-8"))
    raw_entries = data.get("entries", {})
    if not isinstance(raw_entries, dict):
        return IgnoreMemory(entries={})
    entries = {
        canonical_ignore_key(key): str(value).strip()
        for key, value in raw_entries.items()
        if str(key).strip() and str(value).strip()
    }
    return IgnoreMemory(entries=entries)


def clear_ignore_memory_cache() -> None:
    load_ignore_memory.cache_clear()
    default_ignore_memory.cache_clear()


@lru_cache(maxsize=1)
def default_ignore_memory() -> IgnoreMemory:
    for candidate in _default_memory_candidates():
        if candidate.exists():
            return load_ignore_memory(str(candidate.resolve()))
    return IgnoreMemory(entries={})


def _block_sources(block: OcrBlock) -> set[str]:
    return {
        item.strip()
        for item in (block.ocr_text, block.ocr_corrected_text, block.normalized_source_text)
        if item and item.strip()
    }


def _reason_from_note(note: str) -> str:
    lowered = note.strip().lower()
    if "sfx" in lowered or "onomatop" in lowered:
        return "ignore appris: sfx/bruit"
    if "fusion" in lowered:
        return "ignore appris: fusion/non-dialogue"
    return "ignore appris"


def build_ignore_memory(
    project_paths: Iterable[str | Path],
    *,
    min_source_chars: int = 2,
) -> tuple[IgnoreMemory, dict[str, object]]:
    buckets: dict[str, Counter[str]] = defaultdict(Counter)
    examples: dict[str, str] = {}
    scanned_blocks = 0
    eligible_blocks = 0

    for project_path in project_paths:
        project = ProjectCache.load(project_path)
        for page in project.pages:
            for block in page.blocks:
                scanned_blocks += 1
                if block.manual_status != "ignored":
                    continue
                keys = {canonical_ignore_key(source) for source in _block_sources(block)}
                keys = {key for key in keys if len(key) >= min_source_chars}
                if not keys:
                    continue
                reason = _reason_from_note(block.review_notes)
                eligible_blocks += 1
                for key in keys:
                    buckets[key][reason] += 1
                    examples.setdefault(key, block.ocr_text.strip())

    entries: dict[str, str] = {}
    conflicts: dict[str, dict[str, int]] = {}
    for key, counter in buckets.items():
        winner, _count = counter.most_common(1)[0]
        entries[key] = winner
        if len(counter) > 1:
            conflicts[examples.get(key, key)] = dict(counter)

    metadata: dict[str, object] = {
        "projects": [str(Path(path)) for path in project_paths],
        "scanned_blocks": scanned_blocks,
        "eligible_blocks": eligible_blocks,
        "entries": len(entries),
        "conflicts": conflicts,
    }
    return IgnoreMemory(entries=entries), metadata


def write_ignore_memory(memory: IgnoreMemory, metadata: dict[str, object], output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "metadata": metadata,
        "entries": dict(sorted(memory.entries.items())),
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    clear_ignore_memory_cache()
    return path
