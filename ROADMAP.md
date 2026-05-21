# Roadmap

Le projet doit rester guidé par l'objectif final : corriger/remplacer les bulles dans un CBZ traduit, sans dépendance payante.

## Priorité actuelle

Ne pas passer directement à l'export CBZ traduit. La qualité OCR/traduction et la correction humaine doivent d'abord être stabilisées.

## V2.0 — Stabilisation repository / architecture

- Nettoyer les responsabilités entre GUI, OCR, traduction, cache et export.
- Stabiliser les schémas JSON du cache projet.
- Ajouter une documentation de développement maintenue.
- Réduire les effets de bord dans la GUI.
- Garder des tests unitaires rapides sans dépendances ML lourdes.

## V2.1 — OCR comparable et sélectionnable

- Sélection du moteur OCR dans l'interface : EasyOCR, Tesseract, PaddleOCR si installés.
- Comparaison visible des résultats OCR par bloc.
- Meilleur scoring des alternatives OCR.
- Application manuelle ou semi-automatique des meilleures alternatives.
- Amélioration des crops pour bulles inclinées, lettres épaisses et majuscules comics.

## V2.2 — Traducteurs interchangeables

- Garder Helsinki comme backend léger par défaut.
- Ajouter une interface de backend pour tester NLLB/M2M100 localement, sans les imposer.
- Comparer traductions par bloc.
- Ajouter un mode traduction avec contexte page, tout en gardant le mapping bloc par bloc.

## V2.3 — Édition avancée des blocs

- Sélection directe des bbox sur l'image.
- Création/suppression manuelle de blocs.
- Redimensionnement manuel d'une bbox.
- Fusion/séparation à la souris.
- Correction plus fiable de l'ordre de lecture.

## V2.4 — Overlay de traduction

- Afficher la traduction française dans la bbox sans modifier l'image source.
- Taille de police automatique.
- Retours ligne automatiques.
- Alignement, marges, style et contraste configurables.
- Prévisualisation avant export.

## V2.5 — Export image / CBZ traduit

- Effacement du texte original dans les bulles simples.
- Réécriture du texte français.
- Export des pages modifiées.
- Recréation d'un CBZ traduit.
- Conservation stricte de l'original.

## Hors périmètre immédiat

- Scanlation parfaitement automatique sans correction humaine.
- Inpainting avancé sur fonds complexes.
- Traduction haute qualité JP→FR littéraire avec un modèle ultra-léger.
- Hébergement public d'API.
