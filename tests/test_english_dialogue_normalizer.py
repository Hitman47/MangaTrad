from __future__ import annotations

from cbz_manga_translator.translate.english_dialogue_normalizer import EnglishDialogueNormalizer


def test_dialogue_normalizer_keeps_diagnostic_steps() -> None:
    prepared = EnglishDialogueNormalizer.prepare("AIN'T AH TOID YA, NO CLIMBIN' NOWHERE DANGEROUS?")

    assert prepared.corrected_text == "ain't I told you, no climbin' nowhere dangerous?"
    assert prepared.normalized_text == "haven't I told you not to climb anywhere dangerous?"
    assert prepared.override_translation_fr == "Je ne t’ai pas dit de ne pas grimper dans des endroits dangereux ?"


def test_dialogue_normalizer_handles_grandma_looky_that() -> None:
    prepared = EnglishDialogueNormalizer.prepare("GRAMMA, LOOKY THAT.")

    assert prepared.corrected_text == "grandma, looky that."
    assert prepared.normalized_text == "grandma, look at that."
    assert prepared.override_translation_fr == "Grand-mère, regarde ça !"


def test_dialogue_normalizer_keeps_short_interjections_out_of_mt() -> None:
    assert EnglishDialogueNormalizer.prepare("Aww:").override_translation_fr == "Aww..."
    assert EnglishDialogueNormalizer.prepare("okay:").override_translation_fr == "OK."


def test_dialogue_normalizer_repairs_inhook_and_overrides_translation() -> None:
    prepared = EnglishDialogueNormalizer.prepare("please Inhook this")

    assert prepared.corrected_text == "please unhook this"
    assert prepared.normalized_text == "please unhook this"
    assert prepared.override_translation_fr == "Décroche ça, s’il te plaît."


def test_dialogue_normalizer_handles_risky_stuff_warning() -> None:
    prepared = EnglishDialogueNormalizer.prepare("DoN'T you Go DOiN' Risky StuFF No MoRe!")

    assert prepared.normalized_text == "don't go doing risky stuff anymore!"
    assert prepared.override_translation_fr == "Ne fais plus de trucs dangereux !"


def test_dialogue_normalizer_handles_miwa_nee_sentence() -> None:
    prepared = EnglishDialogueNormalizer.prepare("MIWA-NEE WAS LOOKIN' FOR YA. GET GOIN' NOW.")

    assert prepared.normalized_text == "Miwa-nee was looking for you. get going now."
    assert prepared.override_translation_fr == "Miwa-nee te cherchait. Allez, file maintenant."


def test_dialogue_normalizer_short_questions_and_seen_bad_translations() -> None:
    assert EnglishDialogueNormalizer.prepare('WHAT?').override_translation_fr == 'Quoi ?'

    country = EnglishDialogueNormalizer.prepare('"A Picturesque COUNTRY ENCOUNTER Like THAT')
    assert country.normalized_text == 'a picturesque countryside encounter like that'
    assert country.override_translation_fr == 'Une rencontre pittoresque à la campagne comme ça.'

    ignore = EnglishDialogueNormalizer.prepare("I'll Just IGNORE Him:")
    assert ignore.normalized_text == "I will just ignore him."
    assert ignore.override_translation_fr == 'Je vais simplement l’ignorer.'

    expected = EnglishDialogueNormalizer.prepare("I NEVER Expected I'D HAVE:")
    assert expected.normalized_text == "I never expected I would have."
    assert expected.override_translation_fr == 'Je ne m’attendais pas à ça.'


def test_dialogue_normalizer_handles_due_respect_and_exhibition_line() -> None:
    due_respect = EnglishDialogueNormalizer.prepare("Director; With All Due ReSpect. .")
    assert due_respect.normalized_text == "director, with all due respect.."
    assert due_respect.override_translation_fr == "Directeur, avec tout le respect que je vous dois."

    acquired = EnglishDialogueNormalizer.prepare("I'VE ACQUIRED A DISCERNING EYE FROM ALL MY YEARS MANAGING AN EXHIBITION HALL")
    assert acquired.override_translation_fr == "Avec toutes mes années à gérer un hall d’exposition, j’ai acquis un œil exercé."


def test_corpus_learned_ocr_cleanup_examples() -> None:
    assert EnglishDialogueNormalizer.correct_ocr_text("CIRCUM- STANCES") == "circumstances"
    assert EnglishDialogueNormalizer.correct_ocr_text("Iwas in this wopld") == "I was in this world"
    assert EnglishDialogueNormalizer.correct_ocr_text("when I came t0") == "when I came to"


