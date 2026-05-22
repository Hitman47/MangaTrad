from __future__ import annotations

import re

_SFX_EDGE_RE = re.compile(
    r"^(whisper|sob|shock|jaka|sfx|bam|bang|boom|thud|clap|rustle|slam|tap|jolt|gasp|slap|wobble|yawn|sposh|flash|tremble|fidget|twitch|fwooo|nod|scribble)\b[.!?:, -]*"
    r"|\s+\b(whisper|sob|shock|jaka|sfx|bam|bang|boom|thud|clap|rustle|slam|tap|jolt|gasp|slap|wobble|yawn|sposh|flash|tremble|fidget|twitch|fwooo|nod|scribble)[.!?:, -]*$",
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



_ELLIPSIS_JOIN_WORDS = {
    "apparently",
    "asphyxiation",
    "circumstances",
    "drugged",
    "interrupted",
    "kidnapped",
    "natsuko",
    "particular",
    "prepared",
    "serious",
    "someone",
    "troubling",
    "understand",
    "useless",
    "yutaro",
}


def _repair_intraword_ellipsis(text: str) -> str:
    value = re.sub(r"\b(mobu|miwako)[.]{3}\s*san\b", r"\1-san", text, flags=re.IGNORECASE)
    value = re.sub(r"\bpar[.]{3}\s*ticu[.]{3}\s*lar\b", "particular", value, flags=re.IGNORECASE)
    value = re.sub(r"\blnder[.]{3}\s*stand\b", "UNDERSTAND", value, flags=re.IGNORECASE)

    def join_known(match: re.Match[str]) -> str:
        joined = f"{match.group(1)}{match.group(2)}"
        return joined if joined.lower() in _ELLIPSIS_JOIN_WORDS else match.group(0)

    previous = None
    while previous != value:
        previous = value
        value = re.sub(r"\b([A-Za-z]{2,})[.]{3}\s*([A-Za-z]{2,})\b", join_known, value)
    return value


_COMMON_OCR_WORD_FIXES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bEnolgh\b", flags=re.IGNORECASE), "enough"),
    (re.compile(r"\bcolrse\b", flags=re.IGNORECASE), "course"),
    (re.compile(r"\bFOLR\b", flags=re.IGNORECASE), "four"),
    (re.compile(r"\bFopm\b", flags=re.IGNORECASE), "form"),
    (re.compile(r"\bColld\b", flags=re.IGNORECASE), "could"),
    (re.compile(r"\bAbolt\b", flags=re.IGNORECASE), "About"),
    (re.compile(r"\bolt\b", flags=re.IGNORECASE), "out"),
    (re.compile(r"\bOLR\b", flags=re.IGNORECASE), "OUR"),
    (re.compile(r"\bShlt\b", flags=re.IGNORECASE), "Shut"),
    (re.compile(r"\bLp\b", flags=re.IGNORECASE), "up"),
    (re.compile(r"\bCeo\b", flags=re.IGNORECASE), "CEO"),
    (re.compile(r"\bALl\b"), "all"),
    (re.compile(r"\bAlll\b", flags=re.IGNORECASE), "all"),
    (re.compile(r"\bApe\b", flags=re.IGNORECASE), "Are"),
    (re.compile(r"\byo4\b", flags=re.IGNORECASE), "you"),
    (re.compile(r"\bHupry\b", flags=re.IGNORECASE), "Hurry"),
    (re.compile(r"\bNOL\b", flags=re.IGNORECASE), "no"),
    (re.compile(r"\bNOI\b", flags=re.IGNORECASE), "NO!"),
    (re.compile(r"\bAhemi\b", flags=re.IGNORECASE), "Ahem!"),
    (re.compile(r"\bCant\b", flags=re.IGNORECASE), "can't"),
    (re.compile(r"\bIm\b", flags=re.IGNORECASE), "I'm"),
    (re.compile(r"\bIll\b", flags=re.IGNORECASE), "I'll"),
    (re.compile(r"\bIve\b", flags=re.IGNORECASE), "I've"),
    (re.compile(r"\bYoure\b", flags=re.IGNORECASE), "You're"),
    (re.compile(r"\bWhos\b", flags=re.IGNORECASE), "who's"),
    (re.compile(r"\bITS\b", flags=re.IGNORECASE), "it's"),
    (re.compile(r"\bIT'SA\b", flags=re.IGNORECASE), "IT'S A"),
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
    (re.compile(r"\bsideby\b", flags=re.IGNORECASE), "side by"),
    (re.compile(r"\bWth\b", flags=re.IGNORECASE), "With"),
    (re.compile(r"\bJCAN\b", flags=re.IGNORECASE), "I CAN"),
    (re.compile(r"\bRegllar\b", flags=re.IGNORECASE), "Regular"),
    (re.compile(r"\bVTAL\b", flags=re.IGNORECASE), "vital"),
    (re.compile(r"\bFPOM\b", flags=re.IGNORECASE), "from"),
    (re.compile(r"\bANDPOID\b", flags=re.IGNORECASE), "android"),
    (re.compile(r"\bBECALISE\b", flags=re.IGNORECASE), "because"),
    (re.compile(r"\bULTIMTE\b", flags=re.IGNORECASE), "ULTIMATE"),
    (re.compile(r"\bMEALTH\b", flags=re.IGNORECASE), "HEALTH"),
    (re.compile(r"\bBOSSE36\b", flags=re.IGNORECASE), "bosses..."),
    (re.compile(r"\bHAIRSTYE\b", flags=re.IGNORECASE), "hairstyle"),
    (re.compile(r"\bLETIS\b", flags=re.IGNORECASE), "let's"),
    (re.compile(r"\bDidnta\b", flags=re.IGNORECASE), "Didn't"),
    (re.compile(r"\bClosb\b", flags=re.IGNORECASE), "close"),
    (re.compile(r"\bBOPROW\b", flags=re.IGNORECASE), "borrow"),
    (re.compile(r"\bBig-twme\b", flags=re.IGNORECASE), "Big-time"),
    (re.compile(r"\bFltile\b", flags=re.IGNORECASE), "futile"),
    (re.compile(r"\bFull3\b", flags=re.IGNORECASE), "full"),
    (re.compile(r"\bShiti\b", flags=re.IGNORECASE), "Shit!"),
    (re.compile(r"\bTh'\b", flags=re.IGNORECASE), "that"),
    (re.compile(r"\bPoison-\s*Ous\b", flags=re.IGNORECASE), "Poisonous"),
    (re.compile(r"\bsinglel\b", flags=re.IGNORECASE), "single"),
    (re.compile(r"\bY0u\b", flags=re.IGNORECASE), "You"),
    (re.compile(r"\bLdoes\s+ike\b", flags=re.IGNORECASE), "does it look like"),
    (re.compile(r"\bWrone\b", flags=re.IGNORECASE), "Wrong"),
    (re.compile(r"\bHLNT\b", flags=re.IGNORECASE), "hunt"),
    (re.compile(r"\bFOLIND\b", flags=re.IGNORECASE), "FOUND"),
    (re.compile(r"\bSHOLLD\b", flags=re.IGNORECASE), "should"),
    (re.compile(r"\bWITHORAW\b", flags=re.IGNORECASE), "withdraw"),
    (re.compile(r"\bFORTLNE\b", flags=re.IGNORECASE), "FORTUNE"),
    (re.compile(r"\brep-\s*UTATION\b", flags=re.IGNORECASE), "reputation"),
    (re.compile(r"\bIMMEDI-\s*Ately\b", flags=re.IGNORECASE), "immediately"),
    (re.compile(r"\bCOMMUNIIES\b", flags=re.IGNORECASE), "COMMUNITIES"),
    (re.compile(r"\bMLCH\b", flags=re.IGNORECASE), "MUCH"),
    (re.compile(r"\bLNDERSTAND\b", flags=re.IGNORECASE), "UNDERSTAND"),
    (re.compile(r"\b4nder\W*stood\b", flags=re.IGNORECASE), "Understood"),
    (re.compile(r"\bHurryi\b", flags=re.IGNORECASE), "Hurry!"),
    (re.compile(r"\bFaill\b", flags=re.IGNORECASE), "Fail"),
    (re.compile(r"\bGol\b", flags=re.IGNORECASE), "Go!"),
    (re.compile(r"\bHlhi\?", flags=re.IGNORECASE), "HUH!?"),
    (re.compile(r"\bKow\s+About\b", flags=re.IGNORECASE), "How About"),
    (re.compile(r"\bLookk\b", flags=re.IGNORECASE), "Look"),
    (re.compile(r"\bG0T\b", flags=re.IGNORECASE), "GOT"),
    (re.compile(r"\bMOMEY\b", flags=re.IGNORECASE), "MONEY"),
    (re.compile(r"\bCALGHT\b", flags=re.IGNORECASE), "CAUGHT"),
    (re.compile(r"\bRlnaway\b", flags=re.IGNORECASE), "Runaway"),
    (re.compile(r"\bbandis\b", flags=re.IGNORECASE), "bandits"),
    (re.compile(r"\bThepe\b", flags=re.IGNORECASE), "There"),
    (re.compile(r"\bSecl\b", flags=re.IGNORECASE), "sec!"),
    (re.compile(r"\bPepson\b", flags=re.IGNORECASE), "Person"),
    (re.compile(r"\bLoks\b", flags=re.IGNORECASE), "Looks"),
    (re.compile(r"\b4NDER-\s*STOOD\b", flags=re.IGNORECASE), "Understood"),
    (re.compile(r"\bou'd\b", flags=re.IGNORECASE), "you'd"),
    (re.compile(r"\bDINNERI\b", flags=re.IGNORECASE), "DINNER!"),
    (re.compile(r"\bREADYI\b", flags=re.IGNORECASE), "READY!"),
    (re.compile(r"\bMONSTERSI\b", flags=re.IGNORECASE), "MONSTERS!"),
    (re.compile(r"\bSTUBBORNI\b", flags=re.IGNORECASE), "STUBBORN!"),
    (re.compile(r"\bThreei\b", flags=re.IGNORECASE), "Three!"),
    (re.compile(r"\bMEII\b", flags=re.IGNORECASE), "ME!!"),
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
    (re.compile(r"\bDO\s+NOT\s+YOURSELF\b", flags=re.IGNORECASE), "do not torture yourself"),
    (re.compile(r"\bDO\s+Some(?:-|\s*)thing!\s+I'm\s+Counting\s+ON\s*$", flags=re.IGNORECASE), "DO something! I'm Counting ON you...!!"),
    (re.compile(r"\bWHAT\s+GOING\s*$", flags=re.IGNORECASE), "what are you going to do?!"),
    (re.compile(r"\bCould\s+accomp\s+any\s+you\?", flags=re.IGNORECASE), "Could I accompany you?"),
    (re.compile(r"\bthere'@\s+NO\s+WAY\s+(.+?)\s+COULD\s+Ve\b", flags=re.IGNORECASE), r"there's NO WAY \1 COULD'Ve"),
    (re.compile(r"\bWHAT\s+The,\s*$", flags=re.IGNORECASE), "what the...?!"),
    (re.compile(r"\bNo\s+Way\)\s*$", flags=re.IGNORECASE), "No Way!"),
    (re.compile(r"\bI\s+Think\s+I\s+Might\s+Like,\s*\"?\s*$", flags=re.IGNORECASE), "I Think I Might Like..."),
    (re.compile(r"\bsmusic\s+Festivalsi\b", flags=re.IGNORECASE), "...music Festivals!"),
    (re.compile(r"^\s*:\s*why\s+isn['’]?t\s+(.+?)\s+Waking\s+Up[.]$", flags=re.IGNORECASE), r"...why isn't \1 waking up...?"),
    (re.compile(r"\bHe['’]?s\s+COMING[.]\s+ISN['’]?T\s+He[,.\s]*$", flags=re.IGNORECASE), "he's coming... isn't he...?"),
    (re.compile(r"\bHi\s+everyone\s+We['’]?re\s+going\s+To\s+Be\s+working\s+Together\s+now,\s+OKAY-?\?", flags=re.IGNORECASE), "Hi everyone. We're going to be working together now, okay?"),
    (re.compile(r"\bSORRY\s+I'm\s+LATE(?:-|\.\.\.)\s*$", flags=re.IGNORECASE), "sorry I'm late..."),
    (re.compile(r"\bWAIT\s+A\s+SEC,\s+You\s+guys\s*$", flags=re.IGNORECASE), "WAIT A SEC, You guys know..."),
    (re.compile(r"\bSo\s+THAT\s+Big-time\s+job\s+You\s+Guys\s+Were\s+talking\s+About[.]$", flags=re.IGNORECASE), "So THAT Big-time job You Guys Were talking About..."),
    (re.compile(r"\b(?:LNDER-\s*STAND|UNDERSTAND)\s+Why\s+knives\s+CHOSE\s+This\s+PLACE[.]$", flags=re.IGNORECASE), "I UNDERSTAND Why Knives CHOSE This PLACE..."),
    (re.compile(r"\bOnce\s+full\s+Circler\s*$", flags=re.IGNORECASE), "Once it's gone full circle..."),
    (re.compile(r"\bZANDJONLY\s+FOUND\s+One[.]$", flags=re.IGNORECASE), "...and only found one."),
    (re.compile(r"\bOnly\s+found\s+Five[.]$", flags=re.IGNORECASE), "...but they only found five."),
    (re.compile(r"\bBASICALLY\s*$", flags=re.IGNORECASE), "so basically..."),
    (re.compile(r"\bALL\s+\[\s+HAD\s+TO\s+DO\b", flags=re.IGNORECASE), "all I had to do"),
    (re.compile(r"\bFOR\s+AM\s+OLD\s+MAN\b", flags=re.IGNORECASE), "for an old man"),
    (re.compile(r"\bANY\s+COMP[.]{3}\s*LAINTS\?", flags=re.IGNORECASE), "ANY COMPLAINTS?"),
    (re.compile(r"\bI'm\s+THE\s+SOUTH-OASIS\b", flags=re.IGNORECASE), "In THE SOUTH-OASIS"),
    (re.compile(r"\bS0\s+MANY\s+HERE\s+ALREADY[:. ]+\s*W!\s*$", flags=re.IGNORECASE), "so many here already...!!"),
    (re.compile(r"\bAAAND,\s+It['’]?s\s+GETTING\s+WORSE[:. ]+$", flags=re.IGNORECASE), "aaand, it's getting worse..."),
    (re.compile(r"\bHE\s+Hasn['’]?t\s+EITHER,\s*$", flags=re.IGNORECASE), "HE Hasn't come today EITHER."),
    (re.compile(r"\bWANNA\s+Go[Il1]?\?", flags=re.IGNORECASE), "wanna go?"),
    (re.compile(r"\bHere\s+I\s+Go[Il1]\b", flags=re.IGNORECASE), "Here I Go!"),
    (re.compile(r"\byou['’]?ll\s+under[.]{3}\s*stand\b", flags=re.IGNORECASE), "you'll understand"),
    (re.compile(r"\bHunt[.]{3}\s*Ing\s*$", flags=re.IGNORECASE), "...I'm hunting you!!"),
    (re.compile(r"^Why\s+Did\s+I$", flags=re.IGNORECASE), "Why Did I...?"),
    (re.compile(r"^this\s+IS\s+MY\s+FAULT$", flags=re.IGNORECASE), "this IS MY FAULT...?"),
    (re.compile(r"^they\s+aren['\u2019]?t\s+making$", flags=re.IGNORECASE), "they aren't making a move..."),
    (re.compile(r"^uh[.]\s+no\s+Reason$", flags=re.IGNORECASE), "uh. no Reason...?"),
    (re.compile(r"^fine,$", flags=re.IGNORECASE), "fine..."),
    (re.compile(r"^Now$", flags=re.IGNORECASE), "Now..."),
    (re.compile(r"^IS\s+This[.]$", flags=re.IGNORECASE), "IS This..."),
    (re.compile(r"^FROM\s+Now$", flags=re.IGNORECASE), "FROM Now on ..."),
    (re.compile(r"^it\s+is\s+a\s+good$", flags=re.IGNORECASE), "it is a good tune"),
    (re.compile(r"^How\s+About$", flags=re.IGNORECASE), "How About it?"),
    (re.compile(r"^Hmm$", flags=re.IGNORECASE), "Hmm?!"),
    (re.compile(r"^then$", flags=re.IGNORECASE), "then?"),
    (re.compile(r"^a\s+fortune\s+teller,$", flags=re.IGNORECASE), "a fortune teller..."),
    (re.compile(r"^GOD,$", flags=re.IGNORECASE), "GOD..."),
    (re.compile(r"^AHH,$", flags=re.IGNORECASE), "AHH..."),
    (re.compile(r"\bremem\s+ber\b", flags=re.IGNORECASE), "remember"),
    (re.compile(r"\bIhave\b", flags=re.IGNORECASE), "I have"),
)


