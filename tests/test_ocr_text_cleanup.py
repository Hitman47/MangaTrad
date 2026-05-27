from __future__ import annotations

from cbz_manga_translator.ocr.candidates import candidate_quality
from cbz_manga_translator.ocr.fallback_engine import OcrFallbackEngine
from cbz_manga_translator.ocr.text_cleanup import (
    has_random_ocr_casing,
    normalize_ocr_text_for_translation,
)


def test_normalize_random_easyocr_casing() -> None:
    assert has_random_ocr_casing("I NeVeR Expected I'D HAVE:")
    assert normalize_ocr_text_for_translation("I NeVeR Expected I'D HAVE:") == "I never expected I'd have."


def test_normalize_short_semicolon_dialogue() -> None:
    assert normalize_ocr_text_for_translation("Director; With All Due ReSpect. .") == "Director, with all due respect."


def test_common_ocr_corrections_run_after_cleanup() -> None:
    assert OcrFallbackEngine.apply_common_ocr_corrections("Director; With All Due ReSpect. .") == "Director, with all due respect."
    assert OcrFallbackEngine.apply_common_ocr_corrections("I'Il just ignore him") == "I'll just ignore him"


def test_candidate_quality_penalizes_random_case_noise() -> None:
    noisy = candidate_quality("I NeVeR Expected I'D HAVE:", 0.72)
    clean = candidate_quality("I never expected I'd have:", 0.72)
    assert clean > noisy


def test_normalize_linebreak_hyphen_and_common_ocr_typos() -> None:
    assert normalize_ocr_text_for_translation("CERTAIN CIRCUM- STANCES") == "CERTAIN CIRCUMSTANCES"
    assert normalize_ocr_text_for_translation("YeS. He TRANS- FORMED INTO ANIMAL Fopm") == "Yes. he transformed into animal form"
    assert normalize_ocr_text_for_translation("The Tiger TCO WAS sighted FOLR DAYS Ago.") == "The Tiger TCO was sighted four days ago."
    assert normalize_ocr_text_for_translation("ISN'T THAT WHAT A MAN'S POMANCE IS") == "ISN'T THAT WHAT A MAN'S ROMANCE IS"
    assert normalize_ocr_text_for_translation("THAT REASON IS WAY TOO STRANCE ISN'T") == "THAT REASON IS WAY TOO STRANGE ISN'T"
    assert normalize_ocr_text_for_translation("I've WAITED FOR TOO Loncw") == "I've WAITED FOR TOO LONG!!!"
    assert normalize_ocr_text_for_translation("He 'return- ed the dam age?!") == "He returned the damage?!"
    assert normalize_ocr_text_for_translation("He 'returned the damage?!") == "He returned the damage?!"
    assert normalize_ocr_text_for_translation("Bal ancell") == "Balance!!"
    assert normalize_ocr_text_for_translation("Obviously, sensed the danger, and so returned the damagel") == "Obviously, I sensed the danger, and so returned the damage!"


def test_review_learned_ocr_cleanup_examples() -> None:
    assert normalize_ocr_text_for_translation("WHAATI? PEALLYI?") == "what? really?"
    assert normalize_ocr_text_for_translation("The KAWAZL Family") == "The KAWAZU Family"
    assert normalize_ocr_text_for_translation("Sepiously Dont do Something LNNECES- SARY") == "seriously don't do Something unnecessary"
    assert normalize_ocr_text_for_translation("BMUSTHVB GALLENL ASLEEP inifront Computers") == "I must've fallen asleep in front of my computer."


def test_second_review_batch_ocr_cleanup_examples() -> None:
    assert normalize_ocr_text_for_translation("NO WAYI") == "no way!"
    assert normalize_ocr_text_for_translation("Victopy is Minel!") == "Victory is Mine!"
    assert normalize_ocr_text_for_translation("arb What saying? You") == "What are you saying?"
    assert normalize_ocr_text_for_translation("YOU'LL UNDER- STAND ONCE YOU DO!") == "YOU'LL UNDERSTAND ONCE YOU DO!"


