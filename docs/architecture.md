# Architecture

## Objectif

Le projet doit rester modulaire pour pouvoir remplacer progressivement les briques faibles : OCR, traduction, quality check, puis rendu dans les bulles.

## Organisation actuelle

```text
src/cbz_manga_translator/
  app.py                         GUI PySide6
  main.py                        CLI légère + lancement GUI
  server.py                      serveur local Argos HTTP optionnel
  core/
    cbz_reader.py                lecture CBZ/ZIP et tri naturel
    cache.py                     sauvegarde/chargement du cache JSON
    models.py                    modèles ProjectData/PageRecord/OcrBlock
    editing.py                   statuts, fusion/séparation, ordre, validation
  ocr/
    easyocr_engine.py            OCR primaire
    fallback_engine.py           fallback OCR local
    candidates.py                scoring/candidats OCR
    tesseract_engine.py          backend optionnel
    paddleocr_engine.py          backend optionnel
  translate/
    argos.py                     backend Argos local
    helsinki.py                  alias de compatibilité vers Argos
    local_server_client.py       client du serveur local
    english_dialogue_normalizer.py
    builtin_glossary.py
    quality.py
  export/
    html_export.py
```

## Principes

- Le cache JSON est la source de vérité d'un travail de correction.
- Les images originales du CBZ ne sont jamais modifiées dans la V1.
- Les blocs OCR doivent garder leurs `bbox`, car elles serviront aux overlays puis au remplacement de bulles.
- Les backends lourds sont importés paresseusement pour que les tests et la CLI restent rapides.
- Les moteurs optionnels ne doivent jamais casser l'application s'ils sont absents.

## Modèle de bloc

Chaque bloc doit conserver au minimum :

```text
bbox
source_lang
ocr_text
ocr_corrected_text
normalized_source_text
raw_translation_fr
translation_fr
confidence
reading_order
manual_status
quality_warnings
ocr_alternatives
```

Cette séparation est volontaire. Elle permet de diagnostiquer où l'erreur apparaît : OCR, correction OCR, normalisation, traduction brute ou traduction finale.
