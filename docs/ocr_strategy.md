# Stratégie OCR

## Diagnostic

Les captures montrent que le problème principal n'est pas seulement la traduction. Un texte visible peut être lu faux par OCR :

```text
unhook → Inhook
GRAMMA, LOOKY THAT → GRAMMA; THAT;
```

Quand le mot manque ou est mal lu, le traducteur ne peut pas produire une bonne sortie.

## Stratégie actuelle

1. EasyOCR détecte les blocs et les bboxes.
2. Les lignes proches peuvent être fusionnées.
3. Les blocs suspects peuvent être relus via fallback.
4. Les alternatives OCR sont affichées pour sélection humaine.

## Backends

### EasyOCR

Backend primaire. Avantages : simple, local, donne des bounding boxes. Limites : polices comics, majuscules stylisées, japonais vertical/furigana.

### Tesseract optionnel

Utile sur texte imprimé clair, surtout anglais. Nécessite le binaire système Tesseract et les packs de langue.

### PaddleOCR optionnel

Backend alternatif plus lourd. Potentiellement meilleur sur certains crops, mais plus délicat à installer et à maintenir.

### manga-ocr futur

Candidat intéressant pour JP, surtout sur crops déjà localisés. Il ne remplace pas seul la détection des bulles.

## Prochaines améliorations OCR

- Interface de comparaison moteur par moteur.
- Sélection du moteur OCR primaire.
- Bbox éditable à la souris.
- Création/suppression manuelle de blocs.
- Meilleur scoring des alternatives.
- Tests sur pages réelles anonymisées/synthétiques.