def test_corpus_learned_translation_overrides() -> None:
    prep = EnglishDialogueNormalizer.prepare("Did He Just SAY tch")
    assert prep.override_translation_fr == "Il vient de dire « tch » ?"
    prep = EnglishDialogueNormalizer.prepare("Huh? Why's he MAD At Me?")
    assert prep.override_translation_fr == "Hein ? Pourquoi il m’en veut ?"


def test_review_learned_sfx_and_missing_punctuation_patterns() -> None:
    hiyaa = EnglishDialogueNormalizer.prepare("Hi-yaaa-!")
    assert hiyaa.override_translation_fr == "Hi-yaaa-!"

    whoa = EnglishDialogueNormalizer.prepare("WHOAL")
    assert whoa.corrected_text == "whoa!"
    assert whoa.override_translation_fr == "Whoa !"

    tch = EnglishDialogueNormalizer.prepare('Did He Just SAY "tch"!?')
    assert tch.override_translation_fr == 'Est-ce qu\'il vient de dire : "tch" !?'


def test_review_learned_hyphenation_repairs_keep_intentional_cutoffs() -> None:
    repaired = EnglishDialogueNormalizer.prepare("HELP! IS ANY- ONE OUT THERE?!")
    assert repaired.corrected_text == "help! is anyone out there?!"

    cutoff = EnglishDialogueNormalizer.prepare("ASPHYXI- WHAT?")
    assert cutoff.corrected_text == "asphyxi- what?"


def test_review_learned_ocr_and_translation_patterns() -> None:
    things = EnglishDialogueNormalizer.prepare("What kind CF THINGS Did they DO To Yol?")
    assert things.normalized_text == "what kind of THINGS Did they DO To you?"
    assert things.override_translation_fr == "Qu’est-ce qu’ils t’ont fait ?"

    apologies = EnglishDialogueNormalizer.prepare("Apologies_ You ARE UNFAMILIAR With The Tepm?")
    assert apologies.corrected_text == "Apologies You ARE UNFAMILIAR With The term?"
    assert apologies.override_translation_fr == "Mes excuses. Tu ne connais pas ce terme ?"


def test_review_learned_obvious_computer_sentence() -> None:
    prepared = EnglishDialogueNormalizer.prepare("BMUSTHVB GALLENL ASLEEP inifront Computers")

    assert prepared.corrected_text == "I must've fallen asleep in front of my computer."
    assert prepared.normalized_text == "I must've fallen asleep in front of my computer."
    assert prepared.override_translation_fr == "J'ai dû m'endormir devant mon ordinateur."


def test_second_review_batch_learned_patterns() -> None:
    no_way = EnglishDialogueNormalizer.prepare("NO WAYI")
    assert no_way.corrected_text == "no way!"
    assert no_way.override_translation_fr == "Pas moyen !"

    saying = EnglishDialogueNormalizer.prepare("arb What saying? You")
    assert saying.normalized_text == "what are you saying?"
    assert saying.override_translation_fr == "Qu'est-ce que tu dis ?"

    run = EnglishDialogueNormalizer.prepare("MAKE A RUN FOR It,")
    assert run.normalized_text == "make a run for it, you two."
    assert run.override_translation_fr == "Échappez-vous, vous deux."

    thanks = EnglishDialogueNormalizer.prepare("There Apen't WORDS To EXPRESS HOW THANKFLL I AM For yolp Help.")
    assert thanks.corrected_text == "There aren't WORDS To EXPRESS HOW thankful I AM For your Help."

    understand = EnglishDialogueNormalizer.prepare("YOU'LL UNDER- STAND ONCE YOU DO!")
    assert understand.normalized_text == "you'll understand once you do!"
    assert understand.override_translation_fr == "Vous comprendrez quand vous le ferez !"


def test_third_review_batch_learned_patterns_and_sfx_edges() -> None:
    whisper = EnglishDialogueNormalizer.prepare("WHISPER WE ALWAYS TAKE YOU OUT ON OUR QUESTS, RIGHT? WHISPER")
    assert whisper.corrected_text == "we always take you out on our quests, right?"

    tune = EnglishDialogueNormalizer.prepare("Like The Tune.")
    assert tune.normalized_text == "I Like The Tune."
    assert tune.override_translation_fr == "J'aime bien cette mélodie."

    date = EnglishDialogueNormalizer.prepare("THIS IS OUR:. FIRST DATE AFTER")
    assert date.normalized_text == "this is our... first date after all..."
    assert date.override_translation_fr == "Après tout, c'est notre... premier rendez-vous..."


