from __future__ import annotations

import re
from collections.abc import Iterable

from cbz_manga_translator.core.models import OcrBlock, SourceLang
from cbz_manga_translator.ocr.incomplete import zone_quality_warnings

_WORD_RE = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ']+")
_ASCII_WORD_RE = re.compile(r"[A-Za-z']+")
_ASCII_OR_DIGIT_WORD_RE = re.compile(r"[A-Za-z0-9']+")
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
    "'tis",
    "tis",
    "donezo",
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
    (re.compile(r"\b(?:didnta|closb|boprow|pepson|loks|ahemi|secl|4nder|ou'd)\b", flags=re.IGNORECASE), "OCR probable: token appris du dernier batch à vérifier"),
    (re.compile(r"\b(?:big-twme|fltile|full3|shiti|folind|sholld|withoraw|fortlne|communiies|mlch|y0u|ldoes|wrone|hlnt|g0t|momey|calght|rlnaway|bandis|thepe)\b", flags=re.IGNORECASE), "OCR probable: token appris des corrections récentes à vérifier"),
    (re.compile(r"\b(?:could|should|would)\s+ve\b", flags=re.IGNORECASE), "contraction anglaise probable: lire could've/should've/would've"),
    (re.compile(r"\b(?:im|ive|ill|id)\b", flags=re.IGNORECASE), "contraction avec I probable: vérifier I'm/I've/I'll/I'd"),
    (re.compile(r"\b(?:tslrlmi|napehouse|nestern|individlals)\b", flags=re.IGNORECASE), "OCR probable: token inconnu/rompu à vérifier"),
    (re.compile(r"\bbmusthvb\s+gallenl\s+asle+p\s+inifront\s+computers?\b", flags=re.IGNORECASE), "OCR évident: devrait être \"I must've fallen asleep in front of my computer\""),
    (re.compile(r"\b(?:rlpted|lnneces|hideolt|yol|iwas|idont|iguess|wolld|bizarpe|wopld|iaeely|lessil|evepy|theip|dsich|aohto|dollarman|thess|bmusthvb|gallenl|aslep|inifront|t0)\b", flags=re.IGNORECASE), "OCR probable: token appris du corpus à vérifier"),
    (
        re.compile(
            r"\b(?:lrabe|colincil|colncil|wolld|becalse|o4t|youl|seriolsly|unapmed|supve|"
            r"tkinbs|doine|kin[o0]a|dancepols|unneces+aqy|jols|s4y|men[.]{3}\s*tioned|"
            r"st[ul][.]{3}\s*dent|exx?[.]{3}\s*istence|al[.]{3}\s*read|what\s+9i)\b",
            flags=re.IGNORECASE,
        ),
        "profil fonte manga: confusion U/L/I/!/1 probable",
    ),
)

_VISUAL_WORD_TRANSLATION = str.maketrans(
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
    }
)
_COMMON_ENGLISH_WORDS = {
    "about",
    "after",
    "always",
    "are",
    "because",
    "big",
    "care",
    "could",
    "details",
    "easier",
    "for",
    "full",
    "goal",
    "have",
    "long",
    "man",
    "my",
    "report",
    "right",
    "romance",
    "should",
    "small",
    "strange",
    "target",
    "that",
    "their",
    "then",
    "there",
    "tomorrow",
    "too",
    "want",
    "waited",
    "what",
    "would",
}
_I_CONTRACTION_CONFUSION_RE = re.compile(r"\b[l1!]\s*[' ]?(?:m|ve|d|ll)\b", flags=re.IGNORECASE)

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
    "right",
    "gotta",
    "basically",
    "then",
}

_LIKELY_MISSING_PREFIX_STARTS = {
    "have",
    "left",
    "saved",
    "where",
    "but",
    "and",
    "then",
    "with",
    "maybe",
    "after",
    "right",
    "only",
    "where",
}

_LIKELY_MISSING_SUFFIX_ENDS = {
    "on",
    "give",
    "goes",
    "gotta",
    "hey",
    "and",
    "about",
    "guys",
    "basically",
    "then",
}

_SAFE_UPPERCASE_TOKENS = {
    "OK", "NON", "SFX", "RASHOMON", "DAZAI", "TANIZAKI", "ATSUSHI", "NAOMI", "KUNIKIDA",
}

_TRANSLATION_ENGLISH_RESIDUE_RE = re.compile(
    r"\b(?:orphanage|food|shelter|steal|tiger|agency|skills?|earn|master|animal|form|staff|"
    r"backup|sake|bomb|dampen|explosion|button|press|company|dorm|posthaste|lad|ideals|"
    r"mafia|battle|fault|cry|days?|place|else|worldly|knowledge|individuals?|bandit|star|"
    r"mercenary|guy|dollarman|fick|smug|slam|contents|beans?)\b",
    flags=re.IGNORECASE,
)

