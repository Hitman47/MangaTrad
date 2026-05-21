# Stratégie glossaire

## Pourquoi un glossaire

Les noms japonais, lieux, aliments et termes manga sont souvent massacrés par OCR ou traduction. Un glossaire évite de retraduire ou déformer des termes connus.

## Deux niveaux

### Glossaire intégré

Liste prudente de noms, lieux, repas et termes courants. Il doit rester limité pour éviter les faux positifs.

Exemples :

```text
ramen
onigiri
bento
Tokyo
Kyoto
senpai
sensei
Miwa-nee
```

### Glossaire projet

Règles propres au CBZ ou à la série. C'est le plus important.

Exemples :

```text
Naru
NARL=Naru
NARLI=Naru
Miwa-nee
contrail=traînée de condensation
```

## Syntaxe

```text
NomPropre
source=traduction forcée
source=>traduction forcée
```

Séparateurs acceptés : virgule, point-virgule ou nouvelle ligne. Une entrée par ligne est recommandée.

## Prochaines améliorations

- Apprendre depuis les corrections humaines répétées.
- Proposer d'ajouter une correction OCR au glossaire projet.
- Séparer personnages, lieux, OCR corrections et termes de traduction.
- Export/import de glossaire par série.
