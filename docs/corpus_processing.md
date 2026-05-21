# Traitement du corpus

`corpus_sample` extrait des pages représentatives. `corpus_process` lance ensuite OCR + traduction locale sur ces pages et produit les fichiers d’analyse.

## Test recommandé

Toujours commencer petit :

```powershell
python -m cbz_manga_translator.corpus_process `
  --corpus C:\temp\mangatrad_corpus `
  --out C:\temp\mangatrad_corpus_run `
  --source-lang en `
  --limit 30
```

## Traitement complet

```powershell
python -m cbz_manga_translator.corpus_process `
  --corpus C:\temp\mangatrad_corpus `
  --out C:\temp\mangatrad_corpus_run `
  --source-lang en
```

## Options importantes

- `--limit N` : traite seulement N pages.
- `--start N` : commence à l’index N du manifest.
- `--force` : retraite les pages déjà présentes dans le cache.
- `--refine-crops` : plus lent, teste plus de variantes EasyOCR.
- `--fallback suspects` : relit seulement les blocs suspects.
- `--include-optional-ocr` : autorise Tesseract/PaddleOCR si installés.
- `--ocr-only` : ne traduit pas, utile pour diagnostiquer l’OCR.

## Sorties

Le dossier `--out` contient :

```text
mangatrad_corpus_project.json
mangatrad_corpus_progress.json
analysis/
  mangatrad_review_blocks.csv
  mangatrad_review_blocks.jsonl
  mangatrad_quality_report.md
  mangatrad_learning_report.json
  mangatrad_glossary_suggestions.txt
```

## Performance

Par défaut, le traitement est volontairement conservateur : pas de crop refinement et pas de fallback OCR lourd. Sur 1000 pages, lancer d’abord un test avec `--limit 30`, puis augmenter.

## Échantillon de test représentatif

Depuis `0.4.0`, `--limit` utilise par défaut `--limit-mode stratified`. Cela évite le problème observé avec le premier test de 30 pages : les 30 pages venaient toutes de la première série du manifest.

Commandes recommandées :

```powershell
python -m cbz_manga_translator.corpus_process `
  --corpus C:\temp\mangatrad_corpus `
  --out C:\temp\mangatrad_corpus_run_30_stratified `
  --source-lang en `
  --limit 30 `
  --limit-mode stratified `
  --force
```

Pour reproduire l'ancien comportement, utiliser explicitement :

```powershell
--limit-mode first
```

Pour un tirage aléatoire reproductible :

```powershell
--limit-mode random --seed 47
```

## Nouveau lot après une première review

Pour continuer la review sans retomber sur les pages déjà corrigées, préférer un tirage aléatoire avec une nouvelle seed :

```powershell
python -m cbz_manga_translator.corpus_process `
  --corpus C:\temp\mangatrad_corpus `
  --out C:\temp\mangatrad_corpus_run_30_random_YYYYMMDD `
  --source-lang en `
  --limit 30 `
  --limit-mode random `
  --seed YYYYMMDD `
  --force
```

`--limit-mode stratified` reste utile pour un premier échantillon équilibré, mais il peut reprendre les mêmes premières pages par série d'un lot à l'autre. Pour un deuxième lot ou les suivants, `random` avec une seed datée est le choix le plus pratique.

## Lecture du rapport

Le CSV exporté contient maintenant `series_label` et `volume_label`. Le rapport Markdown contient aussi :

- les raisons de risque les plus fréquentes ;
- la distribution des blocs par série ;
- les exemples à risque élevé.

Cela permet de vérifier rapidement qu'un test de 30 ou 50 pages couvre bien plusieurs séries, au lieu de sur-optimiser le QC sur un seul tome.


## Corpus sans manifest

Depuis `0.4.1`, `corpus_process` peut aussi traiter un dossier qui ne contient que des images extraites sous `pages/`.

Le manifest généré par `corpus_sample` reste préférable, car il conserve le tome source et les métadonnées exactes. Mais si seuls les fichiers images ont été copiés, le processeur reconstruit un manifest minimal depuis l’arborescence :

```text
pages/<serie>/<tome>/sample_xxx__page_yyyy.jpg
```

Dans ce mode de secours, les champs source CBZ/page originale peuvent être incomplets.


## Diagnostic corpus

Si `corpus_process` indique qu'aucun manifest ou aucune image n'est trouvé, utilise :

```powershell
python -m cbz_manga_translator.corpus_inspect C:\temp\mangatrad_corpus --count
```

La commande affiche :

- si le chemin existe ;
- les entrées directes du dossier ;
- le nombre d'images sous le dossier et sous `pages/` ;
- le manifest trouvé, si présent ;
- les candidats corpus proches détectés sous le dossier parent.

Depuis `0.4.2`, `--corpus` peut aussi pointer directement vers `manifest.jsonl` ou `manifest.csv`.