_SAFE_SOURCE_RESIDUE = {
    "naru", "miwa", "atsushi", "dazai", "kanade", "fujimura", "usami", "rashomon",
    "gozen", "kariu", "vayne", "provost", "ichinose", "public", "transit",
    "cool", "elizabeth", "hardcore", "rock", "service", "boss",
}

_SEVERE_WARNING_FRAGMENTS = (
    "traduction vide",
    "traduction identique",
    "residu anglais",
    "rÃ©sidu anglais",
    "mots anglais restants",
    "termes source recopi",
    "peu d'indices de fran",
    "japonais residuel",
    "japonais rÃ©siduel",
    "source probablement non japonaise",
    "zone/bulle probablement incomplete",
    "zone trop petite probable",
    "bulle probablement separee",
    "fusion probable",
    "SFX probablement melange",
)


def _copied_source_residue(source: str, translation: str) -> list[str]:
    source_tokens = {token.lower().strip("'") for token in _ASCII_WORD_RE.findall(source) if len(token) >= 4}
    translation_tokens = {token.lower().strip("'") for token in _ASCII_WORD_RE.findall(translation) if len(token) >= 4}
    return sorted((source_tokens & translation_tokens) - _SAFE_SOURCE_RESIDUE)


def _visual_word(token: str) -> str:
    return token.lower().translate(_VISUAL_WORD_TRANSLATION).strip("'")


