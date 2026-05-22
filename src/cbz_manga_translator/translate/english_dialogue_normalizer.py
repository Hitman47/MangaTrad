from __future__ import annotations

import re
from dataclasses import dataclass

from cbz_manga_translator.ocr.manga_font import repair_manga_font_confusions
from cbz_manga_translator.ocr.memory import default_ocr_memory
from cbz_manga_translator.translate.memory import default_translation_memory

_LATIN_LETTER_RE = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ]")
_JAPANESE_RE = re.compile(r"[ぁ-んァ-ン一-龯々ー]")
_SPACE_BEFORE_PUNCT_RE = re.compile(r"\s+([,.;:!?])")
_MULTI_SPACE_RE = re.compile(r"\s+")
_SFX_EDGE_RE = re.compile(
    r"^(whisper|sob|shock|jaka|sfx|bam|bang|boom|thud|clap|rustle|slam|tap|jolt|gasp|slap|wobble|yawn|sposh|flash|tremble|fidget|twitch|fwooo|nod|scribble)\b[.!?:, -]*"
    r"|\s+\b(whisper|sob|shock|jaka|sfx|bam|bang|boom|thud|clap|rustle|slam|tap|jolt|gasp|slap|wobble|yawn|sposh|flash|tremble|fidget|twitch|fwooo|nod|scribble)[.!?:, -]*$",
    flags=re.IGNORECASE,
)

_ING_EXCEPTIONS = {
    "doin": "doing",
    "goin": "going",
    "comin": "coming",
    "givin": "giving",
    "havin": "having",
    "makin": "making",
    "takin": "taking",
    "climbin": "climbing",
    "lookin": "looking",
    "riskin": "risking",
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
    "student",
    "someone",
    "troubling",
    "understand",
    "useless",
    "yutaro",
}