def test_third_review_batch_sfx_edges_and_ocr_cleanup_examples() -> None:
    assert normalize_ocr_text_for_translation("WHISPER WE ALWAYS TAKE YOU OUT ON OUR QUESTS, RIGHT? WHISPER") == "WE ALWAYS TAKE YOU OUT ON OUR QUESTS, RIGHT?"
    assert normalize_ocr_text_for_translation("Fop Singing") == "For Singing"
    assert normalize_ocr_text_for_translation("Fljimura-kln") == "Fujimura-kun"
    assert normalize_ocr_text_for_translation("WHAAAI?") == "WHAAAT?"
    assert normalize_ocr_text_for_translation("BREASTSI!") == "breasts!!"


def test_fourth_review_batch_punctuation_numbers_and_hyphenation_examples() -> None:
    assert normalize_ocr_text_for_translation("The Drugs ARE Still IN YOUR System:") == "The Drugs ARE Still IN YOUR System."
    assert normalize_ocr_text_for_translation("Don't do Anything Sudden:") == "Don't do Anything Sudden."
    assert normalize_ocr_text_for_translation("LISTEN, Yuki:") == "LISTEN, Yuki..."
    assert normalize_ocr_text_for_translation("SO Why,") == "SO Why..."
    assert normalize_ocr_text_for_translation("IF ONE ENER IS About one HLNDRED YEN:, .") == "IF ONE ENER IS About one hundred YEN..."
    assert normalize_ocr_text_for_translation("AND I50, 000 FOR THE INTEL ON THEIR BASE:") == "AND 150,000 FOR THE INTEL ON THEIR BASE."
    assert normalize_ocr_text_for_translation("MAYBE SOME UN- CONTROLLED MONSTERS") == "MAYBE SOME UNCONTROLLED MONSTERS"
    assert normalize_ocr_text_for_translation("In PAR- Ticu- LAR:") == "In particular."
    assert normalize_ocr_text_for_translation("qualification t0 be here, our Iives") == "qualification to be here, our lives"
    assert normalize_ocr_text_for_translation("Feels Like The Kind OF Thing 4 High SCHOOL BOY would") == "Feels Like The Kind OF Thing a High SCHOOL BOY would"


def test_fifth_review_batch_punctuation_digits_and_hyphenation_examples() -> None:
    assert normalize_ocr_text_for_translation("HE'S A Big-time Ceo_") == "HE'S A Big-time CEO"
    assert normalize_ocr_text_for_translation("A MEAL without MEAT ISN'T DINNERI") == "A MEAL without MEAT ISN'T DINNER!"
    assert normalize_ocr_text_for_translation("AND:. =") == "AND..."
    assert normalize_ocr_text_for_translation("~But I Agree With The Other PARTS.") == "...But I Agree With The Other PARTS."
    assert normalize_ocr_text_for_translation("I MUST SHOW MS: ELIZABETH, MS: KAREN, AND MS: UNDINE.") == "I MUST SHOW MS. ELIZABETH, MS. KAREN, AND MS. UNDINE."
    assert normalize_ocr_text_for_translation("WE'LL ACCEPT THIS QUEST,, ,") == "WE'LL ACCEPT THIS QUEST..."
    assert normalize_ocr_text_for_translation("The RECEPTION ANDPOID At Mei's MANU- FACTURER TOLD ME") == "The RECEPTION android At Mei's MANUFACTURER TOLD ME"
    assert normalize_ocr_text_for_translation("WHAT Ape yo4 TALKING Abolt? THIS IS No TIME To Be ACTING STUBBORNI") == "WHAT Are you TALKING About? THIS IS No TIME To Be ACTING STUBBORN!"