def test_fourth_review_batch_punctuation_numbers_and_hyphenation_patterns() -> None:
    system = EnglishDialogueNormalizer.prepare("The Drugs ARE Still IN YOUR System:")
    assert system.corrected_text == "The Drugs ARE Still IN YOUR System."

    yuki = EnglishDialogueNormalizer.prepare("LISTEN, Yuki:")
    assert yuki.normalized_text == "listen, Yuki..."
    assert yuki.override_translation_fr == "Écoute, Yuki..."

    why = EnglishDialogueNormalizer.prepare("SO Why,")
    assert why.normalized_text == "so why..."
    assert why.override_translation_fr == "Alors pourquoi..."

    yen = EnglishDialogueNormalizer.prepare("IF ONE ENER IS About one HLNDRED YEN:, .")
    assert yen.normalized_text == "if one ener is about one hundred yen..."
    assert yen.override_translation_fr == "Si un ener coûte environ cent yens..."

    hyphen = EnglishDialogueNormalizer.prepare("MAYBE SOME UN- CONTROLLED MONSTERS were LEFT BEHIND?")
    assert hyphen.normalized_text == "maybe some uncontrolled monsters were left behind?"

    particular = EnglishDialogueNormalizer.prepare("In PAR- Ticu- LAR:")
    assert particular.corrected_text == "In particular."


def test_fifth_review_batch_punctuation_digits_hyphenation_and_sfx_patterns() -> None:
    ceo = EnglishDialogueNormalizer.prepare("HE'S A Big-time Ceo_")
    assert ceo.corrected_text == "HE'S A Big-time CEO"

    dinner = EnglishDialogueNormalizer.prepare("A MEAL without MEAT ISN'T DINNERI")
    assert dinner.corrected_text == "A MEAL without MEAT ISN'T dinner!"
    assert dinner.override_translation_fr == "Un repas sans viande, ce n'est pas un vrai dîner !"

    assert EnglishDialogueNormalizer.prepare("AND:. =").corrected_text == "AND..."
    assert EnglishDialogueNormalizer.prepare("~But I Agree With The Other PARTS.").corrected_text == "...But I Agree With The Other PARTS."

    ms = EnglishDialogueNormalizer.prepare("I MUST SHOW MS: ELIZABETH, MS: KAREN, AND MS: UNDINE.")
    assert ms.corrected_text == "I must show ms. elizabeth, ms. karen, and ms. undine."

    quest = EnglishDialogueNormalizer.prepare("WE'LL ACCEPT THIS QUEST,, ,")
    assert quest.corrected_text == "we'll accept this quest..."

    manufacturer = EnglishDialogueNormalizer.prepare("The RECEPTION ANDPOID At Mei's MANU- FACTURER TOLD ME")
    assert manufacturer.normalized_text == "the reception android at Mei's manufacturer told me so."

    stubborn = EnglishDialogueNormalizer.prepare("WHAT Ape yo4 TALKING Abolt? THIS IS No TIME To Be ACTING STUBBORNI")
    assert stubborn.normalized_text == "what are you talking about? this is no time to be acting stubborn!"
    assert stubborn.override_translation_fr == "Mais de quoi tu parles ? Ce n'est pas le moment de faire l'entêté !"

    sfx = EnglishDialogueNormalizer.prepare("SLAP WE ALWAYS TAKE YOU OUT ON OUR QUESTS, RIGHT? WOBBLE")
    assert sfx.corrected_text == "we always take you out on our quests, right?"


def test_sixth_review_batch_expands_contractions_and_common_expressions() -> None:
    fate = EnglishDialogueNormalizer.prepare("'tis FATE At WORK.")
    assert fate.normalized_text == "it is FATE At WORK."
    assert fate.override_translation_fr == "C'est le destin qui est à l'oeuvre."

    counting = EnglishDialogueNormalizer.prepare("DO Some- thing! I'm Counting ON")
    assert counting.normalized_text == "do something! I am counting on you...!!"
    assert counting.override_translation_fr == "Fais quelque chose ! Je compte sur toi... !!"

    what = EnglishDialogueNormalizer.prepare("WHAT GOING")
    assert what.normalized_text == "what are you going to do?!"
    assert what.override_translation_fr == "Qu'est-ce que tu vas faire ?!"

    could = EnglishDialogueNormalizer.prepare("there'@ NO WAY Theo COULD Ve pulled It OFF!")
    assert could.normalized_text == "there is no way Theo could have pulled It OFF!"
    assert could.override_translation_fr == "Il n'y a aucune chance que Theo ait pu y arriver !"

    advise = EnglishDialogueNormalizer.prepare("...But i'd REALLY Advise AGAINST Writing Anything untrue.")
    assert "I would" in advise.normalized_text

    silly = EnglishDialogueNormalizer.prepare("Don't Be Silly. ARE You That kinda Pepson?")
    assert silly.normalized_text == "don't be silly. are you that kind of person?"
    assert silly.override_translation_fr == "Ne sois pas ridicule. Tu es ce genre de personne ?"

    assert EnglishDialogueNormalizer.prepare("ACK!!").override_translation_fr == "Argh !!"