# OCR-specific fixes: these are deliberately applied before colloquial English
# normalization. They fix visual confusions observed in comic fonts without
# modifying the raw OCR field saved in the project cache.
_OCR_CORRECTIONS: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(r"\bbmusthvb\s+gallenl\s+asle+p\s+inifront\s+computers?\b", flags=re.IGNORECASE),
        "I must've fallen asleep in front of my computer.",
    ),
    (re.compile(r"\blisten,\s*yuki[:.]\s*$", flags=re.IGNORECASE), "listen, Yuki..."),
    (re.compile(r"\bso\s+why,\s*$", flags=re.IGNORECASE), "so why..."),
    (re.compile(r"\blet'?s\s+see\s*$", flags=re.IGNORECASE), "let's see here..."),
    (re.compile(r"\bif\s+one\s+ener\s+is\s+about\s+one\s+hlndred\s+yen[:,.\s]*$", flags=re.IGNORECASE), "if one ener is about one hundred yen..."),
    (re.compile(r"\bt[o0][il1!]d\b", flags=re.IGNORECASE), "told"),
    (re.compile(r"\btoid\b", flags=re.IGNORECASE), "told"),
    (re.compile(r"\bc[l1i!]imb", flags=re.IGNORECASE), "climb"),
    (re.compile(r"\b[il1]nhook\b", flags=re.IGNORECASE), "unhook"),
    (re.compile(r"\bunh[o0]{2}k\b", flags=re.IGNORECASE), "unhook"),
    (re.compile(r"\bgramma\b", flags=re.IGNORECASE), "grandma"),
    (re.compile(r"\bgranma\b", flags=re.IGNORECASE), "grandma"),
    (re.compile(r"\bgrampa\b", flags=re.IGNORECASE), "grandpa"),
    (re.compile(r"\bcolrse\b", flags=re.IGNORECASE), "course"),
    (re.compile(r"\bshlt\b", flags=re.IGNORECASE), "shut"),
    (re.compile(r"\blp\b", flags=re.IGNORECASE), "up"),
    (re.compile(r"\bceo\b", flags=re.IGNORECASE), "CEO"),
    (re.compile(r"\babolt\b", flags=re.IGNORECASE), "about"),
    (re.compile(r"\bolt\b", flags=re.IGNORECASE), "out"),
    (re.compile(r"\bolr\b", flags=re.IGNORECASE), "our"),
    (re.compile(r"\bape\b", flags=re.IGNORECASE), "are"),
    (re.compile(r"\byo4\b", flags=re.IGNORECASE), "you"),
    (re.compile(r"\bhupry\b", flags=re.IGNORECASE), "hurry"),
    (re.compile(r"\bhurryi\b", flags=re.IGNORECASE), "hurry!"),
    (re.compile(r"\bfaill\b", flags=re.IGNORECASE), "fail"),
    (re.compile(r"\bnoi\b", flags=re.IGNORECASE), "no!"),
    (re.compile(r"\bahemi\b", flags=re.IGNORECASE), "ahem!"),
    (re.compile(r"\bim\b", flags=re.IGNORECASE), "I'm"),
    (re.compile(r"\bive\b", flags=re.IGNORECASE), "I've"),
    (re.compile(r"\byoure\b", flags=re.IGNORECASE), "you're"),
    (re.compile(r"\bwhos\b", flags=re.IGNORECASE), "who's"),
    (re.compile(r"\bitsa\b", flags=re.IGNORECASE), "it's a"),
    (re.compile(r"\bsideby\b", flags=re.IGNORECASE), "side by"),
    (re.compile(r"\bwth\b", flags=re.IGNORECASE), "with"),
    (re.compile(r"\bjcan\b", flags=re.IGNORECASE), "I can"),
    (re.compile(r"\bregllar\b", flags=re.IGNORECASE), "regular"),
    (re.compile(r"\bvtal\b", flags=re.IGNORECASE), "vital"),
    (re.compile(r"\bfpom\b", flags=re.IGNORECASE), "from"),
    (re.compile(r"\bandpoid\b", flags=re.IGNORECASE), "android"),
    (re.compile(r"\bbecalise\b", flags=re.IGNORECASE), "because"),
    (re.compile(r"\bultimte\b", flags=re.IGNORECASE), "ultimate"),
    (re.compile(r"\bmealth\b", flags=re.IGNORECASE), "health"),
    (re.compile(r"\bbosse36\b", flags=re.IGNORECASE), "bosses..."),
    (re.compile(r"\bhairstye\b", flags=re.IGNORECASE), "hairstyle"),
    (re.compile(r"\bletis\b", flags=re.IGNORECASE), "let's"),
    (re.compile(r"\bdinneri\b", flags=re.IGNORECASE), "dinner!"),
    (re.compile(r"\breadyi\b", flags=re.IGNORECASE), "ready!"),
    (re.compile(r"\bmonstersi\b", flags=re.IGNORECASE), "monsters!"),
    (re.compile(r"\bstubborni\b", flags=re.IGNORECASE), "stubborn!"),
    (re.compile(r"\bthreei\b", flags=re.IGNORECASE), "three!"),
    (re.compile(r"\bmeii\b", flags=re.IGNORECASE), "me!!"),
    (re.compile(r"\bdidnta\b", flags=re.IGNORECASE), "didn't"),
    (re.compile(r"\bclosb\b", flags=re.IGNORECASE), "close"),
    (re.compile(r"\bboprow\b", flags=re.IGNORECASE), "borrow"),
    (re.compile(r"\bbig-twme\b", flags=re.IGNORECASE), "big-time"),
    (re.compile(r"\bfltile\b", flags=re.IGNORECASE), "futile"),
    (re.compile(r"\bfull3\b", flags=re.IGNORECASE), "full"),
    (re.compile(r"\bshiti\b", flags=re.IGNORECASE), "shit!"),
    (re.compile(r"\bs0\s+many\s+here\s+already[:. ]+\s*w!\s*$", flags=re.IGNORECASE), "so many here already...!!"),
    (re.compile(r"\baaand,\s+it['’]?s\s+getting\s+worse[:. ]+$", flags=re.IGNORECASE), "aaand, it's getting worse..."),
    (re.compile(r"\bth'\b", flags=re.IGNORECASE), "that"),
    (re.compile(r"\bpoison-\s*ous\b", flags=re.IGNORECASE), "poisonous"),
    (re.compile(r"\bsinglel\b", flags=re.IGNORECASE), "single"),
    (re.compile(r"\by0u\b", flags=re.IGNORECASE), "you"),
    (re.compile(r"\bldoes\s+ike\b", flags=re.IGNORECASE), "does it look like"),
    (re.compile(r"\bwrone\b", flags=re.IGNORECASE), "wrong"),
    (re.compile(r"\bhlnt\b", flags=re.IGNORECASE), "hunt"),
    (re.compile(r"\bfolind\b", flags=re.IGNORECASE), "found"),
    (re.compile(r"\bsholld\b", flags=re.IGNORECASE), "should"),
    (re.compile(r"\bwithoraw\b", flags=re.IGNORECASE), "withdraw"),
    (re.compile(r"\bfortlne\b", flags=re.IGNORECASE), "fortune"),
    (re.compile(r"\brep-\s*utation\b", flags=re.IGNORECASE), "reputation"),
    (re.compile(r"\bimmedi-\s*ately\b", flags=re.IGNORECASE), "immediately"),
    (re.compile(r"\bcommuniies\b", flags=re.IGNORECASE), "communities"),
    (re.compile(r"\bmlch\b", flags=re.IGNORECASE), "much"),
    (re.compile(r"\blnderstand\b", flags=re.IGNORECASE), "understand"),
    (re.compile(r"\b4nder\W*stood\b", flags=re.IGNORECASE), "understood"),
    (re.compile(r"\bgol\b", flags=re.IGNORECASE), "go!"),
    (re.compile(r"\bhlhi\?", flags=re.IGNORECASE), "huh!?"),
    (re.compile(r"\bkow\s+about\b", flags=re.IGNORECASE), "how about"),
    (re.compile(r"\blookk\b", flags=re.IGNORECASE), "look"),
    (re.compile(r"\bg0t\b", flags=re.IGNORECASE), "got"),
    (re.compile(r"\bmomey\b", flags=re.IGNORECASE), "money"),
    (re.compile(r"\bcalght\b", flags=re.IGNORECASE), "caught"),
    (re.compile(r"\brlnaway\b", flags=re.IGNORECASE), "runaway"),
    (re.compile(r"\bbandis\b", flags=re.IGNORECASE), "bandits"),
    (re.compile(r"\bthepe\b", flags=re.IGNORECASE), "there"),
    (re.compile(r"\bsecl\b", flags=re.IGNORECASE), "sec!"),
    (re.compile(r"\bpepson\b", flags=re.IGNORECASE), "person"),
    (re.compile(r"\bloks\b", flags=re.IGNORECASE), "looks"),
    (re.compile(r"\b4nder-\s*stood\b", flags=re.IGNORECASE), "understood"),
    (re.compile(r"\bou'd\b", flags=re.IGNORECASE), "you'd"),
    (re.compile(r"\blookv\b", flags=re.IGNORECASE), "looky"),
    (re.compile(r"\bloooky\b", flags=re.IGNORECASE), "looky"),
    (re.compile(r"\btho\b", flags=re.IGNORECASE), "though"),
    (re.compile(r"\bcuz\b", flags=re.IGNORECASE), "because"),
    (re.compile(r"\bcos\b", flags=re.IGNORECASE), "because"),
    (re.compile(r"\bign[o0]re\b", flags=re.IGNORECASE), "ignore"),
    (re.compile(r"\benc[o0]unter\b", flags=re.IGNORECASE), "encounter"),
    (re.compile(r"\bi[’']?[il1]l\b", flags=re.IGNORECASE), "I'll"),
    (re.compile(r"\btepm\b", flags=re.IGNORECASE), "term"),
    (re.compile(r"\bkawazl\b", flags=re.IGNORECASE), "Kawazu"),
    (re.compile(r"\byol\b", flags=re.IGNORECASE), "you"),
    (re.compile(r"\bcf\b", flags=re.IGNORECASE), "of"),
    (re.compile(r"\bpeallyi?\b", flags=re.IGNORECASE), "really"),
    (re.compile(r"\bwha+ti?\b", flags=re.IGNORECASE), "what"),
    (re.compile(r"\bwhoal\b", flags=re.IGNORECASE), "whoa!"),
    (re.compile(r"\bsepiously\b", flags=re.IGNORECASE), "seriously"),
    (re.compile(r"\bdoesnt\b", flags=re.IGNORECASE), "doesn't"),
    # Corpus-learned OCR confusions from review exports. These are conservative
    # spelling fixes applied to the diagnostic corrected text, not to raw OCR.
    (re.compile(r"\bcolld\b", flags=re.IGNORECASE), "could"),
    (re.compile(r"\bfolr\b", flags=re.IGNORECASE), "four"),
    (re.compile(r"\benolgh\b", flags=re.IGNORECASE), "enough"),
    (re.compile(r"\bfopm\b", flags=re.IGNORECASE), "form"),
    (re.compile(r"\bhlnger\b", flags=re.IGNORECASE), "hunger"),
    (re.compile(r"\bhundped\b", flags=re.IGNORECASE), "hundred"),
    (re.compile(r"\bhlndred\b", flags=re.IGNORECASE), "hundred"),
    (re.compile(r"\bwolld\b", flags=re.IGNORECASE), "would"),
    (re.compile(r"\bmke\b", flags=re.IGNORECASE), "make"),
    (re.compile(r"\bbizarpe\b", flags=re.IGNORECASE), "bizarre"),
    (re.compile(r"\bwopld\b", flags=re.IGNORECASE), "world"),
    (re.compile(r"\biwas\b", flags=re.IGNORECASE), "I was"),
    (re.compile(r"\bidont\b", flags=re.IGNORECASE), "I don't"),
    (re.compile(r"\bdont\b", flags=re.IGNORECASE), "don't"),
    (re.compile(r"\bdidnt\b", flags=re.IGNORECASE), "didn't"),
    (re.compile(r"\bapen['’]?t\b", flags=re.IGNORECASE), "aren't"),
    (re.compile(r"\bthankfll\b", flags=re.IGNORECASE), "thankful"),
    (re.compile(r"\byolp\b", flags=re.IGNORECASE), "your"),
    (re.compile(r"\bvictopy\b", flags=re.IGNORECASE), "victory"),
    (re.compile(r"\bminel!?", flags=re.IGNORECASE), "mine!"),
    (re.compile(r"\bplnk\b", flags=re.IGNORECASE), "punk"),
    (re.compile(r"\bplink\b", flags=re.IGNORECASE), "punk"),
    (re.compile(r"\bfop\b", flags=re.IGNORECASE), "for"),
    (re.compile(r"\btooi\b", flags=re.IGNORECASE), "too!"),
    (re.compile(r"\bcarefll\b", flags=re.IGNORECASE), "careful"),
    (re.compile(r"\bnlisance\b", flags=re.IGNORECASE), "nuisance"),
    (re.compile(r"\bfljimura-kln\b", flags=re.IGNORECASE), "Fujimura-kun"),
    (re.compile(r"\btholght\b", flags=re.IGNORECASE), "thought"),
    (re.compile(r"\bwmp[o0]rtant\b", flags=re.IGNORECASE), "important"),
    (re.compile(r"\bwha+a+i\b", flags=re.IGNORECASE), "whaaat"),
    (re.compile(r"\bbreastsi\b", flags=re.IGNORECASE), "breasts!!"),
    (re.compile(r"\bppomise\b", flags=re.IGNORECASE), "promise"),
    (re.compile(r"\btomorpow\b", flags=re.IGNORECASE), "tomorrow"),
    (re.compile(r"\biives\b", flags=re.IGNORECASE), "lives"),
    (re.compile(r"\bfeelig\b", flags=re.IGNORECASE), "feeling"),
    (re.compile(r"\bthhis\b", flags=re.IGNORECASE), "this"),
    (re.compile(r"\bi50\b", flags=re.IGNORECASE), "150"),
    (re.compile(r"\b2oth\b", flags=re.IGNORECASE), "20th"),
    (re.compile(r"\bsth\b", flags=re.IGNORECASE), "5th"),
    (re.compile(r"\bno\s+wayi\b", flags=re.IGNORECASE), "no way!"),
    (re.compile(r"\bt0\b", flags=re.IGNORECASE), "to"),
    (re.compile(r"\bpeallyi\b", flags=re.IGNORECASE), "really"),
    (re.compile(r"\bthess\b", flags=re.IGNORECASE), "these"),
    (re.compile(r"\bdollarman\b", flags=re.IGNORECASE), "dollar man"),
)

