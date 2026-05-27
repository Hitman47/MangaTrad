from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from typing import Any

from cbz_manga_translator.core.models import OcrBlock

_ENGLISH_WORDS = {
    "the", "a", "an", "and", "or", "to", "of", "in", "on", "for", "with", "from",
    "you", "your", "i", "me", "my", "we", "they", "he", "she", "it", "is", "are",
    "was", "were", "be", "been", "have", "has", "had", "do", "does", "did", "not",
    "no", "yes", "what", "why", "where", "when", "how", "who", "this", "that", "here",
    "there", "now", "then", "man", "director", "house", "key", "trip", "tokyo",
    "orphanage", "food", "shelter", "steal", "tiger", "agency", "skills", "bomb",
    "button", "press", "boss", "company", "dorm", "battle", "fault", "cry",
}


_BAD_OCR_SOURCE_RE = re.compile(
    r"\b(?:enolgh|folr|fopm|colld|hlnger|tslrlmi|napehouse|nestern|individlals|repect|respecl|"
    r"rlpted|lnneces|hideolt|yol|iwas|idont|iguess|wolld|bizarpe|wopld|iaeely|lessil|"
    r"evepy|theip|dsich|aohto|dollarman|thess|bmusthvb|gallenl|aslep|inifront|t0)\b",
    flags=re.IGNORECASE,
)
_TRANSLATION_RESIDUE_RE = re.compile(
    r"\b(?:orphanage|food|shelter|steal|tiger|agency|skills?|earn|master|animal|form|staff|"
    r"backup|sake|bomb|dampen|explosion|button|press|boss|company|dorm|posthaste|lad|ideals|"
    r"mafia|battle|fault|cry|days?|place|else|worldly|knowledge|individuals?|bandit|star|"
    r"mercenary|guy|dollarman|fick|smug|slam|contents|beans?)\b",
    flags=re.IGNORECASE,
)
_UPPERCASE_WORD_RE = re.compile(r"\b[A-Z]{3,}\b")
_SAFE_UPPERCASE = {"OK", "SFX", "RASHOMON", "DAZAI", "TANIZAKI", "ATSUSHI", "NAOMI", "KUNIKIDA"}

_SAFE_UNTRANSLATED = {
    "ok", "okay", "aww", "ah", "oh", "uh", "um", "hm", "hmm", "hum", "hey", "yo", "gon", "bam", "boom",
}

_SYMBOL_RE = re.compile(r"[=_{}<>|\\]+")
_TOKEN_RE = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ']+")


@dataclass(slots=True)
class QualityFeatures:
    block_id: str
    risk_score: int
    action: str
    reasons: list[str]
    source_tokens: int
    translation_tokens: int
    confidence: float | None
    warnings_count: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _tokens(text: str) -> list[str]:
    return _TOKEN_RE.findall(text or "")


def _looks_like_safe_untranslated(source: str) -> bool:
    normalized = re.sub(r"[^a-z]+", "", source.lower())
    return normalized in _SAFE_UNTRANSLATED


def _has_obvious_english_residue(text: str) -> bool:
    lowered = {token.lower().strip("'") for token in _tokens(text)}
    hits = lowered & _ENGLISH_WORDS
    return len(hits) >= 2


def _source_residue_hits(source: str, translation: str) -> set[str]:
    source_tokens = {token.lower().strip("'") for token in _tokens(source) if len(token) >= 4}
    translation_tokens = {token.lower().strip("'") for token in _tokens(translation) if len(token) >= 4}
    safe = {"naru", "miwa", "atsushi", "dazai", "kanade", "fujimura", "usami", "rashomon", "gozen", "kariu"}
    # Keep only tokens that are more likely English residue/OCR garbage than names.
    return (source_tokens & translation_tokens) - safe


