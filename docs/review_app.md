# MangaTrad Reviewer

## Objectif

`review_app` est une application distincte de correction humaine. Elle sert à revoir les blocs générés par `corpus_process` avec le contexte visuel de la page, la bbox, l'OCR, la source, la traduction et les warnings QC.

Elle ne relance pas OCR/traduction. Elle corrige et sauvegarde une copie `*.reviewed.json`.

## Lancement

```powershell
python -m cbz_manga_translator.review_app C:\temp\mangatrad_corpus_run_30_stratified_v043\mangatrad_corpus_project.json
```

Par défaut, la sauvegarde est écrite dans :

```text
mangatrad_corpus_project.reviewed.json
```

## Organisation V0.5.0

L'interface est organisée en trois zones fixes :

1. **File de review** : résumé, filtre, recherche, liste des blocs.
2. **Image** : page complète, bbox sélectionnée en rouge, autres bboxes en gris.
3. **Correction** : contexte, décision, actions explicites, puis champs de correction.

Les champs ne sont plus empilés anonymement. Ils sont organisés par paires :

| À gauche | À droite |
|---|---|
| OCR brut | OCR corrigé |
| Source actuelle | Source corrigée |
| Traduction actuelle | Traduction FR corrigée |
| QC / alternatives OCR | Notes |

Cette organisation limite les erreurs : le texte à analyser est toujours proche du champ à remplir.

## Actions

- `Valider OK (V)` : le bloc est correct, sauvegarde `validate`, puis passe au suivant.
- `Mode correction (C)` : place le focus dans la traduction corrigée, sans sauvegarder.
- `Enregistrer correction + suivant` : sauvegarde les champs corrigés puis passe au suivant.
- `Sauvegarder seulement` : sauvegarde le bloc courant sans changer de sélection.
- `SFX (S)` : marque le bloc comme bruit/onomatopée, sauvegarde puis passe au suivant.
- `Ignorer (I)` : marque un bloc parasite/inutile, sauvegarde puis passe au suivant.
- `À revoir (R)` : marque le bloc pour reprise ultérieure.
- `Précédent` / `Suivant` : navigation explicite, avec confirmation si le bloc courant a des changements non sauvegardés.

Le bouton `SFX` écrit le statut technique `ignored`, mais conserve l'intention via la note `[sfx]`. L'interface le distingue ensuite dans le résumé, la liste et le filtre `SFX`.

## Filtres et recherche

- `À traiter` : blocs encore bruts ou marqués à revoir.
- `Risques HIGH/MED` et `High` : blocs non finalisés avec risque élevé.
- `Corrections faites` : blocs corrigés et sauvegardés.
- `Validés`, `Ignorés`, `SFX`, `À revoir` : vues de contrôle.

La recherche couvre maintenant le texte OCR/source/traduction, l'identifiant du bloc, les warnings QC, les alternatives visibles et les notes reviewer.

## Raccourcis

```text
V              valider OK
C              mode correction, sans sauvegarde immédiate
S              SFX
I              ignorer
R              à revoir
Ctrl+Entrée    enregistrer + suivant
Espace         suivant
Backspace      précédent
Ctrl+S         sauvegarder
```

## Protection contre les pertes

Si tu modifies un champ puis sélectionnes un autre bloc, l'application demande quoi faire :

- sauvegarder ;
- abandonner ;
- annuler le changement de bloc.

La même protection s'applique à la fermeture de la fenêtre.

## Workflow conseillé

1. Lire la bulle dans l'image.
2. Comparer OCR brut et OCR corrigé.
3. Corriger la source si l'anglais est bruité ou mal lu.
4. Corriger la traduction française.
5. Utiliser une action explicite : valider, correction, SFX, ignorer ou à revoir.

## Après review

Si tu as déjà corrigé une partie du corpus et que les règles OCR/traduction ont été améliorées, rafraîchis uniquement les blocs non revus avant de continuer :

```powershell
python -m cbz_manga_translator.review_refresh `
  C:\temp\mangatrad_corpus_run_30_stratified_v043\mangatrad_corpus_project.reviewed.json `
  --out-project C:\temp\mangatrad_corpus_run_30_stratified_v043\mangatrad_corpus_project.reviewed.refreshed.json `
  --source-lang en
```

Cette commande préserve les blocs déjà `validated`, `edited`, `review` ou `ignored`, puis applique les règles déterministes et le QC seulement aux blocs `unchecked`. Elle ne contacte pas le réseau. Pour forcer une retraduction Argos complète des blocs non revus, ajoute `--translate-argos`, mais seulement si l'environnement Argos/Stanza est déjà prêt hors ligne.

Si tu as marqué des blocs en `review` parce que la détection était manifestement mauvaise, ajoute `--include-review` pour les rafraîchir aussi. Les blocs `edited`, `validated`, `ignored` et `sfx` restent protégés.

```powershell
python -m cbz_manga_translator.analysis_export `
  --project C:\temp\...\mangatrad_corpus_project.reviewed.json `
  --out C:\temp\...\analysis_reviewed

python -m cbz_manga_translator.corpus_learn `
  --analysis C:\temp\...\analysis_reviewed `
  --out C:\temp\mangatrad_learned_profile_reviewed
```