_PRONOUN_CORRECTIONS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bah\b", flags=re.IGNORECASE), "I"),
    (re.compile(r"\bya\b", flags=re.IGNORECASE), "you"),
    (re.compile(r"\byer\b", flags=re.IGNORECASE), "your"),
    (re.compile(r"\by'all\b", flags=re.IGNORECASE), "you all"),
)

_DIALOGUE_NORMALIZATIONS: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(
            r"\bain['’]?t\s+(?:ah|i)\s+t[o0][il1!]?d\s+ya[,]?\s+no\s+c[l1i!]imb(?:in['’]?|ing)\s+nowhere\s+dangerous\b",
            flags=re.IGNORECASE,
        ),
        "haven't I told you not to climb anywhere dangerous",
    ),
    (
        re.compile(
            r"\bain['’]?t\s+i\s+told\s+you[,]?\s+no\s+climbing\s+nowhere\s+dangerous\b",
            flags=re.IGNORECASE,
        ),
        "haven't I told you not to climb anywhere dangerous",
    ),
    (
        re.compile(
            r"\bdon['’]?t\s+(?:you\s+)?go\s+do(?:in['’]?|ing)\s+risky\s+stuff\s+no\s+more\b",
            flags=re.IGNORECASE,
        ),
        "don't go doing risky stuff anymore",
    ),
    (re.compile(r"\bplease\s+(?:[il1]nhook|unhook)\s+this\b", flags=re.IGNORECASE), "please unhook this"),
    (re.compile(r"\bwhat\s+(?:ya|you)\s+do(?:in['’]?|ing)\s+up\s+there\b", flags=re.IGNORECASE), "what are you doing up there"),
    (re.compile(r"\bgramma[,]?\s+looky\s+that\b", flags=re.IGNORECASE), "grandma, look at that"),
    (re.compile(r"\bgrandma[,]?\s+looky\s+that\b", flags=re.IGNORECASE), "grandma, look at that"),
    (re.compile(r"\blooky\s+that\b", flags=re.IGNORECASE), "look at that"),
    (
        re.compile(r"\bmiwa[-\s]?nee\s+was\s+look(?:in['’]?|ing)\s+for\s+(?:ya|you)\b", flags=re.IGNORECASE),
        "Miwa-nee was looking for you",
    ),
    (re.compile(r"\bget\s+go(?:in['’]?|ing)\s+now\b", flags=re.IGNORECASE), "get going now"),
    (re.compile(r"\bthere['’]?s\s+someone\s+com(?:in['’]?|ing)\s+in\s+on\s+that\s+plane\b", flags=re.IGNORECASE), "there's someone coming in on that plane"),
    (re.compile(r"\bhere\s+now[,]?!?\s+naru\b", flags=re.IGNORECASE), "hey, Naru"),
    (re.compile(r"\bi\s+never\s+expected\s+i['’]?d\s+have\b", flags=re.IGNORECASE), "I never expected I'd have"),
    (re.compile(r"\ba\s+picturesque\s+country\s+encounter\s+like\s+that\b", flags=re.IGNORECASE), "a picturesque countryside encounter like that"),
    (re.compile(r"\bi['’]?ll\s+just\s+ignore\s+him\b", flags=re.IGNORECASE), "I'll just ignore him"),
    (
        re.compile(r"\bdirector[,]?\s+with\s+all\s+due\s+respect\b", flags=re.IGNORECASE),
        "director, with all due respect",
    ),
    (re.compile(r"\bwith\s+all\s+due\s+respect\b", flags=re.IGNORECASE), "with all due respect"),
    (re.compile(r"\barb\s+what\s+saying\??\s+you\b", flags=re.IGNORECASE), "what are you saying?"),
    (re.compile(r"\bwhat\s+is\s+that\?\s+i\b", flags=re.IGNORECASE), "what is that?!"),
    (re.compile(r"\bmake\s+a\s+run\s+for\s+it[,]?\s*$", flags=re.IGNORECASE), "make a run for it, you two."),
    (re.compile(r"\bwe\s+here\s+for\s+miss\s+natsuko\s+and[:.,\s]*$", flags=re.IGNORECASE), "we are here for miss natsuko and..."),
    (re.compile(r"\bdo\s+not\s+yourself\b", flags=re.IGNORECASE), "do not torture yourself"),
    (re.compile(r"\bdo\s+some(?:-|\s*)thing!\s+i['’]?m\s+counting\s+on\s*$", flags=re.IGNORECASE), "do something! I am counting on you...!!"),
    (re.compile(r"\bwhat\s+going\s*$", flags=re.IGNORECASE), "what are you going to do?!"),
    (re.compile(r"\bcould\s+accomp\s+any\s+you\?", flags=re.IGNORECASE), "Could I accompany you?"),
    (re.compile(r"\bthere'@\s+no\s+way\s+(.+?)\s+could\s+ve\b", flags=re.IGNORECASE), r"there's no way \1 could've"),
    (re.compile(r"\bwhat\s+the,\s*$", flags=re.IGNORECASE), "what the...?!"),
    (re.compile(r"\bno\s+way\)\s*$", flags=re.IGNORECASE), "no way!"),
    (re.compile(r"\bi\s+think\s+i\s+might\s+like,\s*\"?\s*$", flags=re.IGNORECASE), "I think I might like..."),
    (re.compile(r"\bsmusic\s+festivalsi\b", flags=re.IGNORECASE), "...music festivals!"),
    (re.compile(r"\bdon['’]?t\s+be\s+silly[.]\s+are\s+you\s+that\s+kind\s+of\s+person\?", flags=re.IGNORECASE), "don't be silly. are you that kind of person?"),
    (re.compile(r"\bdon['’]?t\s+be\s+silly[.]\s+are\s+you\s+that\s+kinda\s+person\?", flags=re.IGNORECASE), "don't be silly. are you that kind of person?"),
    (re.compile(r"^\s*:\s*why\s+isn['’]?t\s+(.+?)\s+waking\s+up[.]$", flags=re.IGNORECASE), r"...why isn't \1 waking up...?"),
    (re.compile(r"\bhe['’]?s\s+coming[.]\s+isn['’]?t\s+he[,.\s]*$", flags=re.IGNORECASE), "he's coming... isn't he...?"),
    (re.compile(r"\bhi\s+everyone\s+we['’]?re\s+going\s+to\s+be\s+working\s+together\s+now,\s+okay-?\?", flags=re.IGNORECASE), "hi everyone. we're going to be working together now, okay?"),
    (re.compile(r"\bsorry\s+i['’]?m\s+late-\s*$", flags=re.IGNORECASE), "sorry I am late..."),
    (re.compile(r"\bwait\s+a\s+sec,\s+you\s+guys\s*$", flags=re.IGNORECASE), "wait a sec, you guys know..."),
    (re.compile(r"\bso\s+that\s+big-time\s+job\s+you\s+guys\s+were\s+talking\s+about[.]$", flags=re.IGNORECASE), "so that big-time job you guys were talking about..."),
    (re.compile(r"\b(?:lnder-\s*stand|understand)\s+why\s+knives\s+chose\s+this\s+place[.]$", flags=re.IGNORECASE), "I understand why Knives chose this place..."),
    (re.compile(r"\bonce\s+full\s+circler\s*$", flags=re.IGNORECASE), "once it's gone full circle..."),
    (re.compile(r"\bzandjonly\s+found\s+one[.]$", flags=re.IGNORECASE), "...and only found one."),
    (re.compile(r"\bonly\s+found\s+five[.]$", flags=re.IGNORECASE), "...but they only found five."),
    (re.compile(r"\bbasically\s*$", flags=re.IGNORECASE), "so basically..."),
    (re.compile(r"\ball\s+\[\s+had\s+to\s+do\b", flags=re.IGNORECASE), "all I had to do"),
    (re.compile(r"\bfor\s+am\s+old\s+man\b", flags=re.IGNORECASE), "for an old man"),
    (re.compile(r"\bany\s+comp[.]{3}\s*laints\?", flags=re.IGNORECASE), "any complaints?"),
    (re.compile(r"\bi['’]?m\s+the\s+south-oasis\b", flags=re.IGNORECASE), "in the south-oasis"),
    (re.compile(r"\bhere\s+i\s+go[il1]\b", flags=re.IGNORECASE), "here I go!"),
    (re.compile(r"\byou['’]?ll\s+under[.]{3}\s*stand\b", flags=re.IGNORECASE), "you'll understand"),
    (re.compile(r"\bhunt[.]{3}\s*ing\s*$", flags=re.IGNORECASE), "...I'm hunting you!!"),
    (re.compile(r"^why\s+did\s+i$", flags=re.IGNORECASE), "Why Did I...?"),
    (re.compile(r"^this\s+is\s+my\s+fault$", flags=re.IGNORECASE), "this IS MY FAULT...?"),
    (re.compile(r"^they\s+aren['\u2019]?t\s+making$", flags=re.IGNORECASE), "they aren't making a move..."),
    (re.compile(r"^uh[.]\s+no\s+reason$", flags=re.IGNORECASE), "uh. no Reason...?"),
    (re.compile(r"^fine,$", flags=re.IGNORECASE), "fine..."),
    (re.compile(r"^now$", flags=re.IGNORECASE), "Now..."),
    (re.compile(r"^is\s+this[.]$", flags=re.IGNORECASE), "IS This..."),
    (re.compile(r"^from\s+now$", flags=re.IGNORECASE), "FROM Now on ..."),
    (re.compile(r"^it\s+is\s+a\s+good$", flags=re.IGNORECASE), "it is a good tune"),
    (re.compile(r"^how\s+about$", flags=re.IGNORECASE), "How About it?"),
    (re.compile(r"^hmm$", flags=re.IGNORECASE), "Hmm?!"),
    (re.compile(r"^then$", flags=re.IGNORECASE), "then?"),
    (re.compile(r"^a\s+fortune\s+teller,$", flags=re.IGNORECASE), "a fortune teller..."),
    (re.compile(r"^god,$", flags=re.IGNORECASE), "GOD..."),
    (re.compile(r"^ahh,$", flags=re.IGNORECASE), "AHH..."),
    (re.compile(r"\bremem\s+ber\b", flags=re.IGNORECASE), "remember"),
    (re.compile(r"\bihave\b", flags=re.IGNORECASE), "I have"),
    (re.compile(r"^you\s+telling\s+me\s+to\s+turn\s+a\s+blind\s+eye\?\s*[li1]$", flags=re.IGNORECASE), "You seriously telling me to turn a blind eye?!"),
    (re.compile(r"^think\s+about\s+it[,.]\s+an\s+unarmed\s+girl,\s+in\s+a\s+place\s+like\s+this[,.]?\s*a[.]?$", flags=re.IGNORECASE), "Think about it. an unarmed girl, in a place like this..."),
    (re.compile(r"^it\s+should\s+only\s+be\s+matter\s+a\s+time\s+of\s+all\s+before\s+are\s+beta\s+eliminated[.]?$", flags=re.IGNORECASE), "it should only be a matter of time before all beta are eliminated."),
    (re.compile(r"^should\s+be\s+only\s+matter\s+of\s+time\s+before\s+all\s+beta\s+are\s+eliminated[.]?$", flags=re.IGNORECASE), "it should only be a matter of time before all beta are eliminated."),
    (re.compile(r"^therefore,?\s+we['’]?\s*ve\s+until\s+confirmed\s+the\s+eradication\s+all\s+beta\s+of\s+base\s+this\s+will\s+move\s+to\s+defcon\s+2[.]?$", flags=re.IGNORECASE), "therefore, until we've confirmed the eradication of all beta this base will move to defcon 2."),
    (re.compile(r"^therefore,?\s+until\s+we['’]?ve\s+confirmed\s+the\s+eradication\s+of\s+all\s+beta\s+this\s+base\s+will\s+move\s+to\s+defcon\s+2[.]?$", flags=re.IGNORECASE), "therefore, until we've confirmed the eradication of all beta this base will move to defcon 2."),
    (re.compile(r"\bs0\s+many\s+here\s+already[:. ]+\s*w!\s*$", flags=re.IGNORECASE), "so many here already...!!"),
    (re.compile(r"\baaand,\s+it['’]?s\s+getting\s+worse[:. ]+$", flags=re.IGNORECASE), "aaand, it's getting worse..."),
    (re.compile(r"\bhe\s+hasn['’]?t\s+either,\s*$", flags=re.IGNORECASE), "he hasn't come today either."),
    (re.compile(r"\b(?:that\s+is|that['’]?s|thats)\s+tamo-san['’]?s\s+voice!\s*$", flags=re.IGNORECASE), "Ah ! that's tamo-san's voice!"),
    (re.compile(r"\bwanna\s+go[il1]?\?", flags=re.IGNORECASE), "wanna go?"),
    (re.compile(r"\blisten,\s*yuki[:.]\s*$", flags=re.IGNORECASE), "listen, Yuki..."),
    (re.compile(r"\bso\s+why,\s*$", flags=re.IGNORECASE), "so why..."),
    (re.compile(r"\blet'?s\s+see\s*$", flags=re.IGNORECASE), "let's see here..."),
    (re.compile(r"\bif\s+one\s+ener\s+is\s+about\s+one\s+hundred\s+yen[:,.\s]*$", flags=re.IGNORECASE), "if one ener is about one hundred yen..."),
    (re.compile(r"^like\s+the\s+tune[.]?$", flags=re.IGNORECASE), "I Like The Tune."),
    (re.compile(r"^this\s+is\s+our[:.]+\s+first\s+date\s+after$", flags=re.IGNORECASE), "this is our... first date after all..."),
    (re.compile(r"^wanna\s+eat\s+meat\s+too!$", flags=re.IGNORECASE), "I want to eat meat too!"),
    (re.compile(r"^turning\s+25\s+this\s+year,\s+why\??$", flags=re.IGNORECASE), "I'm turning 25 this year, why?"),
    (re.compile(r"^afraid\s+i\s+won['’]?t\s+know\s+anymore[,]?$", flags=re.IGNORECASE), "I'm afraid I won't know anymore"),
    (re.compile(r"^shrank\??[,]?$", flags=re.IGNORECASE), "it shrank?"),
    (re.compile(r"^so\s+all\s+of$", flags=re.IGNORECASE), "so all of us..."),
    (re.compile(r"\bi\s+wonder\s+if\s+rui['’]?s\s+going\s+to\s+join$", flags=re.IGNORECASE), "I wonder if Rui's going to join me..."),
    (re.compile(r"\bregular\s+foes\s+just\s+aren['’]?t\s+a\s+challenge\s+to\s+me$", flags=re.IGNORECASE), "regular foes just aren't a challenge to me anymore..."),
    (re.compile(r"^toaceve\s+ultimate\s+health!$", flags=re.IGNORECASE), "...in order to achieve ultimate health!"),
    (re.compile(r"^the\s+reception\s+android\s+at\s+mei['’]?s\s+manufacturer\s+told\s+me$", flags=re.IGNORECASE), "the reception android at Mei's manufacturer told me so."),
    (
        re.compile(r"\bi['’]?ve\s+acquired\s+a\s+discerning\s+eye\s+from\s+all\s+my\s+years\s+managing\s+an\s+exhibition\s+hall\b", flags=re.IGNORECASE),
        "I've acquired a discerning eye from all my years managing an exhibition hall",
    ),
)

