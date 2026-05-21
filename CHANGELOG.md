# Changelog

Toutes les modifications notables du prototype sont résumées ici.

## 0.1.9

- Ajout d'une correction structurelle OCR : utilisation d'une alternative OCR, fusion de blocs, séparation de bloc, déplacement de l'ordre de lecture.
- Les champs générés en aval sont invalidés proprement après correction OCR.
- Objectif : préparer un workflow de correction humaine stable avant l'overlay dans les bulles.

## 0.1.8

- Ajout du fallback OCR local.
- Ajout d'alternatives OCR par bloc dans le cache JSON.
- Ajout de corrections OCR locales fréquentes : `Inhook/Lnhook/lhook → unhook`, `toid → told`, etc.
- Ajout de backends optionnels Tesseract/PaddleOCR, non bloquants si absents.

## 0.1.7

- Ajout d'overrides locaux pour les interjections et expressions simples que Helsinki traduit mal.
- Meilleure normalisation des dialogues anglais oralisés.
- Protection supplémentaire de noms comme `Miwa` / `Miwa-nee`.

## 0.1.6

- Ajout d'un serveur local Helsinki HTTP.
- Refonte de l'interface : liste compacte + panneau détail au lieu d'un tableau illisible.
- Ajout d'un glossaire projet persistant sauvegardé dans le cache JSON.

## 0.1.5

- Ajout d'une boucle de correction humaine : statuts `brut`, `corrigé`, `validé`, `à revoir`, `ignoré`.
- Ajout de validation, marquage à revoir, ignorance et retraduction de sélection.
- Sauvegarde automatique après correction ou changement de statut.

## 0.1.4

- Ajout du diagnostic visible : OCR brut, OCR corrigé, texte normalisé, traduction brute, traduction finale.
- Extraction de la normalisation anglaise dans un module dédié.
- Ajout de l'OCR multi-variantes sur les crops.

## 0.1.3

- Ajout d'un quality check local après OCR/traduction.
- Ajout d'un dictionnaire manga intégré.
- Détection de traductions suspectes : résidus anglais, OCR basse confiance, fragments absurdes, français peu naturel.

## 0.1.2

- Ajout de normalisations d'anglais familier : `ya`, `ah`, `doin'`, `climbin'`, `ain't`, etc.
- Ajout d'un champ de glossaire simple pour noms propres et corrections.

## 0.1.1

- Ajout du support CUDA côté EasyOCR/Helsinki quand PyTorch détecte CUDA.
- Centrage de la page dans la zone d'affichage.
- Ajout de fusion de lignes, filtrage bruit et seuil de confiance.

## 0.1.0

- Prototype initial : lecture CBZ, affichage page, EasyOCR local, traduction Helsinki EN→FR/JP→FR, cache JSON, export HTML.
