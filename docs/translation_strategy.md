# Stratégie de traduction

## Contraintes

- Gratuit/local.
- Pas de Hugging Face.
- Pas d’API payante.
- EN→FR et JP→FR.
- Correction humaine assumée.

## Backend actuel

MangaTrad utilise Argos Translate avec des packages locaux `.argosmodel`.

Paires recommandées :

```text
en -> fr
ja -> fr direct si disponible
ou ja -> en + en -> fr
```

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

## Limite assumée

Argos est local et simple à contrôler, mais la qualité peut rester moyenne sur dialogue manga, anglais dialectal et japonais contextuel. La correction humaine reste nécessaire.