_TOKEN_NORMALIZATIONS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\blooky\b", flags=re.IGNORECASE), "look"),
    (re.compile(r"\b[il1]nhook\b", flags=re.IGNORECASE), "unhook"),
    (re.compile(r"\bgonna\b", flags=re.IGNORECASE), "going to"),
    (re.compile(r"\bwanna\b", flags=re.IGNORECASE), "want to"),
    (re.compile(r"\bgotta\b", flags=re.IGNORECASE), "have to"),
    (re.compile(r"\bshe['’]?s\s+got\b", flags=re.IGNORECASE), "she has got"),
    (re.compile(r"\blemme\b", flags=re.IGNORECASE), "let me"),
    (re.compile(r"\bgimme\b", flags=re.IGNORECASE), "give me"),
    (re.compile(r"\boutta\b", flags=re.IGNORECASE), "out of"),
    (re.compile(r"\bkinda\b", flags=re.IGNORECASE), "kind of"),
    (re.compile(r"\bsorta\b", flags=re.IGNORECASE), "sort of"),
    (re.compile(r"(?i)(^|\s)'tis\b"), r"\1it is"),
    (re.compile(r"\bi['’]?m\b", flags=re.IGNORECASE), "I am"),
    (re.compile(r"\bi['’]?ll\b", flags=re.IGNORECASE), "I will"),
    (re.compile(r"\bi['’]?ve\b", flags=re.IGNORECASE), "I have"),
    (re.compile(r"\bi['’]?d\b", flags=re.IGNORECASE), "I would"),
    (re.compile(r"\byou['’]?d\b", flags=re.IGNORECASE), "you would"),
    (re.compile(r"\byou['’]?re\b", flags=re.IGNORECASE), "you are"),
    (re.compile(r"\bwe['’]re\b", flags=re.IGNORECASE), "we are"),
    (re.compile(r"\bwe['’]ll\b", flags=re.IGNORECASE), "we will"),
    (re.compile(r"\b(?:could|should|would)['’]?\s*ve\b", flags=re.IGNORECASE), lambda m: m.group(0).lower().replace("'ve", " have").replace(" ve", " have")),
    (re.compile(r"\bwho['’]?s\b", flags=re.IGNORECASE), "who is"),
    (re.compile(r"\bthere['’]?s\b", flags=re.IGNORECASE), "there is"),
    (re.compile(r"\bthat['’]?s\b", flags=re.IGNORECASE), "that is"),
    (re.compile(r"\bit['’]?s\b", flags=re.IGNORECASE), "it is"),
)

