from __future__ import annotations

import json
import os
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from functools import lru_cache
from pathlib import Path
from typing import Iterable

from cbz_manga_translator.core.cache import ProjectCache


def canonical_ocr_key(text: str) -> str:
    compact = " ".join(str(text).replace("\u2019", "'").strip().lower().split())
    compact = compact.strip("\"'`\u00b4\u2018\u2019\u201c\u201d ")
    compact = re.sub(r"\s+([,.;:!?])", r"\1", compact)
    compact = re.sub(r"\s+", " ", compact)
    return compact


_TOKEN_RE = re.compile(r"[a-z0-9']+")
_LIGHT_TOKENS = {
    "a",
    "am",
    "an",
    "and",
    "are",
    "be",
    "do",
    "for",
    "i",
    "in",
    "is",
    "it",
    "me",
    "my",
    "of",
    "on",
    "or",
    "so",
    "the",
    "to",
    "we",
    "you",
}
_VISUAL_CONFUSIONS = str.maketrans(
    {
        "0": "o",
        "1": "i",
        "3": "e",
        "4": "a",
        "5": "s",
        "6": "g",
        "7": "t",
        "8": "b",
        "|": "i",
        "l": "i",
    }
)


def _tokens(text: str) -> list[str]:
    return _TOKEN_RE.findall(canonical_ocr_key(text))


def _visual_token(token: str) -> str:
    return token.translate(_VISUAL_CONFUSIONS).strip("'")


def _token_similarity(left: str, right: str) -> float:
    if left == right:
        return 1.0
    visual_left = _visual_token(left)
    visual_right = _visual_token(right)
    if visual_left == visual_right:
        return 0.98
    return max(
        SequenceMatcher(None, left, right).ratio(),
        SequenceMatcher(None, visual_left, visual_right).ratio(),
    )


def _is_important_token(token: str) -> bool:
    return len(token.strip("'")) >= 4 and token not in _LIGHT_TOKENS


def _best_token_score(token: str, candidates: list[str]) -> float:
    token_visual = _visual_token(token)
    best = 0.0
    for candidate in candidates:
        candidate_visual = _visual_token(candidate)
        if token == candidate:
            return 1.0
        if token_visual == candidate_visual:
            return 0.98
        if token_visual[:1] != candidate_visual[:1] and abs(len(token_visual) - len(candidate_visual)) > 1:
            continue
        best = max(best, _token_similarity(token, candidate))
    return best


def _semantic_ocr_match(query_tokens: list[str], candidate_tokens: list[str]) -> bool:
    if not query_tokens or not candidate_tokens:
        return False
    query_joined = "".join(_visual_token(token) for token in query_tokens)
    candidate_joined = "".join(_visual_token(token) for token in candidate_tokens)
    if SequenceMatcher(None, query_joined, candidate_joined).ratio() >= 0.90:
        return True
    count_ratio = min(len(query_tokens), len(candidate_tokens)) / max(len(query_tokens), len(candidate_tokens))
    if count_ratio < 0.70:
        return False

    scores = [_best_token_score(token, candidate_tokens) for token in query_tokens]
    matched = sum(1 for score in scores if score >= 0.82)
    if matched / len(query_tokens) < 0.72:
        return False

    important = [token for token in query_tokens if _is_important_token(token)]
    if important:
        important_matched = sum(1 for token in important if _best_token_score(token, candidate_tokens) >= 0.78)
        if important_matched / len(important) < 0.80:
            return False

    return True


def _visual_key(text: str) -> str:
    return " ".join(_visual_token(token) for token in _tokens(text))


_FRENCH_CORRECTION_WORD_RE = re.compile(
    r"\b(?:je|tu|il|elle|nous|vous|ils|elles|le|la|les|un|une|des|de|du|"
    r"ce|cette|ca|est|suis|sont|etre|avoir|pas|que|qui|quoi|ou|pourquoi|"
    r"comment|avec|sans|dans|sur|plus|moins|tres|faire|faut|voila|mais|"
    r"donc|alors|comme|pour)\b",
    re.IGNORECASE,
)
_ENGLISH_CORRECTION_WORD_RE = re.compile(
    r"\b(?:i|you|we|they|he|she|it|what|why|how|where|when|who|the|a|an|to|"
    r"of|and|or|is|are|was|were|be|been|have|has|had|do|does|did|not|can|"
    r"will|would|should|could|wanna|gonna|gotta)\b",
    re.IGNORECASE,
)


def _looks_like_translation(value: str, translation: str) -> bool:
    key = canonical_ocr_key(value)
    if not key:
        return False
    if translation and key == canonical_ocr_key(translation):
        return True
    french_hits = len(_FRENCH_CORRECTION_WORD_RE.findall(key))
    english_hits = len(_ENGLISH_CORRECTION_WORD_RE.findall(key))
    return french_hits >= 2 and english_hits == 0


