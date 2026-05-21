# Exécution locale

## Politique

MangaTrad n’utilise plus Hugging Face pour la traduction.

- OCR : EasyOCR local, avec PyTorch CPU/CUDA.
- Traduction : Argos Translate local, via packages `.argosmodel` installés sur la machine.
- Serveur HTTP : optionnel, bindé par défaut sur `127.0.0.1`.

## Modèles requis

Argos ne télécharge pas de modèle implicitement pendant une traduction. Installe les packages nécessaires explicitement :

```powershell
python -m cbz_manga_translator.argos_models --bootstrap-basic
python -m cbz_manga_translator.argos_models --list
```

Alternative par paires explicites :

```powershell
python -m cbz_manga_translator.argos_models --install-index en:fr ja:en
```

Alternative avec fichiers locaux `.argosmodel` déjà téléchargés :

```powershell
python -m cbz_manga_translator.argos_models --install C:\models\translate-en_fr.argosmodel C:\models\translate-ja_en.argosmodel
```

Pour JP→FR, MangaTrad utilise le direct `ja->fr` si installé, sinon le pivot `ja->en->fr` si les deux paires existent.

## Vérification locale

Le bouton `Vérifier local` vérifie les imports locaux, CUDA et les paires Argos installées. Il ne contacte ni registre de modèles ni service externe.

## Serveur Argos

Le serveur local garde le moteur en processus séparé :

```powershell
python -m cbz_manga_translator.server --host 127.0.0.1 --port 8765 --gpu --preload en ja
```

Si les packages Argos nécessaires ne sont pas installés, le préchargement échoue avec un message explicite.


## OCR local renforcé

`Relire OCR suspects` relance le fallback local uniquement sur les blocs déjà suspects.

`Relire OCR tous` relance le fallback local sur tous les blocs de la page. C’est plus lent, mais utile quand une page entière contient des textes lisibles mais mal reconnus par EasyOCR.

Le fallback reste local : corrections déterministes, variantes de crops EasyOCR, Tesseract/PaddleOCR uniquement s’ils sont installés localement.


## OCR optionnels

EasyOCR est le moteur par défaut. Tesseract et PaddleOCR sont uniquement des fallbacks locaux.

Commandes rapides :

```powershell
python -m cbz_manga_translator.ocr_setup --commands
python -m cbz_manga_translator.ocr_setup --check
```

Documentation détaillée : `docs/ocr_backends_install.md`.

## Logs

Les logs sont écrits dans :

```text
logs/mangatrad.log
logs/mangatrad_fatal.log
```

En cas de crash sans message dans l'interface, consulter d'abord `mangatrad_fatal.log`, puis `mangatrad.log`.