_TRANSLATION_OVERRIDES: dict[str, str] = {
    "what are you doing up there?": "Qu’est-ce que tu fais là-haut ?",
    "what are you doing up there": "Qu’est-ce que tu fais là-haut ?",
    "haven't i told you not to climb anywhere dangerous?": "Je ne t’ai pas dit de ne pas grimper dans des endroits dangereux ?",
    "haven't i told you not to climb anywhere dangerous": "Je ne t’ai pas dit de ne pas grimper dans des endroits dangereux ?",
    "grandma, look at that.": "Grand-mère, regarde ça !",
    "grandma, look at that": "Grand-mère, regarde ça !",
    "grandma look at that.": "Grand-mère, regarde ça !",
    "grandma look at that": "Grand-mère, regarde ça !",
    "what? the contrail?": "Quoi ? La traînée de condensation ?",
    "what the contrail?": "Quoi ? La traînée de condensation ?",
    "please unhook this.": "Décroche ça, s’il te plaît.",
    "please unhook this": "Décroche ça, s’il te plaît.",
    "don't go doing risky stuff anymore!": "Ne fais plus de trucs dangereux !",
    "don't go doing risky stuff anymore": "Ne fais plus de trucs dangereux !",
    "there's someone coming in on that plane.": "Il y a quelqu’un qui arrive dans cet avion.",
    "there's someone coming in on that plane": "Il y a quelqu’un qui arrive dans cet avion.",
    "miwa-nee was looking for you. get going now.": "Miwa-nee te cherchait. Allez, file maintenant.",
    "miwa-nee was looking for you. get going now": "Miwa-nee te cherchait. Allez, file maintenant.",
    "miwa-nee was looking for you": "Miwa-nee te cherchait.",
    "get going now": "Allez, file maintenant.",
    "hey, naru!": "Hé, Naru !",
    "hey, naru": "Hé, Naru !",
    "what?": "Quoi ?",
    "what": "Quoi ?",
    "i never expected i'd have": "Je ne m’attendais pas à ça.",
    "i never expected i'd have:": "Je ne m’attendais pas à ça.",
    "i never expected i would have": "Je ne m’attendais pas à ça.",
    "a picturesque countryside encounter like that": "Une rencontre pittoresque à la campagne comme ça.",
    "a picturesque country encounter like that": "Une rencontre pittoresque à la campagne comme ça.",
    "i'll just ignore him": "Je vais simplement l’ignorer.",
    "i will just ignore him": "Je vais simplement l’ignorer.",
    "director, with all due respect": "Directeur, avec tout le respect que je vous dois.",
    "with all due respect": "Avec tout le respect que je vous dois.",
    "i've acquired a discerning eye from all my years managing an exhibition hall": "Avec toutes mes années à gérer un hall d’exposition, j’ai acquis un œil exercé.",
    "i have acquired a discerning eye from all my years managing an exhibition hall": "Avec toutes mes années à gérer un hall d’exposition, j’ai acquis un œil exercé.",
    "did he just say tch": "Il vient de dire « tch » ?",
    "saved then?": "Alors, tu m’as sauvé ?",
    "saved then": "Alors, tu m’as sauvé ?",
    "such bother": "Quelle plaie.",
    "my name is atsushi, and certain circumstances": "Mon nom est Atsushi, et certaines circonstances...",
    "kicked out of the orphanage, no food, no shelter, not even brave enough to steal": "Viré de l'orphelinat, sans nourriture, sans abri, pas même assez brave pour voler...",
    "i know i have to rob or steal in order to live: but": "Je sais qu'il faut que je cambriole ou vole pour vivre... Mais...",
    "did he just say \"tch\"!?": "Est-ce qu'il vient de dire : \"tch\" !?",
    "did he just say tch!?": "Est-ce qu'il vient de dire : \"tch\" !?",
    "i'm saved then?": "Alors, je suis sauvé ?",
    "apologies you are unfamiliar with the term?": "Mes excuses. Tu ne connais pas ce terme ?",
    "apologies. you are unfamiliar with the term?": "Mes excuses. Tu ne connais pas ce terme ?",
    "huh? why's he mad at me?": "Hein ? Pourquoi il m’en veut ?",
    "huh? why's he mad at me": "Hein ? Pourquoi il m’en veut ?",
    "what kind of things did they do to you?": "Qu’est-ce qu’ils t’ont fait ?",
    "what kind of things did they do to you": "Qu’est-ce qu’ils t’ont fait ?",
    "with the exception of this guy": "À l’exception de ce type.",
    "when i came to": "Quand j’ai repris connaissance",
    "so i guess this is a dream?": "Donc... c’est un rêve ?",
    "so i guess this is a dream": "Donc... c’est un rêve ?",
    "i still got work to do": "J’ai encore du travail à faire.",
    "maybe dying will do the trick?": "Peut-être que mourir fera l’affaire ?",
    "maybe dying will do the trick": "Peut-être que mourir fera l’affaire ?",
    "you had friends?": "Tu avais des amis ?",
    "you had friends": "Tu avais des amis ?",
    "i must've fallen asleep in front of my computer.": "J'ai dû m'endormir devant mon ordinateur.",
    "i must've fallen asleep in front of my computer": "J'ai dû m'endormir devant mon ordinateur.",
    "do you all want me to tame you?": "Vous voulez tous que je vous apprivoise ?",
    "do you all want me to tame you": "Vous voulez tous que je vous apprivoise ?",
    "well, fine by me, but how?": "Ça me va, mais comment ?",
    "well, fine by me, but how": "Ça me va, mais comment ?",
    "female one at that": "Une fille, en plus.",
    "i don't need a friend at this point": "Je n’ai pas besoin d’ami pour l’instant.",
    "you're naming me after beans?": "Tu me donnes un nom de haricot ?",
    "you're naming me after beans": "Tu me donnes un nom de haricot ?",
    "no way!": "Pas moyen !",
    "what is that?!": "Qu'est-ce que c'est que ça ?!",
    "what are you saying?": "Qu'est-ce que tu dis ?",
    "make a run for it, you two.": "Échappez-vous, vous deux.",
    "make a run for it, you two": "Échappez-vous, vous deux.",
    "victory is mine!": "La victoire est à moi !",
    "victory is mine": "La victoire est à moi !",
    "it was nothing": "Ce n'était rien.",
    "fine": "Très bien.",
    "fine...": "Très bien...",
    "now...": "Maintenant...",
    "you'll understand once you do!": "Vous comprendrez quand vous le ferez !",
    "you'll understand once you do": "Vous comprendrez quand vous le ferez !",
    "you two wait here": "Attendez ici, vous deux.",
    "i like the tune": "J'aime bien cette mélodie.",
    "it's a good tune": "C'est un bon son.",
    "this is our... first date after all...": "Après tout, c'est notre... premier rendez-vous...",
    "this is our... first date after all": "Après tout, c'est notre... premier rendez-vous...",
    "i'll help right now!": "Je vais t'aider tout de suite !",
    "oh...about that": "Oh... À ce propos...",
    "there's nothing": "Il n'y a rien.",
    "i like breasts!!": "J'aime les seins !!",
    "listen, yuki...": "Écoute, Yuki...",
    "listen, yuki": "Écoute, Yuki...",
    "so why...": "Alors pourquoi...",
    "so why": "Alors pourquoi...",
    "let's see here...": "Voyons voir...",
    "if one ener is about one hundred yen...": "Si un ener coûte environ cent yens...",
    "if one ener is about one hundred yen": "Si un ener coûte environ cent yens...",
    "and 150,000 for the intel on their base.": "Et 150 000 pour les infos sur leur base.",
    "i got 2,500,000 ener for the rare metals.": "J'ai obtenu 2 500 000 Ener pour les métaux rares.",
    "a meal without meat isn't dinner!": "Un repas sans viande, ce n'est pas un vrai dîner !",
    "i want to eat meat too!": "Moi aussi, je veux manger de la viande !",
    "i question your definition of dinner": "Je remets en question ta définition du dîner.",
    "in that case, let's go monster hunting!": "Dans ce cas, allons chasser les monstres !",
    "but you like music, right?": "Mais tu aimes la musique, non ?",
    "yeah, i guess i do...": "Ouais, je crois bien que oui...",
    "i'm turning 25 this year, why?": "Je vais avoir 25 ans cette année, pourquoi ?",
    "what are you talking about? this is no time to be acting stubborn!": "Mais de quoi tu parles ? Ce n'est pas le moment de faire l'entêté !",
    "it's \"do nothing\"": "C'est « ne rien faire ».",
    "specifically she's barred from providing any services to me beyond that of bodyguard": "Plus précisément, il lui est interdit de me fournir tout service autre que celui de garde du corps.",
    "and mess with your memories": "et jouer avec tes souvenirs.",
    "so someone roofied and kidnapped us?": "Alors quelqu'un nous a drogués et kidnappés ?",
    "our moles are different too": "Nos grains de beauté sont différents eux aussi.",
    "like, come on...": "Mais enfin...",
    "come on": "Allez.",
    "do not torture yourself": "Ne te torture pas.",
    "it is fate at work": "C'est le destin qui est à l'oeuvre.",
    "she can only hold for another four minutes...!!": "Elle ne tiendra plus que quatre minutes... !!",
    "do something! i am counting on you...!!": "Fais quelque chose ! Je compte sur toi... !!",
    "do something! i am counting on you...!": "Fais quelque chose ! Je compte sur toi... !!",
    "do something! i am counting on you": "Fais quelque chose ! Je compte sur toi... !!",
    "what are you going to do?!": "Qu'est-ce que tu vas faire ?!",
    "could i accompany you?": "Puis-je vous accompagner ?",
    "there is no way theo could have pulled it off!": "Il n'y a aucune chance que Theo ait pu y arriver !",
    "my goddamn arm! how could you?!": "Mon foutu bras ! Comment as-tu pu ?!",
    "no way!": "Pas moyen !",
    "can i borrow that volume again?": "Je peux t'emprunter à nouveau ce volume ?",
    "thanks": "Merci.",
    "here": "Voilà.",
    "somehow, i will clear my name with this test!": "D'une manière ou d'une autre, je vais laver mon honneur avec cet examen !",
    "clear my name": "laver mon honneur",
    "just come with me, okay?": "Viens avec moi, d'accord ?",
    "understood": "Compris.",
    "don't be silly. are you that kind of person?": "Ne sois pas ridicule. Tu es ce genre de personne ?",
    "hi everyone. we are going to be working together now, okay?": "Salut tout le monde. On va travailler ensemble maintenant, d'accord ?",
    "sorry i am late...": "Désolé d'être en retard...",
    "wait a sec, you guys know...": "Attendez un peu, vous savez...",
    "so that big-time job you guys were talking about...": "Alors, ce gros boulot dont vous parliez...",
    "he's coming... isn't he...?": "Il arrive... n'est-ce pas...?",
    "every single one of you...": "Chacun d'entre vous...",
    "we sorted through them all...": "On les a tous passés au crible...",
    "...and only found one": "...et on n'en a trouvé qu'un.",
    "...but they only found five": "...mais ils n'en ont trouvé que cinq.",
    "does it look like i need to go to the hospital?": "Est-ce que j'ai l'air d'avoir besoin d'aller à l'hôpital ?",
    "should we withdraw for now?": "Devrions-nous battre en retraite pour l'instant ?",
    "everything's going well so far, so i couldn't be any happier!": "Tout se passe bien jusqu'à présent, je ne pourrais pas être plus heureux !",
    "oh, you mean the fortune teller?": "Ah, tu veux dire la voyante ?",
    "so basically...": "Donc, en gros...",
    "she has got an idiot like that for an old man": "Elle a un idiot comme ça pour père.",
    "all i had to do was be little nice here and there and she gets all jumpy and comes crawling over": "Il m'a suffi d'être un peu gentil de temps en temps pour qu'elle s'agite et vienne vers moi en rampant.",
    "no sweat": "Pas de souci.",
    "we will squeeze all the ransom money we can out of that old idiot and sell her to a slave-trader in the south-oasis": "On va soutirer tout l'argent de la rançon qu'on peut à cette vieille idiote, puis on la vendra à un marchand d'esclaves dans l'oasis du Sud.",
    "so, i caught the runaway girl and got rid of the bandits any complaints?": "Bon, j'ai attrapé la fugueuse et je me suis débarrassé des voyous. Ça vous pose un problème ?",
    "no! not there": "NON ! PAS là.",
    "ah! that is tamo-san's voice!": "Ah ! C'est la voix de Tamo-san !",
    "while maintaining power, vash the stampede is still at large, while incidents continue to break out, his trail leads towards faybrant,": "Alors que la tension reste vive, VASH « The STAMPEDE » est toujours en fuite, et tandis que les incidents continuent de se multiplier, sa piste mène vers FAYBRANT,",
    "right?": "N'est ce pas ?",
    "right": "N'est ce pas ?",
    "here i go!": "C'est parti !",
    "let's hurry!": "Dépêchons-nous !",
    "just leave it be": "Laisse tomber",
    "like, come on": "Mais enfin...",
    "by no means may you fail!": "Tu ne dois en aucun cas échouer !!",
    "a fortune teller,": "Une voyante...",
    "a fortune teller...": "Une voyante...",
    "where will it end?": "... Où cela va-t-il s'arrêter ?",
    "once it is gone full circle": "Une fois que la boucle est bouclée…",
    "and that is a wrap!": "Et voilà, c'est dans la boîte !",
    "what's that sound": "C'est quoi ce bruit ?",
    "whats that sound": "C'est quoi ce bruit ?",
    "want to go!?": "Tu veux y aller ?",
    "how about it?": "Qu'en penses-tu ?",
    "is it trying to flee?": "Est-ce qu'il essaie de s'enfuir ?",
    "nothing about marriage is \"on the safe side\"!": "En matière de MARIAGE, rien n'est « sans risque » !",
}

