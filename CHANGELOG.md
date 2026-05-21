# Changelog

## 0.5.0

- Refonte du reviewer humain en vrai poste de travail de correction.
- Champs organisés par paires : texte de référence à gauche, champ à corriger à droite.
- Actions explicites : valider, mode correction, enregistrer correction, SFX, ignorer, à revoir.
- Ajout d’un état modifications non sauvegardées et confirmation avant changement de bloc.
- Résumé de file de review : total, HIGH, MED, validés, ignorés, à revoir.
- Conservation explicite de la décision SFX dans les notes (`[sfx]`).

## 0.4.9

- Correction du comportement du bouton `Corriger (C)` dans `review_app` : il passe maintenant en mode édition sans enregistrer silencieusement ni avancer.
- `Sauver + suivant` applique explicitement la décision sélectionnée et les champs corrigés.
- `Ctrl+S` applique maintenant les champs du bloc courant avant de sauvegarder le projet reviewed.
- Ajout d’un message visible indiquant le mode correction et le prochain geste attendu.
- Navigation après sauvegarde rendue plus prévisible après refresh de la liste filtrée.

## 0.4.8

- Refonte de `review_app` pour rendre l’interface réellement lisible.
- Ajout de panneaux nommés pour chaque zone de texte : OCR brut, OCR corrigé, source actuelle, source corrigée, traduction actuelle, traduction FR corrigée, QC/alternatives, notes.
- Ajout d’un mode d’emploi visible dans l’application, d’explications de décision et de tooltips.
- Le contexte de bloc affiche maintenant clairement page, bloc, statut, confiance OCR, bbox, image et chemin de sauvegarde.

## 0.4.7

- Ajout d’une application séparée `review_app` pour la correction humaine.
- La review se fait par bloc avec image de page, bbox surlignée, champs OCR/source/traduction et boutons rapides.
- Sauvegarde dans un `*.reviewed.json` par défaut pour ne pas écraser le projet original.
- Ajout de notes reviewer persistées dans les blocs.
- Ajout de la documentation `docs/review_app.md`.

## 0.4.6

- Le pack de correction humaine génère maintenant un XLSX recommandé, plus lisible que le TSV.
- Colonnes réordonnées : les champs à remplir sont placés juste à côté des colonnes à analyser.
- Ajout d’une liste déroulante pour `review_decision`.
- Ajout de filtres, gel de ligne d’en-tête, couleurs, largeurs de colonnes et onglet d’instructions.
- `corpus_apply_review` accepte maintenant directement le `.xlsx`, en plus du TSV/CSV de compatibilité.

## 0.4.5

- Le pack de correction humaine est maintenant exporté en TSV UTF-8 (`mangatrad_human_review_pack.tsv`) avec séparateur tabulation.
- Les virgules dans les titres, séries, OCR et traductions ne cassent plus les colonnes lors de la correction humaine.
- `corpus_apply_review` lit désormais le TSV recommandé et reste compatible avec les anciens CSV.
- Mise à jour du guide de correction humaine.

## 0.4.4

- Ajout d’un workflow de correction humaine : génération d’un CSV de review équilibré par série.
- Ajout de `corpus_review_pack` pour produire un pack de 100–200 blocs à corriger.
- Ajout de `corpus_apply_review` pour réinjecter les corrections dans le cache projet.
- Ajout de la documentation `docs/human_review_workflow.md`.

## 0.4.3

- Ajout d’un apprentissage léger depuis les exports d’analyse (`corpus_learn`).
- Génération d’un profil JSON, d’un rapport Markdown, de candidats glossaire et de mots résiduels anglais.
- Renforcement du quality check à partir du corpus réel : résidus source/traduction, OCR confusions fréquentes, césures, chiffres confondus avec lettres.
- Renforcement de la normalisation EN/OCR pour les erreurs observées dans le corpus.

## 0.4.2

- Ajout de `corpus_inspect` pour diagnostiquer les dossiers corpus vides, déplacés ou mal ciblés.
- `corpus_process` affiche maintenant un diagnostic complet quand aucun manifest/image n’est trouvé : contenu du dossier, nombre d’images et candidats proches.
- `corpus_process` accepte aussi un chemin direct vers `manifest.jsonl` ou `manifest.csv`.

## 0.4.1

- `corpus_process` accepte maintenant un corpus sans manifest si le dossier `pages/` contient déjà des images extraites.
- Recherche automatique d’un manifest imbriqué quand un seul `manifest.jsonl` ou `manifest.csv` est trouvé sous le dossier fourni.
- Message d’erreur plus utile si ni manifest ni images ne sont présents.
- Objectif : éviter de bloquer le traitement après copie/déplacement partiel du corpus.

## 0.4.0

- `corpus_process --limit` sélectionne maintenant les pages en mode stratifié par défaut au lieu de prendre les premières pages du manifest.
- Ajout de `--limit-mode stratified|random|first` et `--seed` pour comparer rapidement plusieurs séries.
- Export d'analyse enrichi avec `series_label` et `volume_label` dans le CSV/JSONL.
- Rapport qualité enrichi : raisons de risque les plus fréquentes et distribution par série.
- QC renforcé contre les faux positifs `probably_ok` : résidus anglais, mots en MAJUSCULES, patterns OCR connus, césures OCR.
- Nettoyage OCR renforcé : césures de ligne, `FOLR -> four`, `Enolgh -> enough`, `Fopm -> form`, `Colld -> could`, etc.

## 0.3.9

- Ajout du batch `corpus_process` pour lancer OCR + traduction locale sur le corpus extrait.
- Export automatique des rapports d’analyse après traitement du corpus.
- Ajout de checkpoints/reprise pour traiter plusieurs centaines de pages sans tout perdre après crash.
- Options conservatrices par défaut : fallback OCR lourd désactivé, crop refinement désactivé.

