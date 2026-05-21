from __future__ import annotations

import re
from collections.abc import Iterable

from cbz_manga_translator.core.models import OcrBlock, SourceLang

_WORD_RE = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ']+")
_ASCII_WORD_RE = re.compile(r"[A-Za-z']+")
_JAPANESE_RE = re.compile(r"[ぁ-んァ-ン一-龯々ー]")
_FRENCH_SIGNAL_RE = re.compile(
    r"\b(?:je|tu|il|elle|nous|vous|ils|elles|le|la|les|un|une|des|de|du|ce|cet|cette|ça|cela|"
    r"est|suis|sont|être|avoir|pas|ne|que|quoi|qui|où|pourquoi|comment|dans|sur|avec|sans|"
    r"regarde|grand|grand-mère|mère|père|monsieur|madame|maintenant|là-haut|dangereux|danger)",
    flags=re.IGNORECASE,
)

_ENGLISH_RESIDUE_WORDS = {
    "ain't",
    "aint",
    "ah",
    "ya",
    "yer",
    "y'all",
    "doin",
    "doing",
    "climbin",
    "climbing",
    "looky",
    "look",
    "gramma",
    "grandma",
    "told",
    "toid",
    "what",
    "where",
    "there",
    "here",
    "now",
    "dangerous",
    "contrail",
    "boy",
    "only",
    "being",
    "good",
    "orphanage",
    "food",
    "shelter",
    "steal",
    "tiger",
    "agency",
    "skills",
    "bomb",
    "button",
    "press",
    "battle",
    "fault",
    "cry",
    "days",
    "boss",
    "company",
    "dorm",
}

_SOURCE_SLANG_WORDS = {
    "ain't",
    "aint",
    "ah",
    "ya",
    "yer",
    "y'all",
    "doin",
    "goin",
    "comin",
    "climbin",
    "looky",
    "gramma",
    "grampa",
    "gonna",
    "wanna",
    "gotta",
    "lemme",
    "gimme",
    "outta",
    "kinda",
    "sorta",
    "cuz",
    "cos",
}

_OCR_CONFUSION_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bto[i1l!]d\b", flags=re.IGNORECASE), "OCR probable: 'toid/to1d' devrait être 'told'"),
    (re.compile(r"\bc[l1i!]imbin", flags=re.IGNORECASE), "OCR probable sur 'climbin/climbing'"),
    (re.compile(r"\bnarl[i1]?\b", flags=re.IGNORECASE), "OCR probable sur un nom propre: vérifier Naru/Nari/etc."),
    (re.compile(r"\benolgh\b", flags=re.IGNORECASE), "OCR probable: 'enolgh' devrait être 'enough'"),
    (re.compile(r"\bfolr\b", flags=re.IGNORECASE), "OCR probable: 'FOLR' devrait être 'four'"),
    (re.compile(r"\bfopm\b", flags=re.IGNORECASE), "OCR probable: 'Fopm' devrait être 'form'"),
    (re.compile(r"\bcolld\b", flags=re.IGNORECASE), "OCR probable: 'Colld' devrait être 'could'"),
    (re.compile(r"\bhlnger\b", flags=re.IGNORECASE), "OCR probable: 'Hlnger' devrait être 'hunger'"),
    (re.compile(r"\b(?:tslrlmi|napehouse|nestern|individlals)\b", flags=re.IGNORECASE), "OCR probable: token inconnu/rompu à vérifier"),
    (re.compile(r"\b(?:rlpted|lnneces|hideolt|yol|iwas|idont|iguess|wolld|bizarpe|wopld|iaeely|lessil|evepy|theip|dsich|aohto|dollarman|thess|bmusthvb|gallenl|aslep|inifront|t0)\b", flags=re.IGNORECASE), "OCR probable: token appris du corpus à vérifier"),
)

