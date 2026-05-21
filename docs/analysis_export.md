# Export analyse / apprentissage léger

## Objectif

L’OCR et la traduction doivent être évalués sur plusieurs dizaines de pages, pas seulement sur une capture isolée. L’export analyse produit un corpus local que l’on peut comparer, filtrer et corriger.

## Fichiers exportés

Le bouton `Exporter analyse` et la commande CLI produisent :

```text
mangatrad_review_blocks.csv
mangatrad_review_blocks.jsonl
mangatrad_quality_report.md
mangatrad_learning_report.json
mangatrad_glossary_suggestions.txt
```

## CSV de revue

Chaque ligne correspond à un bloc OCR/traduction. Colonnes importantes :

```text
page_number
image_name
block_id
reading_order
bbox
confidence
manual_status
risk_score
suggested_action
risk_reasons
quality_warnings
ocr_text
ocr_corrected_text
normalized_source_text
source_for_review
raw_translation_fr
translation_fr
ocr_alternatives_count
ocr_alternatives
```

Le CSV est écrit en `utf-8-sig` pour être plus simple à ouvrir sous Excel/LibreOffice Windows.

## Apprentissage léger

Ce n’est pas un fine-tuning de modèle. Le projet utilise pour l’instant un apprentissage local léger et transparent :

- mémoire de traductions exactes à partir de blocs `validé` / `corrigé` ;
- mémoire de corrections OCR quand `OCR brut` diffère de `OCR corrigé` ;
- extraction de candidats glossaire ;
- scoring local de risque qualité.

C’est volontaire : pas de GPU training, pas de dépendance cloud, pas de modèle opaque.

## Commande CLI

```powershell
python -m cbz_manga_translator.analysis_export --project C:\chemin\manga.cbz.manga_translate_project.json --out C:\temp\mangatrad_analysis
```

## Utilisation recommandée

1. OCR + traduction sur 20 à 50 pages.
2. Corriger/valider quelques blocs représentatifs.
3. `Exporter analyse`.
4. Examiner `mangatrad_quality_report.md` et le CSV.
5. Utiliser `mangatrad_glossary_suggestions.txt` pour enrichir le glossaire projet.
6. Envoyer le CSV/JSONL si une analyse externe est nécessaire.
