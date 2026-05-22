from __future__ import annotations

import re

_SFX_EDGE_RE = re.compile(
    r"^(whisper|sob|shock|jaka|sfx|bam|bang|boom|thud|clap|rustle|slam|tap|jolt|gasp)\b[.!?:, -]*"
    r"|\s+\b(whisper|sob|shock|jaka|sfx|bam|bang|boom|thud|clap|rustle|slam|tap|jolt|gasp)[.!?:, -]*$",
    flags=re.IGNORECASE,
)

_WORD_RE = re.compile(r"[A-Za-z][A-Za-z'’.-]*")
_APOSTROPHE_REPLACEMENTS = {
    "i'm": "I'm",
    "i’d": "I'd",
    "i'd": "I'd",
    "i’ll": "I'll",
    "i'll": "I'll",
    "i’ve": "I've",
    "i've": "I've",
}



_COMMON_OCR_WORD_FIXES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bEnolgh\b", flags=re.IGNORECASE), "enough"),
    (re.compile(r"\bFOLR\b", flags=re.IGNORECASE), "four"),
    (re.compile(r"\bFopm\b", flags=re.IGNORECASE), "form"),
    (re.compile(r"\bColld\b", flags=re.IGNORECASE), "could"),
    (re.compile(r"\bALl\b"), "all"),
    (re.compile(r"\bAlll\b", flags=re.IGNORECASE), "all"),
    (re.compile(r"\bNOL\b", flags=re.IGNORECASE), "no"),
    (re.compile(r"\bCant\b", flags=re.IGNORECASE), "can't"),
    (re.compile(r"\bchabter\b", flags=re.IGNORECASE), "chapter"),
    (re.compile(r"\bReSpect\b"), "respect"),
    (re.compile(r"\bHlnger\b", flags=re.IGNORECASE), "hunger"),
    (re.compile(r"\bHundped\b", flags=re.IGNORECASE), "Hundred"),
    (re.compile(r"\bHLNDRED\b", flags=re.IGNORECASE), "hundred"),
    (re.compile(r"\bTepm\b", flags=re.IGNORECASE), "term"),
    (re.compile(r"\bKAWAZL\b", flags=re.IGNORECASE), "KAWAZU"),
    (re.compile(r"\bYol\b", flags=re.IGNORECASE), "you"),
    (re.compile(r"\bPEALLYI?\b", flags=re.IGNORECASE), "really"),
    (re.compile(r"\bWHAATI?\b", flags=re.IGNORECASE), "what"),
    (re.compile(r"\bWHOAL\b", flags=re.IGNORECASE), "whoa!"),
    (re.compile(r"\bSepiously\b", flags=re.IGNORECASE), "seriously"),
    (re.compile(r"\bDont\b", flags=re.IGNORECASE), "don't"),
    (re.compile(r"\bDoesnt\b", flags=re.IGNORECASE), "doesn't"),
    (re.compile(r"\bApen['’]?t\b", flags=re.IGNORECASE), "aren't"),
    (re.compile(r"\bTHANKFLL\b", flags=re.IGNORECASE), "thankful"),
    (re.compile(r"\byolp\b", flags=re.IGNORECASE), "your"),
    (re.compile(r"\bVictopy\b", flags=re.IGNORECASE), "Victory"),
    (re.compile(r"\bMinel!?", flags=re.IGNORECASE), "Mine!"),
    (re.compile(r"\bPlnk\b", flags=re.IGNORECASE), "Punk"),
    (re.compile(r"\bPlink\b", flags=re.IGNORECASE), "Punk"),
    (re.compile(r"\bFop\b", flags=re.IGNORECASE), "For"),
    (re.compile(r"\bTOOI\b", flags=re.IGNORECASE), "too!"),
    (re.compile(r"\bCAREFLL\b", flags=re.IGNORECASE), "careful"),
    (re.compile(r"\bNLISANCE\b", flags=re.IGNORECASE), "nuisance"),
    (re.compile(r"\bFljimura-kln\b", flags=re.IGNORECASE), "Fujimura-kun"),
    (re.compile(r"\bTholght\b", flags=re.IGNORECASE), "thought"),
    (re.compile(r"\bWMP[o0]RTANT\b", flags=re.IGNORECASE), "IMPORTANT"),
    (re.compile(r"\bWHAAAI\b", flags=re.IGNORECASE), "WHAAAT"),
    (re.compile(r"\bBREASTSI!?", flags=re.IGNORECASE), "breasts!!"),
    (re.compile(r"\bt0\b", flags=re.IGNORECASE), "to"),
    (re.compile(r"\bPpomise\b", flags=re.IGNORECASE), "Promise"),
    (re.compile(r"\bTOMORPOW\b", flags=re.IGNORECASE), "TOMORROW"),
    (re.compile(r"\bIives\b", flags=re.IGNORECASE), "lives"),
    (re.compile(r"\bFeelig\b", flags=re.IGNORECASE), "Feeling"),
    (re.compile(r"\bTHHIS\b", flags=re.IGNORECASE), "THIS"),
    (re.compile(r"\bI50\b", flags=re.IGNORECASE), "150"),
    (re.compile(r"\b2Oth\b", flags=re.IGNORECASE), "20th"),
    (re.compile(r"\bSth\b", flags=re.IGNORECASE), "5th"),
    (re.compile(r"\bNO\s+WAYI\b", flags=re.IGNORECASE), "no way!"),
    (re.compile(r"\bLNNECESSARY\b", flags=re.IGNORECASE), "unnecessary"),
    (re.compile(r"\bLNNECES\b", flags=re.IGNORECASE), "unnecessary"),
    (re.compile(r"\bINDIVIDLALS\b", flags=re.IGNORECASE), "individuals"),
    (re.compile(r"\bWAS\b"), "was"),
    (re.compile(r"\bWERE\b"), "were"),
    (re.compile(r"\bHAVE\b"), "have"),
    (re.compile(r"\bDAYS\b"), "days"),
    (re.compile(r"\bAgo\b"), "ago"),
)

