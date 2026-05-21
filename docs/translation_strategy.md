# Stratégie de traduction

## Contraintes

- Gratuit/local.
- Léger autant que possible.
- EN→FR et JP→FR.
- Correction humaine assumée.

## Backend actuel

Helsinki-NLP/OPUS-MT est utilisé parce qu'il est léger et spécialisé traduction.

Modèles :

```text
Helsinki-NLP/opus-mt-en-fr
Helsinki-NLP/opus-mt-ja-fr
```

Limite : Helsinki est faible sur dialogues courts, argot, OCR bruité et contexte manga.

## Pré-traitement indispensable

Avant traduction EN→FR, le texte passe par une normalisation :

```text
ya → you
ah → I selon contexte
ain't → haven't/isn't/aren't selon contexte
climbin' → climbing
gramma → grandma
looky → look at
```

Certaines expressions sont traduites localement quand le résultat est déterministe :

```text
Aww → Aww...
okay → OK.
please unhook this → Décroche ça, s'il te plaît.
```

## Serveur local

Le serveur HTTP local garde les modèles chargés et évite de les recharger depuis la GUI. Il reste local par défaut : `127.0.0.1`.

## Prochaines améliorations

- Interface de backend traducteur interchangeable.
- Comparaison Helsinki / NLLB / M2M100, tous locaux.
- Traduction avec contexte page.
- Post-correction locale optionnelle.
- Mémorisation des choix de traduction dans le glossaire projet.
