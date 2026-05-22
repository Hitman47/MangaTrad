from __future__ import annotations

import re


_EXACT_ELLIPSIS_REPAIRS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"^Oh\s+NO,\s+NOT\s+At\s+ALL[.]$", flags=re.IGNORECASE), "Oh NO, NOT At ALL..."),
    (
        re.compile(r"^So\s+THAT\s+Big-?time\s+job\s+You\s+Guys\s+Were\s+talking\s+About[.]$", flags=re.IGNORECASE),
        "So THAT Big-time job You Guys Were talking About...",
    ),
    (re.compile(r"^If\s+They['’]?re\s+Family[.]$", flags=re.IGNORECASE), "If They're Family..."),
    (re.compile(r"^Every\s+single[Il1]?\s+one\s+of\s+you[.]$", flags=re.IGNORECASE), "Every single one of you..."),
    (re.compile(r"^I\s+just\s+Thought\s+You\s+were\s+A\s+BANDIT[.]$", flags=re.IGNORECASE), "I just Thought You were A BANDIT..."),
    (
        re.compile(r"^And\s+if\s+[|I]\s+could\s+save\s+a\s+citizen\s+of\s+Dalmasca\s+at\s+the\s+same\s+time$", flags=re.IGNORECASE),
        "And if I could save a citizen of Dalmasca at the same time...",
    ),
    (
        re.compile(r"^The\s+guild\s+COMMUNI[I1]IES\s+DON['’]?T\s+have\s+MLCH\s+LAW\s+AND$", flags=re.IGNORECASE),
        "The guild COMMUNItIES DON'T have MucH LAW AND order...",
    ),
    (re.compile(r"^have\s+Left\s+Me\s+At\s+DEATH['’]?S\s+DOOR$", flags=re.IGNORECASE), "...have Left Me At DEATH'S DOOR"),
)

_INCOMPLETE_TAIL_RE = re.compile(
    r"\b("
    r"but|because|before|about|with|without|from|into|"
    r"catches|lately|importantly"
    r")$",
    flags=re.IGNORECASE,
)


def repair_probable_dialogue_ellipsis(text: str) -> str:
    """Repair ellipses when reviewed manga dialogue consistently implies them.

    This is intentionally conservative: exact reviewed shapes first, then only
    bare line endings that finish on a grammatical continuation cue.
    """
    value = str(text).strip()
    if not value:
        return ""
    for pattern, replacement in _EXACT_ELLIPSIS_REPAIRS:
        value = pattern.sub(replacement, value)
    if value.endswith(("...", "?!", "!?")):
        return value
    if re.search(r"[A-Za-z]$", value) and _INCOMPLETE_TAIL_RE.search(value):
        words = re.findall(r"[A-Za-z][A-Za-z'’]*", value)
        if len(words) >= 3:
            return value + "..."
    return value