_CONTEXTUAL_OCR_FIXES: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(r"\bbmusthvb\s+gallenl\s+asle+p\s+inifront\s+computers?\b", flags=re.IGNORECASE),
        "I must've fallen asleep in front of my computer.",
    ),
    (re.compile(r"\bI\s+know\s+1\s+have\b", flags=re.IGNORECASE), "I know I have"),
    (re.compile(r"\bI\s+HAVE\s+No\b", flags=re.IGNORECASE), "I have no"),
    (re.compile(r"\bMY\s+MIND\s+WAS\s+With\s+Hunger\b", flags=re.IGNORECASE), "my mind was with hunger"),
    (re.compile(r"\bmis-\s*UNDERSTAND-\s*ing\b", flags=re.IGNORECASE), "misunderstanding"),
    (re.compile(r"\bSome-\s*Thing\b", flags=re.IGNORECASE), "something"),
    (re.compile(r"\bTROU-\s*bling\b", flags=re.IGNORECASE), "troubling"),
    (re.compile(r"\bYester-\s*DAY\b", flags=re.IGNORECASE), "yesterday"),
    (re.compile(r"\bUN-\s*CONTROLLED\b", flags=re.IGNORECASE), "uncontrolled"),
    (re.compile(r"\bPAR-\s*Ticu-\s*LAR\b", flags=re.IGNORECASE), "particular"),
    (re.compile(r"\bqualif\s+ication\b", flags=re.IGNORECASE), "qualification"),
    (re.compile(r"\bodfrom\b", flags=re.IGNORECASE), "...from"),
    (re.compile(r"\bWorldo\b", flags=re.IGNORECASE), "World."),
    (re.compile(r"\b4\s+(?=High\s+SCHOOL|high\s+school)\b", flags=re.IGNORECASE), "a "),
    (re.compile(r"\barb\s+What\s+saying\??\s+You\b", flags=re.IGNORECASE), "What are you saying?"),
    (re.compile(r"\bWHAT\s+Is\s+THAT\?\s+I\b", flags=re.IGNORECASE), "what is that?!"),
    (re.compile(r"\bMAKE\s+A\s+RUN\s+FOR\s+It,?\s*$", flags=re.IGNORECASE), "make a run for it, you two."),
    (re.compile(r"\bWE\s+HERE\s+FOR\s+Miss\s+NATSUKO\s+AND[:.,\s]*$", flags=re.IGNORECASE), "we are here for miss natsuko and..."),
    (re.compile(r"\bLISTEN,\s*Yuki[:.]\s*$", flags=re.IGNORECASE), "LISTEN, Yuki..."),
    (re.compile(r"\bSO\s+Why,\s*$", flags=re.IGNORECASE), "SO Why..."),
    (re.compile(r"\bLET'?S\s+See\s*$", flags=re.IGNORECASE), "LET'S See here..."),
    (re.compile(r"\bIF\s+ONE\s+ENER\s+IS\s+About\s+one\s+HLNDRED\s+YEN[:,.\s]*$", flags=re.IGNORECASE), "if one ener is about one hundred yen..."),
)


