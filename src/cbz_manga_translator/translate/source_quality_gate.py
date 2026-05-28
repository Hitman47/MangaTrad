from __future__ import annotations

import re
from dataclasses import dataclass

from cbz_manga_translator.core.models import OcrBlock, SourceLang
from cbz_manga_translator.ocr.incomplete import zone_issue_categories, zone_quality_warnings

_ASCII_WORD_RE = re.compile(r"[A-Za-z']+")
_QUESTION_START_RE = re.compile(
    r"^\s*(?:what|why|how|where|when|who|is|are|do|did|does|can|could|would|should|will)\b",
    flags=re.IGNORECASE,
)
_INCOMPLETE_ELLIPSIS_RE = re.compile(r"\.\.$|[.][.](?![.])")


@dataclass(slots=True)
class SourceQualityGateResult:
    should_translate: bool
    warnings: list[str]
    categories: list[str]


class SourceQualityGate:
    """Pre-translation guard for source text that is too risky to translate.

    Translation quality collapses when OCR has already lost punctuation, clipped
    text, or fused SFX/dialogue. This gate runs after deterministic cleanup but
    before Argos so severe source issues become review work instead of bad FR.
    """

    _HOLD_CATEGORIES = {"zone_too_small", "split_bubble", "fused_bubble", "sfx_mixed"}

    @staticmethod
    def _compact(text: str) -> str:
        return " ".join(str(text).strip().split())

    @staticmethod
    def _words(text: str) -> list[str]:
        return [word.lower().strip("'") for word in _ASCII_WORD_RE.findall(text)]

    def evaluate(
        self,
        block: OcrBlock,
        source_lang: SourceLang,
        *,
        raw_source_text: str,
        normalized_source_text: str,
    ) -> SourceQualityGateResult:
        if source_lang != "en":
            return SourceQualityGateResult(True, [], [])

        raw = self._compact(raw_source_text)
        normalized = self._compact(normalized_source_text or raw)
        if not normalized:
            return SourceQualityGateResult(False, ["preflight: source vide avant traduction"], ["empty"])

        categories = zone_issue_categories(normalized)
        warnings = [f"preflight: {warning}" for warning in zone_quality_warnings(normalized)]
        words = self._words(normalized)

        if _QUESTION_START_RE.search(normalized) and "?" not in normalized:
            warnings.append("preflight: point d'interrogation probablement manquant avant traduction")
        if _INCOMPLETE_ELLIPSIS_RE.search(normalized):
            warnings.append("preflight: points de suspension incomplets avant traduction")
        if re.search(r"\b[A-Za-z]{2,}-\s+[A-Za-z]{2,}\b", raw):
            warnings.append("preflight: cesure OCR probable avant traduction")
        if re.search(r"[=()%@#]", raw):
            warnings.append("preflight: symbole OCR suspect avant traduction")
        if re.search(r"[A-Za-z]+[0-9]+|[0-9]+[A-Za-z]+|[$]", raw):
            warnings.append("preflight: confusion chiffre/lettre probable avant traduction")
        if len(words) >= 4 and re.search(r"[A-Za-z0-9\"')]$", normalized):
            warnings.append("preflight: ponctuation finale possiblement manquante avant traduction")

        can_hold = block.manual_status in {"unchecked", "review"}
        should_hold = can_hold and bool(set(categories) & self._HOLD_CATEGORIES)
        if should_hold:
            warnings.insert(0, "preflight: traduction suspendue, source anglaise trop incertaine")

        deduped: list[str] = []
        for warning in warnings:
            if warning not in deduped:
                deduped.append(warning)
        return SourceQualityGateResult(not should_hold, deduped, categories)
