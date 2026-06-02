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
_VISUAL_EDGE_WARNING_RE = re.compile(
    r"(?:zone visuelle|bord du crop|bbox probablement trop petite|texte touche le bord)",
    flags=re.IGNORECASE,
)


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

    _HARD_HOLD_CATEGORIES = {"split_bubble", "fused_bubble", "sfx_mixed"}

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
        visual_edge = any(_VISUAL_EDGE_WARNING_RE.search(warning) for warning in block.quality_warnings)
        risky_visual_edge = visual_edge and (
            (block.confidence is not None and block.confidence < 0.70)
            or len(words) <= 3
            or not re.search(r"[.!?][\"')\]]?$", normalized)
            or bool(re.search(r"\b[A-Za-z]{2,}-\s+[A-Za-z]{2,}\b", raw))
        )
        if risky_visual_edge:
            categories.append("visual_edge")
            warnings.append("preflight: zone visuelle au bord du crop, bbox a verifier avant traduction")

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
        category_set = set(categories)
        hard_hold = bool(category_set & self._HARD_HOLD_CATEGORIES)
        has_terminal_punctuation = bool(re.search(r"[.!?][\"')\]]?$", normalized))
        too_small_hold = "zone_too_small" in category_set and (len(words) <= 2 or not has_terminal_punctuation)
        visual_hold = "visual_edge" in category_set and (
            len(words) <= 1
            or (block.confidence is not None and block.confidence < 0.45 and len(words) <= 2)
        )
        should_hold = can_hold and (hard_hold or too_small_hold or visual_hold)
        if should_hold:
            warnings.insert(0, "preflight: traduction suspendue, source anglaise trop incertaine")
        elif can_hold and category_set:
            warnings.insert(0, "preflight: traduction brouillon proposee, zone/source a verifier")

        deduped: list[str] = []
        for warning in warnings:
            if warning not in deduped:
                deduped.append(warning)
        return SourceQualityGateResult(not should_hold, deduped, categories)