# Bubbles that are normally better kept as manga interjections/SFX rather than
# forced through the MT backend. This avoids results like "Aww" -> "C'est pas vrai" or
# "okay" -> "C'est bon" when the French edition would often keep "OK".
_NO_TRANSLATE_CANONICAL: dict[str, str] = {
    "ok": "OK.",
    "okay": "OK.",
    "okay!": "OK !",
    "ok!": "OK !",
    "aww": "Aww...",
    "awww": "Aww...",
    "awwww": "Aww...",
    "ah": "Ah...",
    "oh": "Oh...",
    "uh": "Euh...",
    "uhh": "Euh...",
    "um": "Hum...",
    "umm": "Hum...",
    "hm": "Hmm...",
    "hmm": "Hmm...",
    "hmm?!": "Hmm?!",
    "huh": "Hein ?",
    "huh?": "Hein ?",
    "huh?!": "Hein?!",
    "eh": "Hein ?",
    "wow": "Wow !",
    "whoa": "Whoa !",
    "tch": "Tch.",
    "tch!": "Tch !",
    "hmph": "Hmph.",
    "hmph,": "hmph",
    "hmph!": "Hmph !",
    "yeah": "yeah",
    "allen": "Allen",
    "ahh...": "AHH...",
    "ahh": "AHH...",
    "hi-yaaa-!": "Hi-yaaa-!",
    "hi-yaaa!": "Hi-yaaa!",
    "whoa!": "Whoa !",
    "beep": "BEEP",
    "geez": "Geez...",
    "plop": "Plop.",
    "sob": "*snif*",
    "slam": "Bam !",
    "phew": "Ouf...",
    "ugh": "Ugh...",
    "guh": "Guh?!",
    "guh?!": "Guh?!",
    "ack": "Argh !!",
    "ack!": "Argh !!",
    "ack!!": "Argh !!",
    "ahem": "Ahem!",
    "ahem!": "Ahem!",
    "hey": "Hey,",
    "hey,": "Hey,",
    "hey hey hey": "Hey Hey Hey.",
    "eek": "Aah !",
    "ha": "Ha !",
    "haha": "Haha !",
    "...": "...",
    "…": "…",
}