_BAD_FRAGMENTS_RE = re.compile(r"\b(?:TOLD\s+YA|I\s+TOLD|WHAT\s+YA|NO\s+CLIMB|LOOKY|GRAMMA|TOID)\b", flags=re.IGNORECASE)
_FRAGMENT_ONLY_WORDS = {
    "did",
    "do",
    "does",
    "with",
    "from",
    "that",
    "the",
    "or",
    "and",
    "but",
}

_SAFE_UPPERCASE_TOKENS = {
    "OK", "SFX", "RASHOMON", "DAZAI", "TANIZAKI", "ATSUSHI", "NAOMI", "KUNIKIDA",
}

_TRANSLATION_ENGLISH_RESIDUE_RE = re.compile(
    r"\b(?:orphanage|food|shelter|steal|tiger|agency|skills?|earn|master|animal|form|staff|"
    r"backup|sake|bomb|dampen|explosion|button|press|boss|company|dorm|posthaste|lad|ideals|"
    r"mafia|battle|fault|cry|days?|place|else|worldly|knowledge|individuals?|bandit|star|"
    r"mercenary|guy|dollarman|fick|smug|slam|contents|beans?)\b",
    flags=re.IGNORECASE,
)

_SAFE_SOURCE_RESIDUE = {"naru", "miwa", "atsushi", "dazai", "kanade", "fujimura", "usami", "rashomon"}


def _copied_source_residue(source: str, translation: str) -> list[str]:
    source_tokens = {token.lower().strip("'") for token in _ASCII_WORD_RE.findall(source) if len(token) >= 4}
    translation_tokens = {token.lower().strip("'") for token in _ASCII_WORD_RE.findall(translation) if len(token) >= 4}
    return sorted((source_tokens & translation_tokens) - _SAFE_SOURCE_RESIDUE)