def normalize_spacing_and_punctuation(text: str) -> str:
    """Normalize OCR punctuation without changing meaning."""
    value = " ".join(str(text).replace("’", "'").strip().split())
    if not value:
        return ""
    # OCR often inserts hyphens at line breaks: CIRCUM- STANCES, TRANS- FORMED, proper- ty.
    previous = None
    while previous != value:
        previous = value
        value = re.sub(r"(?i)\b([a-z]{2,})-\s+([a-z]{2,})\b", lambda m: m.group(1) + m.group(2), value)
    if value.count(";") and len(_WORD_RE.findall(value)) <= 8:
        value = value.replace(";", ",")
    value = re.sub(r"\s+([,.;:!?])", r"\1", value)
    value = re.sub(r"([,.;:!?])(?=\S)", r"\1 ", value)
    value = re.sub(r"(?<=\d),\s+(?=\d{3}\b)", ",", value)
    value = re.sub(r"([!?.,;:])\s+([!?.,;:])", r"\1\2", value)
    value = re.sub(r"\.\s*\.\s*\.\s*", "...", value)
    value = re.sub(r"(?<!\.)\.\.(?!\.)", ".", value)
    value = re.sub(r":\s*,?\s*\.$", "...", value)
    value = re.sub(r":\s*$", ".", value)
    return " ".join(value.split())


def _is_random_case_word(word: str) -> bool:
    letters = [char for char in word if char.isalpha()]
    if len(letters) < 3:
        return False
    has_lower = any(char.islower() for char in letters)
    has_upper = any(char.isupper() for char in letters)
    if not (has_lower and has_upper):
        return False
    return not (letters[0].isupper() and all(char.islower() for char in letters[1:]))


def has_random_ocr_casing(text: str) -> bool:
    words = _WORD_RE.findall(str(text))
    if not words:
        return False
    random_words = [word for word in words if _is_random_case_word(word)]
    uppercase_words = [word for word in words if len(word) >= 3 and word.upper() == word]
    ratio = len(random_words) / max(1, len(words))
    return len(random_words) >= 1 and (ratio >= 0.15 or len(uppercase_words) >= 2)


def normalize_english_ocr_casing(text: str) -> str:
    """Fix random EasyOCR casing while keeping intentional all-caps dialogue."""
    value = normalize_spacing_and_punctuation(text)
    if not value:
        return ""
    words = _WORD_RE.findall(value)
    if not words:
        return value
    all_alpha = "".join(char for char in value if char.isalpha())
    if all_alpha and all_alpha.upper() == all_alpha:
        return value
    if not has_random_ocr_casing(value):
        return value
    lowered = value.lower()
    lowered = re.sub(r"\bi\b", "I", lowered)
    for src, dst in _APOSTROPHE_REPLACEMENTS.items():
        lowered = re.sub(rf"\b{re.escape(src)}\b", dst, lowered)
    lowered = re.sub(r"\bmiwa\s*-\s*nee\b", "Miwa-nee", lowered, flags=re.IGNORECASE)
    lowered = re.sub(r"\bnaru\b", "Naru", lowered, flags=re.IGNORECASE)
    lowered = normalize_spacing_and_punctuation(lowered)
    first_alpha = next((char for char in value if char.isalpha()), "")
    if first_alpha.isupper() and lowered and lowered[0].isalpha():
        lowered = lowered[0].upper() + lowered[1:]
    return lowered


def normalize_ocr_text_for_translation(text: str) -> str:
    value = normalize_english_ocr_casing(normalize_spacing_and_punctuation(text))
    if len(_WORD_RE.findall(value)) >= 5:
        previous = None
        while previous != value:
            previous = value
            value = _SFX_EDGE_RE.sub("", value).strip()
            value = normalize_spacing_and_punctuation(value)
    for pattern, replacement in _COMMON_OCR_WORD_FIXES:
        value = pattern.sub(replacement, value)
    for pattern, replacement in _CONTEXTUAL_OCR_FIXES:
        value = pattern.sub(replacement, value)
    value = normalize_english_ocr_casing(normalize_spacing_and_punctuation(value))
    return value