## 0.3.8

- `corpus_sample` accepte maintenant des dossiers de séries en plus des fichiers CBZ/ZIP.
- Ajout de `--volumes-per-series` pour sélectionner quelques tomes par série.
- Ajout de `--series-mode` (`mixed`, `first`, `last`, `random`) pour contrôler le choix des tomes.
- Ajout de `--recursive` pour traiter un dossier parent contenant plusieurs sous-dossiers de séries.
- Le manifest exporte maintenant les métadonnées de série : `series_path`, `series_label`, `series_volume_number`, `series_volume_count`.
- Clarification : `--require-distinct-parent` est un mode strict hérité à ne pas utiliser quand on veut plusieurs tomes par série.

## 0.3.7

- Ajout d’un script d’échantillonnage de corpus depuis une liste de tomes CBZ/ZIP.
- Extraction configurable de 20–30 pages par tome avec modes `mixed`, `stratified` ou `random`.
- Génération de `manifest.csv`, `manifest.jsonl` et `sample_report.md`.
- Validation optionnelle pour refuser plusieurs tomes issus du même dossier.

## 0.3.6

- Ajout d'un export analyse CSV/JSONL pour comparer OCR/traductions sur plusieurs pages.
- Ajout d'un rapport qualité Markdown et d'un score local de risque par bloc.
- Ajout d'un rapport d'apprentissage léger : mémoire de traductions validées, corrections OCR et suggestions glossaire.
- Ajout d'une commande CLI `python -m cbz_manga_translator.analysis_export`.

## 0.3.5

- Ajout de logs applicatifs et de crash natif : `logs/mangatrad.log` et `logs/mangatrad_fatal.log`.
- Les erreurs de tâches GUI incluent maintenant traceback et chemin des logs.
- Ajout d'un diagnostic/assistant OCR : `python -m cbz_manga_translator.ocr_setup --check` et `--commands`.
- Documentation claire pour installer Tesseract/PaddleOCR localement.
- Le bouton `Relire OCR tous` demande confirmation avant une relance lourde.

## 0.3.4

- Renforcement OCR local : plus de variantes de crop, padding blanc, upscale x4, netteté, médiane et seuils multiples.
- Le fallback EasyOCR teste maintenant aussi le mode paragraphe sur les crops.
- Ajout d’un nettoyage OCR pré-traduction : ponctuation, faux semicolons, double ponctuation et casing aléatoire EasyOCR.
- Scoring OCR amélioré avec pénalités pour casing aléatoire, fragments isolés et tokens OCR suspects.
- Ajout du bouton `Relire OCR tous` pour forcer une relance locale sur tous les blocs de la page.

## 0.3.3

- Ajout d’un bootstrap Argos depuis l’index officiel Argos : `--bootstrap-basic` et `--install-index en:fr ja:en`.
- Le diagnostic local vérifie maintenant les paires Argos nécessaires pour EN→FR et JP→FR via pivot.
- Ajout de règles locales supplémentaires pour certains dialogues courts où Argos/MT est trop faible.
- Le quality check signale les fragments OCR isolés comme `Did:` pour pousser à fusionner/corriger les blocs.

## 0.3.2

- Refonte lisibilité UI : retrait du glossaire du haut de fenêtre, passage à un panneau droit à onglets.
- Ajout d’un onglet dédié `Détail / correction` avec zone défilable et champs empilés verticalement.
- Ajout d’onglets `Glossaire` et `Local` pour éviter de compresser la page manga et les blocs OCR.
- Style Qt renforcé : onglets visibles, scrollbars plus lisibles, champs plus hauts, table plus confortable.

## 0.3.1

- Correction de la liste des paires Argos installées.

## 0.3.0

- Suppression de la dépendance de traduction Hugging Face / Transformers / Helsinki-NLP.
- Ajout d’un backend Argos Translate local basé sur des packages `.argosmodel` installés localement.
- Ajout de `python -m cbz_manga_translator.argos_models` pour installer/lister les packages Argos locaux.
- Le serveur local HTTP utilise maintenant Argos.
- La traduction JP→FR tente `ja->fr`, puis le pivot `ja->en->fr` si disponible.
- Mise à jour de l’interface et de la documentation pour clarifier que la traduction ne passe plus par Hugging Face.

## 0.2.1

- Amélioration de la lisibilité de l’interface.
- Ajout du bouton `Vérifier local`.
- Ajout de corrections déterministes pour plusieurs phrases courtes mal traduites.

## 0.2.0

- Ajout de filtres de blocs, recherche et statistiques projet/page.
- Extraction du thème GUI.
- Stabilisation de l’interface de correction.

## 0.1.9

- Ajout d’une correction structurelle OCR : alternative OCR, fusion de blocs, séparation de bloc, déplacement de l’ordre de lecture.

## 0.1.8

- Ajout du fallback OCR local.
- Ajout d’alternatives OCR par bloc dans le cache JSON.

## 0.1.7

- Ajout d’overrides locaux pour les interjections et expressions simples.
- Meilleure normalisation des dialogues anglais oralisés.

## 0.1.6

- Ajout d’un serveur local HTTP.
- Refonte de l’interface : liste compacte + panneau détail.
- Ajout d’un glossaire projet persistant.

## 0.1.5

- Ajout d’une boucle de correction humaine : statuts `brut`, `corrigé`, `validé`, `à revoir`, `ignoré`.

## 0.1.4

- Ajout du diagnostic visible : OCR brut, OCR corrigé, texte normalisé, traduction brute, traduction finale.
- Ajout de l’OCR multi-variantes sur les crops.

## 0.1.0

- Prototype initial : lecture CBZ, affichage page, OCR local, traduction locale, cache JSON, export HTML.
