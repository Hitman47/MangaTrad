from __future__ import annotations

import re

INCOMPLETE_BUBBLE_WARNING = "zone/bulle probablement incomplete: relire avec crop elargi/fallback"
FUSED_BUBBLE_WARNING = "fusion probable: bulle, SFX ou plusieurs bulles dans la meme bbox"

_WORD_RE = re.compile(r"[A-Za-z']+")
_TERMINAL_RE = re.compile(r"(?:[.!?][\"')\]]?|[.!?][\"')\]]*\s*)$")
_INCOMPLETE_END_RE = re.compile(
    r"\b(?:and|but|or|if|that|this|the|a|an|to|of|for|from|with|without|before|after|"
    r"because|about|into|onto|on|in|at|as|than|then|while|when|where|who|what|why|how|"
    r"gotta|gonna|wanna|lemme|should|could|would|can|cannot|can't|will|still|just|"
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
    r"jolt|gasp|slap|wobble|yawn|fidget|twitch|fwooo|nod|scribble|krehble|krembue|"
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
    sentence_breaks = re.findall(r"[.!?][\"')\]]?(?=\s+[A-Z\"'])", source)
    if len(words) >= 14 and sentence_breaks:
        return True
    return False


def zone_quality_warnings(text: str) -> list[str]:
    warnings: list[str] = []
    if is_probably_incomplete_source(text):
        warnings.append(INCOMPLETE_BUBBLE_WARNING)
    if is_probably_fused_source(text):
        warnings.append(FUSED_BUBBLE_WARNING)
    return warnings
