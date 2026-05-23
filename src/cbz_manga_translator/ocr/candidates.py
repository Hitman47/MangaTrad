from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any

from cbz_manga_translator.ocr.text_cleanup import has_random_ocr_casing, normalize_ocr_text_for_translation

_BAD_OCR_TOKENS = {
    "inhook",
    "lnhook",
    "lhook",
    "toid",
    "to1d",
    "lookv",
    "loooky",
    "l00k",
    "l0ok",
    "repect",
    "respecl",
    "enolgh",
    "folr",
    "fopm",
    "colld",
    "hlnger",
    "individlals",
    "napehouse",
    "nestern",
    "tslrlmi",
    "houps",
    "ramn",
    "rarn",
    "setupi",
    "morningb",
    "howdid",
    "tholsand",
    "entipe",
    "etire",
    "sevenn",
}

_COMMON_ENGLISH_WORDS = {
    "a", "all", "am", "an", "and", "are", "as", "at", "be", "but", "by", "can", "come",
    "coming", "country", "did", "director", "do", "doing", "due", "encounter", "expected",
    "eye", "for", "from", "get", "go", "going", "good", "grandma", "have", "he", "her",
    "here", "him", "his", "i", "i'd", "i'll", "i'm", "i've", "ignore", "in", "is", "it",
    "just", "like", "look", "looking", "looky", "me", "miwa", "more", "my", "nar", "naru",
    "nee", "never", "no", "not", "now", "of", "okay", "on", "one", "or", "please",
    "picturesque", "respect", "risky", "someone", "stuff", "that", "the", "there", "this",
    "to", "told", "unhook", "up", "was", "what", "where", "who", "with", "ya", "you",
    "orphanage", "food", "shelter", "steal", "brave", "enough", "tiger", "four", "days",
    "agency", "individuals", "abilities", "skills", "earn", "keep", "master", "animal",
    "form", "staff", "backup", "sake", "bomb", "explosion", "button", "press", "company",
    "dorm", "posthaste", "lad", "ideals", "mafia", "battle", "fault", "cry",
    "body", "hours", "hour", "few", "first", "place", "seven", "star", "academy",
    "student", "challenge", "dared", "thousand", "hundred", "hunting", "recognized",
    "player", "town", "guess", "happen", "revealed", "late",
}

_RAW_BAD_OCR_RE = re.compile(r"\b(?:houps|b0dy|tholsand|entipe|etire|sevenn)\b", flags=re.IGNORECASE)
_WORD_RE = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿぁ-んァ-ン一-龯々ー']+")
_LETTER_RE = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿぁ-んァ-ン一-龯々]")


@dataclass(slots=True)
class OcrCandidate:
    engine: str
    text: str
    confidence: float | None = None
    score: float = 0.0
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "OcrCandidate":
        return cls(
            engine=str(data.get("engine", "unknown")),
            text=str(data.get("text", "")),
            confidence=None if data.get("confidence") is None else float(data.get("confidence")),
            score=float(data.get("score", 0.0)),
            note=str(data.get("note", "")),
        )


def candidate_quality(text: str, confidence: float | None = None, *, bonus: float = 0.0) -> float:
    compact = normalize_ocr_text_for_translation(text)
    if not compact:
        return -999.0
    letters = _LETTER_RE.findall(compact)
    if not letters:
        return -80.0
    words = _WORD_RE.findall(compact)
    lower_words = {word.lower().strip("'") for word in words}
    bad_token_penalty = sum(3.0 for token in lower_words if token in _BAD_OCR_TOKENS)
    raw_bad_token_penalty = len(_RAW_BAD_OCR_RE.findall(str(text))) * 1.4
    semicolon_penalty = str(text).count(";") * 0.70
    random_case_penalty = 1.15 if has_random_ocr_casing(str(text)) else 0.0
    weird_symbol_penalty = sum(compact.count(char) for char in "|_{}[]<>") * 0.65
    orphan_fragment_penalty = 1.25 if len(words) == 1 and compact.endswith(":") else 0.0
    dictionary_hits = sum(1 for token in lower_words if token in _COMMON_ENGLISH_WORDS)
    dictionary_bonus = min(2.2, dictionary_hits * 0.22)
    all_caps_bonus = 0.18 if compact.upper() == compact and len(words) >= 2 else 0.0
    sentence_bonus = 0.55 if len(words) >= 3 else 0.0
    conf = 0.0 if confidence is None else max(0.0, min(1.0, confidence))
    return (
        min(len(letters), 120) * 0.065
        + len(words) * 0.58
        + conf * 2.0
        + all_caps_bonus
        + sentence_bonus
        + dictionary_bonus
        + bonus
        - bad_token_penalty
        - raw_bad_token_penalty
        - semicolon_penalty
        - random_case_penalty
        - weird_symbol_penalty
        - orphan_fragment_penalty
    )


def bad_ocr_tokens() -> set[str]:
    return set(_BAD_OCR_TOKENS)


def word_tokens(text: str) -> list[str]:
    return _WORD_RE.findall(str(text))