def _english_plausibility_warnings(text: str) -> list[str]:
    warnings: list[str] = []
    tokens = _ASCII_OR_DIGIT_WORD_RE.findall(text)
    if not tokens:
        return warnings

    visual_matches: list[str] = []
    digit_mixed: list[str] = []
    for token in tokens:
        lowered = token.lower().strip("'")
        if re.search(r"[A-Za-z]", token) and re.search(r"\d", token):
            digit_mixed.append(token)
            visual = _visual_word(token)
            if visual in _COMMON_ENGLISH_WORDS and visual != lowered:
                visual_matches.append(f"{token}->{visual}")

    if visual_matches:
        warnings.append("OCR semantique: token visuellement proche d'un mot anglais (" + ", ".join(visual_matches[:3]) + ")")
    elif digit_mixed:
        warnings.append("confusion OCR chiffre/lettre probable: " + ", ".join(digit_mixed[:3]))

    if _I_CONTRACTION_CONFUSION_RE.search(text):
        warnings.append("contraction avec I mal lue probable: verifier I'm/I've/I'd/I'll")

    long_weird = [
        token
        for token in tokens
        if len(token) >= 7
        and not re.search(r"[aeiouy]", _visual_word(token))
        and token.upper() not in _SAFE_UPPERCASE_TOKENS
    ]
    if len(long_weird) >= 2:
        warnings.append("anglais source peu plausible: tokens OCR suspects (" + ", ".join(long_weird[:3]) + ")")

    return warnings


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

    @staticmethod
    def _looks_like_non_japanese_source(text: str) -> bool:
        japanese_chars = len(_JAPANESE_RE.findall(text))
        ascii_tokens = _ASCII_WORD_RE.findall(text)
        if japanese_chars >= 2 or len(ascii_tokens) < 3:
            return False
        if _FRENCH_SIGNAL_RE.search(text):
            return True
        latin_letters = sum(1 for char in text if ("A" <= char <= "Z") or ("a" <= char <= "z"))
        return latin_letters >= 18 and len(ascii_tokens) >= 5

    @staticmethod
    def is_severe_warning(warning: str) -> bool:
        normalized = warning.lower()
        return any(fragment.lower() in normalized for fragment in _SEVERE_WARNING_FRAGMENTS)

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

        if lang == "ja" and self._looks_like_non_japanese_source(source):
            warnings.append("source probablement non japonaise: verifier le dossier corpus ou source-lang")

        if not translation:
            if lang == "ja":
                warnings.append("fragment japonais non traduit: OCR trop court/faible")
            warnings.append("traduction vide")
            return warnings

        if lang == "en":
            source_tokens = set(self._tokens(source))
            corrected_tokens = set(self._tokens(corrected))
            normalized_tokens = set(self._tokens(normalized))
            slang_hits = sorted((source_tokens | corrected_tokens) & _SOURCE_SLANG_WORDS)

            structure_source = normalized or corrected or source
            warnings.extend(zone_quality_warnings(structure_source))
            warnings.extend(_english_plausibility_warnings(structure_source))
            source_word_list = self._ascii_tokens(structure_source)
            if len(source_word_list) == 1 and source_word_list[0] in _FRAGMENT_ONLY_WORDS:
                warnings.append("fragment OCR isolé probable: vérifier/fusionner avec une bulle voisine")
            if len(source_word_list) <= 2 and structure_source.strip().endswith(":"):
                warnings.append("fragment OCR terminé par ':' probable: vérifier/fusionner")
            if ":" in source and not re.search(r"\b(?:chapter|vol|volume|no|number|page)\s*:", source, flags=re.IGNORECASE):
                warnings.append("ponctuation ':' suspecte: souvent '.', '...', '!' ou '?' en fonte manga")
            has_terminal_punctuation = bool(re.search(r"[.!?][\"')\]]?$", structure_source.strip()))
            if re.match(r"(?i)^\s*(?:what|why|how|where|when|who|is|are|do|did|does|can|could|would|should|will)\b", structure_source):
                if "?" not in structure_source:
                    warnings.append("point d'interrogation probablement manquant: relire la ponctuation de la bulle")
            if source_word_list and source_word_list[0] in _LIKELY_MISSING_PREFIX_STARTS and not has_terminal_punctuation:
                warnings.append("début de phrase possiblement manquant: en manga vérifier aussi la bulle à droite")
            if source_word_list and source_word_list[-1] in _LIKELY_MISSING_SUFFIX_ENDS:
                warnings.append("fin de bulle possiblement manquante: vérifier la suite du texte")
            if len(source_word_list) <= 5 and re.search(r"(?i)\b(?:and this is what|only found|wait a sec|basically|then|god|where will it end)\b", structure_source):
                warnings.append("zone de texte probablement trop courte: OCR à relire avec crop élargi/fallback")
            if len(source_word_list) >= 4 and re.search(r"[A-Za-z0-9\"')]$", structure_source):
                warnings.append("ponctuation finale possiblement manquante")
            if len(source_word_list) >= 3 and re.search(r"[:,]\s*$", source):
                warnings.append("fin en ':' ou ',' suspecte: probablement ellipse ou ponctuation forte")
            if structure_source.strip().startswith("..."):
                warnings.append("fragment commençant par ellipse: probablement suite d'une bulle précédente")
            if re.search(r"\.\.$|[.][.](?![.])", structure_source):
                warnings.append("points de suspension incomplets: normaliser en '...' ou '...?'")
            if re.search(r"[=()%@#]", source):
                warnings.append("symboles OCR suspects dans le texte: relire la bulle complète")
            if re.search(r"(?i)\b(?:krehble|krembue|shivr|jmile|fwoop|brip|whooosh|sfx)\b", source) and len(source_word_list) >= 3:
                warnings.append("SFX probablement fusionné avec une bulle: séparer/ignorer la zone sonore")
            if re.fullmatch(r"(?i)right[?.]?", structure_source.strip()):
                warnings.append("ambiguïté: 'right?' peut signifier 'n'est-ce pas ?' selon le contexte")
            if re.search(r"(?i)\b(?:stats|slime|handy|clear my name|come up with|don't be silly|no way|here you go)\b", structure_source):
                warnings.append("expression anglaise/contextuelle: vérifier le rendu naturel en français")
            sentence_breaks = re.findall(r"[.!?][\"')\]]?(?=\s+[A-Z\"'])", structure_source)
            if len(source_word_list) >= 14 and sentence_breaks:
                warnings.append("bloc long avec plusieurs phrases: vérifier si deux bulles ont été fusionnées")

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
            if re.search(r"\b[A-Za-z]{2,}-\s*(?:what|who|where|why|huh)\b", source, flags=re.IGNORECASE):
                warnings.append("mot volontairement coupé: conserver la coupure si elle porte le sens")

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
            preserved = [
                warning for warning in block.quality_warnings
                if warning.startswith("preflight:") or warning.startswith("OCR ")
            ]
            block.quality_warnings = []
            for warning in preserved + self.check_block(block, source_lang=source_lang):
                if warning not in block.quality_warnings:
                    block.quality_warnings.append(warning)
            if block.quality_warnings:
                flagged += 1
                if block.manual_status == "unchecked" and any(self.is_severe_warning(warning) for warning in block.quality_warnings):
                    block.manual_status = "review"
                    if not block.review_notes.strip():
                        block.review_notes = "[postflight] traduction/source a verifier avant validation"
        return flagged
