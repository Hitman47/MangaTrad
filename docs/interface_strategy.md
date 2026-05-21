# Stratégie interface

## Problème

Le projet produit beaucoup d'informations par bloc : OCR brut, correction OCR, texte normalisé, traduction brute, traduction finale, QC, alternatives OCR et statut manuel. Un tableau complet devient rapidement illisible.

## Décision V2.0

L'interface doit distinguer :

- une liste compacte de blocs ;
- un panneau détail lisible ;
- des filtres de workflow ;
- une recherche textuelle ;
- des résumés page/projet.

## Filtres de blocs

Les filtres n'écrivent jamais dans le cache. Ils servent seulement à réduire le bruit visuel :

- tous les blocs ;
- QC uniquement ;
- à revoir ;
- sans traduction ;
- non validés ;
- validés ;
- ignorés.

## Recherche

La recherche inspecte :

- OCR brut ;
- OCR corrigé ;
- texte normalisé ;
- traduction brute ;
- traduction finale ;
- warnings QC.

## Principe pour la suite

Chaque nouvelle fonction doit éviter d'ajouter des colonnes au tableau principal. Les données longues doivent aller dans le panneau détail ou dans des panneaux spécialisés.


## V0.2.1 — Ajustements de lisibilité

- Éviter les rangées de boutons horizontales trop longues : les actions de bloc passent en grille.
- Garder le détail de bloc dans une zone scrollable pour éviter les contrôles coupés.
- Rendre les libellés d’exécution explicites : OCR local, traduction locale, diagnostic local.
- Augmenter la taille de police et les espacements par défaut.

## Décision 0.3.2 — interface à onglets

Le glossaire ne doit plus occuper le haut de la fenêtre. Les grands panneaux sont séparés en onglets :

- `Blocs` : liste filtrable/recherchable des blocs OCR ;
- `Détail / correction` : champs OCR/traduction empilés verticalement dans une zone défilable ;
- `Glossaire` : règles projet persistantes ;
- `Local` : rappel du fonctionnement local/offline.

Cette structure évite de compresser l’image, la table et les champs de correction dans le même espace vertical. Les zones longues doivent toujours avoir une scrollbar explicite.


## Actions OCR

Les actions OCR doivent rester explicites :

- `OCR local page` : première reconnaissance.
- `Relire OCR suspects` : fallback rapide sur les blocs problématiques.
- `Relire OCR tous` : fallback profond sur toute la page, à utiliser quand la qualité OCR globale est mauvaise.
