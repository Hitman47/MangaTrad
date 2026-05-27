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


def test_seventh_review_batch_ellipsis_zone_and_expression_patterns() -> None:
    sigma = EnglishDialogueNormalizer.prepare(": why isn't Sigma-kun Waking Up.")
    assert sigma.normalized_text == "...why isn't Sigma-kun waking up...?"

    coming = EnglishDialogueNormalizer.prepare("He's COMING. ISN'T He,.")
    assert coming.normalized_text == "he's coming... isn't he...?"
    assert coming.override_translation_fr == "Il arrive... n'est-ce pas...?"

    intro = EnglishDialogueNormalizer.prepare("Hi everyone We're going To Be working Together now, OKAY-?")
    assert intro.normalized_text == "hi everyone. we are going to be working together now, okay?"
    assert intro.override_translation_fr == "Salut tout le monde. On va travailler ensemble maintenant, d'accord ?"

    wait = EnglishDialogueNormalizer.prepare("WAIT A SEC, You guys")
    assert wait.normalized_text == "wait a sec, you guys know..."

    only = EnglishDialogueNormalizer.prepare("Only found Five.")
    assert only.normalized_text == "...but they only found five."
    assert only.override_translation_fr == "...mais ils n'en ont trouvé que cinq."

    withdraw = EnglishDialogueNormalizer.prepare("SHOLLD WE WITHORAW For Now?")
    assert withdraw.normalized_text == "should we withdraw for now?"
    assert withdraw.override_translation_fr == "Devrions-nous battre en retraite pour l'instant ?"


def test_fast_ten_batch_reviewed_ocr_and_expression_patterns() -> None:
    old_man = EnglishDialogueNormalizer.prepare("SHE'S G0T An IDIOT Like that FOR AM OLD MAN.")
    assert old_man.normalized_text == "she has got an idiot like that for an old man."
    assert old_man.override_translation_fr == "Elle a un idiot comme ça pour père."

    jumpy = EnglishDialogueNormalizer.prepare("ALL [ HAD TO DO Was BE LITTLE NICE HERE AND THERE And SHE GETS ALL Jumpy and comes CRAWLING OVER.")
    assert jumpy.override_translation_fr == "Il m'a suffi d'être un peu gentil de temps en temps pour qu'elle s'agite et vienne vers moi en rampant."

    complaints = EnglishDialogueNormalizer.prepare("So, I CALGHT The Rlnaway girl And got rid Of the bandis ANY COMP... LAINTS?")
    assert complaints.normalized_text == "So, I caught The runaway girl And got rid Of the bandits any complaints?"
    assert complaints.override_translation_fr == "Bon, j'ai attrapé la fugueuse et je me suis débarrassé des voyous. Ça vous pose un problème ?"

    assert EnglishDialogueNormalizer.prepare("NO! NOT Thepe.").corrected_text == "NO! NOT there."
    assert EnglishDialogueNormalizer.prepare("NO! NOT Thepe.").override_translation_fr == "NON ! PAS là."
    assert EnglishDialogueNormalizer.prepare("NO SWEAT.").override_translation_fr == "Pas de souci."
    assert EnglishDialogueNormalizer.prepare("Hey Hey Hey.").override_translation_fr == "Hey Hey Hey."
    assert EnglishDialogueNormalizer.prepare("I'm THE SOUTH-OASIS.").normalized_text == "in the south-oasis."
    ransom = EnglishDialogueNormalizer.prepare("WE'LL SQUEEZE ALL THE RANSOM MOMEY We can outta That old idiot And sell her to a SLAVE-TRADER I'm THE SOUTH-OASIS.")
    assert ransom.override_translation_fr == "On va soutirer tout l'argent de la rançon qu'on peut à cette vieille idiote, puis on la vendra à un marchand d'esclaves dans l'oasis du Sud."
    tamo = EnglishDialogueNormalizer.prepare("THATS TAMO-SAN'S Voice!")
    assert tamo.normalized_text == "Ah! that is tamo-san's voice!"
    assert tamo.override_translation_fr == "Ah ! C'est la voix de Tamo-san !"
    assert EnglishDialogueNormalizer.prepare("S0 MANY HERE ALREADY:. W!").corrected_text == "so many here already...!!"
    assert EnglishDialogueNormalizer.prepare("AAAND, It's GETTING WORSE:. .").corrected_text == "aaand, it's getting worse..."
    assert EnglishDialogueNormalizer.prepare("WANNA Gol?").normalized_text == "want to go!?"
    assert EnglishDialogueNormalizer.prepare("WANNA Gol?").override_translation_fr == "Tu veux y aller ?"


