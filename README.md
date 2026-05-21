# MangaTrad

Version actuelle : `0.5.0`.

Prototype gratuit/local pour charger un CBZ de manga, faire de l’OCR local, traduire EN→FR ou JP→FR avec **Argos Translate** et corriger les blocs dans une interface PySide6. Le but final reste l’édition des bulles dans l’image puis l’export d’un CBZ traduit.

## Décision importante : plus de Hugging Face

Depuis `0.3.0`, la traduction ne passe plus par Hugging Face, Transformers, Helsinki-NLP, SentencePiece ou Sacremoses.

La traduction utilise maintenant :

```text
Argos Translate + packages locaux .argosmodel
```

Conséquence : tu dois installer localement les modèles Argos nécessaires :

```text
en -> fr
ja -> fr direct si disponible
ou ja -> en + en -> fr pour traduction pivot
```

Argos Translate est une bibliothèque de traduction offline Python. Ses modèles sont des archives `.argosmodel` installées localement.

## État du projet

Le projet sait déjà faire :

- ouvrir un `.cbz` ou `.zip` contenant des images ;
- afficher les pages dans une GUI PySide6 ;
- lancer EasyOCR localement, CPU ou CUDA si PyTorch GPU est installé ;
- relire les blocs OCR suspects ou tous les blocs avec des variantes de crop renforcées et des moteurs optionnels ;
- traduire avec Argos local intégré ou via serveur local HTTP ;
- préserver `bbox`, ordre de lecture, statut manuel, warnings QC et alternatives OCR dans le cache JSON ;
- éditer OCR brut, OCR corrigé, texte normalisé et traduction finale ;
- fusionner/séparer des blocs, corriger l’ordre de lecture et valider/ignorer des blocs ;
- exporter une lecture HTML avec image à gauche et traduction à droite.

Ce qu’il ne fait pas encore correctement :

- remplacement propre du texte dans les bulles ;
- inpainting/nettoyage du texte original ;
- export CBZ traduit ;
- détection robuste de toutes les bulles et textes stylisés ;
- traduction fiable de dialogues manga sans correction humaine.

## Installation Windows

Depuis PowerShell, dans le dossier du projet :

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -e .
```

Lancer la GUI :

```powershell
python -m cbz_manga_translator.main
```

Vérifier la version :

```powershell
python -m cbz_manga_translator.main --version
```

## Installation CUDA pour OCR

EasyOCR utilise PyTorch. Pour une RTX/NVIDIA :

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip uninstall -y torch torchvision torchaudio
python -m pip cache purge
python -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128
python -c "import torch; print('torch:', torch.__version__); print('cuda:', torch.cuda.is_available()); print('gpu:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU only')"
```

Ne relance pas `pip install -r requirements.txt` après une installation CUDA fonctionnelle.

## Installer les modèles Argos localement

Méthode recommandée : laisse l’outil télécharger les packages depuis l’index officiel Argos, sans Hugging Face :

```powershell
.\.venv\Scripts\Activate.ps1
python -m cbz_manga_translator.argos_models --bootstrap-basic
python -m cbz_manga_translator.argos_models --list
```

Tu peux aussi demander explicitement des paires :

```powershell
python -m cbz_manga_translator.argos_models --install-index en:fr ja:en
```

Ou installer des fichiers `.argosmodel` déjà téléchargés :

```powershell
python -m cbz_manga_translator.argos_models --install C:\models\translate-en_fr.argosmodel C:\models\translate-ja_en.argosmodel
```

Pour EN→FR, il faut `en -> fr`.

Pour JP→FR, l’application essaie :

```text
ja -> fr
```

puis, si le direct n’est pas installé :

```text
ja -> en -> fr
```

Donc si aucun modèle direct JP→FR n’est disponible, installe au minimum `ja -> en` et `en -> fr`.

## Vérifier les modèles Argos installés

Après installation des packages Argos, vérifier les paires disponibles :

```powershell
python -m cbz_manga_translator.argos_models --list
```

La commande affiche aussi si MangaTrad peut traduire EN→FR et JP→FR. Le direct `ja->fr` peut être absent de l’index Argos ; dans ce cas `ja->en + en->fr` suffit.

Tester rapidement une traduction locale :

```powershell
python -m cbz_manga_translator.argos_models --test en "hello"
python -m cbz_manga_translator.argos_models --test ja "こんにちは"
```

## Serveur local Argos optionnel

Terminal 1 :

```powershell
.\.venv\Scripts\Activate.ps1
python -m cbz_manga_translator.server --host 127.0.0.1 --port 8765 --gpu --preload en ja
```

Terminal 2 :

```powershell
.\.venv\Scripts\Activate.ps1
python -m cbz_manga_translator.main
```