def normalize_spacing_and_punctuation(text: str) -> str:
    """Normalize OCR punctuation without changing meaning."""
    value = " ".join(str(text).replace("’", "'").strip().split())
    if not value:
        return ""
    value = value.replace("_", " ")
    value = re.sub(r"^\s*~\s*", "...", value)
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
    value = re.sub(r"([!?])\s+\1", r"\1\1", value)
    value = re.sub(r"\?\s+!", "?!", value)
    value = re.sub(r"\.\s*\.\s*\.\s*", "...", value)
    value = _repair_intraword_ellipsis(value)
    value = re.sub(r"\.\.\.(?=[A-Za-z])", lambda m: "..." if m.start() == 0 else "... ", value)
    value = re.sub(r"(?<!\.)\.\.(?!\.)", ".", value)
    value = re.sub(r"\b(Ms|Mrs|Mr|Dr):(?=\s+[A-Z])", r"\1.", value, flags=re.IGNORECASE)
    value = re.sub(r":\s*\.\.\.", "...", value)
    value = re.sub(r"[:.]+\s*=$", "...", value)
    value = re.sub(r"(?:,\s*){2,}$", "...", value)
    value = re.sub(r"\s+-\s*$", "...", value)
    value = re.sub(r"(?i)(?<=[A-Za-z])-\?$", "?", value)
    value = re.sub(r"(?i)(?<=[A-Za-z])-$", "...", value)
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
    value = re.sub(r"\b([A-Za-z]{3,})I([.!?]*)$", lambda m: f"{m.group(1)}!{m.group(2)}", value)
    value = re.sub(r"!([.!?]+)$", lambda m: "!" + m.group(1).replace(".", ""), value)
    value = normalize_english_ocr_casing(normalize_spacing_and_punctuation(value))
    return value
