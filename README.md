# CBZ Manga Translator

Version actuelle : `0.1.9`.

Prototype gratuit/local pour charger un CBZ de manga, faire de l'OCR local, traduire des bulles EN→FR ou JP→FR, corriger les résultats dans une interface PySide6 et sauvegarder un cache JSON structuré. Le but final reste l'édition des bulles dans l'image puis l'export d'un CBZ traduit.

## État du projet

Le projet est encore un prototype. Il est utilisable pour tester la chaîne suivante :

```text
CBZ → pages images → OCR local → corrections OCR → normalisation dialogue → traduction FR → quality check → correction humaine → export HTML
```

Ce qu'il sait déjà faire :

- ouvrir un `.cbz` ou `.zip` contenant des images ;
- afficher les pages dans une GUI PySide6 ;
- lancer EasyOCR en local, CPU ou CUDA si PyTorch GPU est installé ;
- relire les blocs OCR suspects avec des variantes de crop et des moteurs optionnels ;
- traduire EN→FR et JP→FR avec Helsinki-NLP via Transformers ;
- utiliser un serveur local Helsinki optionnel pour garder les modèles chargés ;
- préserver `bbox`, ordre de lecture, statut manuel, warnings QC et alternatives OCR dans le cache JSON ;
- éditer OCR brut, OCR corrigé, texte normalisé et traduction finale ;
- fusionner/séparer des blocs, corriger l'ordre de lecture et valider/ignorer des blocs ;
- exporter une lecture HTML avec image à gauche et traduction à droite.

Ce qu'il ne fait pas encore correctement :

- remplacement propre du texte dans les bulles ;
- inpainting/nettoyage du texte original ;
- export CBZ traduit ;
- détection robuste de toutes les bulles et textes stylisés ;
- traduction fiable de dialogues manga sans correction humaine.

## Gratuité / local

Aucune API payante n'est utilisée. Les dépendances principales sont gratuites/open-source :

- PySide6 pour la GUI ;
- EasyOCR pour l'OCR local ;
- Transformers + Helsinki-NLP pour la traduction ;
- PyTorch comme backend ML.

Après le premier téléchargement/cache des modèles, l'exécution peut rester locale. Le serveur local Helsinki expose seulement `127.0.0.1` par défaut.

## Installation Windows

Depuis PowerShell, dans le dossier du projet :

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -e .
```

Lancer la GUI :

```powershell
python -m cbz_manga_translator.main
```

Tester la CLI :

```powershell
python -m cbz_manga_translator.main --version
python -m cbz_manga_translator.main --inspect C:\chemin\manga.cbz
```

## Installation PyTorch CUDA

Si tu veux utiliser une RTX/NVIDIA, installe une build PyTorch CUDA dans le `.venv`. Exemple avec CUDA 12.8 :

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip uninstall -y torch torchvision torchaudio
python -m pip cache purge
python -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128
python -c "import torch; print('torch:', torch.__version__); print('cuda:', torch.cuda.is_available()); print('gpu:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU only')"
```

Ne relance pas `pip install -r requirements.txt` après une installation CUDA fonctionnelle, sinon pip peut remettre une build CPU selon l'environnement.

## Serveur local Helsinki optionnel

Le serveur garde Helsinki chargé dans un processus séparé. C'est utile quand tu traduis beaucoup de pages ou quand tu relances souvent la GUI.

Terminal 1 :

```powershell
.\.venv\Scripts\Activate.ps1
python -m cbz_manga_translator.server --host 127.0.0.1 --port 8765 --gpu --preload en ja
```

Terminal 2 :

```powershell
.\.venv\Scripts\Activate.ps1
python -m cbz_manga_translator.main
```

Dans l'interface :

1. choisir `Serveur local HTTP` dans `Modèle local` ;
2. garder `http://127.0.0.1:8765` ;
3. cliquer `Tester serveur` ;
4. lancer la traduction.

## Options OCR importantes

- `Fusionner lignes` : regroupe les fragments proches pour éviter les traductions mot à mot.
- `Filtrer bruit` : ignore artefacts, symboles et fragments sous le seuil de confiance.
- `Conf. min` : seuil EasyOCR. `0.20` est volontairement permissif.
- `OCR multi-variantes` : relit les crops avec marge, upscale, contraste et seuillage.
- `Fallback OCR local` : relit les blocs suspects avec corrections locales, EasyOCR crop variants, Tesseract si installé et PaddleOCR si installé.
- `Relire OCR suspects` : applique le fallback sur les blocs marqués par le quality check ou par une confiance faible.

Les moteurs optionnels sont installables via :

```powershell
pip install -r requirements-ocr-extra.txt
```

Pour Tesseract, `pytesseract` ne suffit pas : il faut aussi installer le binaire système Tesseract OCR et les packs de langue nécessaires.

## Options traduction importantes

- `Normaliser EN familier` : transforme des dialogues comme `WHAT YA DOIN'`, `AIN'T AH TOID YA`, `CLIMBIN'`, `GRAMMA`, `LOOKY`, `Inhook` avant traduction.
- `Dico manga intégré` : protège des noms, lieux, repas et termes déjà courants en français.
- `Glossaire projet` : règles propres à un CBZ/série, sauvegardées dans le cache JSON.

Exemple de glossaire :

```text
Naru
NARL=Naru
NARLI=Naru
Miwa-nee
contrail=traînée de condensation
```

## Workflow conseillé

```text
1. Ouvrir le CBZ.
2. Lancer OCR + traduire page.
3. Relire OCR suspects.
4. Choisir une alternative OCR si elle est meilleure.
5. Fusionner/séparer les blocs si la structure est mauvaise.
6. Corriger OCR corrigé ou texte normalisé.
7. Retraduire sélection.
8. Corriger la traduction finale.
9. Valider ou marquer à revoir.
10. Exporter HTML pour lecture.
```

## Tests

Tests locaux complets :

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
pip install -e .
pytest -q
python -m compileall -q src tests
python -m cbz_manga_translator.main --version
python -m cbz_manga_translator.server --help
```

Tests CI légers, sans dépendances ML lourdes :

```powershell
pip install -r requirements-ci.txt
pip install -e . --no-deps
pytest -q
```

## Docker

Docker n'est pas le mode recommandé pour la GUI PySide6. Le projet reste d'abord une application Python native.

Docker sert seulement à :

- tester dans un environnement propre ;
- préparer un futur serveur local OCR/traduction isolé ;
- reproduire des validations CI.

Commandes actuelles :

```bash
docker build -t cbz-manga-translator-proto:local .
docker run --rm cbz-manga-translator-proto:local pytest -q
docker run --rm cbz-manga-translator-proto:local python -m cbz_manga_translator.main --version
```

Voir aussi `docs/docker_policy.md`.

## GitHub

Avant le premier commit, nettoyer les fichiers générés présents dans les ZIP de travail :

```powershell
.\scripts\clean_repo.ps1
```

Puis :

```powershell
git init
git add .
git commit -m "Initial CBZ manga translator prototype"
git branch -M main
git remote add origin https://github.com/<USER>/<REPO>.git
git push -u origin main
```

Détails : `docs/github_setup.md`.

## Documentation projet

- `ROADMAP.md` : suite du plan.
- `CHANGELOG.md` : historique des versions.
- `docs/architecture.md` : structure technique.
- `docs/pipeline.md` : pipeline OCR/traduction/QC.
- `docs/ocr_strategy.md` : stratégie OCR et fallback.
- `docs/translation_strategy.md` : stratégie de traduction.
- `docs/glossary_strategy.md` : glossaires intégrés/projet.
- `docs/docker_policy.md` : rôle exact de Docker.