def test_sixth_review_batch_incomplete_bubbles_questions_and_contractions() -> None:
    assert normalize_ocr_text_for_translation("DO NOT YOURSELF") == "do not torture yourself"
    assert normalize_ocr_text_for_translation("DO Some- thing! I'm Counting ON") == "DO something! I'm Counting ON you...!!"
    assert normalize_ocr_text_for_translation("WHAT GOING") == "what are you going to do?!"
    assert normalize_ocr_text_for_translation("Could accomp any you?") == "Could I accompany you?"
    assert normalize_ocr_text_for_translation("there'@ NO WAY Theo COULD Ve pulled It OFF!") == "there's no way theo could've pulled it off!"
    assert normalize_ocr_text_for_translation("CAN I BOPROW THAT Volume AGAIN?") == "CAN I borrow THAT Volume AGAIN?"
    assert normalize_ocr_text_for_translation("WHAT The,") == "what the...?!"
    assert normalize_ocr_text_for_translation("4NDER- STOOD.") == "Understood."


def test_seventh_review_batch_ellipsis_and_zone_examples() -> None:
    assert normalize_ocr_text_for_translation(": why isn't Sigma-kun Waking Up.") == "...why isn't Sigma-kun waking up...?"
    assert normalize_ocr_text_for_translation("He's COMING. ISN'T He,.") == "he's coming... isn't he...?"
    assert normalize_ocr_text_for_translation("Hi everyone We're going To Be working Together now, OKAY-?") == "Hi everyone. We're going to be working together now, okay?"
    assert normalize_ocr_text_for_translation("SORRY I'm LATE-") == "sorry I'm late..."
    assert normalize_ocr_text_for_translation("WAIT A SEC, You guys") == "WAIT A SEC, You guys know..."
    assert normalize_ocr_text_for_translation("So THAT Big-twme job You Guys Were talking About.") == "So THAT Big-time job You Guys Were talking About..."
    assert normalize_ocr_text_for_translation("LNDER- STAND Why knives CHOSE This PLACE.") == "I UNDERSTAND Why Knives CHOSE This PLACE..."
    assert normalize_ocr_text_for_translation("Only found Five.") == "...but they only found five."
    assert normalize_ocr_text_for_translation("SHOLLD WE WITHORAW For Now?") == "should WE withdraw For Now?"


def test_fast_ten_batch_reviewed_ocr_examples() -> None:
    assert normalize_ocr_text_for_translation("ALL [ HAD TO DO Was BE LITTLE NICE HERE AND THERE") == "all I had to do Was BE LITTLE NICE HERE AND THERE"
    assert normalize_ocr_text_for_translation("SHE'S G0T An IDIOT Like that FOR AM OLD MAN.") == "SHE'S GOT An IDIOT Like that for an old man."
    assert normalize_ocr_text_for_translation("So, I CALGHT The Rlnaway girl And got rid Of the bandis ANY COMP... LAINTS?") == "So, I CAUGHT The Runaway girl And got rid Of the bandits ANY COMPLAINTS?"
    assert normalize_ocr_text_for_translation("NO! NOT Thepe.") == "NO! NOT There."
    assert normalize_ocr_text_for_translation("I'm THE SOUTH-OASIS.") == "In THE SOUTH-OASIS."
    assert normalize_ocr_text_for_translation("S0 MANY HERE ALREADY:. W!") == "so many here already...!!"
    assert normalize_ocr_text_for_translation("AAAND, It's GETTING WORSE:. .") == "aaand, it's getting worse..."


def test_replay_global_common_ocr_repairs() -> None:
    assert normalize_ocr_text_for_translation("4nder... stood.") == "Understood."
    assert normalize_ocr_text_for_translation("Let's hurryi") == "Let's Hurry!"
    assert normalize_ocr_text_for_translation("Here I Gol") == "Here I Go!"
    assert normalize_ocr_text_for_translation("Here:..") == "Here..."
    assert normalize_ocr_text_for_translation("Hlhi?") == "HUH!?"
    assert normalize_ocr_text_for_translation("Kow About") == "How About it?"
    assert normalize_ocr_text_for_translation("you'll under... stand once you do!") == "you'll understand once you do!"
    assert normalize_ocr_text_for_translation("Hunt... Ing") == "...I'm hunting you!!"