def test_replay_global_common_translation_overrides() -> None:
    assert EnglishDialogueNormalizer.prepare("yeah").override_translation_fr == "yeah"
    assert EnglishDialogueNormalizer.prepare("hmph,").override_translation_fr == "hmph"
    assert EnglishDialogueNormalizer.prepare("Allen.").override_translation_fr == "Allen"
    assert EnglishDialogueNormalizer.prepare("Right?").override_translation_fr == "N'est ce pas ?"
    assert EnglishDialogueNormalizer.prepare("Here I Gol").override_translation_fr == "C'est parti !"
    assert EnglishDialogueNormalizer.prepare("Let's hurryi").override_translation_fr == "Dépêchons-nous !"
    assert EnglishDialogueNormalizer.prepare("4nder... stood.").override_translation_fr == "Compris."
    assert EnglishDialogueNormalizer.prepare("Just LEAVE It Be").override_translation_fr == "Laisse tomber"
    assert EnglishDialogueNormalizer.prepare("Like, COME ON.").override_translation_fr == "Mais enfin..."
    assert EnglishDialogueNormalizer.prepare("BY No MEANS MAY You Faill!").override_translation_fr == "Tu ne dois en aucun cas échouer !!"
    assert EnglishDialogueNormalizer.prepare("a fortune teller,").override_translation_fr == "Une voyante..."
    assert EnglishDialogueNormalizer.prepare("Where Will it END?").override_translation_fr == "... Où cela va-t-il s'arrêter ?"
    assert EnglishDialogueNormalizer.prepare("Once full Circler").override_translation_fr == "Une fois que la boucle est bouclée…"
    assert EnglishDialogueNormalizer.prepare("and that is a wrap!").override_translation_fr == "Et voilà, c'est dans la boîte !"
    assert EnglishDialogueNormalizer.prepare("Whats that sound").override_translation_fr == "C'est quoi ce bruit ?"
    assert EnglishDialogueNormalizer.prepare("Kow About it?").override_translation_fr == "Qu'en penses-tu ?"
    assert EnglishDialogueNormalizer.prepare("Is it trying to flee?").override_translation_fr == "Est-ce qu'il essaie de s'enfuir ?"


def test_replay_learned_intraword_ellipsis_and_short_fragment_normalization() -> None:
    assert EnglishDialogueNormalizer.prepare("Are you ser... ious?").normalized_text == "Are you serious?"
    assert EnglishDialogueNormalizer.prepare("so some... one roofied and kid... napped us?").normalized_text == "so someone roofied and kidnapped us?"
    assert EnglishDialogueNormalizer.prepare("In PAR... Ticu... LAR.").corrected_text == "In particular."
    assert EnglishDialogueNormalizer.prepare("Why Did I").normalized_text == "Why Did I...?"
    assert EnglishDialogueNormalizer.prepare("this IS MY FAULT").normalized_text == "this IS MY FAULT...?"
    assert EnglishDialogueNormalizer.prepare("they aren't making").normalized_text == "they aren't making a move..."
    assert EnglishDialogueNormalizer.prepare("fine,").normalized_text == "fine..."
    assert EnglishDialogueNormalizer.prepare("then").normalized_text == "then?"


def test_zone_fix_batch_preserves_then_question_with_hyphenated_target() -> None:
    prepared = EnglishDialogueNormalizer.prepare("then? THERE ARE EASIER TAR- GETS.")

    assert prepared.corrected_text == "then? there are easier targets."
    assert prepared.normalized_text == "then? there are easier targets."


