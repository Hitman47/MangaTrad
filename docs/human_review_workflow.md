# Workflow de correction humaine

## Objectif

Construire une base fiable de 100 à 200 blocs corrigés/validés pour améliorer le dictionnaire, le quality check et les règles OCR/traduction sans fine-tuning lourd.

## Format de correction

Le fichier éditable est maintenant un **TSV UTF-8** :

```text
mangatrad_human_review_pack.tsv
```

Le séparateur est la **tabulation**, pas la virgule. Les titres, noms de séries, OCR et traductions peuvent donc contenir des virgules sans casser les colonnes dans Excel/LibreOffice.

Les anciens packs `.csv` restent lisibles par `corpus_apply_review`, mais ils ne sont plus le format recommandé.

## 1. Générer un pack de correction

À partir d'un dossier `analysis/` contenant `mangatrad_review_blocks.csv` :

```powershell
python -m cbz_manga_translator.corpus_review_pack `
  --analysis C:\temp\mangatrad_corpus_run_30_stratified_v043\analysis `
  --out C:\temp\mangatrad_human_review_pack `
  --max-blocks 200
```

Le script génère :

```text
mangatrad_human_review_pack.tsv
mangatrad_human_review_pack.jsonl
mangatrad_human_review_guide.md
```

## 2. Corriger le TSV

Ouvrir `mangatrad_human_review_pack.tsv` dans Excel, LibreOffice ou un éditeur texte/tableur.

Ne modifier que :

- `review_decision`
- `corrected_ocr`
- `corrected_source`
- `corrected_fr`
- `review_notes`

Décisions acceptées :

```text
validate
correct
review
ignore
sfx
```

## 3. Réinjecter les corrections

```powershell
python -m cbz_manga_translator.corpus_apply_review `
  --project C:\temp\mangatrad_corpus_run_30_stratified_v043\mangatrad_corpus_project.json `
  --review C:\temp\mangatrad_human_review_pack\mangatrad_human_review_pack.tsv `
  --out-project C:\temp\mangatrad_corpus_run_30_stratified_v043\mangatrad_corpus_project.reviewed.json
```

## 4. Réexporter l'analyse et apprendre

```powershell
python -m cbz_manga_translator.analysis_export `
  --project C:\temp\mangatrad_corpus_run_30_stratified_v043\mangatrad_corpus_project.reviewed.json `
  --out C:\temp\mangatrad_corpus_run_30_stratified_v043\analysis_reviewed

python -m cbz_manga_translator.corpus_learn `
  --analysis C:\temp\mangatrad_corpus_run_30_stratified_v043\analysis_reviewed `
  --out C:\temp\mangatrad_learned_profile_reviewed
```

## Règle pratique

Corriger 100 à 200 blocs suffit pour un premier apprentissage utile. Corriger 1000 blocs d'un coup est moins efficace : mieux vaut itérer.
