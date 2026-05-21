# Roadmap

Objectif final : corriger/remplacer les bulles dans un CBZ traduit, sans API payante et sans dépendance Hugging Face.

## Priorité actuelle

- Construire un corpus représentatif via `corpus_sample` pour objectiver les erreurs OCR/traduction sur plusieurs tomes.

Stabiliser la qualité OCR et la correction humaine avant de passer à l’export CBZ traduit.

## V0.3.x — Argos local

- Stabiliser l’installation des packages `.argosmodel`.
- Ajouter une aide GUI indiquant les paires Argos installées.
- Afficher clairement si `en->fr`, `ja->fr` ou `ja->en->fr` sont disponibles.

## V2.1a — Export analyse et apprentissage léger

- Export CSV/JSONL de tous les blocs OCR/traduction.
- Rapport qualité pour repérer les erreurs répétées.
- Mémoire locale de traductions validées et corrections OCR.
- Suggestions glossaire générées depuis les corrections humaines.

## V2.1 — OCR comparable et sélectionnable

- Sélection du moteur OCR dans l’interface : EasyOCR, Tesseract, PaddleOCR si installés.
- Comparaison visible des résultats OCR par bloc.
- Meilleur scoring des alternatives OCR.
- Application manuelle ou semi-automatique des meilleures alternatives.

## V2.2 — Traducteurs locaux interchangeables

- Garder Argos comme backend offline par défaut.
- Prévoir d’autres backends locaux non-Hugging-Face si nécessaire.
- Comparer traductions par bloc sans perdre le mapping bloc par bloc.

## V2.3 — Édition avancée des blocs

- Sélection directe des bbox sur l’image.
- Création/suppression manuelle de blocs.
- Redimensionnement manuel d’une bbox.
- Correction plus fiable de l’ordre de lecture.

## V2.4 — Overlay de traduction

- Afficher la traduction française dans la bbox sans modifier l’image source.
- Taille de police automatique.
- Retours ligne automatiques.
- Prévisualisation avant export.

## V2.5 — Export image / CBZ traduit

- Effacement du texte original dans les bulles simples.
- Réécriture du texte français.
- Export des pages modifiées.
- Recréation d’un CBZ traduit.
- Conservation stricte de l’original.
