from __future__ import annotations

import json
import os
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from difflib import SequenceMatcher
from functools import lru_cache
from pathlib import Path
from typing import Iterable

from cbz_manga_translator.core.cache import ProjectCache
from cbz_manga_translator.core.models import OcrBlock


def canonical_memory_key(text: str) -> str:
    compact = " ".join(str(text).replace("\u2019", "'").strip().lower().split())
    compact = compact.strip("\"'`\u00b4\u2018\u2019\u201c\u201d ")
    compact = re.sub(r"\s+([,.;:!?])", r"\1", compact)
    compact = re.sub(r"\s+", " ", compact)
    compact = re.sub(r"[:.]+$", "", compact)
    compact = re.sub(r"!+$", "!", compact)
    compact = re.sub(r"\?+$", "?", compact)
    return compact


def block_memory_source(block: OcrBlock) -> str:
    return (block.normalized_source_text or block.ocr_corrected_text or block.ocr_text).strip()


@dataclass(slots=True)
class TranslationMemory:
    entries: dict[str, str]

    def lookup(self, source: str) -> str:
        key = canonical_memory_key(source)
        exact = self.entries.get(key, "")
        if exact:
            return exact
        return self._lookup_fuzzy(key)

    def _lookup_fuzzy(self, key: str) -> str:
        if len(key) < 16 or len(self.entries) > 2000:
            return ""
        key_tokens = set(re.findall(r"[a-z0-9']+", key))
        if len(key_tokens) < 3:
            return ""
        best_value = ""
        best_score = 0.0
        for candidate, value in self.entries.items():
            if abs(len(candidate) - len(key)) > max(12, int(len(key) * 0.25)):
                continue
            candidate_tokens = set(re.findall(r"[a-z0-9']+", candidate))
            if not candidate_tokens:
                continue
            token_overlap = len(key_tokens & candidate_tokens) / max(len(key_tokens), len(candidate_tokens))
            if token_overlap < 0.72:
                continue
            score = SequenceMatcher(None, key, candidate).ratio()
            if score > best_score:
                best_score = score
                best_value = value
        return best_value if best_score >= 0.94 else ""


def _default_memory_candidates() -> list[Path]:
    candidates: list[Path] = []
    env_path = os.environ.get("MANGATRAD_TRANSLATION_MEMORY", "").strip()
    if env_path:
        candidates.append(Path(env_path))
    candidates.append(Path.cwd() / "mangatrad_translation_memory.json")
    candidates.append(Path("C:/temp/mangatrad_translation_memory.json"))
    return candidates


@lru_cache(maxsize=8)
def load_translation_memory(path: str) -> TranslationMemory:
    memory_path = Path(path)
    if not memory_path.exists():
        return TranslationMemory(entries={})
    data = json.loads(memory_path.read_text(encoding="utf-8"))
    raw_entries = data.get("entries", {})
    if isinstance(raw_entries, dict):
        entries = {
            canonical_memory_key(key): str(value)
            for key, value in raw_entries.items()
            if str(key).strip() and str(value).strip()
        }
    else:
        entries = {}
        for item in raw_entries:
            if not isinstance(item, dict):
                continue
            key = canonical_memory_key(str(item.get("source", item.get("source_key", ""))))
            value = str(item.get("translation_fr", "")).strip()
            if key and value:
                entries[key] = value
    return TranslationMemory(entries=entries)


def clear_translation_memory_cache() -> None:
    load_translation_memory.cache_clear()
    default_translation_memory.cache_clear()


@lru_cache(maxsize=1)
def default_translation_memory() -> TranslationMemory:
    for candidate in _default_memory_candidates():
        if candidate.exists():
            return load_translation_memory(str(candidate.resolve()))
    return TranslationMemory(entries={})


def build_translation_memory(
    project_paths: Iterable[str | Path],
    *,
    statuses: set[str] | None = None,
    min_source_chars: int = 2,
) -> tuple[TranslationMemory, dict[str, object]]:
    target_statuses = statuses or {"edited", "validated"}
    buckets: dict[str, Counter[str]] = defaultdict(Counter)
    examples: dict[str, str] = {}
    scanned_blocks = 0
    eligible_blocks = 0
    for project_path in project_paths:
        project = ProjectCache.load(project_path)
        for page in project.pages:
            for block in page.blocks:
                scanned_blocks += 1
                if block.manual_status not in target_statuses:
                    continue
                source = block_memory_source(block)
                translation = (block.translation_fr or block.raw_translation_fr).strip()
                key = canonical_memory_key(source)
                if len(key) < min_source_chars or not translation:
                    continue
                eligible_blocks += 1
                buckets[key][translation] += 1
                examples.setdefault(key, source)

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
    return TranslationMemory(entries=entries), metadata


def write_translation_memory(memory: TranslationMemory, metadata: dict[str, object], output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "metadata": metadata,
        "entries": dict(sorted(memory.entries.items())),
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    clear_translation_memory_cache()
    return path
