# Politique Docker

## Décision

Docker n'est pas le mode principal pour la GUI. L'application desktop doit rester lancée en Python natif.

## Pourquoi

La GUI PySide6 dans Docker complique inutilement :

- affichage graphique ;
- accès aux fichiers Windows ;
- CUDA/GPU ;
- OpenGL/Qt ;
- polices ;
- montage de dossiers.

## Usages acceptés de Docker

Docker sert à :

1. lancer les tests dans un environnement propre ;
2. reproduire des validations CI ;
3. héberger plus tard un serveur local OCR/traduction sans GUI.

## Commandes actuelles

```bash
docker build -t cbz-manga-translator-proto:local .
docker run --rm cbz-manga-translator-proto:local pytest -q
docker run --rm cbz-manga-translator-proto:local python -m cbz_manga_translator.main --version
```

## Futur possible

Un futur `docker compose` pourrait lancer seulement un serveur local :

```text
GUI Python Windows native
→ serveur local OCR/traduction Docker
→ modèles gardés chargés
```

Ce n'est pas prioritaire tant que la qualité OCR/traduction et l'édition humaine ne sont pas stabilisées.