def _drops_strong_punctuation(original: str, corrected: str) -> bool:
    original_key = canonical_ocr_key(original)
    corrected_key = canonical_ocr_key(corrected)
    for char in ("?", "!"):
        if char in original_key and char not in corrected_key:
            return True
    if "..." in original_key and "..." not in corrected_key:
        return True
    return False


@dataclass(slots=True)
class OcrCorrectionMemory:
    entries: dict[str, str]
    _fuzzy_items: list[tuple[str, str, list[str], str]] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._fuzzy_items = [
            (key, value, _tokens(key), _visual_key(key))
            for key, value in self.entries.items()
            if key and value
        ]

    def lookup(self, text: str) -> str:
        key = canonical_ocr_key(text)
        exact = self.entries.get(key, "")
        if exact:
            return exact
        return self._lookup_fuzzy(key)

    def _lookup_fuzzy(self, key: str) -> str:
        if len(key) < 8 or len(self.entries) > 2500:
            return ""
        key_tokens = _tokens(key)
        if len(key_tokens) < 2:
            return ""

        visual_key = _visual_key(key)
        best_value = ""
        best_score = 0.0
        for candidate, value, candidate_tokens, candidate_visual_key in self._fuzzy_items:
            if abs(len(candidate) - len(key)) > max(10, int(len(key) * 0.30)):
                continue
            if not _semantic_ocr_match(key_tokens, candidate_tokens):
                continue

            text_score = SequenceMatcher(None, key, candidate).ratio()
            visual_score = SequenceMatcher(None, visual_key, candidate_visual_key).ratio()
            joined_score = SequenceMatcher(None, visual_key.replace(" ", ""), candidate_visual_key.replace(" ", "")).ratio()
            token_score = sum(_best_token_score(token, candidate_tokens) for token in key_tokens) / len(key_tokens)
            score = max(text_score, visual_score, joined_score) * 0.55 + token_score * 0.45
            if score > best_score:
                best_score = score
                best_value = value
        return best_value if best_score >= 0.88 else ""


def _default_memory_candidates() -> list[Path]:
    candidates: list[Path] = []
    env_path = os.environ.get("MANGATRAD_OCR_MEMORY", "").strip()
    if env_path:
        candidates.append(Path(env_path))
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return candidates
    candidates.append(Path.cwd() / "mangatrad_ocr_memory.json")
    candidates.append(Path("C:/temp/mangatrad_ocr_memory.json"))
    return candidates


@lru_cache(maxsize=8)
def load_ocr_memory(path: str) -> OcrCorrectionMemory:
    memory_path = Path(path)
    if not memory_path.exists():
        return OcrCorrectionMemory(entries={})
    data = json.loads(memory_path.read_text(encoding="utf-8"))
    raw_entries = data.get("entries", {})
    if not isinstance(raw_entries, dict):
        return OcrCorrectionMemory(entries={})
    entries = {
        canonical_ocr_key(key): str(value).strip()
        for key, value in raw_entries.items()
        if str(key).strip() and str(value).strip()
    }
    return OcrCorrectionMemory(entries=entries)


def clear_ocr_memory_cache() -> None:
    load_ocr_memory.cache_clear()
    default_ocr_memory.cache_clear()


@lru_cache(maxsize=1)
def default_ocr_memory() -> OcrCorrectionMemory:
    for candidate in _default_memory_candidates():
        if candidate.exists():
            return load_ocr_memory(str(candidate.resolve()))
    return OcrCorrectionMemory(entries={})


def build_ocr_memory(
    project_paths: Iterable[str | Path],
    *,
    statuses: set[str] | None = None,
    min_source_chars: int = 3,
) -> tuple[OcrCorrectionMemory, dict[str, object]]:
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
                original = block.ocr_text.strip()
                corrected = block.ocr_corrected_text.strip()
                translation = (block.translation_fr or block.raw_translation_fr).strip()
                if len(original) < min_source_chars or len(corrected) < min_source_chars:
                    continue
                if _looks_like_translation(corrected, translation):
                    continue
                if _drops_strong_punctuation(original, corrected):
                    continue
                key = canonical_ocr_key(original)
                corrected_key = canonical_ocr_key(corrected)
                if not key or key == corrected_key:
                    continue
                eligible_blocks += 1
                buckets[key][corrected] += 1
                examples.setdefault(key, original)

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
    return OcrCorrectionMemory(entries=entries), metadata


def write_ocr_memory(memory: OcrCorrectionMemory, metadata: dict[str, object], output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "metadata": metadata,
        "entries": dict(sorted(memory.entries.items())),
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    clear_ocr_memory_cache()
    return path