Dans l’interface :

```text
Modèle local : Serveur local HTTP
URL : http://127.0.0.1:8765
Tester serveur
```

Si le serveur n’est pas lancé, choisis plutôt le mode intégré.

## Options OCR importantes

- `Fusionner lignes` : regroupe les fragments proches pour éviter les traductions mot à mot.
- `Filtrer bruit` : ignore artefacts, symboles et fragments sous le seuil de confiance.
- `OCR multi-variantes` : relit les crops avec marge, upscale, contraste et seuillage.
- `Fallback OCR local` : relit les blocs suspects avec corrections locales, EasyOCR crop variants, Tesseract si installé et PaddleOCR si installé.
- `Relire OCR suspects` : applique le fallback sur les blocs marqués par le quality check ou par une confiance faible.
- `Relire OCR tous` : applique le fallback sur tous les blocs de la page. Plus lent, mais utile quand toute une page est mal lue.

Les moteurs optionnels sont installables via :

```powershell
pip install -r requirements-ocr-extra.txt
```

## Options traduction importantes

- `Normaliser EN familier` : transforme `WHAT YA DOIN'`, `AIN'T AH TOID YA`, `CLIMBIN'`, `GRAMMA`, `LOOKY`, `Inhook`, etc. avant traduction.
- `Dico manga intégré` : protège des noms, lieux, repas et termes déjà courants en français.
- `Glossaire projet` : règles propres à un CBZ/série, sauvegardées dans le cache JSON.

Exemple de glossaire :

```text
Naru
NARL=Naru
NARLI=Naru
Miwa-nee
contrail=traînée de condensation
```


## Correction humaine : XLSX recommandé

Le pack de correction humain génère maintenant un classeur `.xlsx` lisible :

```text
mangatrad_human_review_pack.xlsx
```

Il contient des filtres, une ligne d'en-tête figée, une liste déroulante pour `review_decision`, et les colonnes à remplir sont placées juste à côté des colonnes à analyser. Un `.tsv` est encore généré comme fallback, et les anciens `.csv` restent acceptés à l'import.

## Workflow conseillé

```text
1. Ouvrir le CBZ.
2. Lancer OCR local page ou OCR + trad locale.
3. Relire OCR suspects.
4. Choisir une alternative OCR si elle est meilleure.
5. Fusionner/séparer les blocs si la structure est mauvaise.
6. Corriger OCR corrigé ou texte normalisé.
7. Retraduire sélection.
8. Corriger la traduction finale.
9. Valider ou marquer à revoir.
10. Exporter HTML pour lecture.
```


## Logs et diagnostic OCR

L'application écrit maintenant deux fichiers de logs dans le dossier courant :

```text
logs/mangatrad.log
logs/mangatrad_fatal.log
```

`mangatrad.log` contient les tâches lancées, erreurs Python et tracebacks. `mangatrad_fatal.log` est réservé aux crashs natifs possibles de bibliothèques OCR/ML.

Pour afficher les commandes d'installation des OCR optionnels :

```powershell
python -m cbz_manga_translator.ocr_setup --commands
```

Pour vérifier ce que MangaTrad voit réellement :

```powershell
python -m cbz_manga_translator.ocr_setup --check
```

Voir `docs/ocr_backends_install.md`.

## Export analyse

Le bouton `Exporter analyse` produit un corpus local pour comparer plusieurs dizaines de pages :

```text
mangatrad_review_blocks.csv
mangatrad_review_blocks.jsonl
mangatrad_quality_report.md
mangatrad_learning_report.json
mangatrad_glossary_suggestions.txt
```

Commande équivalente :

```powershell
python -m cbz_manga_translator.analysis_export --project C:\chemin\manga.cbz.manga_translate_project.json --out C:\temp\mangatrad_analysis
```

Le mécanisme d’apprentissage reste léger et local : il extrait une mémoire de traductions/corrections depuis les blocs corrigés ou validés, sans fine-tuning et sans service externe.

Détails : `docs/analysis_export.md`.

## Échantillonnage corpus

Pour construire une base représentative, crée un `volumes.txt` avec une ligne par dossier de série ou par CBZ/ZIP :

```text
D:\Mangas\Serie A
D:\Mangas\Serie B
```

Puis :

```powershell
python -m cbz_manga_translator.corpus_sample `
  --input C:\temp\volumes.txt `
  --out C:\temp\mangatrad_corpus `
  --volumes-per-series 2 `
  --pages-per-volume 25 `
  --series-mode mixed `
  --mode mixed `
  --seed 47 `
  --overwrite
```

Si les lignes pointent vers des dossiers parents contenant des sous-dossiers de séries, ajoute `--recursive`. N'utilise pas `--require-distinct-parent` si tu veux plusieurs tomes par série.