def test_hard_english_batch_repairs_i_bang_hyphen_and_missing_ellipsis() -> None:
    assert EnglishDialogueNormalizer.prepare("As a warrior follow my desiresl!").corrected_text == "As a warrior follow my desires!!"
    assert EnglishDialogueNormalizer.prepare("For stronger oppon- ents").corrected_text == "For stronger opponents..."
    assert EnglishDialogueNormalizer.prepare("For more intense battles").corrected_text == "For more intense battles..."
    assert EnglishDialogueNormalizer.prepare("The captain and Vayne").corrected_text == "The captain... and Vayne"
    assert EnglishDialogueNormalizer.prepare("He 'return- ed the dam age?!").corrected_text == "He returned the damage?!"
    assert EnglishDialogueNormalizer.prepare("He 'returned the damage?!").corrected_text == "He returned the damage?!"
    assert EnglishDialogueNormalizer.prepare("Bal ancell").corrected_text == "Balance!!"
    assert EnglishDialogueNormalizer.prepare("Obviously, sensed the danger, and so returned the damagel").corrected_text == "Obviously, I sensed the danger, and so returned the damage!"
    assert EnglishDialogueNormalizer.prepare("C'mere AND Enter- TAIN Me Somel").corrected_text == "C'mere AND EnterTAIN Me some!"


def test_manga_font_ul_i_bang_confusion_profile_in_normalizer() -> None:
    assert EnglishDialogueNormalizer.prepare("ISN'T Lrabe COMING TODAY?").corrected_text == "isn't Urabe coming today?"
    assert EnglishDialogueNormalizer.prepare("Now that You MEN... TIONED THE Previous Prez").corrected_text == "Now that You MENTIONED THE Previous Prez"
    assert EnglishDialogueNormalizer.prepare("01, cut it Out al... Read!!").corrected_text == "Oi, cut it Out already!!"
    assert EnglishDialogueNormalizer.prepare("Hehl I can feel The pressure From her magic! THAT'S A GREAT SAGE FOR Youl").corrected_text == "Heh! I can feel The pressure From her magic! THAT'S A GREAT SAGE FOR You!"
    assert EnglishDialogueNormalizer.prepare("She was TRYING TO PROTECT Everyone Becalse the STAFF Went O4t OF CONTROL!").corrected_text == "She was TRYING TO PROTECT Everyone Because the STAFF Went Out OF CONTROL!"
    assert EnglishDialogueNormalizer.prepare("WHAT 9i").corrected_text == "what?!"
    assert EnglishDialogueNormalizer.prepare("YOU telling Me TO TURN A BLIND Eye? l").normalized_text == "You seriously telling me to turn a blind eye?!"
    assert EnglishDialogueNormalizer.prepare("Should BE ONLY MATTER OF TIME Before all BETA ARE ELIMINATED.").normalized_text == "it should only be a matter of time before all beta are eliminated."


def test_well_is_not_expanded_as_we_will() -> None:
    prepared = EnglishDialogueNormalizer.prepare("Well, ACTUALLY, THAT'S WHAT HAPPENED.")

    assert prepared.normalized_text == "well, actually, that is what happened."


def test_latest_replay_misses_get_deterministic_overrides() -> None:
    assert EnglishDialogueNormalizer.prepare("They're ALL So").override_translation_fr == "Ils sont tous si... jeunes..."
    assert EnglishDialogueNormalizer.prepare("FujiMLRA,").override_translation_fr == "...Fujimura..."
    assert EnglishDialogueNormalizer.prepare("is that s?").override_translation_fr == "Vraiment ?"
    assert EnglishDialogueNormalizer.prepare("be great if").override_translation_fr == "Ce serait super si"
    assert (
        EnglishDialogueNormalizer.prepare("NOW I GOTTA Get Out Before Sensei CATCHES me...").override_translation_fr
        == "Il faut que je me tire avant que Sensei ne me surprenne..."
    )


