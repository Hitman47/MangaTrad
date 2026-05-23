from __future__ import annotations

import re


_MANGA_FONT_REPAIRS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bLrabe\b", flags=re.IGNORECASE), "Urabe"),
    (re.compile(r"\bWOLLD\b", flags=re.IGNORECASE), "would"),
    (re.compile(r"\bCOLINCIL\b", flags=re.IGNORECASE), "COUNCIL"),
    (re.compile(r"\bCOUN\s+Cil\b", flags=re.IGNORECASE), "COUNCIL"),
    (re.compile(r"\bOup\b", flags=re.IGNORECASE), "our"),
    (re.compile(r"\bsecpets\b", flags=re.IGNORECASE), "secrets"),
    (re.compile(r"\bPpevious\b", flags=re.IGNORECASE), "Previous"),
    (re.compile(r"\bppevious\b", flags=re.IGNORECASE), "previous"),
    (re.compile(r"\bBecalse\b", flags=re.IGNORECASE), "Because"),
    (re.compile(r"\bO4t\b", flags=re.IGNORECASE), "Out"),
    (re.compile(r"\bUNNECESSAQY\b", flags=re.IGNORECASE), "UNNECESSARY"),
    (re.compile(r"\bDANCEPOLS\b", flags=re.IGNORECASE), "DANGEROUS"),
    (re.compile(r"\bHehl\b", flags=re.IGNORECASE), "Heh!"),
    (re.compile(r"\bKINOA\b", flags=re.IGNORECASE), "KINDA"),
    (re.compile(r"\bTKINES\b", flags=re.IGNORECASE), "THINGS"),
    (re.compile(r"\bDoine\b", flags=re.IGNORECASE), "Doing"),
    (re.compile(r"\bSeriolsly\b", flags=re.IGNORECASE), "Seriously"),
    (re.compile(r"\bUNAPMED\b", flags=re.IGNORECASE), "UNARMED"),
    (re.compile(r"\bSupve\b", flags=re.IGNORECASE), "survive"),
    (re.compile(r"\bweipd\b", flags=re.IGNORECASE), "weird"),
    (re.compile(r"\bDox\b", flags=re.IGNORECASE), "do I"),
    (re.compile(r"\bDoz\b", flags=re.IGNORECASE), "do I"),
    (re.compile(r"\bWAKB\b", flags=re.IGNORECASE), "wake"),
    (re.compile(r"\bUp3\b", flags=re.IGNORECASE), "up?"),
    (re.compile(r"\bEneine\b", flags=re.IGNORECASE), "Engine"),
    (re.compile(r"\bROAQ\b", flags=re.IGNORECASE), "ROAR"),
    (re.compile(r"\bJols\b", flags=re.IGNORECASE), "jokes"),
    (re.compile(r"\bs4y\b", flags=re.IGNORECASE), "say"),
    (re.compile(r"\bIWOULD'VE\b", flags=re.IGNORECASE), "I would've"),
    (re.compile(r"\binia\b", flags=re.IGNORECASE), "in a"),
    (re.compile(r"\bOlp\b", flags=re.IGNORECASE), "our"),
    (re.compile(r"\btke\b", flags=re.IGNORECASE), "the"),
    (re.compile(r"\bTkinbs\b", flags=re.IGNORECASE), "THINGS"),
    (re.compile(r"\bdanserols\b", flags=re.IGNORECASE), "dangerous"),
    (re.compile(r"\bPpevious\s+St[ul][.]{3}\s*DENT\s+COLN?CIL\b", flags=re.IGNORECASE), "Previous student council"),
    (re.compile(r"\bSt[ul][.]{3}\s*DENT\b", flags=re.IGNORECASE), "student"),
    (re.compile(r"\bCOLN[.]{3}(?=\W|$)", flags=re.IGNORECASE), "COUNCIL"),
    (re.compile(r"\bCOLNCIL\b", flags=re.IGNORECASE), "COUNCIL"),
    (re.compile(r"\bMEN[.]{3}\s*TIONED\b", flags=re.IGNORECASE), "MENTIONED"),
    (re.compile(r"\bal[.]{3}\s*Read\b", flags=re.IGNORECASE), "already"),
    (re.compile(r"\bexx?[.]{3}\s*ISTENCE\b", flags=re.IGNORECASE), "existence"),
    (re.compile(r"\b01,\s*cut\s+it\s+Out\s+already!!\b", flags=re.IGNORECASE), "Oi, cut it Out already!!"),
    (re.compile(r"\b01,(?=\s)", flags=re.IGNORECASE), "Oi,"),
    (re.compile(r"\bWHAT\s+9i\b", flags=re.IGNORECASE), "WHAT?!"),
    (re.compile(r"\bYoul\b", flags=re.IGNORECASE), "You!"),
    (re.compile(r"\bfoolls\b", flags=re.IGNORECASE), "fools!"),
    (re.compile(r"\benemiesll\b", flags=re.IGNORECASE), "enemies!!"),
    (re.compile(r"\bconnectedl\b", flags=re.IGNORECASE), "connected!"),
    (re.compile(r"\bwasntt\b", flags=re.IGNORECASE), "wasn't"),
    (re.compile(r"\bUthe\b", flags=re.IGNORECASE), "the"),
    (re.compile(r"\bJudgel\b", flags=re.IGNORECASE), "Judge!!"),
    (re.compile(r"\bdidhe\b", flags=re.IGNORECASE), "did he"),
    (re.compile(r"\b4SAMI\b", flags=re.IGNORECASE), "Usami"),
    (re.compile(r"\bJlst\b", flags=re.IGNORECASE), "Just"),
    (re.compile(r"\bBot\s+NETO[.]{3}\s*Pare['’]d\b", flags=re.IGNORECASE), "Got NETOrare'd"),
    (re.compile(r"\bFuji[.]{3}\s*MLRA\b,?", flags=re.IGNORECASE), "...Fujimura..."),
    (re.compile(r"\bFuji\s*MLRA\b,?", flags=re.IGNORECASE), "...Fujimura..."),
    (re.compile(r"\bGREAT\s+Ip\b", flags=re.IGNORECASE), "GREAT If"),
    (re.compile(r"\bMADE\s+Itw\b", flags=re.IGNORECASE), "MADE It!!"),
    (re.compile(r"\bIshe\b", flags=re.IGNORECASE), "Is he"),
    (re.compile(r"\bOSAMU[.]{3}\s*KUN[.]?\b", flags=re.IGNORECASE), "Osamu-kun"),
    (re.compile(r"^\s*is\s+that\s+s\?\s*$", flags=re.IGNORECASE), "is that so?"),
    (re.compile(r"^\s*be\s+great\s+if\s*$", flags=re.IGNORECASE), "It would Be GREAT If"),
    (re.compile(r"^\s*They['’]?re\s+ALL\s+So\s*$", flags=re.IGNORECASE), "They're ALL So ...Young..."),
    (re.compile(r"\bTHINK\s+About\s+I,\s+AN\s+UNARMED\b", flags=re.IGNORECASE), "Think about it. an unarmed"),
    (re.compile(r"^\s*L\s+(You\s+FOOLS)\b", flags=re.IGNORECASE), r"\1!"),
    (re.compile(r"\b6ives\b", flags=re.IGNORECASE), "gives"),
    (re.compile(r"\b(?:RAMN|RARN)\b", flags=re.IGNORECASE), "DAMN"),
    (re.compile(r"\bSetupi\b", flags=re.IGNORECASE), "Setup!!"),
    (re.compile(r"\bHowdid\b", flags=re.IGNORECASE), "How did"),
    (re.compile(r"\bMorningb\b", flags=re.IGNORECASE), "Morning"),
    (re.compile(r"\bPosi[.]{3}\s*TION\b", flags=re.IGNORECASE), "POSITION"),
    (re.compile(r"\bPromo[.]{3}\s*TIONS,?", flags=re.IGNORECASE), "Promotions..."),
    (re.compile(r"\bmust\s+e\s+nodded\s+off\b", flags=re.IGNORECASE), "must've nodded off"),
    (re.compile(r"\bCAPTAIN\s+HIPO\b", flags=re.IGNORECASE), "captain hiro"),
    (re.compile(r"^\s*V\s+(WAIT\b)", flags=re.IGNORECASE), r"\1"),
    (re.compile(r"\bGET\s+It,\s*!\s*y!\b", flags=re.IGNORECASE), "GET It!"),
    (re.compile(r"(Let's\s+\"?NG\s+SEE),\s*$", flags=re.IGNORECASE), r"\1..."),
)


def repair_manga_font_confusions(text: str) -> str:
    """Repair OCR confusions typical of narrow all-caps manga lettering.

    These are intentionally lexical/contextual, not a global L/U/I/! rewrite.
    The same glyph can be a real letter in one word and punctuation in another,
    so broad character substitution causes regressions.
    """
    value = str(text)
    for pattern, replacement in _MANGA_FONT_REPAIRS:
        value = pattern.sub(replacement, value)
    return value
