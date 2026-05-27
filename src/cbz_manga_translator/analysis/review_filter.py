from __future__ import annotations

import re
from collections.abc import Iterable

from cbz_manga_translator.analysis.ignore_memory import default_ignore_memory
from cbz_manga_translator.core.models import OcrBlock, SourceLang


_AUTO_WARNING = "auto-ignore: non-dialogue probable"

_SCANLATION_RE = re.compile(
    r"\b("
    r"mangafox|hosted\s+at|we\s+take\s+no\s+credit|credit\s+goes|"
    r"appropriate\s+parties|creation\s+editing|scanlation|raws?|translator|"
    r"reader|viewer|upload(?:ed|er)"
    r")\b",
    flags=re.IGNORECASE,
)

_TECHNICAL_RE = re.compile(
    r"\b("
    r"phase\s*\d|monument|hive|maximum\s+depth|monument\s+height|"
    r"stab\s+radius|notable\s+hives?|main\s+hall|drift|hall|"
    r"depth|radius|diameter|height|meters?|kilometers?|km|oom"
    r")\b",
    flags=re.IGNORECASE,
)

_REFERENCE_PAGE_RE = re.compile(
    r"\b("
    r"characters?|majority\s+faction|opposing\s+faction|west\s+oasis\s+government|"
    r"cyborg\s+soldiers?|master\s+and\s+pupil|in\s+control\s+of|aspiring|"
    r"government|faction|profile|relationship\s+chart"
    r")\b",
    flags=re.IGNORECASE,
)

_MEASURE_RE = re.compile(r"^\s*\d[\d,.\soO]*(?:m|km|cm|mm|%)\s*$", flags=re.IGNORECASE)
_SFX_WORDS = {
    "4-UM",
    "AAAA",
    "AHHH",
    "AHHH-",
    "@ORGL OOO",
    "BLAM",
    "BUMP",
    "CHA",
    "CHATTER",
    "CLACK",
    "CLICK",
    "CREAK",
    "CRASH",
    "DEEEAD",
    "FUMP",
    "FWP",
    "FBY",
    "KACHA",
    "KA CHA",
    "KIDCK",
    "LUNGE",
    "PINCH",
    "POKE",
    "POKE POKE",
    "RUMBLE",
    "SILENCE",
    "SLAM",
    "THUD",
    "TWITCH",
    "WHISPER",
    "WOOSH",
}

_SIGNAGE_TERMS = {"atm", "card", "fee", "phone", "transfer", "store", "convenience"}


def _block_source(block: OcrBlock) -> str:
    return (
        block.ocr_corrected_text.strip()
        or block.normalized_source_text.strip()
        or block.ocr_text.strip()
    )


def is_scanlation_credit(text: str) -> bool:
    return bool(_SCANLATION_RE.search(text))


def is_sfx_or_noise(text: str) -> bool:
    value = " ".join(text.strip().split())
    if not value:
        return True
    upper = value.upper()
    if upper in _SFX_WORDS or upper.strip(" .!?:,-") in _SFX_WORDS:
        return True
    if re.search(r"\bsparkle\b", value, flags=re.IGNORECASE) and len(re.findall(r"[A-Za-z]+", value)) <= 3:
        return True
    letters = [char for char in value if char.isalpha()]
    if len(letters) <= 2:
        return True
    repeated = re.sub(r"[^A-Z]", "", upper)
    if len(repeated) >= 5 and len(set(repeated)) <= 3 and upper == value:
        return True
    if re.fullmatch(r"(?i)[a-z]{2,}a{3,}(?:\s*\([^)]{2,}\))?", value):
        return True
    return False


def is_signage_or_ui_text(text: str) -> bool:
    value = " ".join(text.strip().split()).lower()
    if not value:
        return False
    hits = {term for term in _SIGNAGE_TERMS if re.search(rf"\b{re.escape(term)}\b", value)}
    return len(hits) >= 2


def is_technical_infographic(text: str) -> bool:
    value = " ".join(text.strip().split())
    if not value:
        return False
    if _MEASURE_RE.match(value):
        return True
    if _TECHNICAL_RE.search(value):
        return True
    if len(value) <= 18 and value.lower() in {"stab", "hall", "drift", "main hall", "phase 4", "phase 5"}:
        return True
    return False


def is_reference_profile_text(text: str) -> bool:
    value = " ".join(text.strip().split())
    if not value:
        return False
    if _REFERENCE_PAGE_RE.search(value):
        return True
    words = re.findall(r"[A-Za-z][A-Za-z']+", value)
    titlecase = [word for word in words if len(word) >= 3 and word[:1].isupper() and word[1:].islower()]
    return len(words) >= 8 and len(titlecase) >= 4 and not re.search(r"[!?]", value)


def non_reviewable_reason(block: OcrBlock) -> str:
    source = _block_source(block)
    learned = default_ignore_memory().lookup(source)
    if learned:
        if _is_dialogue_like(source):
            return ""
        return learned
    if is_scanlation_credit(source):
        return "credit scantrad"
    if is_signage_or_ui_text(source):
        return "signalétique/interface"
    if is_technical_infographic(source):
        return "infographie/signaletique"
    if is_sfx_or_noise(source):
        return "sfx/bruit"
    return ""


def _is_dialogue_like(text: str) -> bool:
    words = re.findall(r"[A-Za-z][A-Za-z']+", text)
    if len(words) >= 5:
        return True
    return bool(re.search(r"\b(I|you|we|he|she|they|what|why|how|when|where|can|could|would|should|will|are|is)\b", text, flags=re.IGNORECASE))


def page_non_reviewable_reason(blocks: Iterable[OcrBlock]) -> str:
    items = list(blocks)
    if len(items) < 6:
        return ""
    reasons = [non_reviewable_reason(block) for block in items]
    reason_count = sum(1 for reason in reasons if reason)
    technical_count = sum(1 for block in items if is_technical_infographic(_block_source(block)))
    dialogue_count = sum(1 for block in items if _is_dialogue_like(_block_source(block)))
    if technical_count >= 5 and reason_count / len(items) >= 0.55 and dialogue_count <= max(2, len(items) // 5):
        return "page non exploitable: infographie/signaletique"
    reference_count = sum(1 for block in items if is_reference_profile_text(_block_source(block)))
    dialogue_punctuation_count = sum(1 for block in items if re.search(r"[!?]", _block_source(block)))
    if reference_count >= max(4, len(items) // 2) and dialogue_punctuation_count <= max(1, len(items) // 5):
        return "page non exploitable: fiche personnages/extra dense"
    if reason_count / len(items) >= 0.75 and dialogue_count <= max(1, len(items) // 6):
        return "page non exploitable: non-dialogue"
    return ""


def apply_review_filters(blocks: list[OcrBlock], *, source_lang: SourceLang = "en") -> int:
    if source_lang != "en":
        return 0

    page_reason = page_non_reviewable_reason(blocks)
    changed = 0
    for block in blocks:
        reason = page_reason or non_reviewable_reason(block)
        if not reason:
            continue
        warning = f"{_AUTO_WARNING}: {reason}"
        if warning not in block.quality_warnings:
            block.quality_warnings.append(warning)
        if block.review_notes.strip() == "":
            block.review_notes = f"[auto-ignore] {reason}"
        if block.manual_status in {"unchecked", "review"}:
            block.manual_status = "ignored"
            changed += 1
    return changed