def test_finish_english_validation_ocr_repairs_in_normalizer() -> None:
    assert (
        EnglishDialogueNormalizer.prepare("The ONLY WAY To BREAK YOUR INVINC! Bility Force You To Let G0 OF this SWORD").corrected_text
        == "The only way to break your invincibility is to force you to let go of this sword."
    )
    assert EnglishDialogueNormalizer.prepare("I'e Broken ITI").corrected_text == "I've broken it!"
    assert EnglishDialogueNormalizer.prepare("GRAB MY LAPEL AND GOFOR A Ghoulder").corrected_text == "grab my lapel and go for a shoulder"
    assert EnglishDialogueNormalizer.prepare("GRAB MY LAPEL AND GOFOR A Ghoulder").override_translation_fr == "Attrape mon revers et vise l'epaule."
    assert EnglishDialogueNormalizer.prepare("Hundred THOUSAND People Will Diel").corrected_text == "Hundred THOUSAND People Will die!"
    gozen = EnglishDialogueNormalizer.prepare("He Took AME-NO- Gozen FROM Me!")
    assert gozen.corrected_text == "He Took Ame-no-Gozen FROM Me!"
    assert gozen.override_translation_fr == "Il m'a pris Ame-no-Gozen !"


def test_busy_validation_dialogue_overrides() -> None:
    assert EnglishDialogueNormalizer.prepare("Hum.").override_translation_fr == "Hum."
    assert (
        EnglishDialogueNormalizer.prepare("We Just Need Someone To TAKE The Picture").override_translation_fr
        == "Il nous faut juste quelqu'un pour prendre la photo."
    )
    assert (
        EnglishDialogueNormalizer.prepare("ALRIGHT Get CLOSER To EACH Other~").override_translation_fr
        == "Allez, rapprochez-vous l'un de l'autre."
    )
    assert EnglishDialogueNormalizer.prepare("KARIU YOUR FACE Is SCARY").override_translation_fr == "Kariu, ton visage fait peur."
    assert EnglishDialogueNormalizer.prepare("S0 PEAL COLDW!").corrected_text == "so real cold!!!"
    assert EnglishDialogueNormalizer.prepare("It's really Trlelll").corrected_text == "It's really true!!!"
    provost = EnglishDialogueNormalizer.prepare("Th-the Provosti? Did She Foresee all OF this:: .?")
    assert provost.corrected_text == "Th-the Provost? Did She Foresee all OF this...?"
    assert provost.override_translation_fr == "La Provost ?! Elle avait prevu tout ca... ?"
    ichinose = EnglishDialogueNormalizer.prepare("Well This girl Ichinose Got Me A COMMERCIAL DRIVER'S License")
    assert ichinose.override_translation_fr == "Eh bien, cette fille, Ichinose, m'a obtenu un permis de conduire professionnel."
    transit = EnglishDialogueNormalizer.prepare('MEANS I\'m Like YOUR "Plblic TRANSIT" For the DAY.')
    assert transit.corrected_text == 'MEANS I\'m Like YOUR "public TRANSIT" For the DAY.'
    assert transit.override_translation_fr == 'En gros, je suis ton "transport public" pour la journee.'
    peek = EnglishDialogueNormalizer.prepare("You REALLY CAME Peek.")
    assert peek.corrected_text == "You REALLY came to peek...?"
    assert peek.override_translation_fr == "Tu es vraiment venue jeter un oeil... ?"
    misunderstanding = EnglishDialogueNormalizer.prepare("IT'S A MISUN- DER- STAND- INGU JUST Now... SOMEONE was")
    assert misunderstanding.override_translation_fr == "C'est un malentendu !! A l'instant... quelqu'un etait..."
    assert EnglishDialogueNormalizer.prepare("LNBEL!").override_translation_fr == "Incroyable !"
    person = EnglishDialogueNormalizer.prepare("WHAT ON IS THIS PERSON?!")
    assert person.corrected_text == "what on earth is this person?!"
    assert person.override_translation_fr == "C'est quoi, cette personne ?!"