class TranslationQualityChecker:
    """Cheap local heuristics to flag blocks that require manual review.

    This is deliberately not an LLM and does not call any paid API. It cannot
    prove a translation is correct; it only catches obvious nonsense, OCR
    confusions, English residue and low-confidence blocks.
    """

    def __init__(self, *, low_confidence: float = 0.55) -> None:
        self.low_confidence = low_confidence

    @staticmethod
    def _tokens(text: str) -> list[str]:
        return [token.lower().strip("'") for token in _WORD_RE.findall(text)]

    @staticmethod
    def _ascii_tokens(text: str) -> list[str]:
        return [token.lower().strip("'") for token in _ASCII_WORD_RE.findall(text)]

    @staticmethod
    def _normalized_for_identity(text: str) -> str:
        return re.sub(r"[^a-z0-9]+", "", text.lower())

    @staticmethod
    def _has_mostly_uppercase_residue(text: str) -> bool:
        words = _ASCII_WORD_RE.findall(text)
        if not words:
            return False
        uppercase_words = [
            word for word in words
            if len(word) >= 3 and word.upper() == word and word.upper() not in _SAFE_UPPERCASE_TOKENS
        ]
        return bool(uppercase_words)

    def check_block(self, block: OcrBlock, source_lang: SourceLang | None = None) -> list[str]:
        lang = source_lang or block.source_lang
        source = " ".join(block.ocr_text.split())
        corrected = " ".join(block.ocr_corrected_text.split())
        normalized = " ".join(block.normalized_source_text.split())
        raw_translation = " ".join(block.raw_translation_fr.split())
        translation = " ".join(block.translation_fr.split())
        warnings: list[str] = []

        if block.confidence is not None and block.confidence < self.low_confidence:
            warnings.append(f"OCR confiance basse ({block.confidence:.2f})")

        if not source:
            warnings.append("OCR vide")
            return warnings

        if not translation:
            warnings.append("traduction vide")
            return warnings

        if lang == "en":
            source_tokens = set(self._tokens(source))
            corrected_tokens = set(self._tokens(corrected))
            normalized_tokens = set(self._tokens(normalized))
            slang_hits = sorted((source_tokens | corrected_tokens) & _SOURCE_SLANG_WORDS)

            source_word_list = self._ascii_tokens(source)
            if len(source_word_list) == 1 and source_word_list[0] in _FRAGMENT_ONLY_WORDS:
                warnings.append("fragment OCR isolé probable: vérifier/fusionner avec une bulle voisine")
            if len(source_word_list) <= 2 and source.strip().endswith(":"):
                warnings.append("fragment OCR terminé par ':' probable: vérifier/fusionner")

            for pattern, message in _OCR_CONFUSION_PATTERNS:
                if pattern.search(source):
                    warnings.append(message)

            if _BAD_FRAGMENTS_RE.search(translation):
                warnings.append("résidu anglais évident dans la traduction")

            if re.search(r"\b(?:gramma|grandma)\b", source, flags=re.IGNORECASE) and not re.search(r"\blook", source, flags=re.IGNORECASE):
                if not re.search(r"\bregarde", translation, flags=re.IGNORECASE):
                    warnings.append("OCR probablement incomplet: bulle 'grandma/look' à vérifier")

            if normalized and normalized != source and raw_translation and raw_translation == translation:
                # Informative enough to diagnose, but only flag if the output is still suspicious below.
                pass

            translation_tokens = set(self._ascii_tokens(translation))
            residue_hits = sorted((translation_tokens & _ENGLISH_RESIDUE_WORDS) - {"naru"})
            if residue_hits:
                warnings.append("mots anglais restants: " + ", ".join(residue_hits[:4]))
            if _TRANSLATION_ENGLISH_RESIDUE_RE.search(translation):
                warnings.append("résidu anglais probable dans la traduction")
            copied = _copied_source_residue(source, translation)
            if copied:
                warnings.append("termes source recopiés dans la traduction: " + ", ".join(copied[:4]))
            if re.search(r"[A-Za-z]+[0-9]+|[0-9]+[A-Za-z]+|[$]", source):
                warnings.append("confusion OCR chiffre/symbole probable")

            source_identity = self._normalized_for_identity(source)
            translation_identity = self._normalized_for_identity(translation)
            if len(source_identity) >= 8 and source_identity == translation_identity:
                warnings.append("traduction identique à l'OCR")

            if self._has_mostly_uppercase_residue(translation):
                warnings.append("fragments MAJUSCULES suspects")
            if re.search(r"\b[A-Za-z]{2,}-\s+[A-Za-z]{2,}\b", source):
                warnings.append("césure OCR probable à corriger")

            if len(translation) >= 8 and not _FRENCH_SIGNAL_RE.search(translation) and re.search(r"[A-Za-z]", translation):
                # Do not overflag very short proper-name-only bubbles.
                source_word_count = len(self._ascii_tokens(source))
                if source_word_count >= 3:
                    warnings.append("peu d'indices de français naturel")

            if re.search(r"\bgamma\b", translation, flags=re.IGNORECASE) and re.search(r"\bgramma\b", source, flags=re.IGNORECASE):
                warnings.append("'gramma' probablement mal rendu: grand-mère")

            if slang_hits and warnings:
                warnings.append("anglais familier impliqué: " + ", ".join(slang_hits[:4]))

        elif lang == "ja":
            if _JAPANESE_RE.search(translation):
                warnings.append("japonais résiduel dans la traduction")
            if len(source) <= 2 and block.confidence is not None and block.confidence < 0.75:
                warnings.append("fragment japonais court peu fiable")

        # Remove duplicates while preserving order.
        deduped: list[str] = []
        for warning in warnings:
            if warning not in deduped:
                deduped.append(warning)
        return deduped

    def apply(self, blocks: Iterable[OcrBlock], source_lang: SourceLang | None = None) -> int:
        flagged = 0
        for block in blocks:
            if block.manual_status in {"validated", "ignored"}:
                block.quality_warnings = []
                continue
            block.quality_warnings = self.check_block(block, source_lang=source_lang)
            if block.quality_warnings:
                flagged += 1
        return flagged
