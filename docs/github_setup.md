# Mise en place GitHub

## Nettoyer le dossier avant commit

Les ZIP de travail peuvent contenir des fichiers générés : `__pycache__`, `.egg-info`, `.pytest_cache`, etc. Ils ne doivent pas être versionnés.

Windows :

```powershell
.\scripts\clean_repo.ps1
```

Linux/Fedora :

```bash
./scripts/clean_repo.sh
```

## Initialiser le dépôt

```powershell
git init
git add .
git status
git commit -m "Initial CBZ manga translator prototype"
git branch -M main
```

## Créer le repo GitHub

Créer un repository vide côté GitHub, sans README/license/gitignore générés automatiquement, puis :

```powershell
git remote add origin https://github.com/<USER>/<REPO>.git
git push -u origin main
```

## Branches recommandées

```text
main    version stable testée
dev     intégration des prochaines versions
feature/<sujet> pour les gros changements
```

Exemples :

```powershell
git checkout -b dev
git push -u origin dev

git checkout -b feature/overlay-preview
```

## Tags recommandés

```powershell
git tag v0.1.9
git push origin v0.1.9
```

## À ne pas commiter

- `.venv/`
- `__pycache__/`
- `*.egg-info/`
- fichiers CBZ/CBR/ZIP de mangas
- caches `.manga_translate_project.json`
- exports HTML générés
- caches Hugging Face/EasyOCR si redirigés dans le projet
