# Pipeline OCR / traduction / correction

## Pipeline cible

```text
CBZ
→ extraction page
→ détection OCR primaire
→ post-traitement OCR
→ fallback OCR local si suspect
→ correction humaine éventuelle
→ normalisation dialogue
→ protection glossaire
→ traduction brute
→ post-correction locale
→ quality check
→ validation humaine
→ export HTML / overlay / CBZ traduit
```

## Étapes actuelles

### 1. Lecture CBZ

`CbzReader` lit les fichiers images supportés et les trie naturellement.

### 2. OCR primaire

`EasyOcrEngine` extrait des blocs avec `bbox`, texte et confiance.

Options importantes :

- fusion de lignes ;
- filtrage du bruit ;
- seuil de confiance ;
- OCR multi-variantes.

### 3. Fallback OCR

`OcrFallbackEngine` collecte des alternatives pour les blocs suspects :

- OCR courant ;
- corrections OCR locales ;
- relecture EasyOCR sur crops ;
- Tesseract si disponible ;
- PaddleOCR si disponible.

Les alternatives sont stockées dans `ocr_alternatives`.

### 4. Normalisation

`EnglishDialogueNormalizer` corrige les dialogues anglais oralisés ou bruités avant traduction.

Exemples :

```text
AIN'T AH TOID YA → haven't I told you
CLIMBIN' → climbing
GRAMMA, LOOKY THAT → grandma, look at that
Inhook → unhook
```

### 5. Traduction

`HelsinkiTranslator` utilise Helsinki-NLP localement. Pour certains cas déterministes, une traduction locale est préférée à Helsinki.

### 6. Quality check

`TranslationQualityChecker` signale les blocs probablement faux. Il ne remplace pas une validation humaine.

### 7. Correction humaine

La GUI permet de modifier les champs, appliquer des alternatives OCR, fusionner/séparer les blocs et valider le résultat.