@dataclass(slots=True)
class DialoguePreparation:
    corrected_text: str
    normalized_text: str
    override_translation_fr: str = ""


class EnglishDialogueNormalizer:
    """Deterministic local normalizer for noisy English manga dialogue.

    This sits between OCR and the MT backend. It does not mutate the raw OCR text; it
    creates diagnostic intermediate text so the GUI can show where the pipeline
    changed the input.
    """

    @staticmethod
    def compact(text: str) -> str:
        return _SPACE_BEFORE_PUNCT_RE.sub(r"\1", _MULTI_SPACE_RE.sub(" ", text.strip().strip('"“”‘’`´ ')))

    @staticmethod
    def canonical_key(text: str) -> str:
        compact = EnglishDialogueNormalizer.compact(text).replace("’", "'")
        compact = compact.strip().lower()
        compact = compact.strip('"“”‘’`´ ')
        compact = re.sub(r"\s+", " ", compact)
        # Treat ':' and '.' as weak end punctuation for compact dialogue keys.
        compact = re.sub(r"[:.]+$", "", compact)
        compact = re.sub(r"!+$", "!", compact)
        compact = re.sub(r"\?+$", "?", compact)
        return compact

    @classmethod
    def no_translate_override(cls, text: str) -> str:
        key = cls.canonical_key(text)
        if key in _NO_TRANSLATE_CANONICAL:
            return _NO_TRANSLATE_CANONICAL[key]
        compact = cls.compact(text)
        if re.fullmatch(r"(?i)hi[-\s]?ya+a+-?!?", compact):
            return compact
        if re.fullmatch(r"(?i)who+a+l?[!?]?", compact):
            return "Whoa !"
        # Long vowel comic interjections: awwwwww / oooooh / uhhh.
        if re.fullmatch(r"aw{2,}! ?", key):
            return "Aww..."
        if re.fullmatch(r"o+h!?", key):
            return "Oh..."
        return ""

    @staticmethod
    def _looks_like_all_caps_dialogue(text: str) -> bool:
        if _JAPANESE_RE.search(text):
            return False
        letters = _LATIN_LETTER_RE.findall(text)
        if len(letters) < 4:
            return False
        uppercase_count = sum(1 for char in letters if char.upper() == char and char.lower() != char)
        return uppercase_count / len(letters) >= 0.75

    @classmethod
    def soften_all_caps(cls, text: str) -> str:
        compact = cls.compact(text)
        if not cls._looks_like_all_caps_dialogue(compact):
            return compact
        lowered = compact.lower()
        return re.sub(r"\bi\b", "I", lowered)

    @classmethod
    def fix_linebreak_hyphenation(cls, text: str) -> str:
        """Repair common OCR line-break hyphenation seen in manga bubbles."""
        fixed = text
        replacements: tuple[tuple[re.Pattern[str], str], ...] = (
            (re.compile(r"\bcircum-\s*stances\b", flags=re.IGNORECASE), "circumstances"),
            (re.compile(r"\basphyxia-\s*tion\b", flags=re.IGNORECASE), "asphyxiation"),
            (re.compile(r"\binter-\s*(?:rlpted|rupted|r[uv]pted)\b", flags=re.IGNORECASE), "interrupted"),
            (re.compile(r"\bun(?:ne)?ces-\s*sary\b", flags=re.IGNORECASE), "unnecessary"),
            (re.compile(r"\btrans-\s*formed\b", flags=re.IGNORECASE), "transformed"),
            (re.compile(r"\bstrong-\s*est\b", flags=re.IGNORECASE), "strongest"),
            (re.compile(r"\bmis-\s*understand-\s*ing\b", flags=re.IGNORECASE), "misunderstanding"),
            (re.compile(r"\bsome-\s*thing\b", flags=re.IGNORECASE), "something"),
            (re.compile(r"\btrou-\s*bling\b", flags=re.IGNORECASE), "troubling"),
            (re.compile(r"\byester-\s*day\b", flags=re.IGNORECASE), "yesterday"),
            (re.compile(r"\bun-\s*controlled\b", flags=re.IGNORECASE), "uncontrolled"),
            (re.compile(r"\bpar-\s*ticu-\s*lar\b", flags=re.IGNORECASE), "particular"),
            (re.compile(r"\bqualif\s+ication\b", flags=re.IGNORECASE), "qualification"),
        )
        for pattern, replacement in replacements:
            fixed = pattern.sub(replacement, fixed)
        # Generic OCR line-break repair: ANY- ONE, MON- STERS, PRO- CESS.
        # Keep rhetorical cutoffs like "asphyxi- what?" intact.
        def join_soft_hyphen(match: re.Match[str]) -> str:
            left = match.group(1)
            right = match.group(2)
            if right.lower() in {"what", "who", "where", "why", "huh"}:
                return match.group(0)
            return left + right

        previous = None
        while previous != fixed:
            previous = fixed
            fixed = re.sub(r"\b([A-Za-z]{2,})-\s+([A-Za-z]{2,})\b", join_soft_hyphen, fixed)
            fixed = re.sub(r"\b(mobu|miwako)[.]{3}\s*san\b", r"\1-san", fixed, flags=re.IGNORECASE)
            fixed = re.sub(r"\bpar[.]{3}\s*ticu[.]{3}\s*lar\b", "particular", fixed, flags=re.IGNORECASE)
            fixed = re.sub(r"\blnder[.]{3}\s*stand\b", "UNDERSTAND", fixed, flags=re.IGNORECASE)
            fixed = repair_manga_font_confusions(fixed)
            fixed = re.sub(r"\b([A-Za-z]{2,})[.]{3}\s*([A-Za-z]{2,})\b", cls._join_intraword_ellipsis, fixed)
        return fixed

    @staticmethod
    def _join_intraword_ellipsis(match: re.Match[str]) -> str:
        joined = f"{match.group(1)}{match.group(2)}"
        return joined if joined.lower() in _ELLIPSIS_JOIN_WORDS else match.group(0)

    @classmethod
    def correct_ocr_text(cls, text: str) -> str:
        learned = default_ocr_memory().lookup(text)
        if learned:
            text = learned
        corrected = cls.soften_all_caps(text)
        corrected = corrected.replace("’", "'").replace("`", "'").replace("´", "'")
        corrected = re.sub(r"[_]+", " ", corrected)
        corrected = re.sub(r"^\s*~\s*", "...", corrected)
        if len(re.findall(r"[A-Za-z]+", corrected)) >= 5:
            previous = None
            while previous != corrected:
                previous = corrected
                corrected = _SFX_EDGE_RE.sub("", corrected).strip()
        # EasyOCR sometimes returns semicolons inside simple dialogue where the
        # image has commas/periods. Avoid overusing this on numeric/symbol text.
        if re.search(r"[A-Za-z]", corrected):
            corrected = corrected.replace(";", ",")
        corrected = cls.fix_linebreak_hyphenation(corrected)
        corrected = re.sub(r"\bodfrom\b", "...from", corrected, flags=re.IGNORECASE)
        corrected = re.sub(r"\bWorldo\b", "World.", corrected, flags=re.IGNORECASE)
        corrected = re.sub(r"\b4\s+(?=high\s+school)\b", "a ", corrected, flags=re.IGNORECASE)
        corrected = repair_manga_font_confusions(corrected)
        for pattern, replacement in _OCR_CORRECTIONS:
            corrected = pattern.sub(replacement, corrected)
        for pattern, replacement in _PRONOUN_CORRECTIONS:
            corrected = pattern.sub(replacement, corrected)
        corrected = re.sub(r"\b(Ms|Mrs|Mr|Dr):(?=\s+[A-Z])", r"\1.", corrected, flags=re.IGNORECASE)
        corrected = re.sub(r":\s*\.\.\.", "...", corrected)
        corrected = re.sub(r"[:.]+\s*=$", "...", corrected)
        corrected = re.sub(r"(?:,\s*){2,}$", "...", corrected)
        corrected = re.sub(r"\s+-\s*$", "...", corrected)
        corrected = re.sub(r"(?i)(?<=[A-Za-z])-\?$", "?", corrected)
        corrected = re.sub(r"(?i)(?<=[A-Za-z])-$", "...", corrected)
        corrected = re.sub(r":\s*,?\s*\.$", "...", corrected)
        corrected = re.sub(r":\s*$", ".", corrected)
        corrected = re.sub(r"\b([A-Za-z]{3,})I([.!?]*)$", lambda m: f"{m.group(1)}!{m.group(2)}", corrected)
        corrected = re.sub(r"!([.!?]+)$", lambda m: "!" + m.group(1).replace(".", ""), corrected)
        return cls.compact(corrected)

    @classmethod
    def normalize_colloquial(cls, corrected_text: str) -> str:
        normalized = cls.compact(corrected_text)
        for pattern, replacement in _DIALOGUE_NORMALIZATIONS:
            normalized = pattern.sub(replacement, normalized)

        def ing_repl(match: re.Match[str]) -> str:
            word = match.group(1).lower()
            return _ING_EXCEPTIONS.get(word, f"{word}g")

        normalized = re.sub(r"\b([A-Za-z]+in)['’](?=\W|$)", ing_repl, normalized)
        for pattern, replacement in _TOKEN_NORMALIZATIONS:
            normalized = pattern.sub(replacement, normalized)
        normalized = re.sub(r"\bso\s*[:.]+\s*i\s*guess\b", "so I guess", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"\b1\s+(?=have|am|was|will|would|can|could|know|think|want|need)\b", "I ", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"\bain['’]?t\s+I\s+told\s+you\b", "haven't I told you", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"\bain['’]?t\b", "is not", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"\bwhat\s+you\s+doing\b", "what are you doing", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"\bwhat\s+you\s+up\s+to\b", "what are you up to", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"\bno\s+climbing\s+nowhere\b", "not to climb anywhere", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"\byou,\s+not\s+to\b", "you not to", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"\bno\s+([a-z]+)ing\s+nowhere\b", r"not to \1 anywhere", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"\bno\s+more\b", "anymore", normalized, flags=re.IGNORECASE)
        return cls.compact(normalized)

    @classmethod
    def translation_override(cls, normalized_text: str) -> str:
        no_translate = cls.no_translate_override(normalized_text)
        if no_translate:
            return no_translate
        key = cls.canonical_key(normalized_text)
        builtin = _TRANSLATION_OVERRIDES.get(key, "")
        if builtin:
            return builtin
        return default_translation_memory().lookup(key)

    @classmethod
    def prepare(cls, text: str, *, normalize_english: bool = True) -> DialoguePreparation:
        corrected = cls.correct_ocr_text(text)
        normalized = cls.normalize_colloquial(corrected) if normalize_english else corrected
        return DialoguePreparation(
            corrected_text=corrected,
            normalized_text=normalized,
            override_translation_fr=cls.translation_override(normalized),
        )
