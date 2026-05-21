# Échantillonnage de corpus

## Objectif

Pour améliorer réellement l'OCR, le glossaire et le quality check, il faut un corpus représentatif, pas trois captures isolées.

Le script `corpus_sample` prend maintenant une liste mixte de **dossiers de séries** et/ou de fichiers CBZ/ZIP. Il sélectionne quelques tomes par série, puis extrait 20 à 30 pages par tome dans un dossier dédié, avec manifestes CSV/JSONL.

## Préparer la liste

Créer un fichier `volumes.txt`.

Cas recommandé : une ligne = un dossier de série contenant des tomes CBZ/ZIP :

```text
\\192.168.1.30\sda1\lectures\mangas\romance\Serie A
\\192.168.1.30\sda1\lectures\mangas\action\Serie B
D:\Mangas\Serie C
```

Les fichiers directs sont aussi acceptés :

```text
D:\Mangas\SerieA\Tome 01.cbz
D:\Mangas\SerieB\Tome 04.cbz
```

Les lignes vides et les lignes commençant par `#` sont ignorées.

## Commande recommandée pour dossiers de séries

```powershell
cd C:\temp\MangaTrad_v0_2_0
.\.venv\Scripts\Activate.ps1

python -m cbz_manga_translator.corpus_sample `
  --input C:\temp\volumes.txt `
  --out C:\temp\mangatrad_corpus `
  --volumes-per-series 2 `
  --pages-per-volume 25 `
  --series-mode mixed `
  --mode mixed `
  --seed 47 `
  --overwrite
```

Ne mets pas `--require-distinct-parent` si tu veux prendre plusieurs tomes d'une même série. Cette option est un mode strict hérité qui sert seulement à bloquer plusieurs fichiers venant du même dossier.

## Si la liste contient des dossiers parents

Si une ligne pointe vers un dossier qui contient des sous-dossiers de séries, utilise `--recursive` :

```powershell
python -m cbz_manga_translator.corpus_sample `
  --input C:\temp\volumes.txt `
  --out C:\temp\mangatrad_corpus `
  --recursive `
  --volumes-per-series 2 `
  --pages-per-volume 25 `
  --overwrite
```

Dans ce mode, chaque dossier parent contenant des CBZ/ZIP devient une série.

## Sélection des tomes par série

- `--volumes-per-series 1` : un tome par série.
- `--volumes-per-series 2` : recommandé pour commencer.
- `--volumes-per-series 3` : meilleur corpus, plus lourd.

Modes :

- `--series-mode mixed` : recommandé, prend début/fin + diversité.
- `--series-mode random` : tirage aléatoire déterministe avec `--seed`.
- `--series-mode first` : premiers tomes.
- `--series-mode last` : derniers tomes.

## Sélection des pages

- `mixed` : recommandé. Échantillonnage réparti dans le tome avec un peu d'aléatoire.
- `stratified` : pages régulièrement réparties.
- `random` : tirage purement aléatoire.

Par défaut, le script ignore les 2 premières pages et la dernière page pour éviter couvertures, crédits et pages vides.

## Sortie

Le dossier de sortie contient :

```text
mangatrad_corpus/
  pages/
    001_Serie_A_<hash>/
      001_Serie_A_Tome_01_<hash>/
        sample_001__page_0003.jpg
        ...
  manifest.csv
  manifest.jsonl
  sample_report.md
```

Le manifest contient maintenant `series_path`, `series_label`, `series_volume_number`, `series_volume_count`, `source_path`, `source_page_number`, `output_relpath`, etc.

## Après extraction

1. Utiliser ce corpus pour faire tourner OCR/traduction sur des pages variées.
2. Exporter les résultats via `Exporter analyse`.
3. Comparer les erreurs récurrentes.
4. Construire :
   - corrections OCR ;
   - glossaire projet/global ;
   - quality check ;
   - règles locales de traduction.

Le script ne modifie jamais les CBZ originaux.


## Étape suivante : OCR + traduction du corpus

L’échantillonnage extrait seulement les pages. Il ne lance pas OCR/traduction.

Test rapide sur 30 pages :

```powershell
python -m cbz_manga_translator.corpus_process `
  --corpus C:\temp\mangatrad_corpus `
  --out C:\temp\mangatrad_corpus_run `
  --source-lang en `
  --limit 30
```

Traitement complet :

```powershell
python -m cbz_manga_translator.corpus_process `
  --corpus C:\temp\mangatrad_corpus `
  --out C:\temp\mangatrad_corpus_run `
  --source-lang en
```

Options OCR lourdes à activer seulement sur un sous-échantillon :

```powershell
--fallback suspects --include-optional-ocr
```

Éviter `--fallback all` sur 1000 pages tant que les temps par moteur ne sont pas stabilisés.
