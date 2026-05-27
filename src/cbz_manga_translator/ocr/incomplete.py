from __future__ import annotations

import re

INCOMPLETE_BUBBLE_WARNING = "zone/bulle probablement incomplete: relire avec crop elargi/fallback"
FUSED_BUBBLE_WARNING = "fusion probable: bulle, SFX ou plusieurs bulles dans la meme bbox"
ZONE_TOO_SMALL_WARNING = "zone trop petite probable: texte coupe dans la bulle"
SPLIT_BUBBLE_WARNING = "bulle probablement separee en plusieurs zones"
SFX_MIXED_WARNING = "SFX probablement melange avec une bulle de dialogue"

_WORD_RE = re.compile(r"[A-Za-z']+")
_TERMINAL_RE = re.compile(r"(?:[.!?][\"')\]]?|[.!?][\"')\]]*\s*)$")
_INCOMPLETE_END_RE = re.compile(
    r"\b(?:and|but|or|if|that|this|the|a|an|to|of|for|from|with|without|before|after|"
    r"because|about|into|onto|on|in|at|as|than|then|while|when|where|who|what|why|how|"
    r"gotta|gonna|wanna|lemme|should|could|would|can|cannot|can't|will|still|just|"
    r"is|isn't|isnt|aren't|arent|don't|dont|doesn't|doesnt|are|am|was|were|be|been|being|do|does|did|has|have|had|"
    r"catches|counting|change|sources|place|understanding|mis|doi)\s*$",
    flags=re.IGNORECASE,
)
_INCOMPLETE_START_RE = re.compile(
    r"^\s*(?:\.\.\.)?\s*(?:have|left|saved|only|where|but|and|then|with|without|after|"
    r"before|right|maybe|because|until|unless|when|while)\b",
    flags=re.IGNORECASE,
)
_SHORT_ZONE_RE = re.compile(
    r"\b(?:and this is what|only found|wait a sec|where will it end|now i gotta|"
    r"but our solrces say that|but our sources say that|i'm counting on|i am counting on)\b",
    flags=re.IGNORECASE,
)
_SFX_MIX_RE = re.compile(
    r"\b(?:whisper|sob|shock|jaka|sfx|bam|bang|boom|thud|clap|rustle|slam|tap|tch|"
    r"jolt|gasp|slap|wobble|yawn|fidget|twitch|fwooo|woosh|crash|nod|scribble|krehble|krembue|"
    r"shivr|fwoop|brip|whooosh)\b",
    flags=re.IGNORECASE,
)


def _words(text: str) -> list[str]:
    return [word.lower().strip("'") for word in _WORD_RE.findall(text)]


def _compact(text: str) -> str:
    return " ".join(str(text).strip().split())


def is_probably_incomplete_source(text: str) -> bool:
    source = _compact(text)
    if not source:
        return False
    words = _words(source)
    if len(words) < 2:
        return False
    if _SHORT_ZONE_RE.search(source):
        return True
    if source.endswith((",", ":", ";")) and len(words) >= 3:
        return True
    if source.startswith("...") or source.startswith(". "):
        return True
    has_terminal_punctuation = bool(_TERMINAL_RE.search(source))
    if _INCOMPLETE_START_RE.search(source) and not has_terminal_punctuation:
        return True
    if not has_terminal_punctuation and _INCOMPLETE_END_RE.search(source):
        return True
    if len(words) >= 5 and not has_terminal_punctuation and re.search(r"\b(?:before|after|because|that|if|when)\b", source, re.IGNORECASE):
        return True
    return False


def is_probably_too_small_zone(text: str) -> bool:
    source = _compact(text)
    if not source:
        return False
    words = _words(source)
    if len(words) < 2:
        return False
    if _SHORT_ZONE_RE.search(source):
        return True
    if source.endswith((",", ":", ";")) and len(words) >= 2:
        return True
    if len(words) >= 3 and not _TERMINAL_RE.search(source) and _INCOMPLETE_END_RE.search(source):
        return True
    return False


def is_probably_split_bubble(text: str) -> bool:
    source = _compact(text)
    if not source:
        return False
    words = _words(source)
    if len(words) < 2:
        return False
    if source.startswith("...") or source.startswith(". "):
        return True
    if _INCOMPLETE_START_RE.search(source) and not _TERMINAL_RE.search(source):
        return True
    return False


def is_probably_fused_source(text: str) -> bool:
    source = _compact(text)
    if not source:
        return False
    words = _words(source)
    if len(words) < 3:
        return False
    sfx_hits = _SFX_MIX_RE.findall(source)
    if sfx_hits and len(words) >= 4:
        return True
    if re.search(r"\ball\s+righty!\s+then\?\s+we(?:'re| are)\s+off\.?$", source, flags=re.IGNORECASE):
        return True
    sentence_breaks = re.findall(r"[.!?][\"')\]]?(?=\s+[A-Z\"'])", source)
    if len(words) >= 14 and sentence_breaks:
        return True
    return False


def has_probably_mixed_sfx(text: str) -> bool:
    source = _compact(text)
    if not source:
        return False
    words = _words(source)
    sfx_hits = _SFX_MIX_RE.findall(source)
    return bool(sfx_hits and len(words) >= 4)


def zone_issue_categories(text: str) -> list[str]:
    categories: list[str] = []
    if is_probably_too_small_zone(text):
        categories.append("zone_too_small")
    if is_probably_split_bubble(text):
        categories.append("split_bubble")
    if has_probably_mixed_sfx(text):
        categories.append("sfx_mixed")
    if is_probably_fused_source(text):
        categories.append("fused_bubble")
    return categories


def zone_quality_warnings(text: str) -> list[str]:
    warnings: list[str] = []
    categories = zone_issue_categories(text)
    if "zone_too_small" in categories:
        warnings.append(ZONE_TOO_SMALL_WARNING)
    if "split_bubble" in categories:
        warnings.append(SPLIT_BUBBLE_WARNING)
    if is_probably_incomplete_source(text):
        warnings.append(INCOMPLETE_BUBBLE_WARNING)
    if "sfx_mixed" in categories:
        warnings.append(SFX_MIXED_WARNING)
    if "fused_bubble" in categories:
        warnings.append(FUSED_BUBBLE_WARNING)
    return warnings
