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


_FRENCH_SOURCE_WORD_RE = re.compile(
    r"\b(?:je|tu|il|elle|nous|vous|ils|elles|le|la|les|un|une|des|de|du|"
    r"ce|cette|ca|est|suis|sont|etre|avoir|pas|que|qui|quoi|ou|pourquoi|"
    r"comment|avec|sans|dans|sur|plus|moins|tres|faire|faut|voila|mais|"
    r"donc|alors|comme|pour)\b",
    re.IGNORECASE,
)
_ENGLISH_SOURCE_WORD_RE = re.compile(
    r"\b(?:i|you|we|they|he|she|it|what|why|how|where|when|who|the|a|an|to|"
    r"of|and|or|is|are|was|were|be|been|have|has|had|do|does|did|not|can|"
    r"will|would|should|could|wanna|gonna|gotta)\b",
    re.IGNORECASE,
)


def _source_looks_like_translation(source: str, translation: str) -> bool:
    key = canonical_memory_key(source)
    if not key:
        return False
    if translation and key == canonical_memory_key(translation):
        return True
    french_hits = len(_FRENCH_SOURCE_WORD_RE.findall(key))
    english_hits = len(_ENGLISH_SOURCE_WORD_RE.findall(key))
    return french_hits >= 2 and english_hits == 0


def block_memory_source(block: OcrBlock) -> str:
    return (block.normalized_source_text or block.ocr_corrected_text or block.ocr_text).strip()


def block_memory_sources(block: OcrBlock) -> set[str]:
    """Return all source spellings worth binding to the human translation."""
    sources = {
        block.ocr_text.strip(),
        block.ocr_corrected_text.strip(),
        block.normalized_source_text.strip(),
        block_memory_source(block),
    }
    return {source for source in sources if source}


def memory_source_aliases(source: str) -> set[str]:
    aliases = {source}
    try:
        from cbz_manga_translator.ocr.text_cleanup import normalize_ocr_text_for_translation

        aliases.add(normalize_ocr_text_for_translation(source))
    except Exception:
        pass
    expanded: set[str] = set()
    for item in aliases:
        value = item
        value = re.sub(r"\bgonna\b", "going to", value, flags=re.IGNORECASE)
        value = re.sub(r"\bwanna\b", "want to", value, flags=re.IGNORECASE)
        value = re.sub(r"\bwould['’]?ve\b", "would have", value, flags=re.IGNORECASE)
        value = re.sub(r"\bcould['’]?ve\b", "could have", value, flags=re.IGNORECASE)
        value = re.sub(r"\bshould['’]?ve\b", "should have", value, flags=re.IGNORECASE)
        value = re.sub(r"\bi['’]?m\b", "I am", value, flags=re.IGNORECASE)
        value = re.sub(r"\bi['’]?d\b", "I would", value, flags=re.IGNORECASE)
        value = re.sub(r"\bi['’]?ll\b", "I will", value, flags=re.IGNORECASE)
        value = re.sub(r"\bi['’]?ve\b", "I have", value, flags=re.IGNORECASE)
        expanded.add(value)
    aliases.update(expanded)
    contracted: set[str] = set()
    for item in aliases:
        value = item
        value = re.sub(r"\bit\s+is\b", "it's", value, flags=re.IGNORECASE)
        value = re.sub(r"\bi\s+am\b", "I'm", value, flags=re.IGNORECASE)
        value = re.sub(r"\bi\s+would\b", "I'd", value, flags=re.IGNORECASE)
        value = re.sub(r"\bi\s+will\b", "I'll", value, flags=re.IGNORECASE)
        value = re.sub(r"\bi\s+have\b", "I've", value, flags=re.IGNORECASE)
        value = re.sub(r"\bwould\s+have\b", "would've", value, flags=re.IGNORECASE)
        value = re.sub(r"\bcould\s+have\b", "could've", value, flags=re.IGNORECASE)
        value = re.sub(r"\bshould\s+have\b", "should've", value, flags=re.IGNORECASE)
        contracted.add(value)
    aliases.update(contracted)
    return {alias.strip() for alias in aliases if alias and alias.strip()}


@dataclass(slots=True)
class TranslationMemory:
    entries: dict[str, str]

    def lookup(self, source: str) -> str:
        keys = {
            canonical_memory_key(alias)
            for alias in memory_source_aliases(source)
        }
        keys = {key for key in keys if key}
        for key in sorted(keys, key=len, reverse=True):
            exact = self.entries.get(key, "")
            if exact:
                return exact
        return self._lookup_fuzzy(keys)

    def _lookup_fuzzy(self, keys: set[str]) -> str:
        query_keys = {key for key in keys if len(key) >= 12}
        if not query_keys or len(self.entries) > 5000:
            return ""
        best_value = ""
        best_score = 0.0
        second_score = 0.0
        for candidate, value in self.entries.items():
            candidate_tokens = set(re.findall(r"[a-z0-9']+", candidate))
            if not candidate_tokens:
                continue
            for key in query_keys:
                if abs(len(candidate) - len(key)) > max(14, int(len(key) * 0.30)):
                    continue
                key_tokens = set(re.findall(r"[a-z0-9']+", key))
                if len(key_tokens) < 3:
                    continue
                token_overlap = len(key_tokens & candidate_tokens) / max(len(key_tokens), len(candidate_tokens))
                if token_overlap < 0.68:
                    continue
                sequence_score = SequenceMatcher(None, key, candidate).ratio()
                score = (sequence_score * 0.72) + (token_overlap * 0.28)
                if score > best_score:
                    second_score = best_score
                    best_score = score
                    best_value = value
                elif score > second_score:
                    second_score = score
        if best_score >= 0.96:
            return best_value
        if best_score >= 0.90 and (best_score - second_score) >= 0.03:
            return best_value
        return ""


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
    if os.environ.get("MANGATRAD_DISABLE_TRANSLATION_MEMORY", "").strip():
        return TranslationMemory(entries={})
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
    target_statuses = statuses or {"edited", "validated", "review"}
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
                translation = (block.translation_fr or block.raw_translation_fr).strip()
                sources = {
                    source
                    for source in block_memory_sources(block)
                    if not _source_looks_like_translation(source, translation)
                }
                keys = {
                    canonical_memory_key(alias)
                    for source in sources
                    for alias in memory_source_aliases(source)
                }
                keys = {key for key in keys if len(key) >= min_source_chars}
                if not keys or not translation:
                    continue
                eligible_blocks += 1
                for key in keys:
                    buckets[key][translation] += 1
                    examples.setdefault(key, block_memory_source(block))

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