Détails : `docs/corpus_sampling.md`.

## Tests

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
pip install -e .
pytest -q
python -m compileall -q src tests
python -m cbz_manga_translator.main --version
python -m cbz_manga_translator.server --help
python -m cbz_manga_translator.argos_models --list
```

## Docker

Docker n’est pas le mode recommandé pour la GUI PySide6. Le projet reste d’abord une application Python native.

Docker sert seulement à :

- tester dans un environnement propre ;
- préparer un futur serveur local OCR/traduction isolé ;
- reproduire des validations CI.

## Traiter un corpus extrait

Après `corpus_sample`, lancer OCR + traduction locale sur les pages extraites :

```powershell
python -m cbz_manga_translator.corpus_process `
  --corpus C:\temp\mangatrad_corpus `
  --out C:\temp\mangatrad_corpus_run `
  --source-lang en `
  --limit 30
```

Pour un traitement complet, retirer `--limit`. Les options lourdes sont volontairement désactivées par défaut. Ajouter seulement après test :

```powershell
--fallback suspects --include-optional-ocr
```

Les sorties principales sont `mangatrad_review_blocks.csv`, `mangatrad_review_blocks.jsonl`, `mangatrad_quality_report.md` et `mangatrad_learning_report.json`.


## Corpus sans manifest

Depuis `0.4.3`, `corpus_process` peut reconstruire un manifest minimal quand le dossier fourni contient déjà des images sous `pages/` mais plus de `manifest.jsonl`/`manifest.csv`. Le manifest original reste préférable.

## Apprentissage léger depuis corpus

Après `corpus_process`, génère un profil local exploitable :

```powershell
python -m cbz_manga_translator.corpus_learn `
  --analysis C:\temp\mangatrad_corpus_run_30_stratified\analysis `
  --out C:\temp\mangatrad_learned_profile
```

Sorties :

- `mangatrad_learned_profile.json` : profil structuré ;
- `mangatrad_learned_report.md` : résumé lisible ;
- `mangatrad_project_glossary_seed.txt` : candidats glossaire ;
- `mangatrad_qc_residue_words.txt` : mots source résiduels à surveiller.

Ce n’est pas un fine-tuning lourd : c’est un apprentissage local transparent pour améliorer progressivement OCR, QC et règles de traduction.
## Correction humaine et apprentissage

Après un traitement corpus, génère un pack de correction humain :

```powershell
python -m cbz_manga_translator.corpus_review_pack `
  --analysis C:\temp\mangatrad_corpus_run_30_stratified_v043\analysis `
  --out C:\temp\mangatrad_human_review_pack `
  --max-blocks 200
```

Ouvre `mangatrad_human_review_pack.xlsx`, remplis les colonnes jaunes (`review_decision`, `corrected_ocr`, `corrected_source`, `corrected_fr`, `review_notes`), puis réinjecte :

```powershell
python -m cbz_manga_translator.corpus_apply_review `
  --project C:\temp\mangatrad_corpus_run_30_stratified_v043\mangatrad_corpus_project.json `
  --review C:\temp\mangatrad_human_review_pack\mangatrad_human_review_pack.xlsx `
  --out-project C:\temp\mangatrad_corpus_run_30_stratified_v043\mangatrad_corpus_project.reviewed.json
```

Voir `docs/human_review_workflow.md`.



## Review GUI

Pour corriger des lots de blocs plus confortablement qu’avec un TSV/XLSX :

```powershell
python -m cbz_manga_translator.review_app C:\temp\mangatrad_corpus_run_30_stratified_v043\mangatrad_corpus_project.json
```

L’outil affiche la page, la bbox du bloc, les champs OCR/source/traduction, et sauvegarde par défaut dans un `*.reviewed.json`. Voir `docs/review_app.md`.


## MangaTrad Reviewer

Application séparée pour corriger les résultats du corpus avec image, bbox, OCR, traduction, warnings et notes :

```powershell
python -m cbz_manga_translator.review_app C:\temp\mangatrad_corpus_run_30_stratified_v043\mangatrad_corpus_project.json
```

Voir `docs/review_app.md`.

## Reviewer humain recommandé

Pour corriger un corpus, utilise maintenant le reviewer dédié :

```powershell
python -m cbz_manga_translator.review_app C:\temp\mangatrad_corpus_run_30_stratified_v043\mangatrad_corpus_project.json
```

La V0.5.0 organise l'écran comme un poste de correction : file de blocs à gauche, image au centre, correction à droite. Les champs sont par paires : le texte à analyser est à gauche, le champ à corriger est à droite. Les modifications non sauvegardées déclenchent une confirmation avant de changer de bloc.

