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
    assert ignore.normalized_text == "I'll just ignore him:"
    assert ignore.override_translation_fr == 'Je vais simplement l’ignorer.'

    expected = EnglishDialogueNormalizer.prepare("I NEVER Expected I'D HAVE:")
    assert expected.normalized_text == "I never expected I'd have:"
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