def test_replay_learned_intraword_ellipsis_and_short_fragment_repairs() -> None:
    assert normalize_ocr_text_for_translation("trou... bling?") == "troubling?"
    assert normalize_ocr_text_for_translation("Are you ser... ious?") == "Are you serious?"
    assert normalize_ocr_text_for_translation("so some... one roofied and kid... napped us?") == "so someone roofied and kidnapped us?"
    assert normalize_ocr_text_for_translation("In PAR... Ticu... LAR.") == "In particular."
    assert normalize_ocr_text_for_translation("Why Did I") == "Why Did I...?"
    assert normalize_ocr_text_for_translation("this IS MY FAULT") == "this IS MY FAULT...?"
    assert normalize_ocr_text_for_translation("they aren't making") == "they aren't making a move..."
    assert normalize_ocr_text_for_translation("fine,") == "fine..."
    assert normalize_ocr_text_for_translation("then") == "then?"


def test_manga_font_ul_i_bang_confusion_profile() -> None:
    assert normalize_ocr_text_for_translation("ISN'T Lrabe COMING TODAY?") == "ISN'T Urabe COMING TODAY?"
    assert normalize_ocr_text_for_translation("then? WHAT WOLLD have DONE?") == "then? WHAT would have DONE?"
    assert normalize_ocr_text_for_translation("Now that You MEN... TIONED THE Previous Prez") == "Now that You MENTIONED THE Previous Prez"
    assert normalize_ocr_text_for_translation("01, cut it Out al... Read!!") == "Oi, cut it Out already!!"
    assert normalize_ocr_text_for_translation("Hehl I can feel The pressure From her magic! THAT'S A GREAT SAGE FOR Youl") == "Heh! I can feel The pressure From her magic! THAT'S A GREAT SAGE FOR You!"
    assert normalize_ocr_text_for_translation("She was TRYING TO PROTECT Everyone Becalse the STAFF Went O4t OF CONTROL!") == "She was TRYING TO PROTECT Everyone Because the STAFF Went Out OF CONTROL!"
    assert normalize_ocr_text_for_translation("WHAT 9i") == "WHAT?!"
    assert normalize_ocr_text_for_translation("You Seriolsly Me Tellin' TO TURN BLIND A Eye? i") == "You Seriously Me Tellin' TO TURN BLIND A Eye? i"
    assert normalize_ocr_text_for_translation("SHE'S NOT GONNA Supve MUCH LONGER ON HER OWN.") == "SHE'S NOT GONNA survive MUCH LONGER ON HER OWN."
    assert normalize_ocr_text_for_translation("what kind of Shifty Tkinbs are You Doing In tke stl... DENT COLN...") == "what kind of Shifty THINGS are You Doing In the student COUNCIL"
    assert normalize_ocr_text_for_translation("just kidding say anything was danserols here the previous president's ex... istence") == "just kidding say anything was dangerous here the previous president's existence"
    assert normalize_ocr_text_for_translation("YOU telling Me TO TURN A BLIND Eye? l") == "YOU telling Me TO TURN A BLIND Eye? l"


def test_latest_reviewed_manga_font_examples() -> None:
    assert normalize_ocr_text_for_translation("It connectedl") == "It connected!"
    assert normalize_ocr_text_for_translation("What? It wasntt Uthe Judgel") == "What? It wasn't the Judge!!"
    assert normalize_ocr_text_for_translation("When didhe") == "When did he"
    assert normalize_ocr_text_for_translation("4SAMI?") == "Usami?"
    assert normalize_ocr_text_for_translation("You Jlst Bot NETO... Pare'd") == "You just got netorare'd"
    assert normalize_ocr_text_for_translation("Fuji... MLRA,") == "...Fujimura..."
    assert normalize_ocr_text_for_translation("FujiMLRA,") == "...Fujimura..."
    assert normalize_ocr_text_for_translation("is that s?") == "is that so?"
    assert normalize_ocr_text_for_translation("be great if") == "It would Be GREAT If"
    assert normalize_ocr_text_for_translation("They're ALL So") == "They're ALL So... Young..."
    assert normalize_ocr_text_for_translation("It would Be GREAT Ip") == "It would Be GREAT If"
    assert normalize_ocr_text_for_translation("MADE Itw") == "MADE It!!"
    assert normalize_ocr_text_for_translation("Ishe DEAD?") == "Is he DEAD?"
    assert normalize_ocr_text_for_translation("OSAMU... KUN.") == "Osamu-kun."