def compute_quality_features(block: OcrBlock) -> QualityFeatures:
    source = (block.normalized_source_text or block.ocr_corrected_text or block.ocr_text or "").strip()
    translation = (block.translation_fr or "").strip()
    reasons: list[str] = []
    score = 0

    if block.quality_warnings:
        score += min(35, 9 * len(block.quality_warnings))
        reasons.append(f"QC warnings: {len(block.quality_warnings)}")

    if block.confidence is not None:
        if block.confidence < 0.35:
            score += 30
            reasons.append("OCR confidence very low")
        elif block.confidence < 0.60:
            score += 16
            reasons.append("OCR confidence low")

    if not source:
        score += 30
        reasons.append("empty source")
    if not translation:
        score += 35
        reasons.append("empty translation")

    source_norm = re.sub(r"\s+", " ", source).strip().lower()
    trans_norm = re.sub(r"\s+", " ", translation).strip().lower()
    if source_norm and source_norm == trans_norm and not _looks_like_safe_untranslated(source):
        score += 32
        reasons.append("translation identical to source")

    if _SYMBOL_RE.search(source) or _SYMBOL_RE.search(translation):
        score += 22
        reasons.append("suspicious symbols")

    if _BAD_OCR_SOURCE_RE.search(source):
        score += 22
        reasons.append("known OCR typo pattern")

    if re.search(r"\b[A-Za-z]{2,}-\s+[A-Za-z]{2,}\b", source):
        score += 16
        reasons.append("probable OCR line-break hyphen")

    source_tokens = len(_tokens(source))
    translation_tokens = len(_tokens(translation))
    if source_tokens >= 3 and translation_tokens <= 1:
        score += 24
        reasons.append("translation too short")
    if source_tokens <= 2 and block.confidence is not None and block.confidence < 0.75:
        score += 12
        reasons.append("short uncertain OCR fragment")

    if translation and _has_obvious_english_residue(translation) and not _looks_like_safe_untranslated(translation):
        score += 24
        reasons.append("obvious English residue in French translation")
    if translation and _TRANSLATION_RESIDUE_RE.search(translation) and not _looks_like_safe_untranslated(translation):
        score += 28
        reasons.append("probable English residue in French translation")
    shared_residue = _source_residue_hits(source, translation)
    if shared_residue and not _looks_like_safe_untranslated(source):
        score += 22 if len(shared_residue) == 1 else 30
        reasons.append("source residue copied into translation")
    if re.search(r"[A-Za-z]+[0-9]+|[0-9]+[A-Za-z]+|[$]", source):
        score += 18
        reasons.append("OCR digit/symbol confusion")
    uppercase_hits = [word for word in _UPPERCASE_WORD_RE.findall(translation) if word not in _SAFE_UPPERCASE]
    if uppercase_hits:
        score += 18
        reasons.append("uppercase residue in translation")

    if re.search(r"[a-z][A-Z]|[A-Z][a-z][A-Z]", source):
        score += 10
        reasons.append("random OCR casing")
    if ":" in source and not re.search(r"\b(?:chapter|vol|volume|no|number|page)\s*:", source, flags=re.IGNORECASE):
        score += 16
        reasons.append("suspect colon punctuation")
    if len(_tokens(source)) >= 3 and re.search(r"[:,]\s*$", source):
        score += 16
        reasons.append("probable missing ellipsis or strong punctuation")
    if re.match(r"(?i)^\s*(?:what|why|how|where|when|who|is|are|do|did|does|can|could|would|should|will)\b", source):
        if "?" not in source:
            score += 18
            reasons.append("probable missing question mark")

    score = max(0, min(100, score))
    if block.manual_status == "validated":
        action = "validated"
    elif block.manual_status == "ignored":
        action = "ignored"
    elif score >= 55:
        action = "review_high"
    elif score >= 25:
        action = "review_medium"
    else:
        action = "probably_ok"

    return QualityFeatures(
        block_id=block.id,
        risk_score=score,
        action=action,
        reasons=reasons,
        source_tokens=source_tokens,
        translation_tokens=translation_tokens,
        confidence=block.confidence,
        warnings_count=len(block.quality_warnings),
    )