def test_zone_fallback_batch_font_digit_repairs() -> None:
    assert normalize_ocr_text_for_translation("If I only KNEW About This a few Houps AGO: ' ~") == "If I only KNEW About This a few Hours ago..."
    assert normalize_ocr_text_for_translation("I told The entire ACADEMY Student B0DY To CHALLENGE Me.") == "I told The entire ACADEMY Student Body To CHALLENGE Me."
    assert normalize_ocr_text_for_translation("All two THOLSAND Sevenn students") == "All two THOUSAND Seven students"


def test_finish_english_validation_ocr_repairs() -> None:
    assert (
        normalize_ocr_text_for_translation("The ONLY WAY To BREAK YOUR INVINC! Bility Force You To Let G0 OF this SWORD")
        == "The only way to break your invincibility is to force you to let go of this sword."
    )
    assert normalize_ocr_text_for_translation("I'e Broken ITI") == "I've broken it!"
    assert normalize_ocr_text_for_translation("GRAB MY LAPEL AND GOFOR A Ghoulder") == "GRAB MY LAPEL AND go for A shoulder"
    assert normalize_ocr_text_for_translation("Hundred THOUSAND People Will Diel") == "Hundred THOUSAND People Will die!"
    assert normalize_ocr_text_for_translation("He Took AME-NO- Gozen FROM Me!") == "He took Ame-no-Gozen from me!"
    assert normalize_ocr_text_for_translation("S0 PEAL COLDW!") == "so real cold!!!"
    assert normalize_ocr_text_for_translation("It's really Trlelll") == "It's really true!!!"
    assert normalize_ocr_text_for_translation("Th-the Provosti?") == "Th-the Provost?"
    assert normalize_ocr_text_for_translation('YOUR "Plblic TRANSIT"') == 'YOUR "public TRANSIT"'
    assert normalize_ocr_text_for_translation("MISUN- DER- STAND- INGU") == "misunderstanding"
    assert normalize_ocr_text_for_translation("You REALLY CAME Peek.") == "You REALLY came to peek...?"


def test_candidate_quality_prefers_reviewed_font_digit_repairs() -> None:
    assert candidate_quality("If I only KNEW About This a few Hours AGO.", 0.53) > candidate_quality("If I only KNEW About This a few Houps AGO.", 0.53)
    assert candidate_quality("Student Body", 0.62) > candidate_quality("Student B0DY", 0.62)


def test_latest_clean_batch_ocr_repairs() -> None:
    assert normalize_ocr_text_for_translation("Who 6ives A RAMN About HAVING A Perfectly Accurate Setupi?") == "Who gives A DAMN About HAVING A Perfectly Accurate Setup!!?"
    assert normalize_ocr_text_for_translation("Howdid it even Get to this Point?") == "How did it even Get to this Point?"
    assert normalize_ocr_text_for_translation("THAT ONE Ooo Incident EARLIER this Morningb") == "THAT ONE Ooo Incident EARLIER this Morning"
    assert normalize_ocr_text_for_translation("A DESK Posi... TION. Let's \"NG SEE,") == "A DESK POSITION. Let's \"NG SEE..."
    assert normalize_ocr_text_for_translation("PC TIC Le MARKETING SE OR Promo... TIONS,") == "PC TIC Le MARKETING SE OR Promotions..."
    assert normalize_ocr_text_for_translation("MAYU, I MUST E NODDED OFF.") == "MAYU, I must've nodded off."
    assert normalize_ocr_text_for_translation("CAPTAIN HIPO.") == "captain hiro."
    assert normalize_ocr_text_for_translation("V WAIT A Second, GIANT!") == "WAIT A Second, GIANT!"
